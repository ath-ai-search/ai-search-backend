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
    
    # 🔥 SALE_PRICE CLEANUP: Only keep sale_price if it's a REAL discount (≥ 1% off)
    try:
        price = float(src.get("price", 0) or 0)
    except (TypeError, ValueError):
        price = 0.0
    try:
        sale_price = float(src.get("sale_price", 0) or 0)
    except (TypeError, ValueError):
        sale_price = 0.0
    
    # Calculate actual discount %
    real_sale_price = 0
    if sale_price > 0 and price > 0 and sale_price < price:
        discount_pct = ((price - sale_price) / price) * 100
        # Only treat as a sale if discount is at least 1% (avoids "0% off" badges)
        if discount_pct >= 1.0:
            real_sale_price = sale_price
    
    return {
        "product_id": src.get("product_id"),
        "name": src.get("name", ""),
        "price": price,
        "sale_price": real_sale_price,
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
                # 🔥 SAFELY lowered random range to guarantee we find items!
                random_offset = random.randint(0, 10)

                # Tell OpenSearch NOT to fetch items already in their cart
                must_not = [{"terms": {"product_id": user_pids}}] if user_pids else []
                os_pad_res = os_client.search(
                    index=INDEX_NAME,
                    body={
                        "size": padding_needed,
                        "from": random_offset,          
                        "sort": [{"price": "desc"}], # 🔥 Sorts highest price first (Luxury)
                        "query": {
                            "bool": {
                                "must": [{"match_all": {}}],
                                "must_not": must_not,
                                "filter": [
                                    {"range": {"sale_price": {"gt": 0}}},
                                    {"range": {"price": {"gte": 100}}}, # 🔥 STRICT LUXURY FILTER: $100+
                                    {"query_string": {
                                        "default_field": "category",
                                        "query": "Fashion OR Kitchen OR Clothing"
                                    }}
                                ]
                            }
                        }
                    }
                )
                for hit in os_pad_res.get("hits", {}).get("hits", []):
                    prod = parse_os_product(hit.get("_source", {}))
                    prod["recommendation_reason"] = "Luxury Deals Just For You"
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
                        
                        # 🔥 USE THE EXACT IMAGE USER CLICKED (variant_image from tracking)
                        # Same logic as pick-up API — show what they actually saw
                        var_img = variant_map.get(pid)
                        if var_img and isinstance(var_img, str) and len(var_img) > 10:
                            if "null" not in var_img.lower() and "undefined" not in var_img.lower():
                                prod["image"] = var_img
                                prod["primary_image"] = var_img
                        
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
                # 🔥 Start at 15 so it NEVER overlaps with Pick-Up!
                random_offset = random.randint(15, 25) 
                
                os_pad_res = os_client.search(
                    index=INDEX_NAME,
                    body={
                        "size": padding_needed,
                        "from": random_offset,          
                        "sort": [{"price": "desc"}], # 🔥 Sorts highest price first (Luxury)
                        "query": {
                            "bool": {
                                "must": [{"match_all": {}}],
                                "must_not": must_not,
                                "filter": [
                                    {"range": {"sale_price": {"gt": 0}}},
                                    {"range": {"price": {"gte": 100}}}, # 🔥 STRICT LUXURY FILTER: $100+
                                    {"query_string": {
                                        "default_field": "category",
                                        "query": "Fashion OR Kitchen OR Clothing"
                                    }}
                                ]
                            }
                        }
                    }
                )
                for hit in os_pad_res.get("hits", {}).get("hits", []):
                    prod = parse_os_product(hit.get("_source", {}))
                    prod["recommendation_reason"] = "Luxury Deals Just For You"
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
        # 🛍️ API 5: CONTINUE SHOPPING (Merged Pick-Up + Recommendation Grids)
        # Shows ALL products user touched: saved (cart/wishlist) AND viewed/clicked
        # Ordered by last interaction time. No duplicates.
        # =====================================================================
        elif metric == "continueshop":
            if not identity: return {"error": "visitor_id required"}
            
            # Count anything user has touched (view, click, cart, wishlist)
            cur.execute("""
                SELECT COUNT(*) as t 
                FROM product_metrics 
                WHERE visitor_id = %s AND (views + clicks + carts + wishlist) > 0
            """, (identity,))
            total = cur.fetchone()["t"]
            
            # Fetch every interacted product, newest first
            cur.execute("""
                SELECT product_id, variant_image, carts, wishlist
                FROM product_metrics 
                WHERE visitor_id = %s AND (views + clicks + carts + wishlist) > 0
                ORDER BY last_seen DESC LIMIT %s OFFSET %s
            """, (identity, size, offset))
            user_history = cur.fetchall()
            
            user_pids = [r["product_id"] for r in user_history]
            variant_map = {r["product_id"]: r["variant_image"] for r in user_history if "variant_image" in r and r["variant_image"]}
            saved_map = {r["product_id"]: ((r.get("carts") or 0) + (r.get("wishlist") or 0)) > 0 for r in user_history}
            user_results = []
            
            # Fetch product details from OpenSearch
            if user_pids:
                os_res = os_client.search(
                    index=INDEX_NAME,
                    body={"size": len(user_pids), "query": {"terms": {"product_id": user_pids}}}
                )
                prod_map = {h["_source"]["product_id"]: parse_os_product(h["_source"]) for h in os_res.get("hits", {}).get("hits", [])}
                
                # Preserve user_pids order (newest-touched first)
                for pid in user_pids:
                    if pid in prod_map:
                        prod = prod_map[pid].copy()
                        
                        # 🔥 USE THE EXACT IMAGE USER CLICKED (variant_image override)
                        var_img = variant_map.get(pid)
                        if var_img and isinstance(var_img, str) and len(var_img) > 10:
                            if "null" not in var_img.lower() and "undefined" not in var_img.lower():
                                prod["image"] = var_img
                                prod["primary_image"] = var_img
                        
                        # Tag with reason — UI can use this to show "Saved" vs "Recently Viewed" labels
                        if saved_map.get(pid):
                            prod["recommendation_reason"] = "Saved in Cart/Wishlist"
                        else:
                            prod["recommendation_reason"] = "Recently Viewed by You"
                        
                        user_results.append(prod)
            
            # Pad with luxury sale items if user history < requested size
            padding_needed = size - len(user_results)
            dynamic_results = []
            
            if padding_needed > 0:
                must_not = [{"terms": {"product_id": user_pids}}] if user_pids else []
                random_offset = random.randint(0, 25)
                
                os_pad_res = os_client.search(
                    index=INDEX_NAME,
                    body={
                        "size": padding_needed,
                        "from": random_offset,          
                        "sort": [{"price": "desc"}],
                        "query": {
                            "bool": {
                                "must": [{"match_all": {}}],
                                "must_not": must_not,
                                "filter": [
                                    {"range": {"sale_price": {"gt": 0}}},
                                    {"range": {"price": {"gte": 100}}},
                                    {"query_string": {
                                        "default_field": "category",
                                        "query": "Fashion OR Kitchen OR Clothing"
                                    }}
                                ]
                            }
                        }
                    }
                )
                for hit in os_pad_res.get("hits", {}).get("hits", []):
                    prod = parse_os_product(hit.get("_source", {}))
                    prod["recommendation_reason"] = "Luxury Deals Just For You"
                    dynamic_results.append(prod)
            
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
        # 🏆 API 6: POPULAR CATEGORIES (Global)
        # Aggregates trending_score per category. Returns:
        #   - SEO-friendly Absolute URLs (https://venuemarketplace.com/parent/child/)
        #   - UNIQUE image per category (no duplicates)
        # =====================================================================
        elif metric == "popularcat":
            import re as _re
            
            def _slugify(text):
                s = (text or "").lower()
                s = _re.sub(r"[&]", "", s)
                s = _re.sub(r"[^a-z0-9\s-]", "", s)
                s = _re.sub(r"\s+", "-", s.strip())
                s = _re.sub(r"-+", "-", s)
                return s.strip("-")
            
            def _extract_image(src):
                raw_img_data = src.get("images") or ""
                img = ""
                if isinstance(raw_img_data, list) and len(raw_img_data) > 0:
                    img = str(raw_img_data[0])
                elif isinstance(raw_img_data, str) and raw_img_data:
                    cleaned = raw_img_data.strip("[]'\" ")
                    img = cleaned.split(",")[0].strip("[]'\" ")
                if img and len(img) > 10 and "null" not in img.lower() and "undefined" not in img.lower():
                    return img
                return ""
            
            os_res = os_client.search(
                index=INDEX_NAME,
                body={
                    "size": 2000,
                    "_source": ["category", "trending_score", "images", "name", "product_id", "url", "in_stock"],
                    "query": {
                        "bool": {
                            "must": [{"range": {"trending_score": {"gt": 1}}}]
                        }
                    },
                    "sort": [{"trending_score": "desc"}]
                }
            )
            
            hits = os_res.get("hits", {}).get("hits", [])
            
            FORCE_EXCLUDE = {
                "Amazon", "Best Buy", "Walmart", "Target",
                "Best Sellers", "All Products", "New Releases",
                "Today's Deal", "Outlet Store", "Sale", "Featured"
            }
            
            category_scores = {}
            category_counts = {}
            category_candidates = {}
            
            for hit in hits:
                src = hit.get("_source", {})
                if src.get("in_stock") is False:
                    continue
                
                score = float(src.get("trending_score", 0) or 0)
                cats = src.get("category", [])
                
                if isinstance(cats, str):
                    cats = [cats]
                if not isinstance(cats, list) or len(cats) == 0:
                    continue
                
                product_image = _extract_image(src)
                
                for cat in cats:
                    if not cat:
                        continue
                    cat = str(cat).strip()
                    if not cat or cat in FORCE_EXCLUDE:
                        continue
                    
                    category_scores[cat] = category_scores.get(cat, 0) + score
                    category_counts[cat] = category_counts.get(cat, 0) + 1
                    
                    if cat not in category_candidates:
                        category_candidates[cat] = []
                    category_candidates[cat].append((score, product_image, cats))
            
            sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
            paginated = sorted_cats[offset:offset + size]
            
            used_images = set()
            results = []
            
            for cat_name, score in paginated:
                candidates = category_candidates.get(cat_name, [])
                
                chosen_image = ""
                chosen_cats = []
                for cscore, cimg, ccats in candidates:
                    if cimg and cimg not in used_images:
                        chosen_image = cimg
                        chosen_cats = ccats
                        used_images.add(cimg)
                        break
                
                if not chosen_image:
                    for cscore, cimg, ccats in candidates:
                        if cimg:
                            chosen_image = cimg
                            chosen_cats = ccats
                            break
                
                # 🔥 HIERARCHICAL URL BUILDER
                path = f"/{_slugify(cat_name)}/"
                if chosen_cats:
                    try:
                        idx = chosen_cats.index(cat_name)
                        if idx > 0:
                            parent = chosen_cats[idx - 1]
                            path = f"/{_slugify(parent)}/{_slugify(cat_name)}/"
                    except ValueError:
                        pass
                
                # 🔥 FULL ABSOLUTE URL
                base_domain = "https://venuemarketplace.com"
                absolute_url = f"{base_domain}{path}"
                
                results.append({
                    "category": cat_name,
                    "name": cat_name,
                    "image": chosen_image,
                    "primary_image": chosen_image,
                    "score": round(score, 2),
                    "product_count": category_counts[cat_name],
                    "url": absolute_url,
                    "recommendation_reason": "Popular Category"
                })
            
            response = {
                "results": results,
                "total": len(sorted_cats),
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
        # 🔥 API 3: TRENDING (Reads directly from OpenSearch trending_score)
        # Uses pre-computed values in OpenSearch (kept fresh by sync_trending cron)
        # =====================================================================
        elif metric == "trending":
            # Query OpenSearch directly, sorted by trending_score field
            # 🔥 SALE-ONLY: Only show products that are ON SALE (sale_price > 0)
            os_res = os_client.search(
                index=INDEX_NAME,
                body={
                    "from": offset,
                    "size": size,
                    "query": {
                        "bool": {
                            "must": [{"range": {"trending_score": {"gt": 1}}}],
                            "filter": [
                                {"term": {"in_stock": True}},
                                {"range": {"sale_price": {"gt": 0}}}
                            ]
                        }
                    },
                    "sort": [{"trending_score": "desc"}]
                }
            )

            for hit in os_res.get("hits", {}).get("hits", []):
                src = hit.get("_source", {})
                prod = parse_os_product(src)
                prod["score"] = float(src.get("trending_score", 0))
                prod["total_views"] = int(src.get("stats_views", 0) or 0)
                prod["total_clicks"] = int(src.get("stats_clicks", 0) or 0)
                prod["total_carts"] = int(src.get("stats_carts", 0) or 0)
                prod["total_wishlist"] = int(src.get("stats_wishlist", 0) or 0)
                prod["total_purchases"] = int(src.get("stats_purchases", 0) or 0)
                prod["recommendation_reason"] = "Trending Now"
                results.append(prod)

            total = os_res.get("hits", {}).get("total", {}).get("value", len(results))
            db_rows = []  # 🔥 skip the Postgres-fetch block below

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
            # if metric != "recommendation-grids":
            #     bool_query["filter"] = [{"range": {"sale_price": {"gt": 0}}}]

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