import json
import hashlib
import time
import logging
import re
from app.config import os_client, INDEX_NAME, redis_client, openai_client
from app.models.search import SearchRequest

# ==========================================
# 🛠️ ENTERPRISE LOGGING SETUP
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

MAX_OS_WINDOW = 10000 

# =================================================================
# 🧠 AI SMART BRAND EXTRACTOR
# =================================================================
def get_smart_brand(source):
    raw_brand = source.get("brand", "")
    if raw_brand and str(raw_brand).strip().lower() not in ["none", "", "null", "other brands", "unknown"]:
        return str(raw_brand).strip().upper()
        
    attrs = source.get("attributes", {})
    if isinstance(attrs, dict):
        supplier = attrs.get("supplier", "")
        if supplier and str(supplier).strip().lower() not in ["none", "", "null", "unknown"]:
            return str(supplier).strip().upper()

    title = str(source.get("name", "")).strip()
    title_lower = title.lower()
    
    brand_mappings = {
        "iphone": "APPLE", "ipad": "APPLE", "macbook": "APPLE", "airpods": "APPLE", "imac": "APPLE",
        "galaxy": "SAMSUNG", "s20": "SAMSUNG", "s21": "SAMSUNG", "s22": "SAMSUNG", "s23": "SAMSUNG", "s24": "SAMSUNG",
        "thinkpad": "LENOVO", "yoga": "LENOVO", "ideapad": "LENOVO",
        "predator": "ACER", "aspire": "ACER",
        "pavilion": "HP", "envy": "HP", "omen": "HP", "spectre": "HP",
        "rog": "ASUS", "zenbook": "ASUS", "vivobook": "ASUS",
        "playstation": "SONY", "bravia": "SONY",
        "xbox": "MICROSOFT", "surface": "MICROSOFT",
        "pixel": "GOOGLE", "kindle": "AMAZON", "echo": "AMAZON"
    }
    for keyword, mapped_brand in brand_mappings.items():
        if re.search(rf'\b{keyword}\b', title_lower):
            return mapped_brand
            
    known_brands = [
        "nike", "adidas", "puma", "reebok", "sony", "dell", "asus", "acer", "lenovo", "hp", "microsoft", "apple", "samsung", "viking", "u-line"
    ]
    for b in known_brands:
        if re.search(rf'\b{b}\b', title_lower):
            return b.upper()
            
    words = title.split()
    if words:
        first_word = words[0].strip('",\'()[]{}!@#$%-').upper()
        if len(first_word) > 2 and not first_word.isnumeric() and first_word not in ["THE", "FOR", "AND", "WITH"]:
            return first_word
            
    return "UNKNOWN"

def build_pagination_html(total_pages: int, current_page: int) -> str:
    if total_pages <= 1: return ""
    start = max(1, current_page - 2)
    end = min(total_pages, start + 4)
    if end - start < 4: start = max(1, end - 4)
    
    html = ""
    if start > 1: html += '<button class="page-btn" data-page="1">1</button><span style="align-self:center;">...</span>'
    for i in range(start, end + 1):
        active_class = "active" if i == current_page else ""
        html += f'<button class="page-btn {active_class}" data-page="{i}">{i}</button>'
    if end < total_pages: html += f'<span style="align-self:center;">...</span><button class="page-btn" data-page="{total_pages}">{total_pages}</button>'
    return html

