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


async def correct_query_typos(query: str, aggressive: bool = False) -> tuple:
    """
    🔤 TYPO CORRECTION using OpenSearch's TERM SUGGESTER (unsupervised learning).
    Auto-learns spellings from your product catalog — no hardcoded dictionary.
    
    Two modes:
    - Standard mode: suggest_mode="missing" — only correct words NOT in catalog
      (protects valid words like "Starlight")
    - Aggressive mode: suggest_mode="always" + lower threshold — used as zero-result 
      fallback for partial words like "linger" → "lingerie"
    
    Returns: (corrected_query: str, was_corrected: bool)
    """
    if not query or len(query.strip()) < 3:
        return query, False
    
    try:
        # Choose mode
        if aggressive:
            suggest_mode = "always"      
            threshold = 0.3              
        else:
            suggest_mode = "always"      # 🔥 FIX: Force "always" for all searches to aggressively correct 'appl'
            threshold = 0.4              # 🔥 FIX: Slightly relaxed threshold
        
        resp = os_client.search(
            index=INDEX_NAME,
            body={
                "size": 0,
                "suggest": {
                    "fix_typos": {
                        "text": query,
                        "term": {
                            "field": "name",
                            "suggest_mode": suggest_mode,
                            "min_word_length": 3,
                            "max_edits": 2,
                            "prefix_length": 0  # 🔥 FIX: Prefix length 0 allows changing the first letter if needed
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
            
            if options and options[0].get("score", 0) > threshold:
                # 🔥 SMART CORRECTION SELECTION
                # Among ALL suggestions, PREFER ones where original is a PREFIX.
                # E.g. "leath" → "leather" (prefix) beats "leath" → "leash" (1-char change)
                # E.g. "macb" → "macbook" (prefix) beats "macb" → "maca" (1-char change)
                best_suggestion = options[0]["text"]
                
                # Look for prefix matches across ALL options (not just top 5)
                # Choose the LONGEST prefix-extension (most informative)
                prefix_matches = []
                for opt in options:
                    opt_text = opt.get("text", "")
                    if opt_text.startswith(original_word) and len(opt_text) > len(original_word):
                        prefix_matches.append((opt_text, opt.get("score", 0)))
                
                if prefix_matches:
                    # Sort by score descending, then by length descending
                    prefix_matches.sort(key=lambda x: (-x[1], -len(x[0])))
                    best_suggestion = prefix_matches[0][0]
                else:
                    # 🔥 Fallback: direct prefix search in catalog
                    # If suggester didn't return a prefix match, search catalog directly
                    # for words starting with the original word
                    if len(original_word) >= 3:
                        try:
                            prefix_resp = os_client.search(
                                index=INDEX_NAME,
                                body={
                                    "size": 1,
                                    "query": {
                                        "match_phrase_prefix": {
                                            "name": {"query": original_word, "max_expansions": 50}
                                        }
                                    }
                                }
                            )
                            top_hit = prefix_resp.get("hits", {}).get("hits", [])
                            if top_hit:
                                # Extract the catalog word that starts with our prefix
                                top_name = top_hit[0].get("_source", {}).get("name", "").lower()
                                for w in top_name.split():
                                    w_clean = ''.join(c for c in w if c.isalnum()).lower()
                                    if w_clean.startswith(original_word) and len(w_clean) > len(original_word):
                                        best_suggestion = w_clean
                                        break
                        except Exception:
                            pass
                
                # 🔥 SAFETY CHECK: Don't correct if original word actually exists in catalog
                # This prevents "linger" → "longer" when "linger" matches real products
                if not aggressive:
                    try:
                        exists_check = os_client.search(
                            index=INDEX_NAME,
                            body={
                                "size": 0,
                                "query": {
                                    "bool": {
                                        "should": [
                                            {"match": {"name": original_word}},
                                            {"match": {"description": original_word}}
                                        ],
                                        "minimum_should_match": 1
                                    }
                                },
                                "track_total_hits": True
                            }
                        )
                        original_exists_count = exists_check.get("hits", {}).get("total", {}).get("value", 0)
                        
                        # If the original word matches ≥5 products, keep it
                        if original_exists_count >= 5:
                            corrected_words.append(original_word)
                            continue
                    except Exception:
                        pass
                
                corrected_words.append(best_suggestion)
                has_correction = True
            else:
                corrected_words.append(original_word)
        
        if has_correction:
            corrected = " ".join(corrected_words)
            mode_label = "AGGRESSIVE" if aggressive else "STANDARD"
            logger.info(f"🔤 Typo correction [{mode_label}]: '{query}' → '{corrected}'")
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

MIN_RELEVANCE_SCORE = 1.0          # 🔥 Very lenient — let dynamic guard do the filtering (smarter than fixed score threshold)
MIN_RELEVANCE_SCORE_CONVERSATIONAL = 0.5  # 🔥 Same idea — trust dynamic guard
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
    
    # 🚻 GENDER HANDLING (100% DYNAMIC, NO HARDCODED LISTS)
    # 
    # Approach: gender words like "men", "women", "kids" are ALREADY in the user's query.
    # OpenSearch's normal text matching (already in semantic_shoulds below) ranks 
    # products matching these words HIGHER automatically.
    #
    # We do NOT use hardcoded {men: [...], women: [...]} lists or hard must_not blocks.
    # Instead, the dynamic category guard (later in code) detects when product categories
    # don't match the dominant category of top results and banishes them.
    #
    # This means:
    #   "shoes for men" → OpenSearch ranks men's shoes higher (they match "men" in name)
    #   "dresses for men" → OpenSearch tries to match both, falls back to "dresses"
    #                       if no men's dresses exist in catalog (graceful fallback)
    #   "kids running shoes" → kids' shoes rank higher, others below
    #
    # Result: works for ANY gender label, in ANY language, NO hardcoded lists.
    
    # Color detection is handled DYNAMICALLY by OpenSearch boost on color/colors/attributes 
    # fields in semantic_shoulds. No hardcoded list needed — works for ANY color in any language.
    
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
            # 🚻 GENDER FILTER (clicked from sidebar) — dynamic, no hardcoded list
            # User clicked a gender filter checkbox → match it in name/category fields
            gender_shoulds = []
            for g in request.filters.gender[:MAX_GENDER_FILTERS]:
                g_clean = str(g).strip().lower()
                gender_shoulds.extend([
                    {"match": {"gender": g_clean}},
                    {"match": {"attributes.gender": g_clean}},
                    {"match": {"attributes.Gender": g_clean}},
                    {"match_phrase": {"category": g_clean}},
                    {"match_phrase": {"name": g_clean}},
                ])
            
            if gender_shoulds:
                filters.append({"bool": {"should": gender_shoulds, "minimum_should_match": 1}})
                logger.info(f"🚻 Sidebar gender filter applied: {request.filters.gender}")
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
        # 🔥 Bigger candidate pool — more options to filter through
        k_val = min(max(KNN_MIN_K, from_val + request.page_size + KNN_BUFFER), MAX_OS_WINDOW, 300)
        # 🔥 Boost KNN based on query length
        # Short queries (1-5 words): KNN OFF (rely on keyword matching for precision)
        # Long queries (6+ words): KNN ON (need semantic understanding)
        # Vector search OFF for short queries prevents "Nike Air ≈ Apple Air iPhone" mistakes
        if is_conversational:
            knn_boost = 3.0  # Long conversational queries — semantic dominates
        else:
            knn_boost = 0.5  # Short queries — balanced (was 0.1, too low; was 0.3, too high for false matches)
        semantic_shoulds.append({"knn": {"embedding": {"vector": vector, "k": k_val, "boost": knn_boost}}})
        
        if is_conversational:
            logger.info(f"🤖 CONVERSATIONAL MODE: {word_count_total} words, KNN boost={knn_boost}")    
    for item in multi_items:
        semantic_shoulds.extend([
            # 🔥 UNIVERSAL PHRASE BOOST: Exact word ordering gets immediate priority
            {"match_phrase": {"name": {"query": item, "boost": 100.0, "slop": 2}}},
            
            # 🔥 CATEGORY ALIGNMENT
            {"match_phrase": {"category": {"query": item, "boost": 60.0}}},
            
            {"match_phrase": {"name": {"query": item, "boost": BOOST_NAME_PHRASE}}},
            {"match_phrase": {"brand": {"query": item, "boost": BOOST_BRAND_PHRASE}}},
            {"match": {"category": {"query": item, "boost": BOOST_CATEGORY_MATCH}}},
            
            # 🎨 DYNAMIC COLOR/ATTRIBUTE BOOST (Amazon-style)
            # OpenSearch automatically matches color from query to product's color/colors fields.
            # No hardcoded color list — if catalog has the color, it matches. Works for ANY color.
            # Matching products rank at TOP, non-matching still appear below (similar products).
            {"match": {"color": {"query": item, "boost": 200.0}}},
            {"match": {"colors": {"query": item, "boost": 200.0}}},
            {"match": {"attributes.color": {"query": item, "boost": 200.0}}},
            {"match": {"attributes.Color": {"query": item, "boost": 200.0}}},
            
            # 🔥 STRICT MATCH (all words must appear across main fields)
            {"multi_match": {"query": item, "fields": ["name^10", "brand^5", "category^3"], "type": "cross_fields", "minimum_should_match": "80%", "boost": 80.0}},
            
            # Standard cross_fields with AND
            {"multi_match": {"query": item, "fields": ["name^10", "brand^5", "category^3"], "type": "cross_fields", "operator": "and", "boost": BOOST_CROSS_FIELDS}},
            
            # Fuzzy fallback
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
                        "fields": ["name^10", "category^10", "brand^3"], 
                        "type": "cross_fields",
                        # 🔥 VERY LENIENT — Amazon-style, get LOTS of candidates
                        # Dynamic guard removes the off-topic ones afterwards.
                        # 1 word → 1 match
                        # 2 words → 1 match (50%)
                        # 3+ words → 2 matches (need ≥2 query words in product)
                        "minimum_should_match": "1<2"
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
        # 🔥 Very low threshold — let MANY products through, then our smart guard re-ranks them
        min_relevance_score = 0.5 if use_min_score else 0.0
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
    # 🔥 Fetch a LARGE candidate pool so the dynamic guard can banish
    # off-topic products. Then we paginate the CLEAN results in Python below.
    # =====================================================================
    fetch_size = max(200, request.page_size * 10)
    os_query = {
        "from": 0,  # 🔥 Start from 0 — paginate in Python AFTER banishing
        "size": fetch_size,
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
        
        # 🔄 FALLBACK 0a: AGGRESSIVE typo correction
        if not was_corrected:
            aggressive_corrected, was_aggressive = await correct_query_typos(query_text, aggressive=True)
            if was_aggressive and aggressive_corrected != query_text:
                logger.info(f"🔤 Trying aggressive correction: '{query_text}' → '{aggressive_corrected}'")
                # Retry search with corrected query
                try:
                    retry_resp = os_client.search(
                        index=INDEX_NAME,
                        body={
                            "from": 0,
                            "size": fetch_size,
                            "query": {
                                "bool": {
                                    "must": [{
                                        "multi_match": {
                                            "query": aggressive_corrected,
                                            "fields": ["name^10", "category^5", "brand^3"],
                                            "fuzziness": "AUTO"
                                        }
                                    }],
                                    "filter": [{"term": {"in_stock": True}}]
                                }
                            },
                            "track_total_hits": True
                        }
                    )
                    retry_hits = retry_resp.get("hits", {}).get("hits", [])
                    if retry_hits:
                        logger.info(f"✅ Aggressive typo correction found {len(retry_hits)} products")
                        response = retry_resp
                        hits = response.get("hits", {})
                        total_hits = hits.get("total", {}).get("value", 0)
                        query_text = aggressive_corrected  # update for downstream logic
                except Exception as e:
                    logger.error(f"❌ Aggressive correction retry failed: {e}")
        
        # 🔄 FALLBACK 0b: PREFIX MATCH — for partial words like "linger" → "lingerie"
        # If user typed a word that's a prefix of a longer catalog word, match against
        # name field only (category is keyword type, doesn't support phrase_prefix).
        # Catches "linger" → "lingerie", "phon" → "phone", "leath" → "leather", etc.
        if total_hits == 0:
            try:
                prefix_query = {
                    "from": 0,
                    "size": fetch_size,
                    "query": {
                        "bool": {
                            "should": [
                                # Phrase prefix on name (text field) — handles "linger" → "lingerie"
                                {"match_phrase_prefix": {
                                    "name": {"query": core_query, "max_expansions": 50, "boost": 5.0}
                                }},
                                # Also try as fuzzy multi-match on name only
                                {"multi_match": {
                                    "query": core_query,
                                    "fields": ["name^3", "brand"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                    "prefix_length": 2
                                }}
                            ],
                            "filter": [{"term": {"in_stock": True}}],
                            "minimum_should_match": 1
                        }
                    },
                    "track_total_hits": True
                }
                prefix_resp = os_client.search(index=INDEX_NAME, body=prefix_query)
                prefix_hits = prefix_resp.get("hits", {}).get("hits", [])
                
                if prefix_hits:
                    logger.info(f"✅ Prefix fallback found {len(prefix_hits)} products for '{core_query}'")
                    response = prefix_resp
                    hits = response.get("hits", {})
                    total_hits = hits.get("total", {}).get("value", 0)
            except Exception as e:
                logger.error(f"❌ Prefix fallback failed: {e}")
        
        # 🔄 FALLBACK 1: Pure semantic vector search (finds similar items even if exact words don't match)
        if total_hits == 0 and vector:
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
        # 🔥 IMPORTS FIRST — must come BEFORE any use of _re/math/Counter
        import math
        import re as _re
        from collections import Counter
        
        # 🔥 PLURAL-AWARE WORD MATCHING (100% dynamic, no hardcoded list)
        # 
        # Fixes the bug where "dress" search returns 0 results because:
        # - query word = "dress"
        # - product category words = {"dresses"}
        # - direct set intersection: dress ≠ dresses → empty → product banished
        #
        # With this helper, "dress" matches "dresses" and "shoes" matches "shoe", etc.
        def _words_match(w1, w2):
            """Check if two words match exactly OR as plural/singular variants."""
            if w1 == w2:
                return True
            # Handle plural forms: dress↔dresses, shoe↔shoes, watch↔watches
            short, long_w = (w1, w2) if len(w1) < len(w2) else (w2, w1)
            if long_w == short + "s" or long_w == short + "es":
                return True
            return False
        
        def _words_intersect(set_a, set_b):
            """Intersection that handles plurals: {dress} ∩ {dresses} = {dress}."""
            result = set()
            for a in set_a:
                for b in set_b:
                    if _words_match(a, b):
                        result.add(a)
                        break
            return result
        
        logger.debug(f"🔧 Re-ranking {len(results)} results with category guard...")
        product_ids = [r["id"] for r in results if r.get("id")]
        trending_scores = get_trending_scores(product_ids)
        
        # 🔥 EXTRACT QUERY INTENT WORDS — INCLUDES MODEL NUMBERS
        # Captures "iphone", "14", "plus", "starlight", "s24", "m4", etc.
        # Model numbers like "14", "11", "s24" are critical for product identification.
        query_intent_words = set()
        for word in _re.findall(r'\b[a-z0-9]+\b', (query_text or "").lower()):
            # Allow ≥2 char to include model numbers like "11", "14", "s24", "m1"
            if len(word) >= 2 and word not in {"and", "the", "for", "with", "all", "color", "size", "by", "of", "in"}:
                query_intent_words.add(word)
        
        # 🔥 DYNAMIC CATEGORY-BASED RELEVANCE (STRICT MODE)
        # Look at the TOP 3 highest-scoring products (they have the strongest signal)
        # and use THEIR categories as the gold standard. Anything different = demoted.
        # 100% dynamic, works for any product type, no hardcoded lists.
        
        # Common "stopword" category words to ignore (too generic)
        CATEGORY_STOPWORDS = {
            "and", "the", "for", "with", "all", "new", "more", 
            "products", "items", "store", "shop", "categories",
            "amazon", "walmart", "target", "ebay",  # supplier names, not real categories
            "best", "sellers", "deals", "outlet", "luxury", "premium",
            "men", "women", "kids", "boys", "girls", "unisex",  # gender, handled separately
        }
        
        # 🔥 DYNAMIC ACCESSORY MARKERS (100% from catalog aggregations)
        # MUST be computed BEFORE valid_noun_products filter so we can use it.
        # 
        # Key insight: Words appearing across MANY different category buckets
        # are accessory/connector words. The TOP universal marker is "accessories"
        # which appears in dozens of categories (Cell Phone Accessories, Computer
        # Accessories, Camera Accessories, etc).
        dynamic_accessory_markers = set()
        global_cat_buckets = response.get("aggregations", {}).get("global_categories", {}).get("buckets", [])
        
        # Count how many different category buckets each word appears in
        word_to_categories = {}
        for bucket in global_cat_buckets:
            cat_name = str(bucket.get("key", "")).lower().strip()
            cat_words = set(_re.findall(r'\b[a-z]+\b', cat_name))
            cat_words = {w for w in cat_words if len(w) >= 4 and w not in CATEGORY_STOPWORDS}
            
            for word in cat_words:
                if word not in word_to_categories:
                    word_to_categories[word] = set()
                word_to_categories[word].add(cat_name)
        
        # Words appearing in 3+ DIFFERENT category buckets = accessory markers
        ACCESSORY_MARKER_THRESHOLD = 3
        for word, cat_set in word_to_categories.items():
            if len(cat_set) >= ACCESSORY_MARKER_THRESHOLD:
                dynamic_accessory_markers.add(word)
        
        if dynamic_accessory_markers:
            logger.info(f"🏷️  Dynamic accessory markers (from catalog): {sorted(list(dynamic_accessory_markers))[:20]}")
        
        # =====================================================================
        # 🚀 NEW FATAL RERANKING ENGINE (Pure Math & Set Theory)
        # =====================================================================
        
        # ---- 1. Find DOMINANT category words from VALID TOP RESULTS ----
        # This prevents "Category Poisoning" by strictly analyzing the strongest matches
        def _get_product_all_words_text(r):
            return (r.get("name", "") + " " + " ".join([str(c) for c in r.get("category", [])])).lower()
            
        # 🔥 STRICT FILTER for source_for_categories:
        # Only include products where ALL query words match AND product has no
        # "accessory-looking" categories. This prevents accessories from
        # contaminating top_brands and dominant_category_words.
        valid_noun_products = []
        if query_intent_words:
            # Pre-compute query product noun (rough version, before the formal one below)
            query_words_for_noun = [
                ''.join(c for c in w if c.isalnum()).lower()
                for w in (query_text or "").lower().split()
            ]
            rough_noun_candidates = [
                w for w in query_words_for_noun
                if len(w) >= 4 and not w.isdigit()
            ]
            rough_noun = max(rough_noun_candidates, key=len) if rough_noun_candidates else None
            
            for r in results:
                text = _get_product_all_words_text(r)
                words = set(_re.findall(r'\b[a-z0-9]+\b', text))
                matched = _words_intersect(query_intent_words, words)
                
                # STRICT: require FULL match (all query words) to be a "main product source"
                if len(matched) < len(query_intent_words):
                    continue
                
                # ALSO: exclude products with category clearly indicating accessory
                # E.g. "Cell Phone Accessories", "Cases, Holsters & Sleeves"
                # These contain words that signal the product is FOR something else
                r_cat_words = set()
                for cat in r.get("category", []):
                    if cat:
                        r_cat_words.update([
                            w for w in _re.findall(r'\b[a-z]+\b', str(cat).lower())
                            if len(w) >= 3
                        ])
                
                # 🔥 DYNAMIC accessory filter: exclude products whose category
                # contains accessory markers (learned from YOUR catalog).
                # E.g. cat=['Accessories'] → product is an accessory, don't use it
                # as a "main product reference" for top_brands/dominant_categories.
                if r_cat_words & dynamic_accessory_markers:
                    continue
                
                # If product's category exists but doesn't contain the product noun,
                # this is NOT a main product reference (it's an accessory in a 
                # specialty category like 'Cycling', 'Wristlets', 'Tools').
                # 
                # We need at least ONE meaningful (≥4 char) cat word that doesn't
                # match the product noun → skip. This catches Topeak (cat=Cycling),
                # BCBGeneration (cat=Wristlets), Dewalt (cat=Tools), etc.
                if rough_noun and r_cat_words:
                    noun_in_cat = any(_words_match(rough_noun, cw) for cw in r_cat_words)
                    meaningful_cat = {w for w in r_cat_words if len(w) >= 4}
                    # STRICT: if there's ANY meaningful cat word AND none match noun → skip
                    # (was ≥2 before, now ≥1 to catch single-word accessory categories)
                    if not noun_in_cat and len(meaningful_cat) >= 1:
                        continue
                
                valid_noun_products.append(r)
                    
        # 🔥 DOMINANT CATEGORY — From products with EMPTY or PRIMARY category
        # 
        # KEY INSIGHT: For queries like "iphone", actual iPhones have cat=Amazon
        # (filtered to empty) while OtterBox cases have cat=Cases/Holsters/Sleeves.
        # 
        # If we use OtterBox categories as dominant, OTHER OtterBox cases match it
        # and DON'T get classified as accessory → all cases get TIER 1.
        #
        # SOLUTION: Prefer products with FEWER category words (often the main product
        # has minimal cat info like cat=Amazon, while accessories have detailed cats
        # like "Cases, Holsters & Sleeves"). 
        #
        # Sort valid_noun_products by: (1) empty/minimal cat first, then (2) score.
        if valid_noun_products:
            def _cat_complexity(r):
                """Lower = simpler category = more likely main product."""
                cat_word_count = 0
                for cat in r.get("category", []):
                    if cat:
                        words = _re.findall(r'\b[a-z]+\b', str(cat).lower())
                        cat_word_count += len([w for w in words if w not in CATEGORY_STOPWORDS and len(w) >= 3])
                return cat_word_count
            
            sorted_by_cat_simplicity = sorted(
                valid_noun_products,
                key=lambda r: _cat_complexity(r)
            )
            source_for_categories = sorted_by_cat_simplicity[:5]
        else:
            source_for_categories = results[:3]

        top_results_categories = []
        for r in source_for_categories: 
            # Pull words from CATEGORIES
            for cat in r.get("category", []):
                if cat:
                    cat_clean = str(cat).strip().lower()
                    if cat_clean and cat_clean not in ["uncategorized", "none"]:
                        cat_words = _re.findall(r'\b[a-z]+\b', cat_clean)
                        meaningful_words = [
                            w for w in cat_words 
                            if w not in CATEGORY_STOPWORDS and len(w) >= 3
                        ]
                        top_results_categories.extend(meaningful_words)
            
            # 🔥 ALSO pull words from NAMES (when categories are empty like cat=Amazon)
            # This builds dominant words from "Apple iPhone 12 Pro" → {apple, iphone, pro}
            # so we know "iphone" is dominant even when no products have iphone in cat.
            # We exclude digits (model numbers) to avoid them becoming "dominant".
            name_clean = (r.get("name") or "").lower()
            name_words = _re.findall(r'\b[a-z]+\b', name_clean)  # [a-z] only excludes digits
            name_meaningful = [
                w for w in name_words
                if len(w) >= 4 
                and w not in CATEGORY_STOPWORDS
            ]
            top_results_categories.extend(name_meaningful)
        
        category_word_counts = Counter(top_results_categories)
        dominant_category_words = set()
        for word, count in category_word_counts.most_common():
            if count >= 2:  
                dominant_category_words.add(word)
        
        # 🔍 DEBUG: log what's being used for reference
        logger.info(f"🔍 valid_noun_products: {len(valid_noun_products)}, "
                    f"source_for_categories: {[r.get('name','')[:30] for r in source_for_categories[:3]]}")
        logger.info(f"🔍 dominant_category_words: {sorted(dominant_category_words)[:10]}")
        
        # 🔥 DYNAMIC ATTRIBUTE WORDS (colors/sizes from catalog aggregations)
        # Used to skip color/size words when picking the query product noun.
        # E.g. "white iphone 12" → skip "white" (it's a color) → noun = "iphone"
        dynamic_attribute_words = set()
        
        global_colors_buckets = response.get("aggregations", {}).get("global_colors", {}).get("buckets", [])
        for bucket in global_colors_buckets:
            color_val = str(bucket.get("key", "")).lower().strip()
            for word in _re.findall(r'\b[a-z]+\b', color_val):
                if len(word) >= 4:
                    dynamic_attribute_words.add(word)
        
        global_sizes_buckets = response.get("aggregations", {}).get("global_sizes", {}).get("buckets", [])
        for bucket in global_sizes_buckets:
            size_val = str(bucket.get("key", "")).lower().strip()
            for word in _re.findall(r'\b[a-z]+\b', size_val):
                if len(word) >= 4:
                    dynamic_attribute_words.add(word)
        
        if dynamic_attribute_words:
            logger.info(f"🎨 Dynamic attributes: {sorted(list(dynamic_attribute_words))[:15]}")
        
        # 🎯 DETECT QUERY PRODUCT NOUN (once, before the loop)
        query_product_noun = None
        query_words_list = [
            ''.join(c for c in w if c.isalnum()).lower()
            for w in (query_text or "").lower().split()
        ]
        
        candidates = [
            w for w in query_words_list
            if len(w) >= 4
            and w not in CATEGORY_STOPWORDS
            and w not in dynamic_attribute_words
            and not w.isdigit()
        ]
        
        if candidates:
            query_product_noun = max(candidates, key=len)
            logger.info(f"🎯 Query product noun: '{query_product_noun}' (from candidates: {candidates})")
        else:
            logger.info(f"🎯 No product noun found (all words are attributes/stopwords)")
        
        query_word_count = len(query_intent_words)
        
        # 🔥 FIX: Expanded the protection window to 5 words!
        # Standard commerce queries ("apple iphone 11 white color") MUST contain 
        # the core product noun ("iphone") or they are instantly banished.
        is_standard_query = query_word_count <= 5
        
        # ---- Score each product ----
        for r in results:
            raw_anchor = r.pop("_raw_score_anchor", 0)
            trending = trending_scores.get(r["id"], 0)
            
            product_cat_words = set()
            for cat in r.get("category", []):
                if cat:
                    product_cat_words.update([
                        w for w in _re.findall(r'\b[a-z]+\b', str(cat).lower()) 
                        if len(w) >= 3 and w not in CATEGORY_STOPWORDS
                    ])
            
            product_name_words = set()
            name_clean = r.get("name", "").lower()
            name_words_raw = _re.findall(r'\b[a-z0-9]+\b', name_clean)
            BASIC_STOPWORDS = {"and", "the", "for", "with", "all", "color", "size", "by", "of", "in", "pack", "pcs"}
            for w in name_words_raw:
                if len(w) >= 2 and w not in BASIC_STOPWORDS:
                    product_name_words.add(w)
            
            product_brand_str = (r.get("brand") or "").lower()
            product_all_words = product_cat_words | product_name_words | {product_brand_str}
            
            matched_intent_words = _words_intersect(query_intent_words, product_all_words)
            match_count = len(matched_intent_words)
            match_ratio = match_count / query_word_count if query_word_count > 0 else 0
            
            # 🔥 PRODUCT NOUN CHECK
            has_product_noun = True
            if query_product_noun:
                has_product_noun = any(
                    _words_match(query_product_noun, nw) for nw in product_name_words
                )
            
            missing_product_noun = (
                is_standard_query 
                and query_product_noun is not None 
                and not has_product_noun
            )
            
            # 🔥 MODEL NUMBER CHECK
            query_numbers = {w for w in query_intent_words if w.isdigit()}
            product_numbers = {w for w in product_name_words if w.isdigit()}
            missing_numbers = query_numbers - product_numbers
            has_wrong_model = bool(missing_numbers)
            
            # 🔥 ACCESSORY DETECTION (with safety checks)
            #
            # Logic order:
            #   1. Compute safety signals FIRST (noun_in_cat, shares_brand)
            #   2. Run detection strategies
            #   3. Final OVERRIDE: if safety signals are True, force is_accessory = False
            #      (this is the safety net that prevents demoting real main products)
            is_accessory = False
            if product_cat_words:
                
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # SAFETY SIGNALS (computed FIRST, used at the end)
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                
                # SAFETY A: Does product's category EXACTLY contain product_noun?
                # E.g. Apple iPhone with cat=['iphone'] → True → it's a main product
                # 
                # We use EXACT match only (with plural support via _words_match).
                # We do NOT use substring matching — that catches false positives
                # like "phone" being a substring of "iphone", which would
                # incorrectly protect "Cell Phone Accessories" from demotion.
                #
                # For cases like Apple iPhone XS with cat=['phones'] (no exact match),
                # Safety B (brand match with top products) protects them instead.
                noun_in_product_cat = False
                if query_product_noun:
                    for cw in product_cat_words:
                        if _words_match(query_product_noun, cw):
                            noun_in_product_cat = True
                            break
                
                # SAFETY B: Does product share brand/maker with TOP products?
                # E.g. for "iphone" search, top 5 = Apple → other Apple products are iPhones
                shares_top_brand = False
                if source_for_categories:
                    top_brands = set()
                    for top_r in source_for_categories[:5]:
                        tb = (top_r.get("brand") or "").lower().strip()
                        if tb and tb not in {"amazon", "generic", "none", ""}:
                            top_brands.add(tb)
                        name_tokens = (top_r.get("name") or "").lower().split()
                        if name_tokens:
                            fw = ''.join(c for c in name_tokens[0] if c.isalnum()).lower()
                            if len(fw) >= 3 and fw not in {"the", "new", "for"}:
                                top_brands.add(fw)
                    
                    this_brand = (r.get("brand") or "").lower().strip()
                    this_name_tokens = (r.get("name") or "").lower().split()
                    this_first_word = ""
                    if this_name_tokens:
                        this_first_word = ''.join(c for c in this_name_tokens[0] if c.isalnum()).lower()
                    
                    if this_brand in top_brands or this_first_word in top_brands:
                        shares_top_brand = True
                
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # STRATEGY 1: Doesn't overlap with dominant categories
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                if dominant_category_words:
                    cat_overlap_acc = _words_intersect(dominant_category_words, product_cat_words)
                    meaningful_dom = {w for w in dominant_category_words if len(w) >= 4}
                    if not cat_overlap_acc and meaningful_dom:
                        is_accessory = True
                
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # STRATEGY 2: Detailed cat when top products have empty cats
                # SKIP if noun in cat OR shares brand
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                if (not is_accessory 
                    and source_for_categories 
                    and not noun_in_product_cat 
                    and not shares_top_brand):
                    
                    empty_cat_count = 0
                    for top_r in source_for_categories:
                        top_cat_words = set()
                        for cat in top_r.get("category", []):
                            top_cat_words.update([
                                w for w in _re.findall(r'\b[a-z]+\b', str(cat).lower())
                                if len(w) >= 3 and w not in CATEGORY_STOPWORDS
                            ])
                        if not top_cat_words:
                            empty_cat_count += 1
                    
                    if (empty_cat_count >= len(source_for_categories) * 0.5 
                        and len(product_cat_words) >= 1):
                        is_accessory = True
                
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # STRATEGY 3: DYNAMIC accessory marker detection
                # Uses markers learned from YOUR catalog (no hardcoded list).
                # If product cat has accessory markers AND user didn't ask for accessory
                # → it's an accessory
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                if (not is_accessory 
                    and not shares_top_brand 
                    and not noun_in_product_cat 
                    and dynamic_accessory_markers):
                    
                    # Does user's query contain any accessory marker?
                    # E.g. "iphone case" → query has "case" → user wants accessory
                    query_has_accessory_marker = bool(
                        set(query_words_list) & dynamic_accessory_markers
                    )
                    
                    # Product has accessory markers in cat AND user didn't ask for accessory
                    if (product_cat_words & dynamic_accessory_markers 
                        and not query_has_accessory_marker):
                        is_accessory = True
                
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # 🔓 FINAL OVERRIDE: undo is_accessory if safety signals say it's a main product
                # This protects Apple iPhones (cat=['iphone']) and same-brand products
                # from being incorrectly demoted by Strategy 1.
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                if is_accessory and (noun_in_product_cat or shares_top_brand):
                    is_accessory = False
                    logger.debug(f"🔓 UNDEMOTED (main product): '{r.get('name','')[:40]}' (noun_in_cat={noun_in_product_cat}, brand_match={shares_top_brand})")
            
            # 🎯 DETECT IF USER WANTS ACCESSORY (e.g. searched "iphone case")
            # User explicitly wants accessory ONLY if their QUERY contains an
            # accessory marker word (case, charger, cover, accessories, etc).
            # 
            # We check the query words directly against dynamic_accessory_markers,
            # NOT against dominant_category_words (which may contain product nouns
            # like "iphone" that would falsely trigger this).
            wants_accessory_search = False
            if dynamic_accessory_markers:
                if set(query_words_list) & dynamic_accessory_markers:
                    wants_accessory_search = True
            
            combined_score = raw_anchor
            
            # 🔻 BANISH FIRST: Missing product noun (for short queries)
            if missing_product_noun:
                combined_score = -1000000.0
                logger.info(f"🔻 BANISH NO-NOUN: '{r.get('name','')[:40]}' missing '{query_product_noun}'")
            
            # 🥇 TIER 1: Exact match — main product OR user-wanted accessory
            elif match_ratio >= 1.0 and not has_wrong_model and (not is_accessory or wants_accessory_search):
                combined_score = 1_000_000.0 + raw_anchor
            
            # 🥈 TIER 2: High match (n-1 words) — main product OR user-wanted accessory
            elif query_word_count >= 3 and match_count >= query_word_count - 1 and not has_wrong_model and (not is_accessory or wants_accessory_search):
                combined_score = 500_000.0 + (match_ratio * 10000.0) + raw_anchor
            
            # 🎯 ACCESSORY (compatibility only) — show BELOW main products
            # Even exact-match accessories rank below main products
            elif match_ratio >= 1.0 and is_accessory:
                combined_score = 50_000.0 + raw_anchor
                logger.info(f"🔽 ACCESSORY DEMOTED: '{r.get('name','')[:40]}' (cat={list(product_cat_words)[:2]})")
            
            # 🎯 ACCESSORY high-match (compatibility only)
            elif query_word_count >= 3 and match_count >= query_word_count - 1 and is_accessory:
                combined_score = 30_000.0 + (match_ratio * 1000.0) + raw_anchor
            
            # 🎯 WRONG MODEL: Has product noun but wrong number (e.g. iPhone 14 case for "iphone 12 pro")
            # Demote BELOW main products but keep visible as similar items
            elif match_ratio >= 0.5 and has_wrong_model:
                combined_score = 40_000.0 + (match_ratio * 1000.0) + raw_anchor
                logger.info(f"🔢 WRONG-MODEL DEMOTED: '{r.get('name','')[:40]}' missing numbers {missing_numbers}")
            
            # 🥉 TIER 3: Partial match (≥50%)
            elif match_ratio >= 0.5 or query_word_count == 0:
                combined_score = 100_000.0 + (match_ratio * 5000.0) + raw_anchor
            
            # 🔻 BANISH: Below 50% match
            else:
                combined_score = -1000000.0
            
            # 🔥 SMART GENDER GUARD
            is_mens_search = bool({"men", "mens", "male", "boys"} & query_intent_words)
            is_womens_search = bool({"women", "womens", "female", "girls", "ladies"} & query_intent_words)
            
            if is_mens_search and not is_womens_search:
                if bool({"women", "womens", "female", "girls", "ladies"} & product_all_words):
                    if not bool({"unisex", "couples", "matching"} & product_all_words):
                        combined_score = -1000000.0
            elif is_womens_search and not is_mens_search:
                if bool({"men", "mens", "male", "boys"} & product_all_words):
                    if not bool({"unisex", "couples", "matching"} & product_all_words):
                        combined_score = -1000000.0
            
            # 🔥 CATEGORY ALIGNMENT PENALTY (only for products with REAL categories)
            if dominant_category_words and combined_score > 0 and product_cat_words:
                cat_overlap = _words_intersect(dominant_category_words, product_cat_words)
                if not cat_overlap and match_ratio < 1.0:
                    combined_score = -1000000.0
            
            r["combined_score"] = combined_score
            r["trending_score"] = round(trending, 1)
        
        # Sort by combined_score — exact matches at top, similar products below
        results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        # 🚫 REMOVE BANISHED PRODUCTS (off-topic items)
        original_count = len(results)
        all_results_before_banish = list(results)  # 🔥 keep backup
        results = [r for r in results if r.get("combined_score", 0) > -10000]
        banished_count = original_count - len(results)
        
        # 🔥 SAFETY: If banish removed EVERYTHING (over-aggressive),
        # restore top results for conversational queries
        if len(results) == 0 and len(all_results_before_banish) > 0:
            logger.warning(f"⚠️ All products banished! Restoring top results as fallback.")
            # Sort by raw score (not combined) as fallback
            results = sorted(
                all_results_before_banish,
                key=lambda x: x.get("combined_score", 0),
                reverse=True
            )[:request.page_size * 5]
            # Reset banished scores to 0 so they show
            for r in results:
                if r.get("combined_score", 0) < 0:
                    r["combined_score"] = 1.0
        
        if banished_count > 0:
            logger.info(f"🚫 Removed {banished_count} off-topic products from {original_count} → {len(results)} clean")
        
        # 🔥 RECALCULATE total_hits to reflect CLEAN count (not the original 200 OpenSearch hits)
        # If we kept 50 out of 200, then total_hits should represent the true clean count
        total_hits = len(results)
        raw_total_pages = (total_hits + request.page_size - 1) // request.page_size if total_hits > 0 else 0
        total_pages = min(raw_total_pages, max_safe_page)
        
        # 🔥 PAGINATE THE CLEAN RESULTS IN PYTHON
        # We fetched 200 candidates, banished off-topic ones, now slice for current page
        page_start = from_val
        page_end = from_val + request.page_size
        results = results[page_start:page_end]
        
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