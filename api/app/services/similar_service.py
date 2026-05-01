import os
import time
import hashlib
import logging
from app.config import os_client, INDEX_NAME
from app.utils.cache import cache_get, cache_set
from app.core.constants import CACHE_VERSION

logger = logging.getLogger(__name__)
# Use the same INDEX_NAME from config (works with AOSS auth)
INDEX = INDEX_NAME

print(f"DEBUG: Using INDEX: {INDEX}")


# ==========================
# HELPER: FORMAT RESPONSE (with sale_price + url)
# ==========================
def format_response(data):
    hits = data.get("hits", {}).get("hits", [])
    results = []
    
    for hit in hits:
        src = hit.get("_source", {})
        
        # Extract first image
        raw_images = src.get("images", "")
        img_url = None
        
        if isinstance(raw_images, list) and len(raw_images) > 0:
            img_url = str(raw_images[0]).strip()
        elif isinstance(raw_images, str) and raw_images:
            img_url = raw_images.split(',')[0].strip()
        
        if not img_url:
            img_url = src.get("image") or src.get("primary_image")
        
        product_url = src.get("url") or src.get("product_url") or ""
        
        price = src.get("price", 0)
        sale_price = src.get("sale_price", 0)
        
        discount_percent = 0
        if sale_price and price and sale_price < price:
            discount_percent = round(((price - sale_price) / price) * 100)
        
        results.append({
            "id": src.get("product_id") or hit.get("_id"),
            "name": src.get("name", ""),
            "category": src.get("category", ""),
            "brand": src.get("brand", ""),
            "price": price,
            "sale_price": sale_price if sale_price and sale_price > 0 else None,
            "discount_percent": discount_percent if discount_percent > 0 else None,
            "image": img_url,
            "url": product_url,
            "product_url": product_url,
            "in_stock": src.get("in_stock", True)
        })
    
    return results


# ==========================
# STEP 1: GET EMBEDDING (using os_client with AWS auth)
# ==========================
def get_embedding(product_id):
    """Find product and extract embedding using authenticated os_client."""
    product_id_str = str(product_id).strip()
    
    # Try multiple strategies to find the product
    queries = [
        # Strategy 1: Exact term match on product_id
        {
            "query": {"term": {"product_id": product_id_str}},
            "size": 1,
            "_source": True
        },
        # Strategy 2: Match on product_id (handles different mappings)
        {
            "query": {"match": {"product_id": product_id_str}},
            "size": 1,
            "_source": True
        }
    ]
    
    for i, query_body in enumerate(queries, 1):
        try:
            response = os_client.search(index=INDEX, body=query_body)
            hits = response.get("hits", {}).get("hits", [])
            
            if hits:
                source = hits[0].get("_source", {})
                
                # Try multiple field names for embedding
                for field_name in ["embedding", "vector", "embeddings", "embed"]:
                    embedding = source.get(field_name)
                    if embedding and isinstance(embedding, list) and len(embedding) > 0:
                        print(f"✅ Found embedding for product {product_id_str} (strategy {i}, field '{field_name}', dim={len(embedding)})")
                        return embedding
                
                # Product found but no embedding
                available_fields = list(source.keys())[:15]
                print(f"⚠️  Product {product_id_str} found (strategy {i}) but no embedding field. Available fields: {available_fields}")
                return None
                
        except Exception as e:
            print(f"❌ Strategy {i} failed: {e}")
            continue
    
    print(f"❌ Product {product_id_str} not found in OpenSearch")
    return None


