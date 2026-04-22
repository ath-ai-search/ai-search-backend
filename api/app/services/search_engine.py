"""
=====================================================================================
👑 MAIN SEARCH ENGINE
=====================================================================================
This file handles the MAIN product search — the heart of our e-commerce.

HOW IT WORKS (step by step):
  1. Check Redis cache first (fast path)
  2. Extract semantic info from query (price, sale, multi-item)
  3. Create vector embedding using OpenAI (for KNN semantic search)
  4. Build OpenSearch query with:
     - Hard filters (price, category, brand, color, size, gender, in-stock)
     - Soft scoring (boosts for name/brand/category matches)
     - Accessory demotion (don't show cases when user wants iphone)
  5. Execute OpenSearch query
  6. Parse hits into clean product list
  7. Build facets (for filter sidebar)
  8. Cache results and return

SEARCH TECHNIQUES USED:
  - KNN Vector Search (semantic understanding)
  - Match Phrase (exact matching with boost)
  - Multi-match (cross-field searching)
  - Fuzzy Matching (typo tolerance)
  - Function Score (score multiplication)

🆕 PAGINATION SAFETY (Amazon-style)
  - OpenSearch has hard limit: from + size ≤ 10,000
  - We cap pagination to first 100 pages (at 100 products/page)
  - Beyond that, return empty with proper total_pages capped
  - 99% users never go past page 10 anyway
=====================================================================================
"""

import json
import hashlib
import logging
import re

# Import clients (OpenSearch, OpenAI, Redis)
from app.config import os_client, INDEX_NAME, openai_client

# Import models
from app.models.search import SearchRequest

# Import our utilities
from app.utils.brand_mapper import get_smart_brand
from app.utils.pagination import build_pagination_html
from app.utils.cache import cache_get, cache_set

# Import NLP brain
from app.nlp.semantic_matrix import extract_semantic_matrix

