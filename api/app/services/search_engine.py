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
            - total_pages: Total pages available
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
    # Generate unique cache key from request
    # Using JSON + MD5 hash ensures identical requests get same key
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:ai:{CACHE_VERSION}:{hashlib.md5(request_str.encode()).hexdigest()}"
    
    # Try cache first — if found, return immediately (super fast!)
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
    # Example: "macbook under 2000 on sale" becomes:
    #   core_query = "macbook"
    #   max_price = 2000
    #   is_sale = True
    query_text = request.query.strip() if request.query else ""
    matrix = extract_semantic_matrix(query_text)
    core_query = matrix["core_query"]
    
    # =====================================================================
    # STEP 5: HANDLE MULTI-ITEM QUERIES
    # =====================================================================
    # If user searched "macbook and iphone" → becomes "macbook | iphone"
    # We split these and boost BOTH items equally (the "Equalizer")
    if "|" in core_query:
        multi_items = [item.strip() for item in core_query.split("|") if item.strip()]
        # For vector search, we combine them into one string
        core_query_for_vector = " ".join(multi_items)
    else:
        # Single item query
        multi_items = [core_query]
        core_query_for_vector = core_query
    
    # =====================================================================
    # STEP 6: GENERATE VECTOR EMBEDDING (Semantic Search)
    # =====================================================================
    # Vector = numerical representation of meaning
    # OpenAI converts text into 1536-dimensional vector
    # We then find products whose vectors are "closest" in meaning (KNN)
    vector = None
    if core_query_for_vector:
        try:
            resp = await openai_client.embeddings.create(
                input=core_query_for_vector,
                model=AI_EMBEDDING_MODEL
            )
            vector = resp.data[0].embedding
        except Exception as e:
            # OpenAI down? No problem — we still have keyword search as fallback
            logger.error(f"❌ OpenAI Embedding Failed: {e}")
    
    # =====================================================================
    # STEP 7: BUILD HARD FILTERS (must match these conditions)
    # =====================================================================
    # ALWAYS filter out products not in stock
    filters = [{"term": {"in_stock": True}}]
    must_nots = []
    
    # --------------------------------------------------------------------
    # Price filter from SEMANTIC extraction (user typed "under 100")
    # --------------------------------------------------------------------
    if matrix["min_price"] is not None or matrix["max_price"] is not None:
        price_range = {}
        if matrix["min_price"] is not None:
            price_range["gte"] = matrix["min_price"]  # Greater-than-equal
        if matrix["max_price"] is not None:
            price_range["lte"] = matrix["max_price"]  # Less-than-equal
        filters.append({"range": {"price": price_range}})
    
    # --------------------------------------------------------------------
    # Sale filter (user said "on sale" OR clicked sale filter)
    # --------------------------------------------------------------------
    if (
        matrix["is_sale"] 
        or request.sort == "on_sale" 
        or (request.filters and getattr(request.filters, "on_sale", False))
    ):
        # Only include products with sale_price > 0 (meaning they're on sale)
        filters.append({"range": {"sale_price": {"gt": 0}}})
    
    # --------------------------------------------------------------------
    # FILTERS FROM UI (user clicked sidebar filters)
    # --------------------------------------------------------------------
    if request.filters:
        
        # ============ CATEGORY FILTER ============
        if getattr(request.filters, "category", None):
            filters.append({
                "terms": {  # 'terms' = match ANY of these values
                    "category": request.filters.category[:MAX_CATEGORY_FILTERS]
                }
            })
        
        # ============ IN-STOCK OVERRIDE ============
        if getattr(request.filters, "in_stock", None) is not None:
            filters.append({"term": {"in_stock": request.filters.in_stock}})
        
        # ============ COLOR FILTER ============
        if getattr(request.filters, "color", None):
            # Build OR condition for each color selected
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
                    "minimum_should_match": 1  # At least 1 color must match
                }
            })
        
        # ============ SIZE FILTER ============
        if getattr(request.filters, "size", None):
            size_shoulds = []
            for s in request.filters.size[:MAX_SIZE_FILTERS]:
                size_str = str(s).strip()
                # Smart query: if user says "size M" use as-is, else "size M M"
                # This helps match both "Size M" and just "M" in product data
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
        
        # ============ GENDER FILTER ============
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
                            "attributes.Gender",  # Case variation
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
        
        # ============ BRAND FILTER (CASE-INSENSITIVE) ============
        # This is the BULLETPROOF fix from v135
        # Brands might be stored as "Apple", "APPLE", or "apple"
        # We match all variations to prevent missing products
        if getattr(request.filters, "brand", None):
            brand_shoulds = []
            for b in request.filters.brand[:MAX_BRAND_FILTERS]:
                b_str = str(b).strip()
                brand_shoulds.extend([
                    {"match_phrase": {"brand": b_str}},          # Original
                    {"term": {"brand": b_str}},                  # Exact
                    {"term": {"brand": b_str.upper()}},          # UPPERCASE
                    {"term": {"brand": b_str.title()}}           # Title Case
                ])
            filters.append({
                "bool": {
                    "should": brand_shoulds,
                    "minimum_should_match": 1
                }
            })
        
        # ============ PRICE FILTER FROM UI (sidebar slider) ============
        if getattr(request.filters, "price", None):
            p_range = {}
            
            # Handle MIN price (clean any $ or text characters)
            if getattr(request.filters.price, "min", None) is not None:
                try:
                    # Strip non-numeric chars (so "$100" → "100")
                    clean_min = re.sub(r'[^\d.]', '', str(request.filters.price.min))
                    if clean_min:
                        p_range["gte"] = float(clean_min)
                except Exception:
                    pass
            
            # Handle MAX price
            if getattr(request.filters.price, "max", None) is not None:
                try:
                    clean_max = re.sub(r'[^\d.]', '', str(request.filters.price.max))
                    if clean_max:
                        p_range["lte"] = float(clean_max)
                except Exception:
                    pass
            
            # Only add filter if we got valid prices
            if p_range:
                filters.append({"range": {"price": p_range}})
    
    # =====================================================================
    # STEP 8: BUILD SORT ORDER
    # =====================================================================
    # Default: sort by relevance score (highest first)
    sort_query = [{"_score": "desc"}]
    
    if request.sort == "price_asc":
        sort_query = [{"price": "asc"}]  # Cheapest first
    elif request.sort == "price_desc":
        sort_query = [{"price": "desc"}]  # Most expensive first
    elif request.sort == "on_sale":
        sort_query = [{"_score": "desc"}]  # Sale items by relevance
    
    # =====================================================================
    # STEP 9: BUILD SCORING (BOOST) CLAUSES
    # =====================================================================
    # These determine HOW well products match
    # Each "should" clause adds to the score if it matches
    semantic_shoulds = []
    
    # ---------------------------------------------------------------------
    # KNN SEMANTIC SEARCH (Vector-based similarity)
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
    # For each item in multi-item query, add ALL these boost rules
    # This ensures "macbook | iphone" gets results for BOTH items
    for item in multi_items:
        semantic_shoulds.extend([
            # ============ NAME EXACT PHRASE (Boost: 100) ============
            {
                "match_phrase": {
                    "name": {
                        "query": item,
                        "boost": BOOST_NAME_PHRASE
                    }
                }
            },
            
            # ============ BRAND EXACT PHRASE (Boost: 300) ============
            # Highest boost because brand match is most certain
            {
                "match_phrase": {
                    "brand": {
                        "query": item,
                        "boost": BOOST_BRAND_PHRASE
                    }
                }
            },
            
            # ============ CATEGORY MATCH (Boost: 200) ============
            # Solves the Polysemy problem (Watch Cap vs Wrist Watch)
            # If "watch" matches category, boost it hugely
            {
                "match": {
                    "category": {
                        "query": item,
                        "boost": BOOST_CATEGORY_MATCH
                    }
                }
            },
            
            # ============ CROSS-FIELD MATCH (Boost: 20) ============
            # All words of query must appear SOMEWHERE across fields
            # Good for natural language queries
            {
                "multi_match": {
                    "query": item,
                    "fields": ["name^10", "brand^5", "category^3", "description"],
                    "type": "cross_fields",
                    "operator": "and",
                    "boost": BOOST_CROSS_FIELDS
                }
            },
            
            # ============ FUZZY FALLBACK (Boost: 5) ============
            # Typo tolerance: "iphon" still finds "iphone"
            # Used as last-resort match (lowest boost)
            {
                "multi_match": {
                    "query": item,
                    "fields": ["name^5", "brand^3", "category^2", "description"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",  # Auto-detect typo tolerance
                    "boost": BOOST_FUZZY_FALLBACK
                }
            }
        ])
    
    # =====================================================================
    # STEP 10: BUILD SCORE FUNCTIONS (Demotion Logic)
    # =====================================================================
    # If user DOESN'T want accessories, DEMOTE accessory products
    # Example: searching "iphone" shouldn't show 50 iPhone cases
    score_functions = []
    
    if not matrix["has_accessory_intent"]:
        for acc in matrix["accessory_keywords"]:
            # Multiply score by 0.00001 if accessory word is in name/category
            # This pushes accessories to the VERY bottom of results
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
        # Smart search: use function_score with boosts and demotion
        query_body = {
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "should": semantic_shoulds,  # Scoring boosts
                            "must_not": must_nots,       # Excluded terms
                            "minimum_should_match": 1,   # At least 1 should match
                            "filter": filters            # Hard filters
                        }
                    },
                    "functions": score_functions,        # Demotion functions
                    "score_mode": "multiply",            # How to combine functions
                    "boost_mode": "multiply"             # How functions affect query score
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
        # Two-layer aggregation strategy:
        # 1. "top_relevant_hits" — Get categories from top 100 BEST-matching products
        #    (not from ALL matching products, which includes weak matches)
        # 2. "categories" — Traditional aggregation as fallback
        #
        # Why this works:
        # - Top 100 most-relevant products are TRULY related to the query
        # - Their categories are the ones user actually wants to filter by
        # - Irrelevant categories (like "Kitchen" for "shoes") are excluded
        # - We get 10-15 relevant categories (not just 2-3)
        "aggs": {
            # Primary: Get top 100 relevant product IDs and their categories
            "top_relevant_hits": {
                "top_hits": {
                    "size": 100,  # Top 100 most-relevant products
                    "_source": ["category"]  # Only fetch category field (fast!)
                }
            },
            # Fallback: Regular aggregation (kept for safety)
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
        # OpenSearch down? Return empty results (don't crash)
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
        max_score = 1.0  # Prevent division by zero
    
    # Transform raw OpenSearch hits into clean product dicts
    results = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        
        # Get clean brand using our smart mapper
        brand_display = get_smart_brand(source)
        
        # ---------------------------------------------------------------
        # Clean up category field (could be string OR list in DB)
        # ---------------------------------------------------------------
        raw_cats = source.get("category", [])
        clean_cats = []
        
        if isinstance(raw_cats, str):
            # Category stored as messy string like "['Shoes', 'Men']"
            # Clean it and split by comma
            clean_cats = [
                c.strip() 
                for c in re.sub(r"[\[\]'\"]", "", raw_cats).split(",") 
                if c.strip()
            ]
        elif isinstance(raw_cats, list):
            # Category stored as proper list — just clean each item
            clean_cats = [str(c).strip() for c in raw_cats if c and str(c).strip()]
        
        # Fallback if no category
        if not clean_cats or clean_cats == ["None"]:
            clean_cats = ["Uncategorized"]
        
        # ---------------------------------------------------------------
        # Get first image as primary
        # ---------------------------------------------------------------
        images = source.get("images", [])
        primary_image = images[0] if isinstance(images, list) and len(images) > 0 else None
        
        # ---------------------------------------------------------------
        # Generate FAKE but consistent rating/sales for demo
        # (If real data doesn't exist)
        # ---------------------------------------------------------------
        # Uses product_id hash so same product ALWAYS gets same fake rating
        _pid = str(source.get("product_id", "123"))
        _pid_hash = int(hashlib.md5(_pid.encode()).hexdigest(), 16)
        
        # Fake rating between 4.0 and 4.9
        _demo_rating = DEMO_RATING_BASE + (_pid_hash % DEMO_RATING_RANGE) / 10.0
        
        # Fake sales count between 150 and 949
        _demo_sales = (_pid_hash % DEMO_SALES_RANGE) + DEMO_SALES_BASE
        
        # ---------------------------------------------------------------
        # Normalize relevance score to 0.85-0.99 range (for display)
        # ---------------------------------------------------------------
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
            # Use real rating if > 0, else use demo rating
            "rating": source.get("rating") if source.get("rating", 0) > 0 else _demo_rating,
            # Use real sales count if > 0, else use demo sales
            "sales_count": source.get("sales_count") if source.get("sales_count", 0) > 0 else _demo_sales,
            # Score always displayed as 0.85-0.99 for nice UX
            "score": round(SCORE_DISPLAY_MIN + (normalized_score * SCORE_DISPLAY_RANGE), 2)
        })
    
    # =====================================================================
    # STEP 14: RE-SORT BY SCORE (unless sorting by price)
    # =====================================================================
    # Since we normalized scores, re-sort to guarantee proper order
    if request.sort not in ["price_asc", "price_desc"]:
        results.sort(key=lambda x: x["score"], reverse=True)
    
