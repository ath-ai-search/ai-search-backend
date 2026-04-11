import json
import hashlib
import time
import logging
import re
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
    "453": "Software",
    "1111": "Shoes",
    "1239": "Clothing",
    "2365": "Luxury Bags"
}

MAX_OS_WINDOW = 10000 

# =================================================================
# 🧠 AI SMART BRAND EXTRACTOR (Ultimate Strict Version)
# =================================================================
def get_smart_brand(source):
    raw_brand = source.get("brand", "")
    # 1. Use DB brand if valid
    if raw_brand and str(raw_brand).strip().lower() not in ["none", "", "null", "other brands", "unknown"]:
        return str(raw_brand).strip().upper()
        
    title = str(source.get("name", "")).strip()
    title_lower = title.lower()
    
    # 2. Product Line strict mappings
    brand_mappings = {
        "iphone": "APPLE", "ipad": "APPLE", "macbook": "APPLE", "airpods": "APPLE", "imac": "APPLE",
        "galaxy": "SAMSUNG", "s20": "SAMSUNG", "s21": "SAMSUNG", "s22": "SAMSUNG", "s23": "SAMSUNG",
        "thinkpad": "LENOVO", "yoga": "LENOVO", "ideapad": "LENOVO",
        "predator": "ACER", "aspire": "ACER",
        "pavilion": "HP", "envy": "HP", "omen": "HP", "spectre": "HP",
        "rog": "ASUS", "zenbook": "ASUS", "vivobook": "ASUS",
        "pixel": "GOOGLE", "kindle": "AMAZON", "echo": "AMAZON"
    }
    for keyword, mapped_brand in brand_mappings.items():
        if re.search(rf'\b{keyword}\b', title_lower):
            return mapped_brand
            
    # 3. Known Brands word-boundary check
    known_brands = ["nike", "adidas", "puma", "reebok", "sony", "dell", "asus", "acer", "lenovo", "samsung"]
    for b in known_brands:
        if re.search(rf'\b{b}\b', title_lower):
            return b.upper()

    # 🍎 APPLE FRUIT FILTER
    if re.search(r'\bapple\b', title_lower):
        if not re.search(r'\b(cider|vinegar|organic|juice|cleanser|fruit|tea|body)\b', title_lower):
            return "APPLE"

    # 💻 HP TECH FILTER
    if re.search(r'\bhp\b', title_lower):
        if re.search(r'\b(laptop|pc|computer|printer|ink|monitor|pavilion|envy|probook)\b', title_lower):
            return "HP"
            
    # 4. Fallback: First word of Title
    words = title.split()
    if words:
        first_word = words[0].strip('",\'()[]{}!@#$%-').upper()
        if len(first_word) > 2 and not first_word.isnumeric() and first_word not in ["THE", "FOR", "AND", "WITH"]:
            return first_word
            
    return "UNKNOWN"

# ==========================================
# 📄 SERVER-SIDE HTML GENERATION
# ==========================================
def build_pagination_html(total_pages: int, current_page: int) -> str:
    if total_pages <= 1: return ""
    start = max(1, current_page - 2)
    end = min(total_pages, start + 4)
    if end - start < 4: start = max(1, end - 4)
    html = ""
    if start > 1: html += '<button class="page-btn" data-page="1">1</button><span>...</span>'
    for i in range(start, end + 1):
        active_class = "active" if i == current_page else ""
        html += f'<button class="page-btn {active_class}" data-page="{i}">{i}</button>'
    if end < total_pages: html += f'<span>...</span><button class="page-btn" data-page="{total_pages}">{total_pages}</button>'
    return html

