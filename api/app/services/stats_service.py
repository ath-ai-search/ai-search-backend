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
import random  # 🔥 ADD THIS LINE AT THE TOP
import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import os_client, redis_client, INDEX_NAME

logger = logging.getLogger("StatsService")
CACHE_TTL = 0  

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
    # 1. Grab image data from whichever field your database uses
    raw_img_data = src.get("images") or ""
    
    first_image = ""
    
    # 2. If it's a list, grab STRICTLY the first item
    if isinstance(raw_img_data, list) and len(raw_img_data) > 0:
        first_image = str(raw_img_data[0])
        
    # 3. If it's a string, clean up brackets/quotes and split by comma to force ONLY the first image
    elif isinstance(raw_img_data, str) and raw_img_data:
        cleaned = raw_img_data.strip("[]'\" ")
        first_image = cleaned.split(",")[0].strip("[]'\" ")
    
    return {
        "product_id": src.get("product_id"),
        "name": src.get("name", ""),
        "price": src.get("price", 0),
        "sale_price": src.get("sale_price", 0),
        "image": first_image,          # 🔥 FORCES exactly the first image
        "primary_image": first_image,  # 🔥 Blocks the UI from pulling a secondary image!
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
            
            # Step A: Get exactly what the user viewed/clicked.
            # 🔥 STRICT TIMELINE: The newest thing you clicked is ALWAYS Box 1.
            cur.execute("""
                SELECT product_id 
                FROM product_metrics 
                WHERE visitor_id = %s AND (views + clicks) > 0 
                ORDER BY last_seen DESC LIMIT 100
            """, (identity,))
            history = cur.fetchall()

            # 🔥 COLD START FALLBACK: If it is a brand new user, show dynamic SALE items!
            if not history:
                # 1. Fetch 100 items that are strictly ON SALE
                os_rec_res = os_client.search(
                    index=INDEX_NAME,
                    body={
                        "size": 100, 
                        "query": {
                            "bool": {
                                "must": [{"match_all": {}}],
                                "filter": [{"range": {"sale_price": {"gt": 0}}}]
                            }
                        }
                    }
                )
                
                cold_results = []
                for hit in os_rec_res.get("hits", {}).get("hits", []):
                    prod = parse_os_product(hit.get("_source", {}))
                    prod["recommendation_reason"] = "Trending Deals Just For You"
                    cold_results.append(prod)
                    
                # 2. Dynamically group them by whatever categories OpenSearch found
                grouped = {}
                for p in cold_results:
                    c = p.get("category", ["Uncategorized"])
                    c_name = c[0] if isinstance(c, list) and c else c if isinstance(c, str) else "Uncategorized"
                    if c_name not in grouped: 
                        grouped[c_name] = []
                    grouped[c_name].append(p)
                    
                # 3. Interleave them perfectly (Round-Robin)
                mixed = []
                while any(grouped.values()):
                    for c_name in list(grouped.keys()):
                        if grouped[c_name]: 
                            mixed.append(grouped[c_name].pop(0))
                
                # 4. Chop to the requested UI size and return immediately
                final_results = mixed[:size]
                
                response = {
                    "results": final_results, 
                    "total": len(final_results), 
                    "page": page, "size": size, "metric": metric, 
                    "took_ms": round((time.time() - start_time) * 1000, 2), 
                    "cached": False
                }
                try: 
                    await redis_client.setex(cache_key, CACHE_TTL, json.dumps(response))
                except: pass
                
                return response

            history_pids = [r["product_id"] for r in history]

            # Step B: Get Categories of these items from OpenSearch
            # 🔥 INCREASED size to 100 so it doesn't randomly drop your timeline history!
            os_cat_res = os_client.search(
                index=INDEX_NAME,
                body={"size": 100, "_source": ["category", "product_id"], "query": {"terms": {"product_id": history_pids}}}
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
                        if len(recent_categories) >= 12: # 🔥 INCREASED TO 12 to guarantee iPhones, Shoes, and Dresses all get included!
                            break
                if len(recent_categories) >= 12:
                    break

            if not recent_categories:
                return {
                    "results": [], 
                    "total": 0, 
                    "page": page, 
                    "size": size, 
                    "metric": metric, 
                    "took_ms": 0, 
                    "cached": False
                }

            # Step D: AMAZON LOGIC - Fetch SALE items from the user's recent categories!
            should_clauses = []
            for c in recent_categories:
                should_clauses.append({"match": {"category": {"query": c, "operator": "and"}}})

            os_rec_res = os_client.search(
                index=INDEX_NAME,
                body={
                    "size": 150,  
                    "from": offset,
                    "query": {
                        "bool": {
                            "should": should_clauses,
                            "minimum_should_match": 1,
                            # 🔥 STRICT AMAZON RULE: Only show items that are actually ON SALE!
                            "filter": [
                                {"range": {"sale_price": {"gt": 0}}}
                            ]
                        }
                    }
                }
            )
            
            # Step E: THE PERFECT MIXER (Round-Robin Category Interleaving)
            grouped_prods = {rc: [] for rc in recent_categories}
            leftovers = []
            
            for hit in os_rec_res.get("hits", {}).get("hits", []):
                prod = parse_os_product(hit.get("_source", {}))
                p_cat = prod.get("category")
                
                # Assign the product to its matching category bucket
                placed = False
                for rc in recent_categories:
                    if rc == p_cat or (isinstance(p_cat, list) and rc in p_cat) or (isinstance(p_cat, str) and rc in p_cat):
                        display_cat = prod['category'][0] if isinstance(prod['category'], list) else prod['category']
                        prod["recommendation_reason"] = f"Based on your recent interest in {display_cat}"
                        grouped_prods[rc].append(prod)
                        placed = True
                        break
                
                # If it somehow doesn't match perfectly, put it in leftovers
                if not placed:
                    prod["recommendation_reason"] = "Trending Deals Just For You"
                    leftovers.append(prod)

            # 🔥 AMAZON MIXING: Deal 1 card from Shoe, 1 from Dress, 1 from Phone, repeat!
            mixed_results = []
            while any(grouped_prods.values()):
                for rc in recent_categories:
                    if grouped_prods[rc]:
                        mixed_results.append(grouped_prods[rc].pop(0))
            
            # Combine the perfectly mixed list with any leftovers
            results = mixed_results + leftovers
            
            # 🔥 CHOP THE LIST TO 4 BOXES FOR YOUR UI
            results = results[:size]
            
            total = os_rec_res.get("hits", {}).get("total", {}).get("value", len(results))
            db_rows = []

        # =====================================================================
        # 🛒 API 2: PICK-UP (Carts/Wishlists + Dynamic Sale Padding)
        # =====================================================================
        elif metric == "pick-up":
            if not identity: return {"error": "visitor_id required"}
            
            # Count how many items the user actually has in cart/wishlist
            cur.execute("""
                SELECT COUNT(*) as t 
                FROM product_metrics 
                WHERE visitor_id = %s AND (carts + wishlist) > 0
            """, (identity,))
            total = cur.fetchone()["t"]

            # 🔥 ADDED "variant_image" to the database query
            cur.execute("""
                SELECT product_id, variant_image 
                FROM product_metrics 
                WHERE visitor_id = %s AND (carts + wishlist) > 0 
                ORDER BY last_seen DESC LIMIT %s OFFSET %s
            """, (identity, size, offset))
            user_history = cur.fetchall()

            user_pids = [r["product_id"] for r in user_history]
            
            # 🔥 Create a memory map of the exact variant images the user clicked
            variant_map = {r["product_id"]: r["variant_image"] for r in user_history if "variant_image" in r and r["variant_image"]}
            
            user_results = []

            # 1. Fetch the EXACT items they added to cart/wishlist
            if user_pids:
                os_res = os_client.search(
                    index=INDEX_NAME,
                    body={"size": len(user_pids), "query": {"terms": {"product_id": user_pids}}}
                )
                prod_map = {h["_source"]["product_id"]: parse_os_product(h["_source"]) for h in os_res.get("hits", {}).get("hits", [])}
                for pid in user_pids:
                    if pid in prod_map:
                        prod = prod_map[pid].copy()
                        
                        # 🔥 THE MAGIC OVERRIDE: ONLY overwrite if the variant image actually exists and is not empty!
                        if variant_map.get(pid):
                            prod["image"] = variant_map[pid]
                            prod["primary_image"] = variant_map[pid]
                            
                        prod["recommendation_reason"] = "Saved in Cart/Wishlist"
                        user_results.append(prod)

            # 2. Figure out how many empty spaces we need to fill!
            padding_needed = size - len(user_results)
            dynamic_results = []

            if padding_needed > 0:
                # 🔥 REFRESH LOGIC: Pick a random start point for variety
                random_offset = random.randint(0, 40)

                # Tell OpenSearch NOT to fetch items already in their cart
                must_not = [{"terms": {"product_id": user_pids}}] if user_pids else []
                os_pad_res = os_client.search(
                    index=INDEX_NAME,
                    body={
                        "size": padding_needed,
                        "from": 0,                      # 🔥 BATCH 1: Grab the very top luxurious items
                        "sort": [{"price": "desc"}],    # 🔥 LUXURIOUS: Sort by Highest Price!
                        "query": {
                            "bool": {
                                "must": [{"match_all": {}}],
                                "must_not": must_not,
                                "filter": [
                                    {"range": {"sale_price": {"gt": 0}}},
                                    {"range": {"price": {"gte": 100}}}, # 🔥 STRICT LUXURY FILTER ($100+)
                                    {"bool": {
                                        "should": [
                                            {"match": {"category": "Fashion"}},
                                            {"match": {"category": "Kitchen"}},
                                            {"match": {"category": "Clothing"}}
                                        ],
                                        "minimum_should_match": 1
                                    }}
                                ]
                            }
                        }
                    }
                )
                for hit in os_pad_res.get("hits", {}).get("hits", []):
                    prod = parse_os_product(hit.get("_source", {}))
                    prod["recommendation_reason"] = "Trending Deals Just For You"
                    dynamic_results.append(prod)

            # 3. Combine them together and return instantly!
            final_results = user_results + dynamic_results

            response = {
                "results": final_results,
                "total": max(total, len(final_results)),
                "page": page,
                "size": size,
                "metric": metric,
                "took_ms": round((time.time() - start_time) * 1000, 2),
                "cached": False
            }
            try:
                await redis_client.setex(cache_key, CACHE_TTL, json.dumps(response))
            except:
                pass
            return response

        # =====================================================================
        # 🎯 API 4: RECOMMENDATION GRIDS (Recently Viewed + Dynamic Padding)
        # =====================================================================
        elif metric == "recommendation-grids":
            if not identity: return {"error": "visitor_id required"}
            
            # 🔥 RELAXED RULE: Works if they just VIEWED or CLICKED!
            cur.execute("""
                SELECT COUNT(*) as t 
                FROM product_metrics 
                WHERE visitor_id = %s AND (views + clicks) > 0 AND (carts + wishlist) = 0
            """, (identity,))
            total = cur.fetchone()["t"]

            # 🔥 RELAXED RULE: Fetch exactly what the user viewed or clicked (with variant images)
            # 🔥 EXCLUDE items already in cart/wishlist (those belong to pick-up API)
            cur.execute("""
                SELECT product_id, variant_image 
                FROM product_metrics 
                WHERE visitor_id = %s AND (views + clicks) > 0 AND (carts + wishlist) = 0
                ORDER BY last_seen DESC LIMIT %s OFFSET %s
            """, (identity, size, offset))
            user_history = cur.fetchall()

            user_pids = [r["product_id"] for r in user_history]
            variant_map = {r["product_id"]: r["variant_image"] for r in user_history if "variant_image" in r and r["variant_image"]}
            user_results = []

            # 2. Ask OpenSearch for these exact items
            if user_pids:
                os_res = os_client.search(
                    index=INDEX_NAME,
                    body={"size": len(user_pids), "query": {"terms": {"product_id": user_pids}}}
                )
                prod_map = {h["_source"]["product_id"]: parse_os_product(h["_source"]) for h in os_res.get("hits", {}).get("hits", [])}
                for pid in user_pids:
                    if pid in prod_map:
                        prod = prod_map[pid].copy()
                        
                        # ✅ Use first image from OpenSearch directly (parse_os_product already handles this)
                        prod["recommendation_reason"] = "Recently Viewed by You"
                        user_results.append(prod)

            # 3. Figure out how many empty spaces we need to fill!
            padding_needed = size - len(user_results)
            dynamic_results = []

            if padding_needed > 0:
                # 🔥 Also exclude whatever is already in the user's cart/wishlist (those show in pick-up)
                cur.execute("""
                    SELECT product_id FROM product_metrics 
                    WHERE visitor_id = %s AND (carts + wishlist) > 0
                """, (identity,))
                cart_pids = [r["product_id"] for r in cur.fetchall()]

                all_excluded_pids = list(set(user_pids + cart_pids))
                must_not = [{"terms": {"product_id": all_excluded_pids}}] if all_excluded_pids else []
                os_pad_res = os_client.search(
                    index=INDEX_NAME,
                    body={
                        "size": padding_needed,
                        "from": 20,                     # 🔥 BATCH 2: Skip the first 20 so it NEVER overlaps with Pick-Up!
                        "sort": [{"price": "desc"}],    # 🔥 LUXURIOUS: Sort by Highest Price!
                        "query": {
                            "bool": {
                                "must": [{"match_all": {}}],
                                "must_not": must_not,
                                "filter": [
                                    {"range": {"sale_price": {"gt": 0}}},
                                    {"range": {"price": {"gte": 100}}}, # 🔥 STRICT LUXURY FILTER ($100+)
                                    {"bool": {
                                        "should": [
                                            {"match": {"category": "Fashion"}},
                                            {"match": {"category": "Kitchen"}},
                                            {"match": {"category": "Clothing"}} # Added Clothing just in case your DB uses it!
                                        ],
                                        "minimum_should_match": 1
                                    }}
                                ]
                            }
                        }
                    }
                )
                for hit in os_pad_res.get("hits", {}).get("hits", []):
                    prod = parse_os_product(hit.get("_source", {}))
                    prod["recommendation_reason"] = "Trending Deals Just For You"
                    dynamic_results.append(prod)

            # 4. Combine them together and return instantly!
            final_results = user_results + dynamic_results

            response = {
                "results": final_results,
                "total": max(total, len(final_results)),
                "page": page,
                "size": size,
                "metric": metric,
                "took_ms": round((time.time() - start_time) * 1000, 2),
                "cached": False
            }
            try:
                await redis_client.setex(cache_key, CACHE_TTL, json.dumps(response))
            except:
                pass
            return response

        # =====================================================================
        # 🔥 API 3: TRENDING (GLOBAL Popularity - FIXED!)
        # Uses ALL events: views, clicks, wishlist, carts, purchases
        # Formula: 1.0 + views*1 + clicks*2 + wishlist*3 + carts*5 + purchases*10
        # =====================================================================
        elif metric == "trending":
            # 1. Total count of products with ANY activity (including wishlist!)
            cur.execute("""
                SELECT COUNT(DISTINCT product_id) as t 
                FROM product_metrics 
                WHERE views > 0 OR clicks > 0 OR carts > 0 OR purchases > 0 OR wishlist > 0
            """)
            total = cur.fetchone()["t"]

            # 2. ✅ FIXED: GLOBAL trending using SAME formula as stored trending_score
            # Aggregates from ALL users to find globally popular products
            cur.execute("""
                SELECT 
                    product_id, 
                    SUM(
                        1.0 + 
                        (views * 1) + 
                        (clicks * 2) + 
                        (wishlist * 3) + 
                        (carts * 5) + 
                        (purchases * 10)
                    ) as score,
                    SUM(views) as total_views,
                    SUM(clicks) as total_clicks,
                    SUM(wishlist) as total_wishlist,
                    SUM(carts) as total_carts,
                    SUM(purchases) as total_purchases
                FROM product_metrics 
                GROUP BY product_id 
                HAVING SUM(views + clicks + carts + purchases + wishlist) > 0 
                ORDER BY score DESC 
                LIMIT 100 OFFSET %s
            """, (offset,))
            db_rows = cur.fetchall()

        cur.close()

        # Fetch OpenSearch Details for Trending and Recommendation Grids
        if metric in ["trending", "recommendation-grids"] and db_rows:
            pids = [r["product_id"] for r in db_rows]
            
            # Build a comprehensive score map
            score_map = {}
            for r in db_rows:
                product_data = {"score": float(r["score"])}
                
                # 🔥 Save the variant image to memory if it exists
                if "variant_image" in r and r["variant_image"]:
                    product_data["variant_image"] = r["variant_image"]
                
                # For trending, include all event totals
                if metric == "trending":
                    product_data.update({
                        "total_views": int(r.get("total_views", 0) or 0),
                        "total_clicks": int(r.get("total_clicks", 0) or 0),
                        "total_wishlist": int(r.get("total_wishlist", 0) or 0),
                        "total_carts": int(r.get("total_carts", 0) or 0),
                        "total_purchases": int(r.get("total_purchases", 0) or 0),
                    })
                
                score_map[r["product_id"]] = product_data
            
            # 🔥 STRICT SALE RULE for Trending/Pick-up. 
            # But for Recommendation Grids, show the EXACT product whether it is on sale or not!
            bool_query = {
                "must": [{"terms": {"product_id": pids}}]
            }
            if metric != "recommendation-grids":
                bool_query["filter"] = [{"range": {"sale_price": {"gt": 0}}}]

            os_res = os_client.search(
                index=INDEX_NAME,
                body={
                    "size": len(pids), 
                    "query": {
                        "bool": bool_query
                    }
                }
            )
            
            # Set a custom reason tag for the UI
            for hit in os_res.get("hits", {}).get("hits", []):
                if metric == "recommendation-grids":
                    hit["_source"]["recommendation_reason"] = "Recently Viewed by You"
            
            prod_map = {h["_source"]["product_id"]: parse_os_product(h["_source"]) for h in os_res.get("hits", {}).get("hits", [])}
            
            for pid in pids:
                if pid in prod_map:
                    prod = prod_map[pid].copy()
                    prod.update(score_map[pid])
                    
                    # 🔥 STRICT OVERRIDE: Protect against "null", "undefined", and gallery mistakes!
                    var_img = score_map.get(pid, {}).get("variant_image")
                    
                    # Only override if it is a real string, longer than 10 characters, and doesn't contain "null"
                    if var_img and isinstance(var_img, str) and len(var_img) > 10:
                        if "null" not in var_img.lower() and "undefined" not in var_img.lower():
                            prod["image"] = var_img
                            prod["primary_image"] = var_img
                        
                    results.append(prod)
                    
            # Chop the final list to match the UI's requested size (12)
            results = results[:size]

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