import json
import hashlib
import time
from app.config import os_client, INDEX_NAME, redis_client
from app.models.search import SearchRequest

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

async def execute_search(request: SearchRequest):
    # 1. CREATE A UNIQUE CACHE KEY
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:{hashlib.md5(request_str.encode()).hexdigest()}"

    # 2. CHECK REDIS FIRST
    try:
        start_time = time.time()
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            latency = (time.time() - start_time) * 1000
            print(f"🚀 CACHE HIT: [{latency:.2f}ms] Key: {cache_key}")
            return json.loads(cached_result)
    except Exception as e:
        print(f"⚠️ Redis read error: {e}")

    # 3. BUILD THE OPENSEARCH QUERY
    from_val = (request.page - 1) * request.page_size
    bool_query = {
        "must": [{
            "multi_match": {
                "query": request.query,
                "fields": ["name^10", "brand^5", "category^2", "description"], 
                "fuzziness": "AUTO",           
                "minimum_should_match": "70%"  
            }
        }],
        "should": [{
            "match_phrase": {"name": {"query": request.query, "boost": 100}}
        }],
        "filter": []
    }

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

    # 4. EXECUTE SEARCH
    try:
        os_start = time.time()
        response = os_client.search(index=INDEX_NAME, body=os_query)
        print(f"🔍 DB SEARCH: [{(time.time() - os_start) * 1000:.2f}ms]")
    except Exception as e:
        print(f"❌ OpenSearch Error: {e}")
        return {"error": "Search service unavailable", "results": [], "total_results": 0}
    
    total_hits = response["hits"]["total"]["value"]
    total_pages = (total_hits + request.page_size - 1) // request.page_size

    # Clean Results
    results = []
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        raw_brand = source.get("brand", "")
        brand_display = str(raw_brand).strip() if raw_brand and str(raw_brand).strip() else "Other Brands"
        
        # Translate categories in the results list too
        raw_cats = source.get("category", [])
        if not isinstance(raw_cats, list): raw_cats = [raw_cats]
        clean_cats = [CATEGORY_MAP.get(str(c), f"ID {c}") for c in raw_cats]

        results.append({
            "id": source.get("product_id"),
            "name": source.get("name"),
            "description": source.get("description"),
            "brand": brand_display, 
            "category": clean_cats,
            "price": source.get("price"),
            "sale_price": source.get("sale_price"),
            "in_stock": source.get("in_stock"),
            "sku": source.get("sku"),
            "url": source.get("url"),
            "primary_image": source.get("images", [None])[0] if source.get("images") else None
        })

    # ==========================================
    # ✅ 5. THE PERMANENT FIX: FACET MAPPING
    # ==========================================
    facets = {
        "brands": [
            {
                "label": str(b["key"]).strip() if b.get("key") and str(b["key"]).strip() else "Other Brands", 
                "value": b["key"], 
                "count": b["doc_count"]
            } 
            for b in response["aggregations"]["brands"]["buckets"]
        ],
        "categories": [
            {
                "value": c["key"], 
                "label": CATEGORY_MAP.get(str(c["key"]), f"Category {c['key']}"), 
                "count": c["doc_count"]
            } 
            for c in response["aggregations"]["categories"]["buckets"]
        ]
    }

    final_response = {
        "total_results": total_hits,
        "total_pages": total_pages,
        "current_page": request.page,
        "results": results,
        "facets": facets
    }

    # 6. SAVE TO REDIS
    try:
        await redis_client.set(cache_key, json.dumps(final_response), ex=300)
    except Exception as e:
        print(f"⚠️ Redis write error: {e}")

    return final_response


# =================================================================
# 🚀 NEW: AUTOCOMPLETE FUNCTION (AMAZON-STYLE)
# =================================================================
async def execute_autocomplete(query_string: str):
    """
    Amazon-style Type-ahead logic. Returns unique product names matching the prefix.
    """
    # 1. Create a super-fast cache key
    cache_key = f"auto:{hashlib.md5(query_string.encode()).hexdigest()}"

    # 2. Check Redis
    try:
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
    except Exception as e:
        print(f"⚠️ Redis read error: {e}")

    # 3. Build the OpenSearch "Prefix" Query
    os_query = {
        "size": 10, 
        "_source": ["name", "images"], 
        "query": {
            "match_phrase_prefix": {
                "name": {
                    "query": query_string,
                    "max_expansions": 50 
                }
            }
        }
    }

    # 4. Execute the lightweight search
    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
    except Exception as e:
        print(f"❌ OpenSearch Autocomplete Error: {e}")
        return {"suggestions": []}

    # 5. Clean up the results (Remove duplicates)
    seen_names = set()
    suggestions = []
    
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        name = source.get("name")
        clean_name = str(name).strip().lower()
        
        if clean_name and clean_name not in seen_names:
            seen_names.add(clean_name)
            thumbnail = source.get("images", [None])[0] if source.get("images") else None
            
            suggestions.append({
                "text": name.lower(), 
                "thumbnail": thumbnail
            })

    final_response = {"suggestions": suggestions}

    # 6. Save to Redis (Cache for 1 hour)
    try:
        await redis_client.set(cache_key, json.dumps(final_response), ex=3600)
    except Exception as e:
        pass

    return final_response