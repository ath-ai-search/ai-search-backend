"""
=====================================================================================
📊 STATS SERVICE — Advanced Recommendation Engine
=====================================================================================
Powers the 3 consolidated APIs:
  1. /recommendations -> Category-based filtering (views + clicks)
  2. /pick-up         -> Personal intent (carts + wishlists)
  3. /trending        -> Global popularity (purchases + trending score)
=====================================================================================
"""

import os
import time
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import os_client, redis_client, INDEX_NAME

logger = logging.getLogger("StatsService")
CACHE_TTL = 300  

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "venue_ai"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "shubham16"),
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_query_identity(visitor_id: str, user_id: str = None) -> str:
    """Returns the ID to use for querying."""
    if user_id and user_id.strip() and user_id != "null":
        return user_id.strip()
    return visitor_id.strip() if visitor_id else None

def parse_os_product(src):
    """Helper to parse OpenSearch product source into a clean dictionary."""
    images = src.get("images", "")
    if isinstance(images, list): 
        first_image = images[0] if images else ""
    elif isinstance(images, str): 
        first_image = images.split(",")[0].strip() if images else ""
    else: 
        first_image = ""
    
    return {
        "product_id": src.get("product_id"),
        "name": src.get("name", ""),
        "price": src.get("price", 0),
        "sale_price": src.get("sale_price", 0),
        "image": first_image,
        "url": src.get("url", ""),
        "category": src.get("category", ""),
        "brand": src.get("brand", ""),
        "in_stock": src.get("in_stock", True),
    }

async def get_top_products_by_metric(metric: str, visitor_id: str, user_id: str = None, page: int = 1, size: int = 10) -> dict:
    start_time = time.time()
    identity = get_query_identity(visitor_id, user_id)
    offset = (page - 1) * size

    # =====================================================================
    # 1. CACHE CHECK (Global vs Personal)
    # =====================================================================
    # If it's trending, we cache it globally. Otherwise, cache per user.
    cache_identity = "global" if metric == "trending" else identity
    cache_key = f"stats:{cache_identity}:{metric}:{page}:{size}"
    
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["cached"] = True
            result["took_ms"] = round((time.time() - start_time) * 1000, 2)
            logger.info(f"⚡ CACHE_HIT | metric={metric}")
            return result
    except Exception:
        pass

    conn = None
    results = []
    total = 0

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

