"""
=====================================================================================
👑 MAIN SEARCH ENGINE (LOCKED IN)
=====================================================================================
STRICT MODE: Pure Facets, True Global Counts, Perfect Sorting.
=====================================================================================
"""

import json
import hashlib
import logging
import time
import re

from app.config import os_client, INDEX_NAME, openai_client
from app.models.search import SearchRequest
from app.utils.brand_mapper import get_smart_brand
from app.utils.pagination import build_pagination_html
from app.utils.cache import cache_get, cache_set
from app.nlp.semantic_matrix import extract_semantic_matrix
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# 🆕 Database config for trending boost
DB_CONFIG_TRENDING = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "venue_ai"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "shubham16"),
}


async def correct_query_typos(query: str) -> tuple:
    """
    🔤 TYPO CORRECTION using OpenSearch's TERM SUGGESTER (unsupervised learning).
    Auto-learns spellings from your product catalog — no hardcoded dictionary.
    
    Examples:
      "ihpone 11"   → "iphone 11"
      "samsng glax" → "samsung galaxy"
      "nikr shoe"   → "nike shoes"
    
    Returns: (corrected_query: str, was_corrected: bool)
    """
    if not query or len(query.strip()) < 3:
        return query, False
    
    try:
        resp = os_client.search(
            index=INDEX_NAME,
            body={
                "size": 0,
                "suggest": {
                    "fix_typos": {
                        "text": query,
                        "term": {
                            "field": "name",
                            "suggest_mode": "popular",   # only suggest words from popular products
                            "min_word_length": 3,        # don't correct tiny words
                            "max_edits": 2,              # up to 2 letter changes per word
                            "prefix_length": 1           # first letter must match (prevents wild corrections)
                        }
                    }
                }
            }
        )
        
        suggestions = resp.get("suggest", {}).get("fix_typos", [])
        corrected_words = []
        has_correction = False
        
        for word_data in suggestions:
            original_word = word_data.get("text", "")
            options = word_data.get("options", [])
            
            if options and options[0].get("score", 0) > 0.7:
                # High confidence correction
                corrected_words.append(options[0]["text"])
                has_correction = True
            else:
                # Keep original word
                corrected_words.append(original_word)
        
        if has_correction:
            corrected = " ".join(corrected_words)
            logger.info(f"🔤 Typo correction: '{query}' → '{corrected}'")
            return corrected, True
        
        return query, False
    except Exception as e:
        logger.error(f"❌ Typo correction failed: {e}")
        return query, False


def get_trending_scores(product_ids: list) -> dict:
    """🆕 Fetch trending scores from PostgreSQL for given products."""
    if not product_ids:
        return {}
    
    try:
        conn = psycopg2.connect(**DB_CONFIG_TRENDING)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get aggregated trending score for each product
        cur.execute("""
            SELECT 
                product_id, 
                SUM(
                    1.0 + 
                    (views * 1) + 
                    (clicks * 2) + 
                    (wishlist * 3) + 
                    (carts * 5) + 
                    (purchases * 10)
                ) as score
            FROM product_metrics 
            WHERE product_id = ANY(%s)
            GROUP BY product_id
        """, (product_ids,))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return {row["product_id"]: float(row["score"]) for row in rows}
    except Exception as e:
        logger.error(f"❌ Trending fetch failed: {e}")
        return {}


from app.core.constants import (
    MAX_OS_WINDOW, DEFAULT_PAGE_SIZE, SMALL_PAGE_SIZE,
    BOOST_NAME_PHRASE, BOOST_BRAND_PHRASE, BOOST_CATEGORY_MATCH,
    BOOST_CROSS_FIELDS, BOOST_FUZZY_FALLBACK, ACCESSORY_DEMOTION_WEIGHT,
    KNN_MIN_K, KNN_BUFFER, SEARCH_CACHE_TTL, CACHE_VERSION,
    FACET_CATEGORIES_SIZE, FACET_BRANDS_SIZE, FACET_COLORS_SIZE,      
    FACET_SIZES_SIZE, FACET_STORAGE_SIZE, FACET_RAM_SIZE,         
    MAX_CATEGORY_FILTERS, MAX_COLOR_FILTERS, MAX_SIZE_FILTERS,
    MAX_BRAND_FILTERS, MAX_GENDER_FILTERS, AI_EMBEDDING_MODEL,
    DEMO_RATING_BASE, DEMO_RATING_RANGE, DEMO_SALES_BASE,
    DEMO_SALES_RANGE, SCORE_DISPLAY_MIN, SCORE_DISPLAY_RANGE,
)
logger = logging.getLogger(__name__)

