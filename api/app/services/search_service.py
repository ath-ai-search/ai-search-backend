import json
import hashlib
import time
import logging
from app.config import os_client, INDEX_NAME, redis_client
from app.models.search import SearchRequest

# ==========================================
# 🛠️ ENTERPRISE LOGGING SETUP
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ==========================================
# 🔄 GLOBAL CATEGORY MAPPING
# ==========================================
CATEGORY_MAP = {
    "2152": "Laptops",
    "1607": "Mobiles",
    "116": "Electronics",
    "1330": "Home & Garden",
    "1087": "Fashion",
    "47": "Appliances",
    "2487": "Accessories",
    "453": "Software"
}

MAX_OS_WINDOW = 10000 

# =================================================================
# 🧠 AI SMART BRAND EXTRACTOR (Solves empty database fields)
# =================================================================
def get_smart_brand(source):
    # 1. Check if the database actually has the brand
    raw_brand = source.get("brand", "")
    if raw_brand and str(raw_brand).strip().lower() not in ["none", "", "null", "other brands", "unknown"]:
        return str(raw_brand).strip().upper()
        
    title = str(source.get("name", "")).strip()
    title_lower = title.lower()
    
    # 2. Product Line to Parent Brand Mappings
    brand_mappings = {
        "iphone": "APPLE", "ipad": "APPLE", "macbook": "APPLE", "airpods": "APPLE", "imac": "APPLE",
        "galaxy": "SAMSUNG", "s20": "SAMSUNG", "s21": "SAMSUNG", "s22": "SAMSUNG", "s23": "SAMSUNG", "s24": "SAMSUNG", "note": "SAMSUNG",
        "thinkpad": "LENOVO", "yoga": "LENOVO", "ideapad": "LENOVO",
        "predator": "ACER", "aspire": "ACER",
        "pavilion": "HP", "envy": "HP", "omen": "HP", "spectre": "HP",
        "rog": "ASUS", "zenbook": "ASUS", "vivobook": "ASUS",
        "playstation": "SONY", "bravia": "SONY",
        "xbox": "MICROSOFT", "surface": "MICROSOFT",
        "pixel": "GOOGLE", "kindle": "AMAZON", "echo": "AMAZON"
    }
    for keyword, mapped_brand in brand_mappings.items():
        if keyword in title_lower:
            return mapped_brand
            
    # 3. Known Brands Check
    known_brands = [
        "nike", "adidas", "puma", "reebok", "under armour", "new balance", "vans",
        "sony", "lg", "panasonic", "dell", "asus", "acer", "lenovo", "hp", "microsoft", "apple", "samsung",
        "omnica", "envysun", "hogan", "guess", "gabs", "michael kors", "springa"
    ]
    for b in known_brands:
        if b in title_lower:
            return b.upper()
            
    # 4. Fallback: Extract the first word of the title as the brand
    words = title.split()
    if words:
        first_word = words[0].strip('",\'()[]{}!@#$%-').upper()
        if len(first_word) > 1 and not first_word.isnumeric():
            return first_word
            
    return "UNKNOWN BRAND"

# ==========================================
# 📄 SERVER-SIDE HTML GENERATION
# ==========================================
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