# =====================================================================
        # 🔥 API 1: RECOMMENDATIONS (Category-Based with Recency Bias)
        # =====================================================================
        if metric == "recommendations":
            if not identity: return {"error": "visitor_id required"}
            
            # Step A: Get exactly what the user viewed/clicked, sorted by NEWEST first
            cur.execute("""
                SELECT product_id 
                FROM product_metrics 
                WHERE visitor_id = %s AND (views + clicks) > 0 
                ORDER BY last_seen DESC LIMIT 20
            """, (identity,))
            history = cur.fetchall()

            # If they have no history, fallback to trending
            if not history:
                return await get_top_products_by_metric("trending", visitor_id, user_id, page, size)

            history_pids = [r["product_id"] for r in history]

            # Step B: Get Categories of these items from OpenSearch
            os_cat_res = os_client.search(
                index=INDEX_NAME,
                body={"size": 20, "_source": ["category", "product_id"], "query": {"terms": {"product_id": history_pids}}}
            )

            # Step C: Extract categories in the EXACT order they were viewed
            pid_to_cat = {}
            for hit in os_cat_res.get("hits", {}).get("hits", []):
                cat_data = hit.get("_source", {}).get("category")
                pid = hit.get("_source", {}).get("product_id")
                if cat_data:
                    pid_to_cat[pid] = cat_data if isinstance(cat_data, list) else [cat_data]

            recent_categories = []
            for pid in history_pids:
                cats = pid_to_cat.get(pid, [])
                for cat in cats:
                    if cat and cat not in recent_categories:
                        recent_categories.append(cat)
                        if len(recent_categories) >= 3: # Keep the 3 most recent unique categories
                            break
                if len(recent_categories) >= 3:
                    break

            if not recent_categories:
                return await get_top_products_by_metric("trending", visitor_id, user_id, page, size)

            # Step D: Ask OpenSearch for NEW products in these recent categories
            os_rec_res = os_client.search(
                index=INDEX_NAME,
                body={
                    "size": size, 
                    "from": offset,
                    "query": {
                        "bool": {
                            "should": [{"match": {"category": c}} for c in recent_categories],
                            "must_not": [{"terms": {"product_id": history_pids}}],
                            "minimum_should_match": 1
                        }
                    }
                }
            )

            for hit in os_rec_res.get("hits", {}).get("hits", []):
                prod = parse_os_product(hit.get("_source", {}))
                # Check if category is a list, and if so, just grab the first one to look clean!
                display_cat = prod['category'][0] if isinstance(prod['category'], list) else prod['category']
                prod["recommendation_reason"] = f"Based on your recent interest in {display_cat}"
                results.append(prod)
            
            # Step E: Sort the final results so the most recent category is at the front of the slider!
            def get_category_rank(prod_cat):
                for i, rc in enumerate(recent_categories):
                    if rc == prod_cat or (isinstance(prod_cat, list) and rc in prod_cat):
                        return i
                return 999

            results.sort(key=lambda p: get_category_rank(p.get("category")))
            
            total = os_rec_res.get("hits", {}).get("total", {}).get("value", len(results))
            db_rows = []

        # =====================================================================
        # 🛒 API 2: PICK-UP (Personal Carts & Wishlists)
        # =====================================================================
        elif metric == "pick-up":
            if not identity: return {"error": "visitor_id required"}
            cur.execute("SELECT COUNT(*) as t FROM product_metrics WHERE visitor_id = %s AND (carts + wishlist) > 0", (identity,))
            total = cur.fetchone()["t"]

            cur.execute("""
                SELECT product_id, (carts + wishlist) as score 
                FROM product_metrics 
                WHERE visitor_id = %s AND (carts + wishlist) > 0 
                ORDER BY score DESC LIMIT %s OFFSET %s
            """, (identity, size, offset))
            db_rows = cur.fetchall()

        # =====================================================================
        # 🌍 API 3: TRENDING (Global Purchases & Engagement)
        # =====================================================================
        elif metric == "trending":
            # Global query, no visitor_id filtering
            cur.execute("SELECT COUNT(DISTINCT product_id) as t FROM product_metrics WHERE trending_score > 0 OR purchases > 0")
            total = cur.fetchone()["t"]

            cur.execute("""
                SELECT product_id, SUM(purchases * 10 + trending_score) as score 
                FROM product_metrics 
                GROUP BY product_id 
                HAVING SUM(purchases * 10 + trending_score) > 0 
                ORDER BY score DESC LIMIT %s OFFSET %s
            """, (size, offset))
            db_rows = cur.fetchall()

        cur.close()

        # Fetch OpenSearch Details for Pick-Up and Trending
        if metric in ["pick-up", "trending"] and db_rows:
            pids = [r["product_id"] for r in db_rows]
            score_map = {r["product_id"]: float(r["score"]) for r in db_rows}
            
            os_res = os_client.search(
                index=INDEX_NAME,
                body={"size": len(pids), "query": {"terms": {"product_id": pids}}}
            )
            
            prod_map = {h["_source"]["product_id"]: parse_os_product(h["_source"]) for h in os_res.get("hits", {}).get("hits", [])}
            
            for pid in pids:
                if pid in prod_map:
                    prod = prod_map[pid].copy()
                    prod["score"] = score_map[pid]
                    results.append(prod)

    except Exception as e:
        logger.error(f"❌ Query failed: {e}")
        return {"error": "Failed to fetch data", "results": []}
    finally:
        if conn: conn.close()

    # Finalize Response
    took_ms = round((time.time() - start_time) * 1000, 2)
    response = {
        "results": results, 
        "total": total, 
        "page": page, 
        "size": size,
        "metric": metric, 
        "took_ms": took_ms, 
        "cached": False
    }

    try:
        await redis_client.setex(cache_key, CACHE_TTL, json.dumps(response))
    except Exception:
        pass
        
    return response


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