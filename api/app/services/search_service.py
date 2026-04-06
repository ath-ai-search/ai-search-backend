from app.config import os_client, INDEX_NAME
from app.models.search import SearchRequest

def execute_search(request: SearchRequest):
    from_val = (request.page - 1) * request.page_size

    bool_query = {
        "must": [{"multi_match": {"query": request.query, "fields": ["name^3", "brand^2", "category^1.5", "description"]}}],
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
        "aggs": {
            "brands": {"terms": {"field": "brand", "size": 10}},
            "categories": {"terms": {"field": "category", "size": 10}}
        }
    }

    response = os_client.search(index=INDEX_NAME, body=os_query)
    
    # ==========================================
    # ✅ NEW: Pulling all the rich product data!
    # ==========================================
    results = []
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        
        results.append({
            "id": source.get("product_id"),
            "name": source.get("name"),
            "description": source.get("description"),
            "brand": source.get("brand"),
            "category": source.get("category", []),
            "price": source.get("price"),
            "sale_price": source.get("sale_price"),
            "in_stock": source.get("in_stock"),
            "sku": source.get("sku"),
            "url": source.get("url"),
            "attributes": source.get("attributes", {}),
            "total_sold": source.get("total_sold"),
            # Keep a convenient "primary_image" while also sending all images
            "primary_image": source.get("images", [None])[0] if source.get("images") else None,
            "images": source.get("images", [])
        })

    facets = {
        "brands": [{"value": b["key"], "count": b["doc_count"]} for b in response["aggregations"]["brands"]["buckets"]],
        "categories": [{"value": c["key"], "count": c["doc_count"]} for c in response["aggregations"]["categories"]["buckets"]]
    }

    return {"total": response["hits"]["total"]["value"], "page": request.page, "results": results, "facets": facets}