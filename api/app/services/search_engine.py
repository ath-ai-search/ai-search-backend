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
            suggest_mode = "always"      # Try to correct even valid words
            threshold = 0.4              # Lower confidence threshold
        else:
            suggest_mode = "missing"     # Only words not in catalog
            threshold = 0.7              # Higher confidence
        
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
                            "min_word_length": 4,
                            "max_edits": 2,
                            "prefix_length": 1
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
        
        # ---- 1. Find DOMINANT category words from TOP 3 results ONLY ----
        # 🔥 TOP 3 is more reliable than top 10. Top 3 = strongest matches.
        # Using top 10 lets accessories at positions 6-10 pollute the signal.
        # Example: "iphone 14 plus midnight" top 3 = iPhones (cat=Amazon, filtered)
        # → dominant_category_words = only query words → accessory headphones get banished.
        top_results_categories = []
        for r in results[:3]:  # 🔥 TOP 3 ONLY for clean signal
            for cat in r.get("category", []):
                if cat:
                    cat_clean = str(cat).strip().lower()
                    if cat_clean and cat_clean not in ["uncategorized", "none"]:
                        cat_words = _re.findall(r'\b[a-z]+\b', cat_clean)
                        meaningful_words = [
                            w for w in cat_words 
                            if w not in CATEGORY_STOPWORDS and len(w) >= 4
                        ]
                        top_results_categories.extend(meaningful_words)
        
        # Count word frequency
        category_word_counts = Counter(top_results_categories)
        
        # 🔥 Word must appear in ≥2 of top 3 to be considered dominant
        dominant_category_words = set()
        for word, count in category_word_counts.most_common():
            if count >= 2:  # appears in at least 2 of top 3
                dominant_category_words.add(word)
        
        # 🎯 ESSENTIAL BRAND DETECTION (100% dynamic, from OpenSearch global aggregation)
        # 
        # Why GLOBAL aggregation (not top 10 results):
        # For short queries like "iphone", OpenSearch ranks SHORT product names higher.
        # OtterBox case names are short ("Otterbox Defender for iPhone 14") so they
        # dominate top 10. Apple iPhone names are longer ("Apple iPhone 14 Plus, 256GB,
        # Midnight - Unlocked Renewed") so they rank lower despite being the main product.
        #
        # SOLUTION: Use OpenSearch's global_brands aggregation which counts brands
        # across ALL matching products (not just top 10). 
        # 
        # Example for "iphone" query:
        # - Top 10 results: 8 OtterBox + 2 Apple (skewed by ranking)
        # - Global aggregation: 50 Apple, 25 OtterBox, 15 others (full picture)
        # - Apple = 55% of matches → APPLE is essential brand ✓
        essential_brand = None
        
        global_brands_buckets = response.get("aggregations", {}).get("global_brands", {}).get("buckets", [])
        
        if global_brands_buckets and len(global_brands_buckets) >= 1:
            total_matching = sum(b.get("doc_count", 0) for b in global_brands_buckets)
            top_brand_bucket = global_brands_buckets[0]
            top_brand_name = str(top_brand_bucket.get("key", "")).lower().strip()
            top_brand_count = top_brand_bucket.get("doc_count", 0)
            
            if total_matching > 0 and top_brand_name and len(top_brand_name) >= 3:
                top_brand_ratio = top_brand_count / total_matching
                
                # 🔥 If top brand has 40%+ of ALL matches, it's the essential brand
                # 40% threshold:
                #   - "iphone" → Apple = 50%+ → essential (good!)
                #   - "running shoes" → Nike = 25-30% → not essential (good, multi-brand)
                #   - "dresses" → top brand = 5% → not essential (good, varied)
                if top_brand_ratio >= 0.4:
                    essential_brand = top_brand_name
                    logger.info(
                        f"🏷️ Essential brand detected: '{essential_brand}' "
                        f"({top_brand_count}/{total_matching} = {top_brand_ratio:.0%} of all matches)"
                    )
                else:
                    top_3_brands = [(b.get("key"), b.get("doc_count")) for b in global_brands_buckets[:3]]
                    logger.info(
                        f"🏷️ No dominant brand (top {top_brand_ratio:.0%} < 40%): {top_3_brands}"
                    )
        
        # 🎯 QUERY PRODUCT NOUN: The core "type" the user is searching for
        # First ≥4-char meaningful word in query becomes the product noun.
        # 
        # Examples:
        #   "iphone 11 white"          → "iphone"
        #   "samsung galaxy s24"       → "samsung"  (then "galaxy" as fallback)
        #   "macbook pro 16"           → "macbook"
        #   "running shoes"            → "running"
        #
        # TIER 3 (accessories) requires this word in product name — prevents
        # Cuisinart "11 white" cookware from being classified as iPhone accessory.
        query_product_noun = None
        for word in (query_text or "").lower().split():
            word_clean = ''.join(c for c in word if c.isalnum()).lower()
            if len(word_clean) >= 4 and word_clean not in CATEGORY_STOPWORDS:
                query_product_noun = word_clean
                break
        
        if query_product_noun:
            logger.info(f"🎯 Query product noun: '{query_product_noun}'")
        
        # 🎯 OPERATIVE BRAND: Use essential_brand or derive from exact matches
        # 
        # If global aggregation didn't find a dominant brand (e.g. Apple < 40% for
        # "iphone 11 white" because catalog has many cases), look at products that
        # exactly match all query words — their brands tell us the user's intent.
        #
        # Example: "iphone 11 white" exact matches → all Apple iPhones → operative_brand = "apple"
        # Example: "running shoes" exact matches → Nike, Adidas, ASICS (mixed) → no operative_brand
        operative_brand = essential_brand
        if not operative_brand and query_intent_words and len(query_intent_words) >= 2:
            exact_match_brand_candidates = []
            for r in results[:50]:
                name = (r.get("name") or "").lower()
                name_words_set = set(_re.findall(r'\b[a-z0-9]+\b', name))
                matched = query_intent_words & name_words_set
                if len(matched) == len(query_intent_words):
                    # Exact match — extract brand signal from first 2 words of name
                    first_tokens = name.split()[:2]
                    for tok in first_tokens:
                        tok_clean = ''.join(c for c in tok if c.isalnum()).lower()
                        if len(tok_clean) >= 3 and tok_clean not in {"the", "for", "new", "with", "from", "amazon", "generic", "your", "all"}:
                            exact_match_brand_candidates.append(tok_clean)
                            break
            
            if exact_match_brand_candidates:
                brand_counts_em = Counter(exact_match_brand_candidates)
                most_common_em, count_em = brand_counts_em.most_common(1)[0]
                total_em = len(exact_match_brand_candidates)
                # Use only if ONE brand dominates exact matches (≥50%)
                if count_em / total_em >= 0.5:
                    operative_brand = most_common_em
                    logger.info(
                        f"🎯 Operative brand from exact matches: '{operative_brand}' "
                        f"({count_em}/{total_em})"
                    )
                else:
                    logger.info(
                        f"🎯 Multiple brands in exact matches — no brand filter: "
                        f"{brand_counts_em.most_common(3)}"
                    )
        
        # 🔥 STRONGER: Always add query intent words FIRST — they're the most reliable signal
        # User TYPED these words — they know what they want.
        # "formal red dresses for men" → dresses, formal, red, men become required
        dominant_category_words.update(query_intent_words)
        
        # 🔥 Check if any query word also appears as a real category (extra signal)
        query_words = _re.findall(r'\b[a-z]+\b', (query_text or "").lower())
        for word in query_words:
            if len(word) >= 4 and word not in CATEGORY_STOPWORDS:
                appears_in_any_category = any(
                    word in " ".join([str(c).lower() for c in r.get("category", [])])
                    for r in results
                )
                if appears_in_any_category:
                    dominant_category_words.add(word)
        
        if dominant_category_words:
            logger.info(f"🎯 Dynamic category intent (combined): {sorted(list(dominant_category_words))[:10]}")
        
        # ---- 2. Score each product based on category + name alignment ----
        for r in results:
            raw_anchor = r.pop("_raw_score_anchor", 0)
            trending = trending_scores.get(r["id"], 0)
            # 🔥 Trending boost REMOVED from main scoring — was causing exact matches to rank lower
            # Trending only displayed in the result, not used for ranking
            combined_score = raw_anchor
            
            # Get product CATEGORY words
            product_cat_words = set()
            for cat in r.get("category", []):
                if cat:
                    cat_words = _re.findall(r'\b[a-z]+\b', str(cat).lower())
                    meaningful = [w for w in cat_words if w not in CATEGORY_STOPWORDS and len(w) >= 4]
                    product_cat_words.update(meaningful)
            
            # 🔥 Get product NAME words — INCLUDES MODEL NUMBERS  
            # Captures alphanumeric tokens like "iphone", "14", "plus", "starlight", "s24"
            product_name_words = set()
            name_clean = r.get("name", "").lower()
            name_words = _re.findall(r'\b[a-z0-9]+\b', name_clean)
            for w in name_words:
                # Allow ≥2 to keep model numbers (11, 14, s24, m1, etc.)
                if len(w) >= 2 and w not in CATEGORY_STOPWORDS:
                    product_name_words.add(w)
            
            # Combine for full product signal
            product_all_words = product_cat_words | product_name_words
            
            # 🔥 SMART ALIGNMENT CHECK with GUARANTEED EXACT-MATCH PRIORITY
            # If product name contains ALL user query words → force to top of results.
            
            query_match_count = len(query_intent_words & product_name_words)
            query_match_ratio = query_match_count / len(query_intent_words) if query_intent_words else 0
            
            # Debug log removed — was for troubleshooting Starlight tokenization
            
            # ═══════════════════════════════════════════════════════════════════
            # 🎯 TIERED RANKING (100% DYNAMIC) — v2 STRICT
            #
            # TIER 1 (1,000,000+):  EXACT MATCH — all query words in product name
            # TIER 2 (500,000+):    RELATED — has operative_brand + product_noun OR ratio≥0.4
            # TIER 3 (100,000+):    ACCESSORY — different category but mentions product_noun
            # TIER 4 (+1k-5k):      Generic match (no brand context)
            # BANISH (-100,000):    UNRELATED — wrong brand AND no product_noun
            # ═══════════════════════════════════════════════════════════════════
            
            # 🔥 Plural-aware overlaps (dress ↔ dresses, shoe ↔ shoes)
            category_overlap = _words_intersect(dominant_category_words, product_cat_words) if dominant_category_words else set()
            name_overlap = _words_intersect(dominant_category_words, product_name_words) if dominant_category_words else set()
            
            product_brand_str = (r.get("brand") or "").lower()
            product_name_lower = (r.get("name") or "").lower()
            
            # 🎯 BRAND MATCH: Check if operative_brand appears in BRAND field OR
            # in the first 3 tokens of product name (more reliable than brand field
            # alone, since some products have brand="AMAZON" instead of actual brand).
            #
            # Default FALSE (was True — that was the bug!). A product passes the brand
            # check only if it explicitly has the operative brand.
            has_operative_brand = False
            if operative_brand:
                first_3_tokens = [w.strip(',.').lower() for w in product_name_lower.split()[:3]]
                has_operative_brand = (
                    operative_brand in product_brand_str or
                    operative_brand in first_3_tokens or
                    any(operative_brand in tok for tok in first_3_tokens if len(tok) >= 3)
                )
            
            # 🎯 PRODUCT NOUN MATCH: Does the product name contain the query's core noun?
            # Without this, Cuisinart "11 White" cookware would be classified as iPhone accessory
            # just because "11" and "white" match. We require "iphone" to be in name for it to
            # count as iPhone-related.
            has_product_noun = False
            if query_product_noun:
                # Check exact AND plural-aware (handles dress↔dresses)
                for nw in product_name_words:
                    if _words_match(query_product_noun, nw):
                        has_product_noun = True
                        break
            
            # 🎯 ACCESSORY: Product in different category that mentions the product noun
            # E.g. iPhone case has cat=Cases, name="Otterbox Case for iPhone" → accessory
            is_accessory = (
                len(product_cat_words) > 0 and       # has real category
                len(category_overlap) == 0 and       # different from search target
                has_product_noun                     # but mentions the product noun
            )
            
            # ═══════════════════════════════════════════════════════════════════
            # 🥇 TIER 1: EXACT MATCH (all query words in name)
            # ═══════════════════════════════════════════════════════════════════
            if query_match_ratio >= 1.0 and (len(query_intent_words) >= 2 or has_product_noun):
                combined_score = 1_000_000.0 + raw_anchor
                logger.info(
                    f"🥇 TIER 1 EXACT: '{r.get('name','')[:40]}' "
                    f"| all matched: {sorted(query_intent_words)[:5]}"
                )
            
            # ═══════════════════════════════════════════════════════════════════
            # 🥈 TIER 2: SAME-BRAND RELATED PRODUCT
            # Requires operative_brand to exist AND product to have it
            # AND (has product_noun OR ratio ≥ 0.4)
            # ═══════════════════════════════════════════════════════════════════
            elif operative_brand and has_operative_brand and (has_product_noun or query_match_ratio >= 0.4):
                combined_score = 500_000.0 + (query_match_ratio * 10000.0) + raw_anchor
                logger.info(
                    f"🥈 TIER 2 RELATED: '{r.get('name','')[:40]}' "
                    f"| brand='{operative_brand}' | ratio={query_match_ratio:.2f}"
                )
            
            # ═══════════════════════════════════════════════════════════════════
            # 🥉 TIER 3: COMPATIBLE ACCESSORY (different category, has product_noun)
            # E.g. iPhone case for "iphone 11 white" — at BOTTOM but still visible
            # ═══════════════════════════════════════════════════════════════════
            elif is_accessory:
                combined_score = 100_000.0 + (len(name_overlap) * 1000.0)
                logger.info(
                    f"🥉 TIER 3 ACCESSORY: '{r.get('name','')[:40]}' "
                    f"| cat={list(product_cat_words)[:2]}"
                )
            
            # ═══════════════════════════════════════════════════════════════════
            # TIER 4a: NO BRAND CONTEXT — strong name match
            # For generic searches like "dress" with no single brand
            # ═══════════════════════════════════════════════════════════════════
            elif not operative_brand and len(name_overlap) >= 2:
                combined_score += 1000.0 + (query_match_ratio * 5000.0)
            
            # ═══════════════════════════════════════════════════════════════════
            # TIER 4b: CATEGORY MATCH — strong category overlap
            # ═══════════════════════════════════════════════════════════════════
            elif len(category_overlap) >= 2:
                combined_score += 500.0 + (query_match_ratio * 2000.0)
            
            # ═══════════════════════════════════════════════════════════════════
            # TIER 5: HAS PRODUCT NOUN (weak but on-topic)
            # ═══════════════════════════════════════════════════════════════════
            elif has_product_noun:
                combined_score += 500.0
            
            # ═══════════════════════════════════════════════════════════════════
            # 🔻 BANISH: WRONG BRAND + NO PRODUCT NOUN = unrelated junk
            # E.g. Nike sneaker "size 11 white" for "iphone 11 white" search
            # E.g. Cuisinart "11-Cup White" for "iphone 11 white" search
            # ═══════════════════════════════════════════════════════════════════
            elif operative_brand and not has_operative_brand and not has_product_noun:
                combined_score -= 100000.0
                logger.info(
                    f"🔻 BANISH UNRELATED: '{r.get('name','')[:40]}' "
                    f"| no '{operative_brand}' brand | no '{query_product_noun}' word"
                )
            
            # ═══════════════════════════════════════════════════════════════════
            # 🔻 BANISH: OFF-TOPIC (no overlap, no product noun, has unrelated cat)
            # ═══════════════════════════════════════════════════════════════════
            elif not category_overlap and not has_product_noun and product_cat_words:
                combined_score -= 100000.0
                logger.info(
                    f"🔻 BANISH OFF-TOPIC: '{r.get('name','')[:40]}' "
                    f"| cat={list(product_cat_words)[:2]}"
                )
            
            r["combined_score"] = combined_score
            r["trending_score"] = round(trending, 1)  
        
        # Sort by combined_score — exact matches at top, similar products below
        results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        # 🚫 REMOVE BANISHED PRODUCTS (off-topic items)
        # iPhone search should NEVER show shoes. Shoes search should NEVER show phones.
        # The dynamic guard banishes off-topic products with -100000 penalty.
        original_count = len(results)
        results = [r for r in results if r.get("combined_score", 0) > -10000]
        banished_count = original_count - len(results)
        
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