async def execute_search(request: SearchRequest):
    request.page_size = 25
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:{hashlib.md5(request_str.encode()).hexdigest()}"

    try:
        start_time = time.time()
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            latency = (time.time() - start_time) * 1000
            logger.info(f"🚀 CACHE HIT: [{latency:.2f}ms] Key: {cache_key}")
            return json.loads(cached_result)
    except Exception as e:
        logger.warning(f"⚠️ Redis read error (bypassing cache): {e}")

    from_val = (request.page - 1) * request.page_size
    if from_val + request.page_size > MAX_OS_WINDOW: from_val = MAX_OS_WINDOW - request.page_size 

    bool_query = {"must": [], "should": [], "filter": [], "minimum_should_match": 0}
    query_text = request.query.strip() if request.query else ""
    
    if query_text:
        bool_query["minimum_should_match"] = 1
        bool_query["should"].append({
            "multi_match": {
                "query": query_text,
                "fields": ["name^10", "description"], 
                "fuzziness": "AUTO",           
                "minimum_should_match": "70%",
                "analyzer": "standard",
                "boost": 1.0 
            }
        })
        bool_query["should"].append({"match_phrase": {"name": {"query": query_text, "boost": 50.0}}})
    else:
        bool_query["must"].append({"match_all": {}})

    bool_query["should"].append({"term": {"in_stock": {"value": True, "boost": 2.0}}})

    if request.filters:
        if request.filters.brand: bool_query["filter"].append({"terms": {"brand": request.filters.brand}})
        if request.filters.category: bool_query["filter"].append({"terms": {"category": request.filters.category}})
        if request.filters.in_stock is not None: bool_query["filter"].append({"term": {"in_stock": request.filters.in_stock}})
        if request.filters.price:
            price_range = {}
            if request.filters.price.min is not None: price_range["gte"] = request.filters.price.min
            if request.filters.price.max is not None: price_range["lte"] = request.filters.price.max
            if price_range: bool_query["filter"].append({"range": {"price": price_range}})

    sort_query = [{"price": "asc"}] if request.sort == "price_asc" else [{"price": "desc"}] if request.sort == "price_desc" else ["_score"]

    os_query = {
        "from": from_val, "size": request.page_size,
        "query": {
            "function_score": {
                "query": {"bool": bool_query},
                "functions": [
                    {"field_value_factor": {"field": "rating", "factor": 1.5, "missing": 1.0}},
                    {"field_value_factor": {"field": "sales_count", "modifier": "log1p", "factor": 0.5, "missing": 0}}
                ],
                "boost_mode": "multiply", "score_mode": "sum"
            }
        },
        "sort": sort_query, "track_total_hits": True,
        "aggs": {"brands": {"terms": {"field": "brand", "size": 25}}, "categories": {"terms": {"field": "category", "size": 25}}}
    }

    try:
        os_start = time.time()
        response = os_client.search(index=INDEX_NAME, body=os_query)
        logger.info(f"🔍 DB SEARCH: [{(time.time() - os_start) * 1000:.2f}ms]")
    except Exception as e:
        logger.error(f"❌ OpenSearch Error: {str(e)}")
        return {"error": "Search service unavailable", "results": [], "total_results": 0}
    
    hits = response.get("hits", {})
    total_hits = hits.get("total", {}).get("value", 0)
    total_pages = (total_hits + request.page_size - 1) // request.page_size if total_hits > 0 else 0

    results = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        
        # ✅ Using the Smart Extractor!
        brand_display = get_smart_brand(source)
        
        raw_cats = source.get("category", [])
        if not isinstance(raw_cats, list): raw_cats = [raw_cats]
        clean_cats = [CATEGORY_MAP.get(str(c), f"Category {c}") for c in raw_cats if c]

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
        "categories": [{"value": c.get("key"), "label": CATEGORY_MAP.get(str(c.get("key")), f"Category {c.get('key')}"), "count": c.get("doc_count", 0)} for c in categories_agg]
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
# 🎨 MEGA MENU HTML GENERATOR
# =================================================================
async def get_mega_menu_widget(query_string: str, recent_searches: str = ""):
    clean_query = query_string.strip().lower()
    
    if not clean_query:
        os_query = {
            "size": 4, "query": {"match_all": {}}, "sort": [{"_score": {"order": "desc"}}],
            "aggs": {"top_categories": {"terms": {"field": "category", "size": 3}}}
        }
    else:
        os_query = {
            "size": 4,
            "query": {
                "bool": {
                    "should": [
                        {"multi_match": {"query": clean_query, "fields": ["name^10", "description^2"], "fuzziness": "AUTO", "minimum_should_match": "60%"}},
                        {"match_phrase_prefix": {"name": {"query": clean_query, "boost": 10.0}}}
                    ],
                    "minimum_should_match": 1
                }
            },
            "sort": [{"_score": {"order": "desc"}}],
            "aggs": {"top_categories": {"terms": {"field": "category", "size": 3}}}
        }

    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
        hits = response.get("hits", {}).get("hits", [])
        total_products = response.get("hits", {}).get("total", {}).get("value", 0)

        cats_agg = response.get("aggregations", {}).get("top_categories", {}).get("buckets", [])
        dynamic_cats = []
        for c in cats_agg:
            cat_val = str(c.get("key"))
            cat_name = CATEGORY_MAP.get(cat_val, cat_val).title()
            if cat_name and cat_name.lower() != "none": dynamic_cats.append(cat_name)

    except Exception as e:
        logger.error(f"❌ OpenSearch Mega Menu Error: {e}")
        hits = []
        total_products = 0
        dynamic_cats = []

    products_html = ""
    dynamic_brands_set = set() # We build this directly from the smart extractor!
    
    if not hits:
        products_html = "<div style='padding: 20px; color: #666;'>No products found.</div>"
    else:
        for hit in hits:
            source = hit.get("_source", {})
            name = source.get("name", "Unknown Product")
            
            # ✅ Using the Smart Extractor to build the Sidebar and the Cards!
            brand_display = get_smart_brand(source)
            if brand_display != "UNKNOWN BRAND":
                dynamic_brands_set.add(brand_display)
            
            price = float(source.get("price", 0.0))
            images = source.get("images", [])
            img_url = images[0] if isinstance(images, list) and images else "https://placehold.co/100x100?text=No+Image"

            products_html += f"""
            <div class="ath-prod-row" onclick="window.location.href='/search.php?search_query={name}'">
                <div class="ath-prod-img"><img src="{img_url}" alt="{name}"></div>
                <div class="ath-prod-info">
                    <div class="ath-prod-brand">{brand_display}</div>
                    <div class="ath-prod-title" title="{name}">{name}</div>
                    <div class="ath-prod-price">${price:.2f}</div>
                </div>
            </div>
            """

    sidebar_html = ""
    
    if recent_searches:
        recent_list = recent_searches.split("||")[:3]
        if recent_list and recent_list[0]:
            sidebar_html += "<div class='ath-side-title'>RECENT SEARCHES</div>"
            for r in recent_list:
                sidebar_html += f"""
                <div class='ath-side-item' onclick='document.getElementById("search_query").value="{r}"; document.getElementById("search_query").dispatchEvent(new Event("input"));'>
                    <div style="display:flex; align-items:center; gap:12px;"><i class='far fa-clock'></i> <span>{r}</span></div>
                    <div style="display:flex; gap:8px; color:#999;"><i class="fas fa-times" style="font-size:10px;"></i><i class="fas fa-arrow-up" style="transform: rotate(45deg); font-size:10px;"></i></div>
                </div>"""

    dynamic_brands = list(dynamic_brands_set)
    if dynamic_brands:
        sidebar_html += "<div class='ath-side-title' style='margin-top:24px;'>BRAND</div>"
        for b in dynamic_brands[:4]:
            sidebar_html += f"<div class='ath-side-item'><div style='display:flex; align-items:center; gap:12px;'><i class='fas fa-filter'></i> <span>{b}</span></div></div>"

    if dynamic_cats:
        sidebar_html += "<div class='ath-side-title' style='margin-top:24px;'>POPULAR SEARCHES</div>"
        for c in dynamic_cats[:3]:
            sidebar_html += f"""
            <div class='ath-side-item' onclick='window.location.href="/search.php?search_query={c}"'>
                <div style='display:flex; align-items:center; gap:12px;'><i class='fas fa-search'></i> <span>{c}</span></div>
                <i class="fas fa-arrow-up" style="transform: rotate(45deg); font-size:10px; color:#999;"></i>
            </div>
            """

    master_html = f"""
    <style>
        .ath-mega-menu {{ display: flex; width: 100%; max-width: 900px; height: 500px; background: white; border-radius: 8px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); font-family: 'Inter', sans-serif; text-align: left; overflow: hidden; border: 1px solid #e5e7eb; }}
        .ath-left-col {{ width: 320px; background: #fdfdfd; padding: 24px; border-right: 1px solid #f0f0f0; overflow-y: auto; }}
        .ath-side-title {{ font-size: 12px; font-weight: 700; color: #111; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .ath-side-item {{ font-size: 14px; color: #111; padding: 10px 0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background 0.2s; }}
        .ath-side-item i {{ color: #111; font-size: 14px; }}
        .ath-side-item:hover {{ background: #f5f5f5; border-radius: 4px; }}
        .ath-right-col {{ flex: 1; padding: 24px 32px; background: white; overflow-y: auto; }}
        .ath-guide-title {{ font-size: 14px; font-weight: 700; color: #111; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .ath-guide-card {{ display: flex; align-items: center; gap: 20px; background: #f9fafb; padding: 16px; border-radius: 12px; margin-bottom: 32px; cursor: pointer; transition: 0.2s; }}
        .ath-guide-card:hover {{ background: #f3f4f6; }}
        .ath-guide-img {{ width: 80px; height: 80px; background: white; border-radius: 8px; display: flex; align-items: center; justify-content: center; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        .ath-guide-img img {{ width: 100%; height: 100%; object-fit: contain; }}
        .ath-guide-text h4 {{ font-size: 14px; font-weight: 600; color: #111; margin-bottom: 6px; }}
        .ath-guide-text p {{ font-size: 12px; color: #666; line-height: 1.4; }}
        .ath-prod-header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 16px; }}
        .ath-prod-header h3 {{ font-size: 14px; font-weight: 700; color: #111; text-transform: uppercase; letter-spacing: 0.5px; margin: 0; }}
        .ath-prod-header span {{ font-size: 13px; color: #111; cursor: pointer; font-weight: 500; }}
        .ath-prod-header span:hover {{ text-decoration: underline; }}
        .ath-prod-row {{ display: flex; align-items: flex-start; gap: 20px; padding: 16px 0; border-bottom: 1px solid #f5f5f5; cursor: pointer; transition: 0.2s; }}
        .ath-prod-row:hover {{ background: #fafafa; }}
        .ath-prod-row:last-child {{ border-bottom: none; }}
        .ath-prod-img {{ width: 60px; height: 60px; background: white; display: flex; align-items: center; justify-content: center; }}
        .ath-prod-img img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
        .ath-prod-info {{ flex: 1; overflow: hidden; }}
        .ath-prod-brand {{ font-size: 13px; font-weight: 800; color: #000; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px; }}
        .ath-prod-title {{ font-size: 14px; color: #444; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .ath-prod-price {{ font-size: 14px; font-weight: 700; color: #111; }}
    </style>

    <div class="ath-mega-menu">
        <div class="ath-left-col">
            {sidebar_html}
        </div>
        <div class="ath-right-col">
            <div class="ath-guide-title">SHOPPING GUIDES</div>
            <div class="ath-guide-card">
                <div class="ath-guide-img">
                    <img src="https://placehold.co/80x80?text=Guide" alt="Guide">
                </div>
                <div class="ath-guide-text">
                    <h4>Choosing The Right Product For Your Style</h4>
                    <p>Explore different styles to find what suits you best. From casual to formal, understanding shapes and sizes can elevate your look.</p>
                </div>
            </div>

            <div class="ath-prod-header">
                <h3>PRODUCTS</h3>
                <span onclick='window.location.href="/search.php?search_query={clean_query}"'>See {total_products} more products &rarr;</span>
            </div>
            {products_html}
        </div>
    </div>
    """
    return {"html": master_html}