# Import all constants (magic numbers)
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
# 👑 MAIN SEARCH FUNCTION
# =========================================================================
async def execute_search(request: SearchRequest) -> dict:
    """
    Executes a full product search with AI-powered semantic matching.
    
    ARGS:
        request: SearchRequest object with query, page, filters, sort
    
    RETURNS:
        dict with:
            - total_results: Total matching products
            - total_pages: Total pages available (capped at MAX_OS_WINDOW)
            - current_page: Current page number
            - pagination_html: Ready-to-render pagination buttons
            - results: List of product dicts
            - facets: Category counts for filter sidebar
    """
    
    # =====================================================================
    # STEP 1: NORMALIZE PAGE SIZE
    # =====================================================================
    # Logic: if not exactly 10 (used by AI), force it to 100 (main search)
    # - 10 = AI assistant chat results (compact view)
    # - 100 = Main search page (standard view)
    request.page_size = DEFAULT_PAGE_SIZE if request.page_size != SMALL_PAGE_SIZE else SMALL_PAGE_SIZE
    
    # =====================================================================
    # STEP 2: CHECK REDIS CACHE
    # =====================================================================
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:ai:{CACHE_VERSION}:{hashlib.md5(request_str.encode()).hexdigest()}"
    
    cached_result = await cache_get(cache_key)
    if cached_result:
        return cached_result
    
    # =====================================================================
    # STEP 3: 🆕 CALCULATE SAFE PAGINATION (Amazon-style)
    # =====================================================================
    # OpenSearch has hard limit: from + size ≤ 10,000
    # Any request beyond this causes "failed to parse field [should]" error
    #
    # SAFE APPROACH:
    #   - Calculate max allowed page based on MAX_OS_WINDOW
    #   - If requested page > max_safe_page → return empty (don't even try)
    #   - Normal page calculation for valid pages
    
    # Calculate maximum safe page number based on page_size
    # E.g., 10000 / 100 = 100 max pages
    max_safe_page = MAX_OS_WINDOW // request.page_size
    
    # 🆕 EARLY RETURN: If user clicks beyond safe pages, return empty gracefully
    # This is better than broken OpenSearch query errors
    if request.page > max_safe_page:
        # User tried to go too deep — this shouldn't normally happen if
        # we cap total_pages correctly, but this is a safety net
        logger.warning(
            f"⚠️ Page {request.page} exceeds max safe page {max_safe_page}. Returning empty."
        )
        return {
            "total_results": 0,
            "total_pages": max_safe_page,
            "current_page": request.page,
            "pagination_html": build_pagination_html(max_safe_page, request.page),
            "results": [],
            "facets": {"categories": []}
        }
    
    # Normal offset calculation for valid page
    from_val = (request.page - 1) * request.page_size
    
    # =====================================================================
    # STEP 4: EXTRACT SEMANTIC INFO FROM QUERY
    # =====================================================================
    query_text = request.query.strip() if request.query else ""
    matrix = extract_semantic_matrix(query_text)
    core_query = matrix["core_query"]
    
    # =====================================================================
    # STEP 5: HANDLE MULTI-ITEM QUERIES
    # =====================================================================
    if "|" in core_query:
        multi_items = [item.strip() for item in core_query.split("|") if item.strip()]
        core_query_for_vector = " ".join(multi_items)
    else:
        multi_items = [core_query]
        core_query_for_vector = core_query
    
    # =====================================================================
    # STEP 6: GENERATE VECTOR EMBEDDING (Semantic Search)
    # =====================================================================
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
    
    # =====================================================================
    # STEP 7: BUILD HARD FILTERS (must match these conditions)
    # =====================================================================
    filters = [{"term": {"in_stock": True}}]
    must_nots = []
    
    # Price filter from SEMANTIC extraction (user typed "under 100")
    if matrix["min_price"] is not None or matrix["max_price"] is not None:
        price_range = {}
        if matrix["min_price"] is not None:
            price_range["gte"] = matrix["min_price"]
        if matrix["max_price"] is not None:
            price_range["lte"] = matrix["max_price"]
        filters.append({"range": {"price": price_range}})
    
    # Sale filter
    if (
        matrix["is_sale"] 
        or request.sort == "on_sale" 
        or (request.filters and getattr(request.filters, "on_sale", False))
    ):
        filters.append({"range": {"sale_price": {"gt": 0}}})
    
    # FILTERS FROM UI (user clicked sidebar filters)
    if request.filters:
        
        # CATEGORY FILTER
        if getattr(request.filters, "category", None):
            filters.append({
                "terms": {
                    "category": request.filters.category[:MAX_CATEGORY_FILTERS]
                }
            })
        
        # IN-STOCK OVERRIDE
        if getattr(request.filters, "in_stock", None) is not None:
            filters.append({"term": {"in_stock": request.filters.in_stock}})
        
        # COLOR FILTER
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
            filters.append({
                "bool": {
                    "should": color_shoulds,
                    "minimum_should_match": 1
                }
            })
        
        # SIZE FILTER
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
            filters.append({
                "bool": {
                    "should": size_shoulds,
                    "minimum_should_match": 1
                }
            })
        
        # GENDER FILTER
        if getattr(request.filters, "gender", None):
            gender_shoulds = []
            for g in request.filters.gender[:MAX_GENDER_FILTERS]:
                g_str = str(g).strip()
                gender_shoulds.append({
                    "multi_match": {
                        "query": g_str,
                        "fields": [
                            "gender",
                            "attributes.gender",
                            "attributes.Gender",
                            "category",
                            "name"
                        ],
                        "type": "best_fields"
                    }
                })
            filters.append({
                "bool": {
                    "should": gender_shoulds,
                    "minimum_should_match": 1
                }
            })
        
        # BRAND FILTER (CASE-INSENSITIVE)
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
            filters.append({
                "bool": {
                    "should": brand_shoulds,
                    "minimum_should_match": 1
                }
            })
        
        # PRICE FILTER FROM UI (sidebar slider)
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
    
    # =====================================================================
    # STEP 8: BUILD SORT ORDER
    # =====================================================================
    sort_query = [{"_score": "desc"}]
    
    if request.sort == "price_asc":
        sort_query = [{"price": "asc"}]
    elif request.sort == "price_desc":
        sort_query = [{"price": "desc"}]
    elif request.sort == "on_sale":
        sort_query = [{"_score": "desc"}]
    
    # =====================================================================
    # STEP 9: BUILD SCORING (BOOST) CLAUSES
    # =====================================================================
    semantic_shoulds = []
    
    # ---------------------------------------------------------------------
    # 🆕 KNN SEMANTIC SEARCH (with SAFE k_val calculation)
    # ---------------------------------------------------------------------
    if vector:
        # k = how many similar products to find
        # 🆕 SAFETY FIX: Cap k at MAX_OS_WINDOW to prevent OpenSearch errors
        # Original formula: max(KNN_MIN_K, from_val + page_size + KNN_BUFFER)
        # Problem: When from_val was near max, k became invalid
        # Fix: Ensure k stays safely within bounds
        desired_k = max(KNN_MIN_K, from_val + request.page_size + KNN_BUFFER)
        k_val = min(desired_k, MAX_OS_WINDOW)  # 🆕 SAFETY CAP
        
        semantic_shoulds.append({
            "knn": {
                "embedding": {
                    "vector": vector,
                    "k": k_val
                }
            }
        })
    
    # ---------------------------------------------------------------------
    # KEYWORD MATCHING FOR EACH ITEM (Multi-item Equalizer)
    # ---------------------------------------------------------------------
    for item in multi_items:
        semantic_shoulds.extend([
            # NAME EXACT PHRASE (Boost: 100)
            {
                "match_phrase": {
                    "name": {
                        "query": item,
                        "boost": BOOST_NAME_PHRASE
                    }
                }
            },
            
            # BRAND EXACT PHRASE (Boost: 300)
            {
                "match_phrase": {
                    "brand": {
                        "query": item,
                        "boost": BOOST_BRAND_PHRASE
                    }
                }
            },
            
            # CATEGORY MATCH (Boost: 200)
            {
                "match": {
                    "category": {
                        "query": item,
                        "boost": BOOST_CATEGORY_MATCH
                    }
                }
            },
            
            # CROSS-FIELD MATCH (Boost: 20)
            {
                "multi_match": {
                    "query": item,
                    "fields": ["name^10", "brand^5", "category^3", "description"],
                    "type": "cross_fields",
                    "operator": "and",
                    "boost": BOOST_CROSS_FIELDS
                }
            },
            
            # FUZZY FALLBACK (Boost: 5)
            {
                "multi_match": {
                    "query": item,
                    "fields": ["name^5", "brand^3", "category^2", "description"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                    "boost": BOOST_FUZZY_FALLBACK
                }
            }
        ])
    
    # =====================================================================
    # STEP 10: BUILD SCORE FUNCTIONS (Demotion Logic)
    # =====================================================================
    score_functions = []
    
    if not matrix["has_accessory_intent"]:
        for acc in matrix["accessory_keywords"]:
            score_functions.append({
                "filter": {"match": {"name": acc}},
                "weight": ACCESSORY_DEMOTION_WEIGHT
            })
            score_functions.append({
                "filter": {"match": {"category": acc}},
                "weight": ACCESSORY_DEMOTION_WEIGHT
            })
    
    # =====================================================================
    # STEP 11: COMBINE EVERYTHING INTO FINAL OPENSEARCH QUERY
    # =====================================================================
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
        # No query? Just match all products with filters (for browsing)
        query_body = {
            "query": {
                "bool": {
                    "must": [{"match_all": {}}],
                    "filter": filters,
                    "must_not": must_nots
                }
            }
        }
    
    # Build the FINAL OpenSearch request
    os_query = {
        "from": from_val,
        "size": request.page_size,
        **query_body,
        "sort": sort_query,
        "track_total_hits": True,
        "track_scores": True,
        
        # =====================================================================
        # 🎯 SMART CATEGORY FACETS (Contextual Filtering)
        # =====================================================================
        "aggs": {
            "top_relevant_hits": {
                "top_hits": {
                    "size": 100,
                    "_source": ["category"]
                }
            },
            "categories": {
                "terms": {
                    "field": "category",
                    "size": FACET_CATEGORIES_SIZE,
                    "min_doc_count": FACET_MIN_DOC_COUNT,
                    "shard_size": FACET_CATEGORIES_SIZE * 3,
                    "order": {"_count": "desc"}
                }
            }
        }
    }
    
    # =====================================================================
    # STEP 12: EXECUTE OPENSEARCH QUERY
    # =====================================================================
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
    
    # =====================================================================
    # STEP 13: PARSE RESULTS
    # =====================================================================
    hits = response.get("hits", {})
    total_hits = hits.get("total", {}).get("value", 0)
    
    # 🆕 Calculate total pages (ceiling division) WITH SAFETY CAP
    # Even if OpenSearch reports 23,761 results, we can only paginate through 10,000
    # So cap total_pages to prevent users from clicking pages that would fail
    raw_total_pages = (total_hits + request.page_size - 1) // request.page_size if total_hits > 0 else 0
    total_pages = min(raw_total_pages, max_safe_page)  # 🆕 SAFETY CAP
    
    # Get max score for normalization
    max_score = hits.get("max_score")
    if not max_score or max_score == 0:
        max_score = 1.0
    
    # Transform raw OpenSearch hits into clean product dicts
    results = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        
        brand_display = get_smart_brand(source)
        
        # Clean up category field
        raw_cats = source.get("category", [])
        clean_cats = []
        
        if isinstance(raw_cats, str):
            clean_cats = [
                c.strip() 
                for c in re.sub(r"[\[\]'\"]", "", raw_cats).split(",") 
                if c.strip()
            ]
        elif isinstance(raw_cats, list):
            clean_cats = [str(c).strip() for c in raw_cats if c and str(c).strip()]
        
        if not clean_cats or clean_cats == ["None"]:
            clean_cats = ["Uncategorized"]
        
        # Get first image as primary
        images = source.get("images", [])
        primary_image = images[0] if isinstance(images, list) and len(images) > 0 else None
        
        # Generate FAKE but consistent rating/sales for demo
        _pid = str(source.get("product_id", "123"))
        _pid_hash = int(hashlib.md5(_pid.encode()).hexdigest(), 16)
        _demo_rating = DEMO_RATING_BASE + (_pid_hash % DEMO_RATING_RANGE) / 10.0
        _demo_sales = (_pid_hash % DEMO_SALES_RANGE) + DEMO_SALES_BASE
        
        # Normalize relevance score to 0.85-0.99 range (for display)
        raw_score = hit.get("_score", 0) or 0
        normalized_score = min(1.0, raw_score / max_score) if max_score > 0 else 0
        
        # Build clean product dict for frontend
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
    
    # =====================================================================
    # STEP 14: RE-SORT BY SCORE (unless sorting by price)
    # =====================================================================
    if request.sort not in ["price_asc", "price_desc"]:
        results.sort(key=lambda x: x["score"], reverse=True)
    
    # =====================================================================
    # STEP 15: BUILD FACETS (Smart Contextual Category Filtering)
    # =====================================================================
    aggregations = response.get("aggregations", {})
    
    top_hits_data = aggregations.get("top_relevant_hits", {}).get("hits", {}).get("hits", [])
    
    category_counts = {}
    
    for hit in top_hits_data:
        source = hit.get("_source", {})
        raw_cats = source.get("category", [])
        
        if isinstance(raw_cats, str):
            cats_list = [
                c.strip() 
                for c in re.sub(r"[\[\]'\"]", "", raw_cats).split(",") 
                if c.strip()
            ]
        elif isinstance(raw_cats, list):
            cats_list = [str(c).strip() for c in raw_cats if c and str(c).strip()]
        else:
            cats_list = []
        
        for cat in cats_list:
            if cat and cat != "None" and cat != "Uncategorized":
                category_counts[cat] = category_counts.get(cat, 0) + 1
    
    global_agg_buckets = {
        str(c.get("key")).strip(): c.get("doc_count", 0)
        for c in aggregations.get("categories", {}).get("buckets", [])
        if c.get("key")
    }
    
    sorted_categories = sorted(
        category_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:15]
    
    facets = {
        "categories": [
            {
                "value": cat_name,
                "label": cat_name,
                "count": global_agg_buckets.get(cat_name, top_count)
            }
            for cat_name, top_count in sorted_categories
        ]
    }
    
    # =====================================================================
    # STEP 16: BUILD FINAL RESPONSE
    # =====================================================================
    final_response = {
        "total_results": total_hits,
        "total_pages": total_pages,  # 🆕 Already capped at max_safe_page
        "current_page": request.page,
        "pagination_html": build_pagination_html(total_pages, request.page),
        "results": results,
        "facets": facets
    }
    
    # =====================================================================
    # STEP 17: CACHE FOR NEXT TIME
    # =====================================================================
    await cache_set(cache_key, final_response, ttl_seconds=SEARCH_CACHE_TTL)
    
    return final_response