import os
import requests
from dotenv import load_dotenv

# Load variables from your .env file
load_dotenv()

OPENSEARCH_URL = os.getenv("OPENSEARCH_HOST")
INDEX = os.getenv("OPENSEARCH_INDEX", "products")

# ✅ Keep these for debugging
print(f"DEBUG: OPENSEARCH_URL is: {OPENSEARCH_URL}")
print(f"DEBUG: INDEX is: {INDEX}")

# ==========================
# HELPER: FORMAT RESPONSE
# ==========================
def format_response(data):
    hits = data.get("hits", {}).get("hits", [])
    results = []
    for hit in hits:
        src = hit.get("_source", {})
        
        # Extract the first image from the 'images' string or list
        raw_images = src.get("images", "")
        img_url = raw_images.split(',')[0].strip() if isinstance(raw_images, str) else src.get("image")

        results.append({
            "id": src.get("product_id"),
            "name": src.get("name"),
            "category": src.get("category"),
            "price": src.get("price"),
            "sale_price": src.get("sale_price"),
            "image": img_url,
            "url": src.get("url"),
            "product_url": src.get("url")
        })
    return results

# ==========================
# STEP 1: GET EMBEDDING (MUST BE NAMED get_embedding)
# ==========================
def get_embedding(product_id):
    if not OPENSEARCH_URL:
        raise ValueError("OPENSEARCH_HOST is missing from .env file!")
        
    res = requests.post(
        f"{OPENSEARCH_URL}/{INDEX}/_search",
        json={
            "query": {
                "bool": {
                    "should": [
                        {"match": {"product_id": product_id}},
                        {"term": {"_id": product_id}}
                    ]
                }
            },
            "size": 1
        }
    )
    
    data = res.json()
    hits = data.get("hits", {}).get("hits", [])
    
    if not hits:
        return None
        
    return hits[0].get("_source", {}).get("embedding")

# ==========================
# STEP 2: AI SIMILAR SEARCH
# ==========================
def ai_search(vector, product_id, category_id, page, size):
    return requests.post(
        f"{OPENSEARCH_URL}/{INDEX}/_search",
        json={
            "from": (page - 1) * size,
            "size": size,
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
                            "filter": [
                                {"term": {"category_id": category_id}}
                            ] if category_id else [],
                            "must_not": [
                                {"match": {"product_id": product_id}} 
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
    ).json()

# ==========================
# STEP 3: FALLBACK SEARCH
# ==========================
def fallback_search(product_id, category_id, page, size):
    return requests.post(
        f"{OPENSEARCH_URL}/{INDEX}/_search",
        json={
            "from": (page - 1) * size,
            "size": size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "more_like_this": {
                                "fields": ["name^3", "description"],
                                "like": [
                                    {
                                        "doc": {
                                            "product_id": product_id
                                        }
                                    }
                                ],
                                "min_term_freq": 1,
                                "max_query_terms": 12
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"category_id": category_id}}
                    ] if category_id else [],
                    "must_not": [
                        {"match": {"product_id": product_id}} 
                    ]
                }
            }
        }
    ).json()