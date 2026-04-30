import os
import requests
from dotenv import load_dotenv

# Load variables from your .env file
load_dotenv()

# Pulling strictly from your .env file
OPENSEARCH_URL = os.getenv("OPENSEARCH_HOST")
INDEX = os.getenv("OPENSEARCH_INDEX", "products")

# ==========================
# HELPER: FORMAT RESPONSE
# ==========================
def format_response(data):
    hits = data.get("hits", {}).get("hits", [])

    results = []
    for hit in hits:
        src = hit.get("_source", {})

        results.append({
            "id": hit.get("_id"),
            "name": src.get("name"),
            "price": src.get("price"),
            "sale_price": src.get("sale_price"),  # ✅ Included sale price
            "image": src.get("image") or src.get("primary_image"),
            "url": src.get("url")                 # ✅ Included product URL
        })

    return results

# ==========================
# STEP 1: GET EMBEDDING (FAST)
# ==========================
def get_embedding(product_id):
    if not OPENSEARCH_URL:
        raise ValueError("OPENSEARCH_HOST is missing from .env file!")
        
    res = requests.get(f"{OPENSEARCH_URL}/{INDEX}/_doc/{product_id}")
    data = res.json()
    return data.get("_source", {}).get("embedding")

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
                                {"term": {"_id": product_id}}
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
                                        "_index": INDEX,
                                        "_id": product_id
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
                        {"term": {"_id": product_id}}
                    ]
                }
            }
        }
    ).json()