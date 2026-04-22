"""
=====================================================================================
👑 MAIN SEARCH ENGINE
=====================================================================================
STRICT MODE: Only returns highly relevant products with accurate pagination.

HOW PAGINATION WORKS NOW:
  1. Run count query WITH min_score → get REAL count of relevant products
  2. Calculate total_pages based on REAL count
  3. Only show pages that will actually have results
  4. Last page always has actual products (may be partial)

Example:
  - Search "shoes" with min_score=15 → Real count: 487 products
  - Pages shown: 1, 2, 3, 4, 5 (page 5 has 87 products)
  - No garbage pages, no "0 products found" errors
=====================================================================================
"""

import json
import hashlib
import logging
import re

from app.config import os_client, INDEX_NAME, openai_client
from app.models.search import SearchRequest
from app.utils.brand_mapper import get_smart_brand
from app.utils.pagination import build_pagination_html
from app.utils.cache import cache_get, cache_set
from app.nlp.semantic_matrix import extract_semantic_matrix

from app.core.constants import (
    MAX_OS_WINDOW,
    DEFAULT_PAGE_SIZE,
    SMALL_PAGE_SIZE,
    BOOST_NAME_PHRASE,
    BOOST_BRAND_PHRASE,
    BOOST_CATEGORY_MATCH,
    BOOST_CROSS_FIELDS,
    BOOST_FUZZY_FALLBACK,
    ACCESSORY_DEMOTION_WEIGHT,
    KNN_MIN_K,
    KNN_BUFFER,
    SEARCH_CACHE_TTL,
    CACHE_VERSION,
    FACET_CATEGORIES_SIZE,
    MAX_CATEGORY_FILTERS,
    MAX_COLOR_FILTERS,
    MAX_SIZE_FILTERS,
    MAX_BRAND_FILTERS,
    MAX_GENDER_FILTERS,
    AI_EMBEDDING_MODEL,
    DEMO_RATING_BASE,
    DEMO_RATING_RANGE,
    DEMO_SALES_BASE,
    DEMO_SALES_RANGE,
    SCORE_DISPLAY_MIN,
    FACET_MIN_DOC_COUNT,
    SCORE_DISPLAY_RANGE,
)

logger = logging.getLogger(__name__)


# =========================================================================
# 🆕 MINIMUM RELEVANCE THRESHOLD
# =========================================================================
# Products scoring below this are filtered out.
# Tuned based on boost values to keep only meaningful matches.
# =========================================================================
MIN_RELEVANCE_SCORE = 15.0