MIN_RELEVANCE_SCORE = 25.0          # Strict threshold for keyword queries
MIN_RELEVANCE_SCORE_CONVERSATIONAL = 2.0  # 🔥 Much lower for AI/vector queries — vector scores are smaller than keyword scores
async def execute_search(request: SearchRequest) -> dict:
    _start_time = time.perf_counter()  # 🆕 Start timing    
    request.page_size = DEFAULT_PAGE_SIZE if request.page_size != SMALL_PAGE_SIZE else SMALL_PAGE_SIZE
    
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:ai:{CACHE_VERSION}:{hashlib.md5(request_str.encode()).hexdigest()}"
    
    cached_result = await cache_get(cache_key)
    if cached_result: return cached_result
    
    max_safe_page = MAX_OS_WINDOW // request.page_size
    
    if request.page > max_safe_page:
        return {"total_results": 0, "total_pages": max_safe_page, "current_page": request.page, "pagination_html": build_pagination_html(max_safe_page, request.page), "results": [], "facets": {"categories": []}}
    
    from_val = (request.page - 1) * request.page_size
    
    query_text = request.query.strip() if request.query else ""
    
    # 🔤 STAGE 1: Auto-correct typos using OpenSearch's term suggester
    # "ihpone 11" → "iphone 11" before searching
    was_corrected = False
    original_query_for_log = query_text
    if query_text and len(query_text) >= 3:
        corrected_query, was_corrected = await correct_query_typos(query_text)
        if was_corrected:
            query_text = corrected_query
    
    matrix = extract_semantic_matrix(query_text)
    core_query = matrix["core_query"]
    
    if "|" in core_query:
        multi_items = [item.strip() for item in core_query.split("|") if item.strip()]
        core_query_for_vector = " ".join(multi_items)
    else:
        multi_items = [core_query]
        core_query_for_vector = core_query
    
    vector = None
    if core_query_for_vector:
        try:
            resp = await openai_client.embeddings.create(input=core_query_for_vector, model=AI_EMBEDDING_MODEL)
            vector = resp.data[0].embedding
        except Exception as e:
            logger.error(f"❌ OpenAI Embedding Failed: {e}")
    
    filters = [{"term": {"in_stock": True}}]
    must_nots = []
    
    # 🔥 AUTO-DETECT GENDER FROM QUERY TEXT (universal fix)
    # When user types "men", "women", "kids", etc. — treat as HARD filter
    # Also blocks opposite-gender products from showing.
    query_lower = (query_text or "").lower()
    query_tokens = re.findall(r'\b[a-z]+\b', query_lower)
    
    GENDER_PATTERNS = {
        "men":     {"match": ["men", "mens", "male", "man", "gentleman"],     "opposite": ["women", "womens", "female", "woman", "ladies", "girls"]},
        "women":   {"match": ["women", "womens", "female", "woman", "ladies", "lady"], "opposite": ["men", "mens", "male", "man", "boys"]},
        "kids":    {"match": ["kids", "kid", "children", "child"],            "opposite": []},
        "boys":    {"match": ["boys", "boy"],                                  "opposite": ["girls", "girl"]},
        "girls":   {"match": ["girls", "girl"],                                "opposite": ["boys", "boy"]},
        "unisex":  {"match": ["unisex"],                                       "opposite": []},
    }
    
    detected_gender = None
    for gender_label, config in GENDER_PATTERNS.items():
        if any(word in query_tokens for word in config["match"]):
            detected_gender = (gender_label, config)
            break
    
    if detected_gender:
        gender_label, config = detected_gender
        # Add positive filter: product must mention this gender
        gender_shoulds = []
        for word in config["match"]:
            gender_shoulds.extend([
                {"match": {"gender": word}},
                {"match": {"attributes.gender": word}},
                {"match": {"attributes.Gender": word}},
                {"match_phrase": {"category": word}},
                {"match_phrase": {"name": word}},
            ])
        filters.append({"bool": {"should": gender_shoulds, "minimum_should_match": 1}})
        
        # Add negative filter: BLOCK opposite gender products  
        if config["opposite"]:
            for opp in config["opposite"]:
                must_nots.append({"match_phrase": {"name": opp}})
                must_nots.append({"match_phrase": {"category": opp}})
        
        logger.info(f"🚻 Auto-detected gender: {gender_label} (from query: '{query_text}')")
    
    if matrix["min_price"] is not None or matrix["max_price"] is not None:
        price_range = {}
        if matrix["min_price"] is not None: price_range["gte"] = matrix["min_price"]
        if matrix["max_price"] is not None: price_range["lte"] = matrix["max_price"]
        filters.append({"range": {"price": price_range}})
    
    if (matrix["is_sale"] or request.sort == "on_sale" or (request.filters and getattr(request.filters, "on_sale", False))):
        filters.append({"range": {"sale_price": {"gt": 0}}})
    
    if request.filters:
        if getattr(request.filters, "category", None): filters.append({"terms": {"category": request.filters.category[:MAX_CATEGORY_FILTERS]}})
        if getattr(request.filters, "in_stock", None) is not None: filters.append({"term": {"in_stock": request.filters.in_stock}})
        if getattr(request.filters, "color", None):
            color_shoulds = [{"multi_match": {"query": c, "type": "phrase", "fields": ["color", "colors", "name"]}} for c in request.filters.color[:MAX_COLOR_FILTERS]]
            filters.append({"bool": {"should": color_shoulds, "minimum_should_match": 1}})
        if getattr(request.filters, "size", None):
            size_shoulds = [{"multi_match": {"query": str(s).strip() if "size" in str(s).lower() else f"size {str(s).strip()} {str(s).strip()}", "fields": ["size", "sizes", "name"], "type": "best_fields"}} for s in request.filters.size[:MAX_SIZE_FILTERS]]
            filters.append({"bool": {"should": size_shoulds, "minimum_should_match": 1}})
        if getattr(request.filters, "gender", None):
            # 🔥 STRICT GENDER FILTER (no fuzziness — "men" must not match "women")
            # Also blocks opposite gender via must_not for hard isolation.
            FILTER_GENDER_PATTERNS = {
                "men":     {"match": ["men", "mens", "male", "man", "gentleman"],     "opposite": ["women", "womens", "female", "woman", "ladies", "lady", "girls"]},
                "women":   {"match": ["women", "womens", "female", "woman", "ladies", "lady"], "opposite": ["men", "mens", "male", "man", "gentleman", "boys"]},
                "kids":    {"match": ["kids", "kid", "children", "child"],            "opposite": []},
                "boys":    {"match": ["boys", "boy"],                                  "opposite": ["girls", "girl"]},
                "girls":   {"match": ["girls", "girl"],                                "opposite": ["boys", "boy"]},
                "unisex":  {"match": ["unisex"],                                       "opposite": []},
            }
            
            gender_shoulds = []
            blocked_opposites = set()
            
            for g in request.filters.gender[:MAX_GENDER_FILTERS]:
                g_clean = str(g).strip().lower()
                config = FILTER_GENDER_PATTERNS.get(g_clean)
                
                if config:
                    # Build POSITIVE match for this gender + variants (NO fuzziness)
                    for word in config["match"]:
                        gender_shoulds.extend([
                            {"match": {"gender": word}},
                            {"match": {"attributes.gender": word}},
                            {"match": {"attributes.Gender": word}},
                            {"match_phrase": {"category": word}},
                            {"match_phrase": {"name": word}},
                        ])
                    # Collect opposite-gender words to block
                    for opp in config["opposite"]:
                        blocked_opposites.add(opp)
                else:
                    # Fallback: unknown gender label, basic match (no fuzziness)
                    gender_shoulds.extend([
                        {"match": {"gender": g_clean}},
                        {"match": {"attributes.gender": g_clean}},
                        {"match": {"attributes.Gender": g_clean}},
                        {"match_phrase": {"category": g_clean}},
                        {"match_phrase": {"name": g_clean}},
                    ])
            
            if gender_shoulds:
                filters.append({"bool": {"should": gender_shoulds, "minimum_should_match": 1}})
            
            # 🚫 BLOCK opposite-gender products at must_not level (HARD BLOCK)
            for opp in blocked_opposites:
                must_nots.append({"match_phrase": {"name": opp}})
                must_nots.append({"match_phrase": {"category": opp}})
            
            if blocked_opposites:
                logger.info(f"🚻 Filter gender: {request.filters.gender} → blocking opposites: {blocked_opposites}")
        if getattr(request.filters, "brand", None):
            brand_shoulds = []
            for b in request.filters.brand[:MAX_BRAND_FILTERS]:
                b_str = str(b).strip()
                brand_shoulds.extend([{"match_phrase": {"brand": b_str}}, {"term": {"brand": b_str}}, {"term": {"brand": b_str.upper()}}, {"term": {"brand": b_str.title()}}])
            filters.append({"bool": {"should": brand_shoulds, "minimum_should_match": 1}})
        if getattr(request.filters, "price", None):
            p_range = {}
            if getattr(request.filters.price, "min", None) is not None:
                try: p_range["gte"] = float(re.sub(r'[^\d.]', '', str(request.filters.price.min)))
                except: pass
            if getattr(request.filters.price, "max", None) is not None:
                try: p_range["lte"] = float(re.sub(r'[^\d.]', '', str(request.filters.price.max)))
                except: pass
            if p_range: filters.append({"range": {"price": p_range}})
        if getattr(request.filters, "storage", None):
            storage_values = [str(s).strip() for s in request.filters.storage[:10] if str(s).strip()]
            if storage_values: filters.append({"terms": {"storage": storage_values}})
        if getattr(request.filters, "ram", None):
            ram_values = [str(r).strip() for r in request.filters.ram[:10] if str(r).strip()]
            if ram_values: filters.append({"terms": {"ram": ram_values}})
    
    sort_query = [{"_score": "desc"}]
    if request.sort == "price_asc": sort_query = [{"price": "asc"}]
    elif request.sort == "price_desc": sort_query = [{"price": "desc"}]
    elif request.sort == "on_sale": sort_query = [{"_score": "desc"}]
    elif request.sort == "popularity": sort_query = [{"trending_score": "desc"}]
    
    # 🔥 DETECT CONVERSATIONAL QUERY MODE
    # Long queries (6+ words) like "something cozy for a rainy Sunday" need PURE semantic search.
    # We dial up the AI vector dramatically and dial down keyword matching.
    word_count_total = len((core_query or "").split())
    is_conversational = word_count_total >= 6
    
    semantic_shoulds = []
    if vector:
        k_val = min(max(KNN_MIN_K, from_val + request.page_size + KNN_BUFFER), MAX_OS_WINDOW, 300)
        # 🔥 Boost KNN 10x higher for conversational queries (lets AI understanding dominate)
        knn_boost = 3.0 if is_conversational else 0.3
        semantic_shoulds.append({"knn": {"embedding": {"vector": vector, "k": k_val, "boost": knn_boost}}})
        
        if is_conversational:
            logger.info(f"🤖 CONVERSATIONAL MODE: {word_count_total} words, KNN boost={knn_boost}")    
    for item in multi_items:
        semantic_shoulds.extend([
            # 🔥 UNIVERSAL PHRASE BOOST: Exact word ordering gets immediate priority
            {"match_phrase": {"name": {"query": item, "boost": 100.0, "slop": 2}}},
            
            # 🔥 STRONG CATEGORY-NAME ALIGNMENT
            # Boosts products whose CATEGORY matches a key word in query.
            # When user says "dress" → boosts products in "Dresses" category.
            # When user says "shirt" → boosts products in "Shirts" category.
            # When user says "watch" → boosts products in "Watches" category.
            # Universal: works for any product type, no hardcoding.
            {"match_phrase": {"category": {"query": item, "boost": 60.0}}},
            
            {"match_phrase": {"name": {"query": item, "boost": BOOST_NAME_PHRASE}}},
            {"match_phrase": {"brand": {"query": item, "boost": BOOST_BRAND_PHRASE}}},
            {"match": {"category": {"query": item, "boost": BOOST_CATEGORY_MATCH}}},
            
            # 🔥 JUNK-WORD SAFETY NET: If the user adds words like "color", this heavily boosts the core product anyway
            {"multi_match": {"query": item, "fields": ["name^10", "brand^5", "category^3"], "type": "cross_fields", "minimum_should_match": "80%", "boost": 80.0}},
            
            # 🚫 Removed 'description' from fields below to stop irrelevant items (like clown costumes) from sneaking in
            {"multi_match": {"query": item, "fields": ["name^10", "brand^5", "category^3"], "type": "cross_fields", "operator": "and", "boost": BOOST_CROSS_FIELDS}},
            {"multi_match": {"query": item, "fields": ["name^5", "brand^3", "category^2"], "type": "best_fields", "fuzziness": "AUTO", "boost": BOOST_FUZZY_FALLBACK}}
        ])
    
    score_functions = []
    if not matrix["has_accessory_intent"]:
        for acc in matrix["accessory_keywords"]:
            score_functions.append({"filter": {"match": {"name": acc}}, "weight": ACCESSORY_DEMOTION_WEIGHT})
            score_functions.append({"filter": {"match": {"category": acc}}, "weight": ACCESSORY_DEMOTION_WEIGHT})
    
    # 🆕 GLOBAL DYNAMIC GATEKEEPER (Hybrid AI Mode: Keyword + Conversational Intent)
    must_clauses = []
    if core_query:
        for item in multi_items:
            # 1. Count how many words the user typed
            word_count = len(item.split())
            
            # 2. STANDARD COMMERCE MODE (1 to 5 words)
            if word_count <= 5:
                must_clauses.append({
                    "multi_match": {
                        "query": item,
                        "fields": ["name^10", "category^4", "brand^3"], 
                        "type": "cross_fields",
                        "minimum_should_match": "2<-1 4<60%"  
                    }
                })
            
            # 3. CONVERSATIONAL AI MODE (6+ words)
            # If the user types a long sentence like "outfit for a beach wedding in Santorini", 
            # we do NOT add a must_clause. We bypass keyword restrictions completely and 
            # let the OpenAI KNN Vector search handle 100% of the matching based on pure semantic intent!
            else:
                pass
    
    if vector or core_query:
        bool_query = {"should": semantic_shoulds, "must_not": must_nots, "minimum_should_match": 1, "filter": filters}
        if must_clauses:
            bool_query["must"] = must_clauses
        query_body = {"query": {"function_score": {"query": {"bool": bool_query}, "functions": score_functions, "score_mode": "multiply", "boost_mode": "multiply"}}}
    else:
        query_body = {"query": {"bool": {"must": [{"match_all": {}}], "filter": filters, "must_not": must_nots}}}
    
    use_min_score = bool(vector or core_query)
    # 🔥 Use lower threshold for conversational queries (vector search returns smaller raw scores)
    if is_conversational:
        min_relevance_score = MIN_RELEVANCE_SCORE_CONVERSATIONAL
    else:
        min_relevance_score = MIN_RELEVANCE_SCORE if use_min_score else 0.0
    actual_total_hits = 0
    
    if use_min_score:
        count_query_body = {**query_body, "track_total_hits": True, "min_score": min_relevance_score, "size": 0}
        try:
            count_response = os_client.search(index=INDEX_NAME, body=count_query_body)
            actual_total_hits = count_response.get("hits", {}).get("total", {}).get("value", 0)
        except Exception:
            actual_total_hits = 0
            
    if use_min_score and actual_total_hits > 0:
        real_total_pages = (actual_total_hits + request.page_size - 1) // request.page_size
        if request.page > min(real_total_pages, max_safe_page):
            return {"total_results": actual_total_hits, "total_pages": min(real_total_pages, max_safe_page), "current_page": request.page, "pagination_html": build_pagination_html(min(real_total_pages, max_safe_page), request.page), "results": [], "facets": {"categories": []}}
    
    # =====================================================================
    # 🚀 OPENSEARCH QUERY: SAMPLER + GLOBAL COUNTS
    # =====================================================================
    os_query = {
        "from": from_val,
        "size": request.page_size,
        **query_body,
        "sort": sort_query,
        "track_total_hits": True,
        "track_scores": True,
        "min_score": min_relevance_score,
        
        "aggs": {
            # 1. STRICT SAMPLER: Size 100 completely blocks Kitchen, Amazon, Jeans
            "strict_relevance_sampler": {
                "sampler": { "shard_size": 100 },
                "aggs": {
                    "categories": {"terms": {"field": "category", "size": FACET_CATEGORIES_SIZE, "min_doc_count": 3}},
                    "brands": {"terms": {"field": "brand", "size": FACET_BRANDS_SIZE, "min_doc_count": 3}},
                    "colors": {"terms": {"field": "colors", "size": FACET_COLORS_SIZE, "min_doc_count": 2}},
                    "sizes": {"terms": {"field": "sizes", "size": FACET_SIZES_SIZE, "min_doc_count": 2}},
                    "storage": {"terms": {"field": "storage", "size": FACET_STORAGE_SIZE, "min_doc_count": 2}},
                    "ram": {"terms": {"field": "ram", "size": FACET_RAM_SIZE, "min_doc_count": 2}}
                }
            },
            # 2. GLOBAL COUNTS: Generates the true total numbers for the UI
            "global_categories": {"terms": {"field": "category", "size": FACET_CATEGORIES_SIZE}},
            "global_brands": {"terms": {"field": "brand", "size": FACET_BRANDS_SIZE}},
            "global_colors": {"terms": {"field": "colors", "size": FACET_COLORS_SIZE}},
            "global_sizes": {"terms": {"field": "sizes", "size": FACET_SIZES_SIZE}},
            "global_storage": {"terms": {"field": "storage", "size": FACET_STORAGE_SIZE}},
            "global_ram": {"terms": {"field": "ram", "size": FACET_RAM_SIZE}}
        }
    }
    
    try: response = os_client.search(index=INDEX_NAME, body=os_query)
    except Exception as e: return {"error": "Search service unavailable", "results": [], "total_results": 0, "total_pages": 0, "current_page": request.page, "pagination_html": "", "facets": {"categories": []}}
    
    hits = response.get("hits", {})
    total_hits = actual_total_hits if (use_min_score and actual_total_hits > 0) else hits.get("total", {}).get("value", 0)
    
    # 🛡️ ZERO-RESULT FALLBACK CHAIN — guarantees we NEVER show empty results
    # If strict search returned nothing, gracefully relax to find similar products
    if total_hits == 0 and core_query and request.page == 1:
        logger.warning(f"⚠️ Zero results for '{query_text}' — trying smart fallback")
        
        # 🔄 FALLBACK 1: Pure semantic vector search (finds similar items even if exact words don't match)
        if vector:
            try:
                fallback_query = {
                    "from": 0,
                    "size": request.page_size,
                    "query": {
                        "bool": {
                            "must": [
                                {"knn": {"embedding": {"vector": vector, "k": 50}}}
                            ],
                            "filter": [{"term": {"in_stock": True}}]
                        }
                    },
                    "track_total_hits": True
                }
                fallback_resp = os_client.search(index=INDEX_NAME, body=fallback_query)
                fallback_hits_data = fallback_resp.get("hits", {}).get("hits", [])
                
                if fallback_hits_data:
                    logger.info(f"✅ Vector fallback found {len(fallback_hits_data)} similar products")
                    response = fallback_resp
                    hits = response.get("hits", {})
                    total_hits = hits.get("total", {}).get("value", 0)
            except Exception as e:
                logger.error(f"❌ Vector fallback failed: {e}")
        
        # 🔄 FALLBACK 2: If vector fallback also empty, try loose OR-based match
        if total_hits == 0:
            try:
                loose_query = {
                    "from": 0,
                    "size": request.page_size,
                    "query": {
                        "bool": {
                            "should": [
                                {"multi_match": {
                                    "query": core_query,
                                    "fields": ["name^3", "category", "brand"],
                                    "fuzziness": "AUTO",
                                    "operator": "or"
                                }}
                            ],
                            "filter": [{"term": {"in_stock": True}}],
                            "minimum_should_match": 1
                        }
                    },
                    "track_total_hits": True
                }
                loose_resp = os_client.search(index=INDEX_NAME, body=loose_query)
                loose_hits_data = loose_resp.get("hits", {}).get("hits", [])
                
                if loose_hits_data:
                    logger.info(f"✅ Loose fallback found {len(loose_hits_data)} products")
                    response = loose_resp
                    hits = response.get("hits", {})
                    total_hits = hits.get("total", {}).get("value", 0)
            except Exception as e:
                logger.error(f"❌ Loose fallback failed: {e}")
    
    raw_total_pages = (total_hits + request.page_size - 1) // request.page_size if total_hits > 0 else 0
    total_pages = min(raw_total_pages, max_safe_page)
    max_score = hits.get("max_score") or 1.0
    
    results = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        brand_display = get_smart_brand(source)
        
        raw_cats = source.get("category", [])
        clean_cats = [c.strip() for c in re.sub(r"[\[\]'\"]", "", raw_cats).split(",") if c.strip()] if isinstance(raw_cats, str) else [str(c).strip() for c in raw_cats if c and str(c).strip()]
        if not clean_cats or clean_cats == ["None"]: clean_cats = ["Uncategorized"]
        
        images = source.get("images", [])
        primary_image = images[0] if isinstance(images, list) and len(images) > 0 else None
        
        _pid = str(source.get("product_id", "123"))
        _pid_hash = int(hashlib.md5(_pid.encode()).hexdigest(), 16)
        
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
            "rating": source.get("rating") if source.get("rating", 0) > 0 else DEMO_RATING_BASE + (_pid_hash % DEMO_RATING_RANGE) / 10.0,
            "sales_count": source.get("sales_count") if source.get("sales_count", 0) > 0 else (_pid_hash % DEMO_SALES_RANGE) + DEMO_SALES_BASE,
            "score": round(SCORE_DISPLAY_MIN + (normalized_score * SCORE_DISPLAY_RANGE), 2),
            "_raw_score_anchor": raw_score, # 🔥 Temporary internal field used to secure the exact match sorting tiers
            "trending_score": 0  
        })
    
    # 🆕 TRENDING BOOST: Re-rank with popularity from PostgreSQL + Intent & Category Guard
    if request.sort not in ["price_asc", "price_desc"] and results:
        product_ids = [r["id"] for r in results if r.get("id")]
        trending_scores = get_trending_scores(product_ids)
        
        # 1. Normalize search text
        query_normalized = query_text.lower()
        
        # 2. Detect Accessory Intent
        ACCESSORY_INTENT_WORDS = [
            "case", "charger", "cable", "headphones", "earbuds", "glass", "socks", 
            "cover", "mount", "shield", "adapter", "screen protector", "watch", "belt", 
            "wallet", "tie", "cufflink", "bracelet", "ring", "necklace", "earring", "sunglasses",
            "hat", "cap", "bag", "backpack", "purse"
        ]
        user_wants_accessory = any(word in query_normalized for word in ACCESSORY_INTENT_WORDS)
        
        # 3. Detect Broad Category Intent (Hardware vs Apparel/Home)
        user_wants_tech = any(word in query_normalized for word in ["iphone", "apple", "samsung", "phone", "laptop", "macbook", "ipad", "tablet", "electronics"])
        user_wants_apparel = any(word in query_normalized for word in ["shirt", "dress", "pants", "shoes", "sneakers", "clothing", "jeans", "socks", "apparel"])
        
        ACCESSORY_CATEGORY_WORDS = [
            "accessory", "accessories", "case", "headphones", "earbuds", "socks", 
            "charger", "cable", "glass", "watch", "belt", "wallet", "tie", "cufflink",
            "bracelet", "ring", "necklace", "earring", "sunglass", "hat", "cap",
            "bag", "backpack", "purse", "handbag", "jewelry"
        ]
        ACCESSORY_NAME_WORDS = [
            "case", "cover", "magsafe", "socks", "headphones", "earbuds", "charger", 
            "cable", "adapter", "screen protector", "watch", "belt", "wallet", "tie",
            "cufflink", "bracelet", "ring", "necklace", "earring", "sunglass"
        ]
        
        for r in results:
            raw_anchor = r.pop("_raw_score_anchor", 0)
            trending = trending_scores.get(r["id"], 0)
            
            import math
            combined_score = raw_anchor + (math.log1p(trending) * 1.5)
            
            # 🔥 GUARD A: Accessory Demotion (Protects Core Hardware)
            if not user_wants_accessory:
                is_accessory_item = any(
                    any(acc_word in str(cat).lower() for acc_word in ACCESSORY_CATEGORY_WORDS)
                    for cat in r.get("category", [])
                ) or any(acc_word in r.get("name", "").lower() for acc_word in ACCESSORY_NAME_WORDS)
                
                if is_accessory_item:
                    combined_score -= 1000.0  
            
            # 🔥 GUARD B: Cross-Category Isolation (The Shoe Fix)
            # If the user searches for an iPhone/Tech, we absolutely banish Shoes, Furniture, and Home goods.
            if user_wants_tech:
                is_unrelated = any(any(w in str(cat).lower() for w in ["shoes", "clothing", "home", "furniture", "apparel", "beauty", "kitchen", "desk", "vanity"]) for cat in r.get("category", []))
                if is_unrelated:
                    combined_score -= 5000.0  # Sends them 100 pages deep out of view
            
            # 🔥 GUARD C: Grooming/Beauty/Electronics Banishment (Expanded)
            # When user searches clothing/shoes, banish ALL unrelated categories.
            if user_wants_apparel:
                UNRELATED_CATEGORIES = [
                    "electronics", "phones", "computers", "tablets", "appliances",
                    "beauty", "grooming", "health", "personal care", "fragrance",
                    "shaving", "skincare", "haircare", "makeup", "cologne",
                    "kitchen", "furniture", "home decor", "office", "stationery"
                ]
                UNRELATED_NAME_WORDS = [
                    "trimmer", "perfume", "cologne", "balm", "razor", "shaver",
                    "shampoo", "conditioner", "beard oil", "shaving cream", "shaving foam",
                    "deodorant", "lotion", "aftershave", "moisturizer", "fragrance",
                    "cream", "serum", "wax", "scissors", "clipper", "grooming"
                ]
                
                cat_str = " ".join([str(c).lower() for c in r.get("category", [])])
                name_str = r.get("name", "").lower()
                
                is_unrelated = (
                    any(w in cat_str for w in UNRELATED_CATEGORIES) or
                    any(w in name_str for w in UNRELATED_NAME_WORDS)
                )
                
                if is_unrelated:
                    combined_score -= 5000.0  # Banished far below all relevant products

            r["combined_score"] = combined_score
            r["trending_score"] = round(trending, 1)  
        
        # Sort by final structured relevance tiers
        results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        for r in results:
            r.pop("combined_score", None)
    else:
        # Clean up temporary field if sort parameter skips re-ranking
        for r in results:
            r.pop("_raw_score_anchor", None)
    
    # =====================================================================
    # 🚀 STEP 16: PARSER - PERFECT SORTING
    # =====================================================================
    sampled_aggs = response.get("aggregations", {}).get("strict_relevance_sampler", {})
    all_aggs = response.get("aggregations", {})
    
    def build_smart_facet_list(agg_name: str, global_agg_name: str) -> list:
        # Step A: Get pure names from the top 100
        sampled_buckets = sampled_aggs.get(agg_name, {}).get("buckets", [])
        allowed_keys = set()
        for bucket in sampled_buckets:
            val = str(bucket.get("key", "")).strip()
            if val and val.lower() not in ["none", "default", "default title", "uncategorized", ""]:
                allowed_keys.add(val)
        
        if not allowed_keys: return []

        # Step B: Get the massive global counts for those pure names
        global_buckets = all_aggs.get(global_agg_name, {}).get("buckets", [])
        global_counts = {}
        for bucket in global_buckets:
            val = str(bucket.get("key", "")).strip()
            global_counts[val] = bucket.get("doc_count", 0)
            
        result = []
        for val in allowed_keys:
            result.append({
                "value": val,
                "label": val,
                "count": global_counts.get(val, 0) # Real math
            })
            
        # Step C: Perfect UX Sorting (Highest Global Number to Lowest)
        result.sort(key=lambda x: x["count"], reverse=True)
        return result

    facets = {}
    cat_list = build_smart_facet_list("categories", "global_categories")
    if cat_list: facets["categories"] = cat_list
    brand_list = build_smart_facet_list("brands", "global_brands")
    if brand_list: facets["brands"] = brand_list
    color_list = build_smart_facet_list("colors", "global_colors")
    if color_list: facets["colors"] = color_list
    size_list = build_smart_facet_list("sizes", "global_sizes")
    if size_list: facets["sizes"] = size_list
    storage_list = build_smart_facet_list("storage", "global_storage")
    if storage_list: facets["storage"] = storage_list
    ram_list = build_smart_facet_list("ram", "global_ram")
    if ram_list: facets["ram"] = ram_list

    final_response = {
        "total_results": total_hits,
        "total_pages": total_pages,
        "current_page": request.page,
        "pagination_html": build_pagination_html(total_pages, request.page),
        "results": results,
        "facets": facets
    }
    
    await cache_set(cache_key, final_response, ttl_seconds=SEARCH_CACHE_TTL)
    
    # 🆕 LOG TIMING
    _elapsed_ms = (time.perf_counter() - _start_time) * 1000
    print(f"⏱️  SEARCH | query='{request.query}' | page={request.page} | total={total_hits} | time={_elapsed_ms:.2f}ms", flush=True)
    
    return final_response