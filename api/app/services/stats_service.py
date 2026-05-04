"""
=====================================================================================
📊 STATS SERVICE — Top Products by Engagement Metrics
=====================================================================================
Powers 6 APIs that return top products sorted by different metrics:

  1. /products/view          → Most viewed products
  2. /products/click         → Most clicked products
  3. /products/add-to-cart   → Most added to cart
  4. /products/wishlist      → Most wished products
  5. /products/purchase      → Most purchased (best sellers)
  6. /products/trending      → Hot products (combined trending_score)

USES SHARED CONFIG:
  - os_client     → OpenSearch client (from config.py)
  - redis_client  → Redis client (from config.py)
  - INDEX_NAME    → Products index name (from config.py)

PERFORMANCE:
  - First call: ~50-100ms (OpenSearch query)
  - Cached call: ~2-5ms (Redis)
  - Cache key: stats:{metric}:{page}:{size}
=====================================================================================
"""

import time
import json
import logging

# 🆕 Import everything from existing config (uses correct endpoint automatically)
from app.config import os_client, redis_client, INDEX_NAME

# =========================================================================
# ⚙️ CONFIG
# =========================================================================

logger = logging.getLogger("StatsService")

CACHE_TTL = 300  # 5 minutes

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
    size = max(1, min(size, 100))  # Cap at 100
    
    sort_field = METRIC_FIELDS[metric]
    
    # =====================================================================
    # 1. CHECK REDIS CACHE
    # =====================================================================
    cache_key = f"stats:{metric}:{page}:{size}"
    
    try:
        cached = await redis_client.get(cache_key)
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
            index=INDEX_NAME,
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
        
        # Get first image (handles both list and comma-separated string formats)
        images = source.get("images", "")
        if isinstance(images, list):
            first_image = images[0] if images else ""
        elif isinstance(images, str):
            first_image = images.split(",")[0].strip() if images else ""
        else:
            first_image = ""
        
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
    try:
        await redis_client.setex(
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

async def invalidate_stats_cache():
    """Clear all stats cache entries. Call after pipeline.py runs."""
    try:
        keys = await redis_client.keys("stats:*")
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"🗑️  Invalidated {len(keys)} stats cache entries")
        return True
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        return False
