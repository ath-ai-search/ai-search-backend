import json
import hashlib
import time
import logging
from app.config import os_client, INDEX_NAME, redis_client
from app.models.search import SearchRequest

# ==========================================
# 🛠️ ENTERPRISE LOGGING SETUP
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ==========================================
# 🔄 GLOBAL CATEGORY MAPPING
# ==========================================
CATEGORY_MAP = {
    "2152": "Laptops",
    "1607": "Mobiles",
    "116": "Electronics",
    "1330": "Home & Garden",
    "1087": "Fashion",
    "47": "Appliances",
    "2487": "Accessories",
    "453": "Software"
}

# Maximum allowed results by OpenSearch without scroll API (Default is 10,000)
MAX_OS_WINDOW = 10000 

async def execute_search(request: SearchRequest):
    """
    Executes a highly optimized, Pure BM25 Keyword Search.
    Architected with a 'should' array foundation to allow seamless drop-in of Vector/AI search in the future.
    """
    # 1. CREATE A UNIQUE CACHE KEY
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:{hashlib.md5(request_str.encode()).hexdigest()}"

    # 2. CHECK REDIS FIRST (Safe failure handling)
    try:
        start_time = time.time()
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            latency = (time.time() - start_time) * 1000
            logger.info(f"🚀 CACHE HIT: [{latency:.2f}ms] Key: {cache_key}")
            return json.loads(cached_result)
    except Exception as e:
        logger.warning(f"⚠️ Redis read error (bypassing cache): {e}")

    # 3. PAGINATION SAFETY CHECK
    from_val = (request.page - 1) * request.page_size
    if from_val + request.page_size > MAX_OS_WINDOW:
        logger.warning(f"⚠️ User attempted deep pagination: Page {request.page}")
        from_val = MAX_OS_WINDOW - request.page_size # Lock to maximum safe depth

    # ==========================================
    # 🧠 FUTURE-PROOF HYBRID QUERY ARCHITECTURE
    # ==========================================
    bool_query = {
        "must": [],     # Strict rules (Must match)
        "should": [],   # Scoring elements (BM25 Lexical + Future AI Vector)
        "filter": [],   # Yes/No filters (Brand, Price, Category)
        "minimum_should_match": 0
    }

    query_text = request.query.strip() if request.query else ""
    
    if query_text:
        # User typed a search. They MUST match at least ONE of the 'should' conditions.
        bool_query["minimum_should_match"] = 1
        
        # --- PART A: PURE BM25 LEXICAL ENGINE ---
        bool_query["should"].append({
            "multi_match": {
                "query": query_text,
                "fields": ["name^10", "brand^5", "category^2", "description"], 
                "fuzziness": "AUTO",           
                "minimum_should_match": "70%",
                "analyzer": "standard",  # Pre-empts the edge_ngram autocomplete bug
                "boost": 1.0             # Weight of the keyword engine
            }
        })
        
        # --- PART B: EXACT PHRASE BOOSTER ---
        bool_query["should"].append({
            "match_phrase": {
                "name": {
                    "query": query_text, 
                    "boost": 50.0 
                }
            }
        })

        # =================================================================
        # 🤖 FUTURE AI SLOT: When you get your API Key, your Vector `knn` 
        # block will be `.append()`ed right here into the `should` array.
        # =================================================================
        
    else:
        # Empty Search Box: Return everything
        bool_query["must"].append({"match_all": {}})

    # --- PART C: IN-STOCK BOOSTER (Always apply) ---
    bool_query["should"].append({
        "term": {
            "in_stock": {
                "value": True,
                "boost": 2.0  # Pushes in-stock items higher in ties
            }
        }
    })

    # 4. APPLY HARD FILTERS
    if request.filters:
        if request.filters.brand:
            bool_query["filter"].append({"terms": {"brand": request.filters.brand}})
        if request.filters.category:
            bool_query["filter"].append({"terms": {"category": request.filters.category}})
        if request.filters.in_stock is not None:
            bool_query["filter"].append({"term": {"in_stock": request.filters.in_stock}})
        if request.filters.price:
            price_range = {}
            if request.filters.price.min is not None: price_range["gte"] = request.filters.price.min
            if request.filters.price.max is not None: price_range["lte"] = request.filters.price.max
            if price_range: bool_query["filter"].append({"range": {"price": price_range}})

    # 5. EXECUTE SEARCH
    sort_query = [{"price": "asc"}] if request.sort == "price_asc" else [{"price": "desc"}] if request.sort == "price_desc" else ["_score"]

    os_query = {
        "from": from_val,
        "size": request.page_size,
        "query": {"bool": bool_query},
        "sort": sort_query,
        "track_total_hits": True,
        "aggs": {
            "brands": {"terms": {"field": "brand", "size": 25}},
            "categories": {"terms": {"field": "category", "size": 25}}
        }
    }

    try:
        os_start = time.time()
        response = os_client.search(index=INDEX_NAME, body=os_query)
        logger.info(f"🔍 DB SEARCH: [{(time.time() - os_start) * 1000:.2f}ms]")
    except Exception as e:
        logger.error(f"❌ OpenSearch Error: {str(e)}")
        return {"error": "Search service unavailable", "results": [], "total_results": 0}
    
    # Safely extract hits
    hits = response.get("hits", {})
    total_hits = hits.get("total", {}).get("value", 0)
    total_pages = (total_hits + request.page_size - 1) // request.page_size if total_hits > 0 else 0

    # 6. CLEAN RESULTS & PREPARE FRONTEND PAYLOAD
    results = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        
        # Safely parse Brand
        raw_brand = source.get("brand", "")
        brand_display = str(raw_brand).strip() if raw_brand and str(raw_brand).strip() else "Other Brands"
        
        # Safely parse Categories
        raw_cats = source.get("category", [])
        if not isinstance(raw_cats, list): 
            raw_cats = [raw_cats]
        clean_cats = [CATEGORY_MAP.get(str(c), f"Category {c}") for c in raw_cats if c]

        # Safely parse Images
        images = source.get("images", [])
        primary_image = images[0] if isinstance(images, list) and len(images) > 0 else None

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
            "primary_image": primary_image
        })

    # Safely extract Aggregations (Facets)
    aggregations = response.get("aggregations", {})
    brands_agg = aggregations.get("brands", {}).get("buckets", [])
    categories_agg = aggregations.get("categories", {}).get("buckets", [])

    facets = {
        "brands": [
            {
                "label": str(b.get("key", "")).strip() if b.get("key") and str(b.get("key")).strip() else "Other Brands", 
                "value": b.get("key"), 
                "count": b.get("doc_count", 0)
            } 
            for b in brands_agg
        ],
        "categories": [
            {
                "value": c.get("key"), 
                "label": CATEGORY_MAP.get(str(c.get("key")), f"Category {c.get('key')}"), 
                "count": c.get("doc_count", 0)
            } 
            for c in categories_agg
        ]
    }

    final_response = {
        "total_results": total_hits,
        "total_pages": total_pages,
        "current_page": request.page,
        "results": results,
        "facets": facets
    }

    # 7. SAVE TO REDIS (Safe write)
    try:
        await redis_client.set(cache_key, json.dumps(final_response), ex=300)
    except Exception as e:
        logger.warning(f"⚠️ Redis write error: {e}")

    return final_response


