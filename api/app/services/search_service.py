from app.config import os_client, INDEX_NAME
from app.models.search import SearchRequest

def execute_search(request: SearchRequest):
    # 1. Calculate starting point for pagination
    from_val = (request.page - 1) * request.page_size

    # 2. Build the base query (UPGRADED FOR SMART RELEVANCE)
    bool_query = {
        "must": [
            {
                "multi_match": {
                    "query": request.query,
                    "fields": ["name^4", "brand^2", "category^1.5", "description"],
                    "fuzziness": "AUTO",           # Handles typos and spaces
                    "minimum_should_match": "70%"  # Ensures most words match
                }
            }
        ],
        "should": [
            {
                "match_phrase": {
                    "name": {
                        "query": request.query,
                        "boost": 10                # Massive boost for exact phrase matches
                    }
                }
            }
        ],
        "filter": []
    }

    # 3. Apply Filters dynamically
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

    # 4. Apply Sorting
    sort_query = [{"price": "asc"}] if request.sort == "price_asc" else [{"price": "desc"}] if request.sort == "price_desc" else ["_score"]

    # 5. Full OpenSearch Payload
    os_query = {
        "from": from_val,
        "size": request.page_size,
        "query": {"bool": bool_query},
        "sort": sort_query,
        "aggs": {
            "brands": {"terms": {"field": "brand", "size": 15}},
            "categories": {"terms": {"field": "category", "size": 15}}
        }
    }

    # 6. Execute Search
    response = os_client.search(index=INDEX_NAME, body=os_query)
    
    # 7. Calculate Pagination Logic
    total_hits = response["hits"]["total"]["value"]
    total_pages = (total_hits + request.page_size - 1) // request.page_size

    # 8. Clean up Results and Empty Brands
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
            "total_sold": source.get("total_sold"),
            "primary_image": source.get("images", [None])[0] if source.get("images") else None,
            "images": source.get("images", [])
        })

    # 9. Clean up Facets for the UI Sidebar
    facets = {
        "brands": [
            {
                "label": b["key"] if b["key"] and str(b["key"]).strip() else "Other Brands", 
                "value": b["key"], 
                "count": b["doc_count"]
            } 
            for b in response["aggregations"]["brands"]["buckets"]
        ],
        "categories": [
            {"value": c["key"], "count": c["doc_count"]} 
            for c in response["aggregations"]["categories"]["buckets"]
        ]
    }

    # 10. Return the perfect JSON package
    return {
        "total_results": total_hits,
        "total_pages": total_pages,
        "current_page": request.page,
        "results": results,
        "facets": facets
    }