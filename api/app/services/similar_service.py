import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

OPENSEARCH_URL = os.getenv("OPENSEARCH_HOST")
INDEX = os.getenv("OPENSEARCH_INDEX", "products")

logger = logging.getLogger(__name__)

print(f"DEBUG: OPENSEARCH_URL is: {OPENSEARCH_URL}")
print(f"DEBUG: INDEX is: {INDEX}")


# ==========================
# HELPER: FORMAT RESPONSE (with sale_price + url)
# ==========================
def format_response(data):
    hits = data.get("hits", {}).get("hits", [])
    results = []
    
    for hit in hits:
        src = hit.get("_source", {})
        
        # Extract first image from images field (string or list)
        raw_images = src.get("images", "")
        img_url = None
        
        if isinstance(raw_images, list) and len(raw_images) > 0:
            img_url = str(raw_images[0]).strip()
        elif isinstance(raw_images, str) and raw_images:
            img_url = raw_images.split(',')[0].strip()
        
        # Fallback to other image fields
        if not img_url:
            img_url = src.get("image") or src.get("primary_image")
        
        # Build product URL
        product_url = src.get("url") or src.get("product_url") or ""
        
        # Get prices
        price = src.get("price", 0)
        sale_price = src.get("sale_price", 0)
        
        # Calculate discount if on sale
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
# STEP 1: GET EMBEDDING (BULLETPROOF)
# ==========================
def get_embedding(product_id):
    """
    Tries multiple strategies to find embedding:
    1. Search by product_id field
    2. Search by _id
    3. Try multiple embedding field names
    """
    if not OPENSEARCH_URL:
        raise ValueError("OPENSEARCH_HOST is missing from .env file!")
    
    # Convert to string (OpenSearch stores as keyword)
    product_id_str = str(product_id).strip()
    
    # Try multiple search strategies
    queries = [
        # Strategy 1: Exact match on product_id
        {
            "query": {"term": {"product_id": product_id_str}},
            "size": 1,
            "_source": True  # Include all fields
        },
        # Strategy 2: Match on product_id
        {
            "query": {"match": {"product_id": product_id_str}},
            "size": 1,
            "_source": True
        },
        # Strategy 3: Match on _id
        {
            "query": {"term": {"_id": product_id_str}},
            "size": 1,
            "_source": True
        }
    ]
    
    for i, query in enumerate(queries, 1):
        try:
            res = requests.post(
                f"{OPENSEARCH_URL}/{INDEX}/_search",
                json=query,
                timeout=10
            )
            data = res.json()
            hits = data.get("hits", {}).get("hits", [])
            
            if hits:
                source = hits[0].get("_source", {})
                
                # Try multiple field names for embedding
                for field_name in ["embedding", "vector", "embeddings", "embed"]:
                    embedding = source.get(field_name)
                    if embedding and isinstance(embedding, list) and len(embedding) > 0:
                        print(f"✅ Found embedding for product {product_id_str} (strategy {i}, field '{field_name}', dim={len(embedding)})")
                        return embedding
                
                # Product found but no embedding
                print(f"⚠️  Product {product_id_str} found but no embedding field. Available fields: {list(source.keys())[:10]}")
                return None
        except Exception as e:
            print(f"❌ Strategy {i} failed: {e}")
            continue
    
    print(f"❌ Product {product_id_str} not found in any strategy")
    return None


# ==========================
# STEP 2: AI SIMILAR SEARCH (KNN Vector)
# ==========================
def ai_search(vector, product_id, category_id, page, size):
    product_id_str = str(product_id).strip()
    
    # Build filters list
    filters = [{"term": {"in_stock": True}}]
    if category_id:
        filters.append({"term": {"category_id": category_id}})
    
    query_body = {
        "from": (page - 1) * size,
        "size": size,
        "_source": {"excludes": ["embedding", "vector"]},  # Don't send huge vectors back
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
        res = requests.post(
            f"{OPENSEARCH_URL}/{INDEX}/_search",
            json=query_body,
            timeout=15
        )
        return res.json()
    except Exception as e:
        print(f"❌ AI search failed: {e}")
        return {"hits": {"hits": []}}


# ==========================
# STEP 3: FALLBACK SEARCH (More Like This)
# ==========================
def fallback_search(product_id, category_id, page, size):
    product_id_str = str(product_id).strip()
    
    filters = [{"term": {"in_stock": True}}]
    if category_id:
        filters.append({"term": {"category_id": category_id}})
    
    query_body = {
        "from": (page - 1) * size,
        "size": size,
        "_source": {"excludes": ["embedding", "vector"]},
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
        res = requests.post(
            f"{OPENSEARCH_URL}/{INDEX}/_search",
            json=query_body,
            timeout=15
        )
        return res.json()
    except Exception as e:
        print(f"❌ Fallback search failed: {e}")
        return {"hits": {"hits": []}}