# =================================================================
# 🚀 AUTOCOMPLETE FUNCTION (AMAZON-STYLE)
# =================================================================
async def execute_autocomplete(query_string: str):
    """
    Lightning-fast edge_ngram autocomplete.
    """
    clean_query = query_string.strip()
    if not clean_query:
        return {"suggestions": []}

    cache_key = f"auto:{hashlib.md5(clean_query.encode()).hexdigest()}"

    try:
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
    except Exception as e:
        logger.warning(f"⚠️ Redis read error: {e}")

    os_query = {
        "size": 10, 
        "_source": ["name", "images"], 
        "query": {
            "match_phrase_prefix": {
                "name": {
                    "query": clean_query,
                    "max_expansions": 50 
                }
            }
        }
    }

    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
    except Exception as e:
        logger.error(f"❌ OpenSearch Autocomplete Error: {e}")
        return {"suggestions": []}

    seen_names = set()
    suggestions = []
    
    for hit in response.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        name = source.get("name", "")
        normalized_name = str(name).strip().lower()
        
        if normalized_name and normalized_name not in seen_names:
            seen_names.add(normalized_name)
            
            images = source.get("images", [])
            thumbnail = images[0] if isinstance(images, list) and len(images) > 0 else None
            
            suggestions.append({
                "text": name, # Return the original casing for display
                "thumbnail": thumbnail
            })

    final_response = {"suggestions": suggestions}

    try:
        await redis_client.set(cache_key, json.dumps(final_response), ex=3600)
    except Exception as e:
        pass

    return final_response