"""
=====================================================================================
📊 STATS SERVICE — Top Products by Engagement Metrics
=====================================================================================
This service powers 6 APIs that return top products sorted by different metrics:

  1. /products/view          → Most viewed products
  2. /products/click         → Most clicked products
  3. /products/add-to-cart   → Most added to cart
  4. /products/wishlist      → Most wished products
  5. /products/purchase      → Most purchased (best sellers)
  6. /products/trending      → Hot products (combined trending_score)

HOW IT WORKS:
  1. Query OpenSearch products index
  2. Filter products with engagement (stat > 0)
  3. Sort by the specified stat field DESC
  4. Cache results in Redis for 5 minutes (avoid hitting OpenSearch repeatedly)
  5. Return paginated, formatted results

PERFORMANCE:
  - First call: ~50-100ms (OpenSearch query)
  - Cached call: ~2-5ms (Redis)
  - Cache key: stats:{metric}:{page}:{size}
=====================================================================================
"""

import os
import time
import json
import logging
from typing import Optional

import redis
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import boto3

# =========================================================================
# ⚙️ CONFIG
# =========================================================================

logger = logging.getLogger("StatsService")

# OpenSearch config (matches your existing config)
OPENSEARCH_HOST = os.getenv(
    "OPENSEARCH_HOST",
    "ud6wzyczsjqz2nc3fmw9.us-west-2.aoss.amazonaws.com"
)
OPENSEARCH_REGION = os.getenv("OPENSEARCH_REGION", "us-west-2")
OPENSEARCH_INDEX = os.getenv("OPENSEARCH_INDEX", "products")

# Redis config
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
CACHE_TTL = 300  # 5 minutes

# =========================================================================
# 🔌 OPENSEARCH CLIENT (AWS Sig V4 auth)
# =========================================================================

credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, OPENSEARCH_REGION, 'aoss')

os_client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=30
)

# =========================================================================
# 🔌 REDIS CLIENT (with graceful fallback)
# =========================================================================

try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=2
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
    logger.info("✅ Redis connected for stats caching")
except Exception as e:
    REDIS_AVAILABLE = False
    logger.warning(f"⚠️  Redis not available — caching disabled: {e}")

# =========================================================================
# 🗺️ METRIC FIELD MAPPING
# Maps API names to OpenSearch field names
# =========================================================================

METRIC_FIELDS = {
    "view":         "stats_views",
    "click":        "stats_clicks",
    "add-to-cart":  "stats_carts",
    "wishlist":     "stats_wishlist",
    "purchase":     "stats_purchases",
    "trending":     "trending_score",
}

# =========================================================================
# 🎯 MAIN FUNCTION — Get Top Products by Metric
# =========================================================================

async def get_top_products_by_metric(
    metric: str,
    page: int = 1,
    size: int = 10
) -> dict:
    """
    Get top products sorted by a specific engagement metric.
    
    Args:
        metric: One of 'view', 'click', 'add-to-cart', 'wishlist', 'purchase', 'trending'
        page: Page number (1-indexed)
        size: Number of results per page
    
    Returns:
        {
            "results": [...products...],
            "total": int,
            "page": int,
            "size": int,
            "took_ms": float,
            "metric": str,
            "cached": bool
        }
    """
    start_time = time.time()
    
    # Validate metric
    if metric not in METRIC_FIELDS:
        return {
            "error": f"Invalid metric. Must be one of: {list(METRIC_FIELDS.keys())}",
            "results": [],
            "total": 0
        }
    
    # Validate pagination
    page = max(1, page)
    size = max(1, min(size, 100))  # Cap at 100 results
    
    sort_field = METRIC_FIELDS[metric]
    
    # =====================================================================
    # 1. CHECK REDIS CACHE
    # =====================================================================
    cache_key = f"stats:{metric}:{page}:{size}"
    
    if REDIS_AVAILABLE:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                result = json.loads(cached)
                result["cached"] = True
                result["took_ms"] = round((time.time() - start_time) * 1000, 2)
                logger.info(f"⚡ STATS_CACHE_HIT | metric={metric} | page={page} | took={result['took_ms']}ms")
                return result
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
    
    # =====================================================================
    # 2. QUERY OPENSEARCH
    # =====================================================================
    from_offset = (page - 1) * size
    
    # For trending, threshold is > 1 (default value). For others, > 0.
    threshold = 1 if metric == "trending" else 0
    
    query_body = {
        "size": size,
        "from": from_offset,
        "_source": [
            "product_id",
            "name",
            "price",
            "sale_price",
            "images",
            "url",
            "category",
            "brand",
            "in_stock",
            "trending_score",
            "stats_views",
            "stats_clicks",
            "stats_carts",
            "stats_wishlist",
            "stats_purchases"
        ],
        "query": {
            "bool": {
                "must": [
                    {"range": {sort_field: {"gt": threshold}}}
                ],
                "filter": [
                    {"term": {"in_stock": True}}
                ]
            }
        },
        "sort": [
            {sort_field: {"order": "desc"}}
        ]
    }
    
    try:
        response = os_client.search(
            index=OPENSEARCH_INDEX,
            body=query_body
        )
    except Exception as e:
        logger.error(f"❌ OpenSearch query failed: {e}")
        return {
            "error": "Failed to fetch products",
            "results": [],
            "total": 0,
            "page": page,
            "size": size
        }
    
    # =====================================================================
    # 3. FORMAT RESULTS
    # =====================================================================
    hits = response.get("hits", {}).get("hits", [])
    total = response.get("hits", {}).get("total", {}).get("value", 0)
    
    results = []
    for hit in hits:
        source = hit.get("_source", {})
        
        # Get first image (images is comma-separated string)
        images = source.get("images", "")
        first_image = images.split(",")[0].strip() if images else ""
        
        results.append({
            "product_id": source.get("product_id"),
            "name": source.get("name", ""),
            "price": source.get("price", 0),
            "sale_price": source.get("sale_price", 0),
            "image": first_image,
            "url": source.get("url", ""),
            "category": source.get("category", ""),
            "brand": source.get("brand", ""),
            "in_stock": source.get("in_stock", True),
            "trending_score": source.get("trending_score", 0),
            "stats_views": source.get("stats_views", 0),
            "stats_clicks": source.get("stats_clicks", 0),
            "stats_carts": source.get("stats_carts", 0),
            "stats_wishlist": source.get("stats_wishlist", 0),
            "stats_purchases": source.get("stats_purchases", 0),
        })
    
    took_ms = round((time.time() - start_time) * 1000, 2)
    
    result = {
        "results": results,
        "total": total,
        "page": page,
        "size": size,
        "metric": metric,
        "took_ms": took_ms,
        "cached": False
    }
    
    # =====================================================================
    # 4. SAVE TO REDIS CACHE
    # =====================================================================
    if REDIS_AVAILABLE:
        try:
            redis_client.setex(
                cache_key,
                CACHE_TTL,
                json.dumps(result)
            )
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
    
    logger.info(f"✅ STATS | metric={metric} | page={page} | results={len(results)} | took={took_ms}ms")
    
    return result


# =========================================================================
# 🔥 CACHE INVALIDATION (use after pipeline.py runs)
# =========================================================================

def invalidate_stats_cache():
    """
    Clear all stats cache entries. Call this after pipeline.py finishes
    re-indexing OpenSearch with fresh tracking data.
    """
    if not REDIS_AVAILABLE:
        return False
    
    try:
        keys = redis_client.keys("stats:*")
        if keys:
            redis_client.delete(*keys)
            logger.info(f"🗑️  Invalidated {len(keys)} stats cache entries")
        return True
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        return False
