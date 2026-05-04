"""
=====================================================================================
📊 STATS SERVICE — Personal Top Products (Per Visitor)
=====================================================================================
Queries product_metrics table (now per-user) to return personalized products.

LOGIC:
  - If user_id provided → query by user_id
  - If only visitor_id → query by visitor_id
  - Both work because we store either user_id or visitor_id in same column

Powers 6 APIs:
  /products/view, /products/click, /products/add-to-cart,
  /products/wishlist, /products/purchase, /products/trending
=====================================================================================
"""

import os
import time
import json
import logging

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import os_client, redis_client, INDEX_NAME

# =========================================================================
# ⚙️ CONFIG
# =========================================================================

logger = logging.getLogger("StatsService")

CACHE_TTL = 300  # 5 minutes

# Database config
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "venue_ai"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "shubham16"),
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# =========================================================================
# 🗺️ METRIC FIELD MAPPING — Maps API names to database column names
# =========================================================================

METRIC_FIELDS = {
    "view":         "views",
    "click":        "clicks",
    "add-to-cart":  "carts",
    "wishlist":     "wishlist",
    "purchase":     "purchases",
    "trending":     "trending_score",
}

# =========================================================================
# 🆕 HELPER: Determine which ID to use for query
# =========================================================================

def get_query_identity(visitor_id: str, user_id: str = None) -> str:
    """
    Returns the ID to use for querying:
    - If user_id provided (logged in): use user_id
    - Otherwise: use visitor_id
    
    This matches what tracking.py stored in the database.
    """
    if user_id and user_id.strip() and user_id != "null":
        return user_id.strip()
    return visitor_id.strip() if visitor_id else None

# =========================================================================
# 🎯 MAIN FUNCTION — Get Top Products for Visitor
# =========================================================================

async def get_top_products_by_metric(
    metric: str,
    visitor_id: str,
    user_id: str = None,
    page: int = 1,
    size: int = 10
) -> dict:
    """
    Get top products for this visitor/user sorted by metric.
    
    Args:
        metric: 'view', 'click', 'add-to-cart', 'wishlist', 'purchase', 'trending'
        visitor_id: Browser UUID (always present)
        user_id: BigCommerce customer ID (only if logged in)
        page: Page number (1-indexed)
        size: Results per page
    """
    start_time = time.time()
    
    # Validate metric
    if metric not in METRIC_FIELDS:
        return {
            "error": f"Invalid metric. Must be one of: {list(METRIC_FIELDS.keys())}",
            "results": [],
            "total": 0
        }
    
    # 🆕 Determine identity (matches tracking.py logic)
    identity = get_query_identity(visitor_id, user_id)
    
    if not identity:
        return {
            "error": "visitor_id or user_id is required",
            "results": [],
            "total": 0
        }
    
    # Validate pagination
    page = max(1, page)
    size = max(1, min(size, 100))
    
    sort_column = METRIC_FIELDS[metric]
    
    # =====================================================================
    # 1. CHECK REDIS CACHE
    # =====================================================================
    cache_key = f"stats:{identity}:{metric}:{page}:{size}"
    
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["cached"] = True
            result["took_ms"] = round((time.time() - start_time) * 1000, 2)
            logger.info(f"⚡ STATS_CACHE_HIT | id={identity[:12]}... | metric={metric} | took={result['took_ms']}ms")
            return result
    except Exception as e:
        logger.warning(f"Cache read failed: {e}")
    
    # =====================================================================
    # 2. QUERY POSTGRESQL — Get product IDs for this identity
    # =====================================================================
    offset = (page - 1) * size
    threshold = 1 if metric == "trending" else 0
    
    query = f"""
        SELECT product_id, {sort_column} as score, last_seen
        FROM product_metrics
        WHERE visitor_id = %s AND {sort_column} > {threshold}
        ORDER BY {sort_column} DESC, last_seen DESC
        LIMIT %s OFFSET %s
    """
    
    count_query = f"""
        SELECT COUNT(*) as total
        FROM product_metrics
        WHERE visitor_id = %s AND {sort_column} > {threshold}
    """
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(count_query, (identity,))
        total = cur.fetchone()["total"]
        
        cur.execute(query, (identity, size, offset))
        rows = cur.fetchall()
        
        cur.close()
        
    except Exception as e:
        logger.error(f"❌ PostgreSQL query failed: {e}")
        if conn:
            conn.close()
        return {
            "error": "Failed to fetch data",
            "results": [],
            "total": 0,
            "page": page,
            "size": size
        }
    finally:
        if conn:
            conn.close()
    
    # If no data for this identity
    if not rows:
        return {
            "results": [],
            "total": 0,
            "page": page,
            "size": size,
            "metric": metric,
            "identity": identity,
            "took_ms": round((time.time() - start_time) * 1000, 2),
            "cached": False,
            "message": "No history found for this user"
        }
    
    # =====================================================================
    # 3. FETCH PRODUCT DETAILS FROM OPENSEARCH
    # =====================================================================
    product_ids = [row["product_id"] for row in rows]
    score_map = {row["product_id"]: float(row["score"]) for row in rows}
    
    try:
        os_response = os_client.search(
            index=INDEX_NAME,
            body={
                "size": len(product_ids),
                "_source": [
                    "product_id", "name", "price", "sale_price",
                    "images", "url", "category", "brand", "in_stock"
                ],
                "query": {
                    "terms": {"product_id": product_ids}
                }
            }
        )
        
        product_map = {}
        for hit in os_response.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            pid = source.get("product_id")
            
            # Get first image (handles list or string)
            images = source.get("images", "")
            if isinstance(images, list):
                first_image = images[0] if images else ""
            elif isinstance(images, str):
                first_image = images.split(",")[0].strip() if images else ""
            else:
                first_image = ""
            
            product_map[pid] = {
                "product_id": pid,
                "name": source.get("name", ""),
                "price": source.get("price", 0),
                "sale_price": source.get("sale_price", 0),
                "image": first_image,
                "url": source.get("url", ""),
                "category": source.get("category", ""),
                "brand": source.get("brand", ""),
                "in_stock": source.get("in_stock", True),
            }
        
    except Exception as e:
        logger.error(f"❌ OpenSearch query failed: {e}")
        return {
            "error": "Failed to fetch product details",
            "results": [],
            "total": 0,
            "page": page,
            "size": size
        }
    
    # =====================================================================
    # 4. BUILD RESULTS (preserving PostgreSQL order)
    # =====================================================================
    results = []
    for pid in product_ids:
        if pid in product_map:
            product = product_map[pid].copy()
            product[f"user_{sort_column}"] = score_map[pid]
            results.append(product)
    
    took_ms = round((time.time() - start_time) * 1000, 2)
    
    result = {
        "results": results,
        "total": total,
        "page": page,
        "size": size,
        "metric": metric,
        "identity": identity,
        "took_ms": took_ms,
        "cached": False
    }
    
    # =====================================================================
    # 5. SAVE TO REDIS CACHE
    # =====================================================================
    try:
        await redis_client.setex(
            cache_key,
            CACHE_TTL,
            json.dumps(result)
        )
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")
    
    logger.info(f"✅ STATS | id={identity[:12]}... | metric={metric} | results={len(results)} | took={took_ms}ms")
    
    return result


# =========================================================================
# 🔥 CACHE INVALIDATION
# =========================================================================

async def invalidate_user_cache(identity: str):
    """Clear cache for a specific user/visitor."""
    try:
        keys = await redis_client.keys(f"stats:{identity}:*")
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"🗑️  Invalidated {len(keys)} cache entries for {identity[:12]}...")
        return True
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        return False