# =================================================================
# 🚀 CORE SEARCH: LLM VECTOR + KNN + EXACT FILTERS (HYBRID)
# =================================================================
async def execute_search(request: SearchRequest):
    request.page_size = 25
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:ai:{hashlib.md5(request_str.encode()).hexdigest()}"

    try:
        start_time = time.time()
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            latency = (time.time() - start_time) * 1000
            logger.info(f"🚀 CACHE HIT: [{latency:.2f}ms] Key: {cache_key}")
            return json.loads(cached_result)
    except Exception as e:
        logger.warning(f"⚠️ Redis read error: {e}")

    from_val = (request.page - 1) * request.page_size
    if from_val + request.page_size > MAX_OS_WINDOW: from_val = MAX_OS_WINDOW - request.page_size 

    query_text = request.query.strip() if request.query else ""
    vector = None

    # 🕵️ SMART INTENT EXTRACTION
    smart_max_price = None
    price_match = re.search(r'(?:under|less than)\s*\$?\s*(\d+)', query_text.lower())
    if price_match:
        smart_max_price = float(price_match.group(1))

    # 1️⃣ AI STEP: Convert Text to 1536-Dimension Vector Embeddings
    if query_text:
        try:
            ai_start = time.time()
            resp = await openai_client.embeddings.create(
                input=query_text,
                model="text-embedding-3-small"
            )
            vector = resp.data[0].embedding
            logger.info(f"🧠 OPENAI VECTORIZED: [{(time.time() - ai_start) * 1000:.2f}ms]")
        except Exception as e:
            logger.error(f"❌ OpenAI Embedding Failed: {e}")

    # 2️⃣ EXACT MATH FILTERS
    filters = [{"term": {"in_stock": True}}]
    
    if smart_max_price:
        filters.append({"range": {"price": {"lte": smart_max_price}}})

    if request.filters:
        if request.filters.brand: filters.append({"terms": {"brand": request.filters.brand}})
        if request.filters.category: filters.append({"terms": {"category": request.filters.category}})
        if request.filters.in_stock is not None: filters.append({"term": {"in_stock": request.filters.in_stock}})
        if request.filters.price:
            price_range = {}
            if request.filters.price.min is not None: price_range["gte"] = request.filters.price.min
            if request.filters.price.max is not None: price_range["lte"] = request.filters.price.max
            if price_range: filters.append({"range": {"price": price_range}})

    if request.sort == "on_sale":
        filters.append({"range": {"sale_price": {"gt": 0}}})
        sort_query = [{"_score": "desc"}] 
    else:
        sort_query = [{"price": "asc"}] if request.sort == "price_asc" else [{"price": "desc"}] if request.sort == "price_desc" else [{"_score": "desc"}]

    # 3️⃣ HYBRID QUERY ASSEMBLY (✅ NMSLIB CRASH FIX)
    if vector:
        # Increase K because NMSLIB filters AFTER finding the nearest neighbors
        k_val = max(200, from_val + request.page_size + 100)
        query_body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": vector,
                                    "k": k_val
                                }
                            }
                        }
                    ],
                    "filter": filters
                }
            }
        }
    else:
        query_body = {
            "query": {
                "bool": {
                    "must": [{"match_all": {}}],
                    "filter": filters
                }
            }
        }

    os_query = {
        "from": from_val, "size": request.page_size,
        **query_body,
        "sort": sort_query, "track_total_hits": True,
        "aggs": {"brands": {"terms": {"field": "brand", "size": 25}}, "categories": {"terms": {"field": "category", "size": 25}}}
    }

    try:
        os_start = time.time()
        response = os_client.search(index=INDEX_NAME, body=os_query)
        logger.info(f"🔍 DB VECTOR SEARCH: [{(time.time() - os_start) * 1000:.2f}ms]")
    except Exception as e:
        logger.error(f"❌ OpenSearch Error: {str(e)}")
        return {"error": "Search service unavailable", "results": [], "total_results": 0}
    
    hits = response.get("hits", {})
    total_hits = hits.get("total", {}).get("value", 0)
    total_pages = (total_hits + request.page_size - 1) // request.page_size if total_hits > 0 else 0

    results = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        brand_display = get_smart_brand(source)
        
        raw_cats = source.get("category", [])
        clean_cats = []
        if isinstance(raw_cats, str):
            cleaned_str = re.sub(r"[\[\]'\"]", "", raw_cats)
            clean_cats = [c.strip() for c in cleaned_str.split(",") if c.strip()]
        elif isinstance(raw_cats, list):
            clean_cats = [str(c).strip() for c in raw_cats if c and str(c).strip()]
            
        if not clean_cats or clean_cats == ["None"]:
            clean_cats = ["Uncategorized"]

        images = source.get("images", [])
        primary_image = images[0] if isinstance(images, list) and len(images) > 0 else None

        _pid = str(source.get("product_id", "123"))
        _demo_rating = 4.0 + (int(hashlib.md5(_pid.encode()).hexdigest(), 16) % 10) / 10.0
        _demo_sales = (int(hashlib.md5(_pid.encode()).hexdigest(), 16) % 800) + 150

        results.append({
            "id": source.get("product_id"), "name": source.get("name", "Unknown Product"),
            "description": source.get("description", ""), "brand": brand_display, 
            "category": clean_cats, "price": source.get("price", 0.0),
            "sale_price": source.get("sale_price"), "in_stock": source.get("in_stock", False),
            "sku": source.get("sku", ""), "url": source.get("url", ""),
            "primary_image": primary_image, "rating": source.get("rating") if source.get("rating", 0) > 0 else _demo_rating,
            "sales_count": source.get("sales_count") if source.get("sales_count", 0) > 0 else _demo_sales,
            "score": round(hit.get("_score", 0) or 0, 2)
        })

    aggregations = response.get("aggregations", {})
    brands_agg = aggregations.get("brands", {}).get("buckets", [])
    categories_agg = aggregations.get("categories", {}).get("buckets", [])

    facets = {
        "brands": [{"label": str(b.get("key", "")).strip() if b.get("key") and str(b.get("key")).strip() else "Other Brands", "value": b.get("key"), "count": b.get("doc_count", 0)} for b in brands_agg],
        "categories": [{"value": str(c.get("key")).strip(), "label": str(c.get("key")).strip(), "count": c.get("doc_count", 0)} for c in categories_agg if c.get("key")]
    }

    final_response = {"total_results": total_hits, "total_pages": total_pages, "current_page": request.page, "pagination_html": build_pagination_html(total_pages, request.page), "results": results, "facets": facets}

    try: await redis_client.set(cache_key, json.dumps(final_response), ex=300)
    except Exception as e: logger.warning(f"⚠️ Redis write error: {e}")

    return final_response