async def execute_search(request: SearchRequest):
    request.page_size = 25
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:{hashlib.md5(request_str.encode()).hexdigest()}"

    try:
        cached_result = await redis_client.get(cache_key)
        if cached_result: return json.loads(cached_result)
    except Exception: pass

    from_val = (request.page - 1) * request.page_size
    bool_query = {"must": [], "should": [], "filter": [], "minimum_should_match": 0}
    query_text = request.query.strip() if request.query else ""
    
    if query_text:
        bool_query["minimum_should_match"] = 1
        bool_query["should"].append({
            "multi_match": {
                "query": query_text,
                "fields": ["name^10", "description"], 
                "fuzziness": "AUTO"
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

    os_query = {
        "from": from_val, "size": request.page_size,
        "query": {
            "function_score": {
                "query": {"bool": bool_query},
                "functions": [
                    {"field_value_factor": {"field": "rating", "factor": 1.5, "missing": 1.0}},
                    {"field_value_factor": {"field": "sales_count", "modifier": "log1p", "factor": 0.5, "missing": 0}}
                ],
                "boost_mode": "multiply"
            }
        },
        "sort": [{"_score": "desc"}],
        "aggs": {"brands": {"terms": {"field": "brand", "size": 25}}, "categories": {"terms": {"field": "category", "size": 25}}}
    }

    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
    except Exception as e:
        return {"error": "Search unavailable", "results": [], "total_results": 0}
    
    hits = response.get("hits", {})
    total_hits = hits.get("total", {}).get("value", 0)
    total_pages = (total_hits + request.page_size - 1) // request.page_size if total_hits > 0 else 0

    results = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        results.append({
            "id": source.get("product_id"), "name": source.get("name", "Unknown"),
            "brand": get_smart_brand(source), "price": source.get("price", 0.0),
            "sale_price": source.get("sale_price"),
            "primary_image": source.get("images", [""])[0], "rating": source.get("rating", 4.5),
            "score": round(hit.get("_score", 0) or 0, 2)
        })

    aggregations = response.get("aggregations", {})
    facets = {
        "brands": [{"label": str(b.get("key", "")).upper(), "value": b.get("key"), "count": b.get("doc_count", 0)} for b in aggregations.get("brands", {}).get("buckets", [])],
        "categories": [{"value": c.get("key"), "label": CATEGORY_MAP.get(str(c.get("key")), f"Category {c.get('key')}"), "count": c.get("doc_count", 0)} for c in aggregations.get("categories", {}).get("buckets", [])]
    }

    final_response = {"total_results": total_hits, "total_pages": total_pages, "current_page": request.page, "pagination_html": build_pagination_html(total_pages, request.page), "results": results, "facets": facets}
    try: await redis_client.set(cache_key, json.dumps(final_response), ex=300)
    except Exception: pass
    return final_response

async def execute_autocomplete(query_string: str):
    clean_query = query_string.strip()
    if not clean_query: return {"suggestions": []}
    os_query = {"size": 10, "_source": ["name", "images"], "query": {"match_phrase_prefix": {"name": {"query": clean_query, "max_expansions": 50}}}}
    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
        suggestions = [{"text": h['_source']['name'], "thumbnail": h['_source'].get('images', [None])[0]} for h in response['hits']['hits']]
        return {"suggestions": suggestions}
    except Exception: return {"suggestions": []}

# =================================================================
# 🎨 MEGA MENU HTML GENERATOR (With Sale Badge Logic)
# =================================================================
async def get_mega_menu_widget(query_string: str, recent_searches: str = ""):
    clean_query = query_string.strip().lower()
    
    if not clean_query:
        os_query = {
            "size": 4, "query": {"match_all": {}}, "sort": [{"_score": "desc"}],
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
            "sort": [{"_score": "desc"}],
            "aggs": {"top_categories": {"terms": {"field": "category", "size": 3}}}
        }

    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
        hits = response.get("hits", {}).get("hits", [])
        total_products = response.get("hits", {}).get("total", {}).get("value", 0)

        cats_agg = response.get("aggregations", {}).get("top_categories", {}).get("buckets", [])
        dynamic_cats = [CATEGORY_MAP.get(str(c.get("key")), str(c.get("key")).title()) for c in cats_agg]
        
        dynamic_brands_set = set()
        for hit in hits:
            b = get_smart_brand(hit.get("_source", {}))
            if b != "UNKNOWN": dynamic_brands_set.add(b)

    except Exception:
        hits, total_products, dynamic_cats, dynamic_brands_set = [], 0, [], set()

    products_html = ""
    for hit in hits:
        source = hit.get("_source", {})
        brand = get_smart_brand(source)
        img_url = source.get("images", ["https://placehold.co/100x100?text=No+Image"])[0]
        
        # 🏷️ FETCH PRICING LOGIC
        price = float(source.get("price", 0.0))
        raw_sale = source.get("sale_price")
        sale_price = float(raw_sale) if raw_sale is not None else 0.0

        # 🏷️ BUILD SALE BADGE AND PRICE HTML
        if sale_price > 0 and sale_price < price:
            # It IS on sale
            badge_html = '<div style="position: absolute; top: -6px; right: -6px; background: #CC0000; color: white; font-size: 9px; font-weight: bold; padding: 2px 6px; border-radius: 3px; z-index: 10; text-transform: uppercase; letter-spacing: 0.5px;">Sale</div>'
            price_html = f'<div class="ath-prod-price"><span style="color: #CC0000; font-weight: 800;">${sale_price:.2f}</span> <del style="color: #888; font-size: 13px; font-weight: 600; margin-left: 4px;">${price:.2f}</del></div>'
        else:
            # It is NOT on sale
            badge_html = ""
            price_html = f'<div class="ath-prod-price">${price:.2f}</div>'

        products_html += f"""
        <div class="ath-prod-row" onclick="window.location.href='/search.php?search_query={source.get('name')}'">
            <div class="ath-prod-img" style="position: relative;">
                {badge_html}
                <img src="{img_url}">
            </div>
            <div class="ath-prod-info">
                <div class="ath-prod-brand">{brand}</div>
                <div class="ath-prod-title" title="{source.get('name')}">{source.get('name')}</div>
                {price_html}
            </div>
        </div>"""

    sidebar_html = ""
    if recent_searches:
        sidebar_html += "<div class='ath-side-title'>RECENT SEARCHES</div>"
        for r in recent_searches.split("||")[:3]:
            sidebar_html += f"<div class='ath-side-item' onclick='window.location.href=\"/search.php?search_query={r}\"'><span>{r}</span></div>"

    if dynamic_brands_set:
        sidebar_html += "<div class='ath-side-title' style='margin-top:24px;'>BRAND</div>"
        for b in list(dynamic_brands_set)[:4]:
            sidebar_html += f"<div class='ath-side-item'><span>{b}</span></div>"

    if dynamic_cats:
        sidebar_html += "<div class='ath-side-title' style='margin-top:24px;'>POPULAR SEARCHES</div>"
        for c in dynamic_cats:
            sidebar_html += f"<div class='ath-side-item' onclick='window.location.href=\"/search.php?search_query={c}\"'><span>{c}</span><i class='fas fa-arrow-up' style='transform: rotate(45deg); font-size:10px; color:#999;'></i></div>"

    master_html = f"""
    <style>
        .ath-mega-menu {{ display: flex; width: 100%; max-width: 900px; height: 500px; background: white; border-radius: 8px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); font-family: 'Inter', sans-serif; text-align: left; overflow: hidden; border: 1px solid #e5e7eb; }}
        .ath-left-col {{ width: 320px; background: #fdfdfd; padding: 24px; border-right: 1px solid #f0f0f0; overflow-y: auto; }}
        .ath-side-title {{ font-size: 11px; font-weight: 800; color: #111; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .ath-side-item {{ font-size: 14px; color: #333; padding: 8px 0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: color 0.2s; }}
        .ath-side-item:hover {{ color: #000; text-decoration: underline; }}
        .ath-right-col {{ flex: 1; padding: 24px 32px; background: white; overflow-y: auto; }}
        .ath-prod-header {{ display: flex; justify-content: space-between; margin-bottom: 16px; font-size: 12px; font-weight: 800; text-transform: uppercase; }}
        .ath-prod-header span {{ font-weight: normal; color: #666; cursor: pointer; text-transform: none; }}
        .ath-prod-row {{ display: flex; gap: 20px; padding: 12px 0; border-bottom: 1px solid #f5f5f5; cursor: pointer; transition: background 0.2s; }}
        .ath-prod-row:hover {{ background: #fafafa; }}
        .ath-prod-img {{ width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; background: #fff; border-radius: 4px; }}
        .ath-prod-img img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
        .ath-prod-info {{ flex: 1; overflow: hidden; }}
        .ath-prod-brand {{ font-size: 12px; font-weight: 800; color: #000; text-transform: uppercase; margin-bottom: 4px; }}
        .ath-prod-title {{ font-size: 14px; color: #444; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .ath-prod-price {{ font-size: 14px; font-weight: 700; color: #111; display: flex; align-items: baseline; }}
    </style>
    <div class="ath-mega-menu">
        <div class="ath-left-col">{sidebar_html}</div>
        <div class="ath-right-col">
            <div class="ath-guide-title" style="font-size:11px; font-weight:800; margin-bottom:12px;">SHOPPING GUIDES</div>
            <div style="background:#f9fafb; padding:16px; border-radius:12px; margin-bottom:24px; display:flex; gap:16px;">
                <div style="width:60px; height:60px; background:#fff; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:10px; color:#999; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">Guide</div>
                <div>
                    <div style="font-size:13px; font-weight:700; margin-bottom:4px;">Find Your Perfect Match</div>
                    <div style="font-size:11px; color:#666; line-height:1.4;">Explore our top-rated collections based on your unique search interest.</div>
                </div>
            </div>
            <div class="ath-prod-header">PRODUCTS <span onclick='window.location.href="/search.php?search_query={clean_query}"'>See all products &rarr;</span></div>
            {products_html}
        </div>
    </div>"""
    return {"html": master_html}