# =========================================================================
# 👑 MAIN SEARCH FUNCTION
# =========================================================================
async def execute_search(request: SearchRequest) -> dict:
    """Executes a full product search. STRICT MODE: only relevant products."""
    
    # STEP 1: NORMALIZE PAGE SIZE
    request.page_size = DEFAULT_PAGE_SIZE if request.page_size != SMALL_PAGE_SIZE else SMALL_PAGE_SIZE
    
    # STEP 2: CHECK REDIS CACHE
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:ai:{CACHE_VERSION}:{hashlib.md5(request_str.encode()).hexdigest()}"
    
    cached_result = await cache_get(cache_key)
    if cached_result:
        return cached_result
    
    # STEP 3: CALCULATE PAGINATION OFFSET (SAFE)
    max_safe_page = MAX_OS_WINDOW // request.page_size
    
    if request.page > max_safe_page:
        logger.warning(f"⚠️ Page {request.page} exceeds max safe page {max_safe_page}.")
        return {
            "total_results": 0,
            "total_pages": max_safe_page,
            "current_page": request.page,
            "pagination_html": build_pagination_html(max_safe_page, request.page),
            "results": [],
            "facets": {"categories": []}
        }
    
    from_val = (request.page - 1) * request.page_size
    
    # STEP 4: EXTRACT SEMANTIC INFO
    query_text = request.query.strip() if request.query else ""
    matrix = extract_semantic_matrix(query_text)
    core_query = matrix["core_query"]
    
    # STEP 5: HANDLE MULTI-ITEM QUERIES
    if "|" in core_query:
        multi_items = [item.strip() for item in core_query.split("|") if item.strip()]
        core_query_for_vector = " ".join(multi_items)
    else:
        multi_items = [core_query]
        core_query_for_vector = core_query
    
    # STEP 6: GENERATE VECTOR EMBEDDING
    vector = None
    if core_query_for_vector:
        try:
            resp = await openai_client.embeddings.create(
                input=core_query_for_vector,
                model=AI_EMBEDDING_MODEL
            )
            vector = resp.data[0].embedding
        except Exception as e:
            logger.error(f"❌ OpenAI Embedding Failed: {e}")
    
    # STEP 7: BUILD HARD FILTERS
    filters = [{"term": {"in_stock": True}}]
    must_nots = []
    
    if matrix["min_price"] is not None or matrix["max_price"] is not None:
        price_range = {}
        if matrix["min_price"] is not None:
            price_range["gte"] = matrix["min_price"]
        if matrix["max_price"] is not None:
            price_range["lte"] = matrix["max_price"]
        filters.append({"range": {"price": price_range}})
    
    if (matrix["is_sale"] or request.sort == "on_sale" or 
        (request.filters and getattr(request.filters, "on_sale", False))):
        filters.append({"range": {"sale_price": {"gt": 0}}})
    
    if request.filters:
        if getattr(request.filters, "category", None):
            filters.append({
                "terms": {"category": request.filters.category[:MAX_CATEGORY_FILTERS]}
            })
        
        if getattr(request.filters, "in_stock", None) is not None:
            filters.append({"term": {"in_stock": request.filters.in_stock}})
        
        if getattr(request.filters, "color", None):
            color_shoulds = []
            for c in request.filters.color[:MAX_COLOR_FILTERS]:
                color_shoulds.append({
                    "multi_match": {
                        "query": c,
                        "type": "phrase",
                        "fields": ["color", "attributes*", "name"]
                    }
                })
            filters.append({"bool": {"should": color_shoulds, "minimum_should_match": 1}})
        
        if getattr(request.filters, "size", None):
            size_shoulds = []
            for s in request.filters.size[:MAX_SIZE_FILTERS]:
                size_str = str(s).strip()
                safe_size_query = size_str if "size" in size_str.lower() else f"size {size_str} {size_str}"
                size_shoulds.append({
                    "multi_match": {
                        "query": safe_size_query,
                        "fields": ["size", "attributes*", "name"],
                        "type": "best_fields"
                    }
                })
            filters.append({"bool": {"should": size_shoulds, "minimum_should_match": 1}})
        
        if getattr(request.filters, "gender", None):
            gender_shoulds = []
            for g in request.filters.gender[:MAX_GENDER_FILTERS]:
                g_str = str(g).strip()
                gender_shoulds.append({
                    "multi_match": {
                        "query": g_str,
                        "fields": ["gender", "attributes.gender", "attributes.Gender", "category", "name"],
                        "type": "best_fields"
                    }
                })
            filters.append({"bool": {"should": gender_shoulds, "minimum_should_match": 1}})
        
        if getattr(request.filters, "brand", None):
            brand_shoulds = []
            for b in request.filters.brand[:MAX_BRAND_FILTERS]:
                b_str = str(b).strip()
                brand_shoulds.extend([
                    {"match_phrase": {"brand": b_str}},
                    {"term": {"brand": b_str}},
                    {"term": {"brand": b_str.upper()}},
                    {"term": {"brand": b_str.title()}}
                ])
            filters.append({"bool": {"should": brand_shoulds, "minimum_should_match": 1}})
        
        if getattr(request.filters, "price", None):
            p_range = {}
            if getattr(request.filters.price, "min", None) is not None:
                try:
                    clean_min = re.sub(r'[^\d.]', '', str(request.filters.price.min))
                    if clean_min:
                        p_range["gte"] = float(clean_min)
                except Exception:
                    pass
            if getattr(request.filters.price, "max", None) is not None:
                try:
                    clean_max = re.sub(r'[^\d.]', '', str(request.filters.price.max))
                    if clean_max:
                        p_range["lte"] = float(clean_max)
                except Exception:
                    pass
            if p_range:
                filters.append({"range": {"price": p_range}})
    
    # STEP 8: BUILD SORT ORDER
    sort_query = [{"_score": "desc"}]
    if request.sort == "price_asc":
        sort_query = [{"price": "asc"}]
    elif request.sort == "price_desc":
        sort_query = [{"price": "desc"}]
    elif request.sort == "on_sale":
        sort_query = [{"_score": "desc"}]
    
    # STEP 9: BUILD SCORING CLAUSES
    semantic_shoulds = []
    
    if vector:
        desired_k = max(KNN_MIN_K, from_val + request.page_size + KNN_BUFFER)
        k_val = min(desired_k, MAX_OS_WINDOW, 300)  # Cap KNN for strict mode
        semantic_shoulds.append({
            "knn": {
                "embedding": {
                    "vector": vector,
                    "k": k_val,
                    "boost": 0.5  # Lower KNN influence for strict mode
                }
            }
        })
    
    for item in multi_items:
        semantic_shoulds.extend([
            {"match_phrase": {"name": {"query": item, "boost": BOOST_NAME_PHRASE}}},
            {"match_phrase": {"brand": {"query": item, "boost": BOOST_BRAND_PHRASE}}},
            {"match": {"category": {"query": item, "boost": BOOST_CATEGORY_MATCH}}},
            {"multi_match": {
                "query": item,
                "fields": ["name^10", "brand^5", "category^3", "description"],
                "type": "cross_fields",
                "operator": "and",
                "boost": BOOST_CROSS_FIELDS
            }},
            {"multi_match": {
                "query": item,
                "fields": ["name^5", "brand^3", "category^2", "description"],
                "type": "best_fields",
                "fuzziness": "AUTO",
                "boost": BOOST_FUZZY_FALLBACK
            }}
        ])
    
    # STEP 10: BUILD SCORE FUNCTIONS (Demotion)
    score_functions = []
    if not matrix["has_accessory_intent"]:
        for acc in matrix["accessory_keywords"]:
            score_functions.append({"filter": {"match": {"name": acc}}, "weight": ACCESSORY_DEMOTION_WEIGHT})
            score_functions.append({"filter": {"match": {"category": acc}}, "weight": ACCESSORY_DEMOTION_WEIGHT})
    
    # STEP 11: BUILD QUERY BODY
    if vector or core_query:
        query_body = {
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "should": semantic_shoulds,
                            "must_not": must_nots,
                            "minimum_should_match": 1,
                            "filter": filters
                        }
                    },
                    "functions": score_functions,
                    "score_mode": "multiply",
                    "boost_mode": "multiply"
                }
            }
        }
    else:
        query_body = {
            "query": {
                "bool": {
                    "must": [{"match_all": {}}],
                    "filter": filters,
                    "must_not": must_nots
                }
            }
        }
    
    # =====================================================================
    # 🆕 STEP 11.5: COUNT QUERY — Get ACCURATE total (post-filter)
    # =====================================================================
    # Why: OpenSearch "total" counts ALL matches (pre-filter).
    # min_score filters out weak matches, so "total" is inflated.
    # We need real count to build correct pagination.
    
    use_min_score = bool(vector or core_query)
    min_relevance_score = MIN_RELEVANCE_SCORE if use_min_score else 0.0
    
    actual_total_hits = 0
    
    if use_min_score:
        count_query_body = {
            **query_body,
            "track_total_hits": True,
            "min_score": min_relevance_score,
            "size": 0,
        }
        
        try:
            count_response = os_client.search(index=INDEX_NAME, body=count_query_body)
            actual_total_hits = count_response.get("hits", {}).get("total", {}).get("value", 0)
        except Exception as e:
            logger.error(f"❌ Count query failed: {e}")
            actual_total_hits = 0
    
    # 🆕 STEP 11.6: EARLY RETURN IF PAGE BEYOND ACTUAL RESULTS
    if use_min_score and actual_total_hits > 0:
        real_total_pages = (actual_total_hits + request.page_size - 1) // request.page_size
        real_total_pages = min(real_total_pages, max_safe_page)
        
        if request.page > real_total_pages:
            return {
                "total_results": actual_total_hits,
                "total_pages": real_total_pages,
                "current_page": request.page,
                "pagination_html": build_pagination_html(real_total_pages, request.page),
                "results": [],
                "facets": {"categories": []}
            }
    
    # STEP 12: BUILD FINAL OPENSEARCH QUERY
    os_query = {
        "from": from_val,
        "size": request.page_size,
        **query_body,
        "sort": sort_query,
        "track_total_hits": True,
        "track_scores": True,
        "min_score": min_relevance_score,
        
        "aggs": {
    "top_relevant_hits": {
        "top_hits": {"size": 100, "_source": ["category"]}
    },
    "categories": {
        "terms": {
            "field": "category",
            "size": FACET_CATEGORIES_SIZE,  # 🆕 Now 10000 = effectively all
            "min_doc_count": FACET_MIN_DOC_COUNT,
            "shard_size": min(FACET_CATEGORIES_SIZE * 3, 65536),  # 🆕 Safety cap
            "order": {"_count": "desc"}
        }
    }
}
    }
    
    # STEP 13: EXECUTE MAIN QUERY
    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
    except Exception as e:
        logger.error(f"❌ OpenSearch Error: {str(e)}")
        return {
            "error": "Search service unavailable",
            "results": [],
            "total_results": 0,
            "total_pages": 0,
            "current_page": request.page,
            "pagination_html": "",
            "facets": {"categories": []}
        }
    
    # STEP 14: PARSE RESULTS
    hits = response.get("hits", {})
    
    # 🆕 Use accurate count from count query when min_score is active
    if use_min_score and actual_total_hits > 0:
        total_hits = actual_total_hits
    else:
        total_hits = hits.get("total", {}).get("value", 0)
    
    raw_total_pages = (total_hits + request.page_size - 1) // request.page_size if total_hits > 0 else 0
    total_pages = min(raw_total_pages, max_safe_page)
    
    max_score = hits.get("max_score")
    if not max_score or max_score == 0:
        max_score = 1.0
    
    results = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        brand_display = get_smart_brand(source)
        
        raw_cats = source.get("category", [])
        clean_cats = []
        
        if isinstance(raw_cats, str):
            clean_cats = [c.strip() for c in re.sub(r"[\[\]'\"]", "", raw_cats).split(",") if c.strip()]
        elif isinstance(raw_cats, list):
            clean_cats = [str(c).strip() for c in raw_cats if c and str(c).strip()]
        
        if not clean_cats or clean_cats == ["None"]:
            clean_cats = ["Uncategorized"]
        
        images = source.get("images", [])
        primary_image = images[0] if isinstance(images, list) and len(images) > 0 else None
        
        _pid = str(source.get("product_id", "123"))
        _pid_hash = int(hashlib.md5(_pid.encode()).hexdigest(), 16)
        _demo_rating = DEMO_RATING_BASE + (_pid_hash % DEMO_RATING_RANGE) / 10.0
        _demo_sales = (_pid_hash % DEMO_SALES_RANGE) + DEMO_SALES_BASE
        
        raw_score = hit.get("_score", 0) or 0
        normalized_score = min(1.0, raw_score / max_score) if max_score > 0 else 0
        
        results.append({
            "id": source.get("product_id"),
            "name": source.get("name", "Unknown Product"),
            "description": source.get("description", ""),
            "brand": brand_display,
            "category": clean_cats,
            "price": source.get("price", 0.0),
            "sale_price": source.get("sale_price"),
            "in_stock": source.get("in_stock", False),
            "sku": source.get("sku", ""),
            "url": source.get("url", ""),
            "primary_image": primary_image,
            "rating": source.get("rating") if source.get("rating", 0) > 0 else _demo_rating,
            "sales_count": source.get("sales_count") if source.get("sales_count", 0) > 0 else _demo_sales,
            "score": round(SCORE_DISPLAY_MIN + (normalized_score * SCORE_DISPLAY_RANGE), 2)
        })
    
    # STEP 15: RE-SORT BY SCORE
    if request.sort not in ["price_asc", "price_desc"]:
        results.sort(key=lambda x: x["score"], reverse=True)
    
    # =====================================================================
    # 🆕 STEP 16: BUILD FACETS (Query-Specific Counts — Amazon Style)
    # =====================================================================
    # PROBLEM SOLVED:
    #   Before: Sidebar showed GLOBAL category counts (not matching top total)
    #           Example: Search "shoes" → Top: 487, Sidebar "Shoes": 2596 ❌
    #
    # SOLUTION:
    #   Use the "categories" aggregation from main query.
    #   This counts categories WITHIN the search results (post-filter).
    #   Example: Search "shoes" → Top: 487, Sidebar "Shoes": 245 ✅
    #
    # HOW IT WORKS:
    #   - OpenSearch "categories" aggregation runs ON the matched results
    #   - With min_score applied, it only counts RELEVANT products
    #   - Sidebar counts now reflect current search exactly
    # =====================================================================
    
    aggregations = response.get("aggregations", {})
    
    # Get category buckets from the MAIN search aggregation
    # These counts are query-specific (only matching products)
    query_specific_buckets = aggregations.get("categories", {}).get("buckets", [])
    
    # Also use top_hits for relevance-based ordering
    # (popular categories from top 100 most-relevant products appear first)
    top_hits_data = aggregations.get("top_relevant_hits", {}).get("hits", {}).get("hits", [])
    
    # Build relevance score for each category (how often it appears in top 100)
    category_relevance = {}
    for hit in top_hits_data:
        source = hit.get("_source", {})
        raw_cats = source.get("category", [])
        
        if isinstance(raw_cats, str):
            cats_list = [c.strip() for c in re.sub(r"[\[\]'\"]", "", raw_cats).split(",") if c.strip()]
        elif isinstance(raw_cats, list):
            cats_list = [str(c).strip() for c in raw_cats if c and str(c).strip()]
        else:
            cats_list = []
        
        for cat in cats_list:
            if cat and cat != "None" and cat != "Uncategorized":
                category_relevance[cat] = category_relevance.get(cat, 0) + 1
    
    # 🆕 Build final facets (show ALL categories with matches)
    # - Use query-specific count from main aggregation (accurate)
    # - Order by count (most products first) — natural ranking
    # - No relevance filter — show every category with matching products
    facets_list = []
    for bucket in query_specific_buckets:
        cat_name = str(bucket.get("key", "")).strip()
        cat_count = bucket.get("doc_count", 0)
        
        # Skip empty/invalid categories
        if not cat_name or cat_name in ["None", "Uncategorized"]:
            continue
        
        # 🆕 Add relevance score if available (for sorting only)
        # If category was in top 100 relevant → appears first
        # If not in top 100 → appears after (but still shown)
        relevance_score = category_relevance.get(cat_name, 0)
        
        facets_list.append({
            "value": cat_name,
            "label": cat_name,
            "count": cat_count,  # Query-specific count (accurate!)
            "_relevance_score": relevance_score
        })
    
    # 🆕 Sort: relevance first (top 100 matches), then by count
    # This puts most-relevant categories at top, but shows ALL others too
    facets_list.sort(
        key=lambda x: (x["_relevance_score"], x["count"]),
        reverse=True
    )
    
    # 🆕 Show ALL categories (no limit) — user requested long sidebar
    # Categories ordered by relevance (top 100 appearance) then count
    # Frontend can add scroll if list is very long    
    # Remove internal relevance field before sending to frontend
    for f in facets_list:
        f.pop("_relevance_score", None)
    
    facets = {"categories": facets_list}
    
    # STEP 17: BUILD FINAL RESPONSE
    final_response = {
        "total_results": total_hits,
        "total_pages": total_pages,
        "current_page": request.page,
        "pagination_html": build_pagination_html(total_pages, request.page),
        "results": results,
        "facets": facets
    }
    
    # STEP 18: CACHE
    await cache_set(cache_key, final_response, ttl_seconds=SEARCH_CACHE_TTL)
    
    return final_response