async def execute_autocomplete(query_string: str):
    clean_query = query_string.strip()
    if not clean_query: return {"suggestions": []}
    cache_key = f"auto:{hashlib.md5(clean_query.encode()).hexdigest()}"
    
    try:
        cached_result = await redis_client.get(cache_key)
        if cached_result: return json.loads(cached_result)
    except Exception: pass

    os_query = {"size": 10, "_source": ["name", "images"], "query": {"match_phrase_prefix": {"name": {"query": clean_query, "max_expansions": 50}}}}
    try: response = os_client.search(index=INDEX_NAME, body=os_query)
    except Exception: return {"suggestions": []}

    seen_names = set()
    suggestions = []
    for hit in response.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        name = source.get("name", "")
        normalized_name = str(name).strip().lower()
        if normalized_name and normalized_name not in seen_names:
            seen_names.add(normalized_name)
            images = source.get("images", [])
            thumbnail = images[0] if isinstance(images, list) and len(images) > 0 else None
            suggestions.append({"text": name, "thumbnail": thumbnail})

    final_response = {"suggestions": suggestions}
    try: await redis_client.set(cache_key, json.dumps(final_response), ex=3600)
    except Exception: pass
    return final_response

# =================================================================
# 🧠 JSON AI-SEARCH (Groups products by Category for the Mega Menu)
# =================================================================
async def execute_ai_search(query_string: str):
    """ ✅ This is the exact endpoint your Sir requested """
    clean_query = query_string.strip().lower()
    
    vector = None
    if clean_query:
        try:
            resp = await openai_client.embeddings.create(input=clean_query, model="text-embedding-3-small")
            vector = resp.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI error in ai_search: {e}")

    if vector:
        # ✅ NMSLIB CRASH FIX applied here as well
        os_query = {
            "size": 12, 
            "query": {
                "bool": {
                    "must": [
                        {"knn": {"embedding": {"vector": vector, "k": 50}}}
                    ],
                    "filter": [{"term": {"in_stock": True}}]
                }
            }
        }
    else:
        os_query = {
            "size": 12,
            "query": {
                "bool": {
                    "must": [{"match_all": {}}],
                    "filter": [{"term": {"in_stock": True}}]
                }
            },
            "sort": [{"_score": {"order": "desc"}}]
        }

    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
        hits = response.get("hits", {}).get("hits", [])
    except Exception as e:
        logger.error(f"❌ OpenSearch AI Search Error: {e}")
        return {"categories": []}

    category_map = {}
    cat_id_counter = 1
    
    for hit in hits:
        source = hit.get("_source", {})
        
        raw_cats = source.get("category", [])
        clean_cats = []
        if isinstance(raw_cats, str):
            cleaned_str = re.sub(r"[\[\]'\"]", "", raw_cats)
            clean_cats = [c.strip() for c in cleaned_str.split(",") if c.strip()]
        elif isinstance(raw_cats, list):
            clean_cats = [str(c).strip() for c in raw_cats if c and str(c).strip()]
            
        primary_cat = clean_cats[0] if clean_cats and clean_cats[0] != "None" else "Top Suggestions"

        if primary_cat not in category_map:
            category_map[primary_cat] = {
                "id": cat_id_counter,
                "name": primary_cat,
                "products": []
            }
            cat_id_counter += 1
            
        images = source.get("images", [])
        img_url = images[0] if isinstance(images, list) and images else "https://placehold.co/150x150?text=No+Image"
        
        category_map[primary_cat]["products"].append({
            "name": source.get("name", "Unknown Product"),
            "price": float(source.get("price", 0.0)),
            "primary_image": img_url,
            "url": source.get("url", "#")
        })

    return {
        "categories": list(category_map.values())
    }