import json
import hashlib
from app.config import os_client, INDEX_NAME, redis_client # ✅ Added redis_client
from app.models.search import SearchRequest

async def execute_search(request: SearchRequest):
    # ==========================================
    # 1. CREATE A UNIQUE CACHE KEY
    # ==========================================
    # We turn the whole request into a unique string to use as a "folder name" in Redis
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:{hashlib.md5(request_str.encode()).hexdigest()}"

    # ==========================================
    # 2. CHECK REDIS FIRST (The "Fast Lane")
    # ==========================================
    try:
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            print(f"🚀 CACHE HIT: Serving results for key {cache_key}")
            return json.loads(cached_result)
    except Exception as e:
        print(f"⚠️ Redis read error (skipping to OpenSearch): {e}")

    # ==========================================
    # 3. BUILD THE OPENSEARCH QUERY (Your Existing Logic)
    # ==========================================
    from_val = (request.page - 1) * request.page_size

    bool_query = {
        "must": [
            {
                "multi_match": {
                    "query": request.query,
                    "fields": ["name^10", "brand^5", "category^2", "description"], 
                    "fuzziness": "AUTO",           
                    "minimum_should_match": "70%"  
                }
            }
        ],
        "should": [
            {
                "match_phrase": {
                    "name": {
                        "query": request.query,
                        "boost": 100 
                    }
                }
            }
        ],
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
            if request.filters.price.min is not None:
                price_range["gte"] = request.filters.price.min
            if request.filters.price.max is not None:
                price_range["lte"] = request.filters.price.max
            if price_range:
                bool_query["filter"].append({"range": {"price": price_range}})

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

    # ==========================================
    # 4. EXECUTE SEARCH IN OPENSEARCH
    # ==========================================
    response = os_client.search(index=INDEX_NAME, body=os_query)
    
    total_hits = response["hits"]["total"]["value"]
    total_pages = (total_hits + request.page_size - 1) // request.page_size

    results = []
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        raw_brand = source.get("brand", "")
        brand_display = raw_brand if raw_brand and str(raw_brand).strip() else "Other Brands"
        
        results.append({
            "id": source.get("product_id"),
            "name": source.get("name"),
            "description": source.get("description"),
            "brand": brand_display, 
            "category": source.get("category", []),
            "price": source.get("price"),
            "sale_price": source.get("sale_price"),
            "in_stock": source.get("in_stock"),
            "sku": source.get("sku"),
            "url": source.get("url"),
            "attributes": source.get("attributes", {}),
            "primary_image": source.get("images", [None])[0] if source.get("images") else None,
            "images": source.get("images", [])
        })

    facets = {
        "brands": [
            {"label": b["key"] if b["key"].strip() else "Other Brands", "value": b["key"], "count": b["doc_count"]} 
            for b in response["aggregations"]["brands"]["buckets"]
        ],
        "categories": [
            {"value": c["key"], "label": f"Category {c['key']}", "count": c["doc_count"]} 
            for c in response["aggregations"]["categories"]["buckets"]
        ]
    }

    # ==========================================
    # 5. PREPARE FINAL RESPONSE
    # ==========================================
    final_response = {
        "total_results": total_hits,
        "total_pages": total_pages,
        "current_page": request.page,
        "results": results,
        "facets": facets
    }

    # ==========================================
    # 6. SAVE TO REDIS (Set it and forget it)
    # ==========================================
    try:
        # We save it for 300 seconds (5 minutes). 
        # This gives you a great speed boost without results getting too old.
        await redis_client.set(
            cache_key, 
            json.dumps(final_response), 
            ex=300
        )
    except Exception as e:
        print(f"⚠️ Redis write error: {e}")

    return final_response