# =====================================================================
    # STEP 15: BUILD FACETS (Smart Contextual Category Filtering)
    # =====================================================================
    # STRATEGY:
    #   1. Grab top 100 most-relevant products (via top_hits aggregation)
    #   2. Count categories that appear in those top 100
    #   3. Sort by count (most common first)
    #   4. Return top 15 categories
    #
    # This guarantees:
    #   - Categories are TRULY related to the search query
    #   - User sees 10-15 useful filter options (not 2-3)
    #   - No irrelevant categories like "Kitchen" for "shoes" query
    
    aggregations = response.get("aggregations", {})
    
    # Get the top 100 most-relevant products from our custom aggregation
    top_hits_data = aggregations.get("top_relevant_hits", {}).get("hits", {}).get("hits", [])
    
    # Count how many times each category appears in top 100 products
    # This gives us the "relevance weight" of each category
    category_counts = {}
    
    for hit in top_hits_data:
        source = hit.get("_source", {})
        raw_cats = source.get("category", [])
        
        # Handle both string and list formats for category field
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
        
        # Increment count for each valid category
        for cat in cats_list:
            if cat and cat != "None" and cat != "Uncategorized":
                category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # Get ACTUAL counts from the global aggregation (more accurate totals)
    # We use counts from aggregation, but only for categories in our top list
    global_agg_buckets = {
        str(c.get("key")).strip(): c.get("doc_count", 0)
        for c in aggregations.get("categories", {}).get("buckets", [])
        if c.get("key")
    }
    
    # Sort categories by their appearance in top 100 (relevance)
    # Keep top 15 most relevant
    sorted_categories = sorted(
        category_counts.items(),
        key=lambda x: x[1],  # Sort by count in top 100 (most common first)
        reverse=True
    )[:15]
    
    # Build the final facets list
    # Use global count (more accurate) but ordered by relevance
    facets = {
        "categories": [
            {
                "value": cat_name,
                "label": cat_name,
                # Use global count if available, else use top-100 count
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
        "total_pages": total_pages,
        "current_page": request.page,
        "pagination_html": build_pagination_html(total_pages, request.page),
        "results": results,
        "facets": facets
    }
    
    # =====================================================================
    # STEP 17: CACHE FOR NEXT TIME
    # =====================================================================
    # Save to Redis with 5-minute expiry
    await cache_set(cache_key, final_response, ttl_seconds=SEARCH_CACHE_TTL)
    
    return final_response