# ==========================
# STEP 2: AI SIMILAR SEARCH (KNN Vector) — WITH CACHE
# ==========================
async def ai_search(vector, product_id, category_id, page, size):
    product_id_str = str(product_id).strip()
    
    # 🆕 CHECK CACHE FIRST
    cache_key_str = f"ai_similar:{product_id_str}:{category_id}:{page}:{size}"
    cache_key = f"similar:{CACHE_VERSION}:{hashlib.md5(cache_key_str.encode()).hexdigest()}"
    
    _start = time.perf_counter()
    cached = await cache_get(cache_key)
    if cached:
        elapsed = (time.perf_counter() - _start) * 1000
        print(f"⚡ AI_SIMILAR | product={product_id_str} | time={elapsed:.2f}ms | mode=CACHED", flush=True)
        return cached
    
    filters = [{"term": {"in_stock": True}}]
    if category_id:
        filters.append({"term": {"category_id": category_id}})

    query_body = {
        "from": (page - 1) * size,
        "size": size,
        "_source": {"excludes": ["embedding", "vector", "embeddings"]},
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": vector,
                                        "k": 50
                                    }
                                }
                            }
                        ],
                        "filter": filters,
                        "must_not": [
                            {"term": {"product_id": product_id_str}}
                        ]
                    }
                },
                "functions": [
                    {
                        "field_value_factor": {
                            "field": "trending_score",
                            "factor": 0.1,
                            "missing": 1
                        }
                    }
                ],
                "boost_mode": "sum"
            }
        }
    }
    
    try:
        response = os_client.search(index=INDEX, body=query_body)
        
        # 🆕 SAVE TO CACHE (1 hour TTL)
        await cache_set(cache_key, response, ttl_seconds=3600)
        
        elapsed = (time.perf_counter() - _start) * 1000
        print(f"✅ AI_SIMILAR | product={product_id_str} | time={elapsed:.2f}ms | mode=full", flush=True)
        
        return response
    except Exception as e:
        print(f"❌ AI search failed: {e}")
        return {"hits": {"hits": []}}


# ==========================
# STEP 3: FALLBACK SEARCH (More Like This) — WITH CACHE
# ==========================
async def fallback_search(product_id, category_id, page, size):
    product_id_str = str(product_id).strip()
    
    # 🆕 CHECK CACHE FIRST
    cache_key_str = f"fallback_similar:{product_id_str}:{category_id}:{page}:{size}"
    cache_key = f"similar:{CACHE_VERSION}:{hashlib.md5(cache_key_str.encode()).hexdigest()}"
    
    _start = time.perf_counter()
    cached = await cache_get(cache_key)
    if cached:
        elapsed = (time.perf_counter() - _start) * 1000
        print(f"⚡ FALLBACK_SIMILAR | product={product_id_str} | time={elapsed:.2f}ms | mode=CACHED", flush=True)
        return cached
    
    filters = [{"term": {"in_stock": True}}]
    if category_id:
        filters.append({"term": {"category_id": category_id}})

    query_body = {
        "from": (page - 1) * size,
        "size": size,
        "_source": {"excludes": ["embedding", "vector", "embeddings"]},
        "query": {
            "bool": {
                "must": [
                    {
                        "more_like_this": {
                            "fields": ["name^3", "description", "category^2"],
                            "like": [
                                {
                                    "_index": INDEX,
                                    "_id": product_id_str
                                }
                            ],
                            "min_term_freq": 1,
                            "max_query_terms": 12,
                            "minimum_should_match": "30%"
                        }
                    }
                ],
                "filter": filters,
                "must_not": [
                    {"term": {"product_id": product_id_str}}
                ]
            }
        }
    }
    
    try:
        response = os_client.search(index=INDEX, body=query_body)
        
        # 🆕 SAVE TO CACHE
        await cache_set(cache_key, response, ttl_seconds=3600)
        
        elapsed = (time.perf_counter() - _start) * 1000
        print(f"✅ FALLBACK_SIMILAR | product={product_id_str} | time={elapsed:.2f}ms | mode=full", flush=True)
        
        return response
    except Exception as e:
        print(f"❌ Fallback search failed: {e}")
        # Try without _id (if the product_id format doesn't match _id)
        try:
            query_body["query"]["bool"]["must"][0]["more_like_this"]["like"] = [
                f"product_id:{product_id_str}"
            ]
            response = os_client.search(index=INDEX, body=query_body)
            
            # 🆕 SAVE TO CACHE
            await cache_set(cache_key, response, ttl_seconds=3600)
            
            return response
        except Exception as e2:
            print(f"❌ Fallback retry failed: {e2}")
            return {"hits": {"hits": []}}