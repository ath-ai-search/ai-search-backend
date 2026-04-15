import json
import hashlib
import time
import logging
import re
from app.config import os_client, INDEX_NAME, redis_client, openai_client
from app.models.search import SearchRequest

# =========================================================================
# ⚙️ SECTION 1: SYSTEM SETUP & CONFIGURATION
# =========================================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

MAX_OS_WINDOW = 10000 

# =========================================================================
# 🛠️ SECTION 2: UTILITY FUNCTIONS (Brand Cleanup & Pagination)
# =========================================================================
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

# =========================================================================
# 🧠 SECTION 3: AI NLP (NATURAL LANGUAGE PROCESSING) MATRIX
# Automatically detects sizes, colors, and sales from chat text
# =========================================================================
def extract_semantic_matrix(query_string):
    query_lower = query_string.lower()
    core_query = query_lower
    
    smart_min_price, smart_max_price, smart_size, smart_discount = None, None, None, None
    is_sale_intent = False

    range_match = re.search(r'(?:between|from)?\s*\$?\s*(\d+)\s*(?:to|and|-)\s*\$?\s*(\d+)', query_lower)
    if range_match:
        smart_min_price, smart_max_price = float(range_match.group(1)), float(range_match.group(2))
        core_query = core_query.replace(range_match.group(0), '')
    else:
        max_match = re.search(r'(?:under|less than|below|<)\s*\$?\s*(\d+)', query_lower)
        if max_match: 
            smart_max_price = float(max_match.group(1))
            core_query = core_query.replace(max_match.group(0), '')
        min_match = re.search(r'(?:over|more than|above|>)\s*\$?\s*(\d+)', query_lower)
        if min_match: 
            smart_min_price = float(min_match.group(1))
            core_query = core_query.replace(min_match.group(0), '')

    size_match = re.search(r'size\s*(\d+(?:\.\d+)?)', query_lower)
    if size_match: 
        smart_size = str(size_match.group(1))
        core_query = core_query.replace(size_match.group(0), '')

    disc_match = re.search(r'(\d+)%\s*(?:off|discount|sale)', query_lower)
    if disc_match: 
        smart_discount = int(disc_match.group(1))
        core_query = core_query.replace(disc_match.group(0), '')
    
    if "sale" in query_lower or "clearance" in query_lower or "discount" in query_lower or smart_discount:
        is_sale_intent = True
        core_query = re.sub(r'\b(?:with\s+sale|on\s+sale|sale|clearance|discount)\b', '', core_query)

    # 🚀 AI Extractor Dictionaries (Colors, Personas, etc.)
    colors_dict = ["red", "blue", "black", "white", "green", "yellow", "pink", "purple", "brown", "grey", "silver", "gold", "beige"]
    personas_dict = ["men", "mens", "women", "womens", "kids", "boys", "girls", "baby", "unisex"]
    occasions_dict = ["wedding", "party", "gym", "running", "casual", "formal", "summer", "winter", "fall", "spring", "outdoor", "indoor", "beach"]
    
    extracted_colors = [c for c in colors_dict if re.search(rf'\b{c}\b', query_lower)]
    extracted_personas = [p for p in personas_dict if re.search(rf'\b{p}\b', query_lower)]
    extracted_occasions = [o for o in occasions_dict if re.search(rf'\b{o}\b', query_lower)]

    # Clean the Core Query for accurate text matching
    for c in extracted_colors: core_query = re.sub(rf'\b{c}\b', '', core_query)
    core_query = re.sub(r'\s+', ' ', core_query).strip()
    if not core_query:
        core_query = query_lower 

    return {
        "core_query": core_query,
        "min_price": smart_min_price, "max_price": smart_max_price, 
        "size": smart_size, "discount": smart_discount, "is_sale": is_sale_intent,
        "personas": extracted_personas, "colors": extracted_colors, "occasions": extracted_occasions
    }

# =========================================================================
# 🎨 SECTION 4: BACKEND HTML SIDEBAR GENERATOR (For Sir Rajinder's Request)
# This perfectly generates the left Sidebar UI based on active filters
# =========================================================================
def build_sidebar_html(facets, active_state):
    min_p = active_state.get('min_price') or ""
    max_p = active_state.get('max_price') or ""
    in_stock_chk = "checked" if active_state.get('in_stock') else ""

    html = f'''
    <div style="font-weight: 800; font-size: 0.8rem; margin-bottom: 20px; color:#888; text-transform: uppercase;">Refine By</div>
    
    <div class="filter-group" style="padding-bottom: 1.5rem; border-bottom: 1px solid #f0f2f5; margin-bottom: 1.5rem;">
        <h3 style="font-size: 0.85rem; text-transform: uppercase; font-weight: 800; color: #111; margin-bottom: 1rem;">Price Range</h3>
        <div class="price-inputs" style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <input type="number" id="priceMin" placeholder="Min $" value="{min_p}" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #e5e7eb; outline: none; font-size: 0.9rem;">
            <span style="color:#9ca3af;">-</span>
            <input type="number" id="priceMax" placeholder="Max $" value="{max_p}" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #e5e7eb; outline: none; font-size: 0.9rem;">
        </div>
        <button id="applyStaticFilters" class="update-btn" style="background: #111827; color: white; border: none; padding: 10px 15px; border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 0.8rem; width: 100%;">UPDATE</button>
    </div>
    
    <div class="filter-group" style="padding-bottom: 1.5rem; border-bottom: 1px solid #f0f2f5; margin-bottom: 1.5rem;">
        <h3 style="font-size: 0.85rem; text-transform: uppercase; font-weight: 800; color: #111; margin-bottom: 1rem;">Availability</h3>
        <div class="check-item" style="padding: 6px 0;">
            <label style="cursor: pointer; display: flex; align-items: center; gap: 10px; font-weight: 600; color: #111;">
                <input type="checkbox" id="inStockOnly" {in_stock_chk} style="accent-color: #111; width: 16px; height: 16px;"> 
                <span>In Stock Only</span>
            </label>
        </div>
    </div>
    '''

    def make_section(title, key, css_class):
        items = facets.get(key, [])
        if not items: return ""
        active_list = [str(x).lower() for x in active_state.get(key, [])]
        
        sec_html = f'<div class="filter-group" style="padding-bottom: 1.5rem; border-bottom: 1px solid #f0f2f5; margin-bottom: 1.5rem;">'
        sec_html += f'<h3 style="font-size: 0.85rem; text-transform: uppercase; font-weight: 800; color: #111; margin-bottom: 1rem;">{title}</h3>'
        sec_html += f'<div class="filter-scroll" style="max-height: 200px; overflow-y: auto;">'
        
        for item in items[:15]:
            val = str(item['value'])
            label = str(item['label'] or val).title()
            count = item['count']
            checked = "checked" if val.lower() in active_list else ""
            
            sec_html += f'''
            <div class="check-item" style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0;">
                <label style="cursor: pointer; display: flex; align-items: center; gap: 10px; font-weight: 500; font-size: 0.85rem; color: #444;">
                    <input type="checkbox" class="{css_class}" value="{val}" {checked} style="accent-color: #111; width: 16px; height: 16px;">
                    <span>{label}</span>
                </label>
                <span class="count-badge" style="background: #f3f4f6; padding: 2px 8px; border-radius: 40px; font-size: 0.7rem; font-weight: 600; color: #6b7280;">({count})</span>
            </div>
            '''
        sec_html += '</div></div>'
        return sec_html

    # Injecting all the dynamic filters!
    html += make_section('Categories', 'categories', 'cat-filter')
    html += make_section('Brands', 'brands', 'brand-filter')
    html += make_section('Colors', 'colors', 'color-filter')
    html += make_section('Sizes', 'sizes', 'size-filter')
    html += make_section('Gender', 'genders', 'gender-filter')

    html += '<button id="globalResetFilters" style="width: 100%; background: transparent; border: 1px solid #e5e7eb; padding: 12px; border-radius: 40px; font-weight: 600; font-size: 0.8rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; margin-top:1rem;"><i class="fas fa-undo-alt"></i> Reset Filters</button>'
    return html

# =========================================================================
# 👑 SECTION 5: MAIN SEARCH ROUTE (Handles Core Searches)
# =========================================================================
async def execute_search(request: SearchRequest):
    request.page_size = 25 if request.page_size != 10 else 10
    request_data = request.model_dump()
    req_filters = request_data.get("filters", {}) or {}
    
    query_text = request.query.strip() if request.query else ""
    vector = None

    # Step 5.1: Run the NLP Matrix
    matrix = extract_semantic_matrix(query_text)
    core_query = matrix["core_query"]

    # Generate Embeddings
    if query_text:
        try:
            resp = await openai_client.embeddings.create(input=query_text, model="text-embedding-3-small")
            vector = resp.data[0].embedding
        except Exception as e:
            logger.error(f"❌ OpenAI Embedding Failed: {e}")

    # 🚀 SYNC UI CHECKBOXES WITH AI CHAT EXTRACTIONS
    # This automatically combines clicks from the UI with keywords typed in the Chat!
    active_colors = list(set(req_filters.get("colors", []) + matrix["colors"]))
    active_sizes = list(set(req_filters.get("sizes", []) + ([matrix["size"]] if matrix["size"] else [])))
    active_genders = list(set(req_filters.get("genders", []) + matrix["personas"]))
    
    active_state = {
        "min_price": req_filters.get("price", {}).get("min") or matrix["min_price"],
        "max_price": req_filters.get("price", {}).get("max") or matrix["max_price"],
        "in_stock": req_filters.get("in_stock", False),
        "colors": active_colors, 
        "sizes": active_sizes, 
        "genders": active_genders,
        "brands": req_filters.get("brand", []), 
        "categories": req_filters.get("category", [])
    }

    # 🛡️ HARD FILTERS (Database Logic)
    filters = [{"term": {"in_stock": True}}] if active_state["in_stock"] else []
    
    if active_state["min_price"] is not None or active_state["max_price"] is not None:
        p_range = {}
        if active_state["min_price"] is not None: p_range["gte"] = active_state["min_price"]
        if active_state["max_price"] is not None: p_range["lte"] = active_state["max_price"]
        filters.append({"range": {"price": p_range}})

    if matrix["is_sale"] or request.sort == "on_sale": filters.append({"range": {"sale_price": {"gt": 0}}})
    
    if active_state["brands"]: filters.append({"terms": {"brand": active_state["brands"]}})
    if active_state["categories"]: filters.append({"terms": {"category": active_state["categories"]}})
    if active_state["colors"]: filters.append({"terms": {"attributes.color": active_state["colors"]}})
    if active_state["sizes"]: filters.append({"terms": {"attributes.size": active_state["sizes"]}})
    if active_state["genders"]: filters.append({"terms": {"attributes.gender": active_state["genders"]}})

    # Sorting
    sort_query = [{"_score": "desc"}]
    if request.sort == "price_asc": sort_query = [{"price": "asc"}]
    elif request.sort == "price_desc": sort_query = [{"price": "desc"}]
    
    from_val = (request.page - 1) * request.page_size
    if from_val + request.page_size > MAX_OS_WINDOW: from_val = MAX_OS_WINDOW - request.page_size 

    if vector:
        k_val = max(200, from_val + request.page_size + 100)
        semantic_shoulds = [
            {"match_phrase": {"name": {"query": core_query, "boost": 10.0}}},      
            {"match_phrase": {"brand": {"query": core_query, "boost": 8.0}}},       
            {"match_phrase": {"category": {"query": core_query, "boost": 5.0}}},    
            {
                "multi_match": {
                    "query": core_query, 
                    "fields": ["name^4", "brand^3", "category^2"],
                    "operator": "and",     
                    "fuzziness": "AUTO",   
                    "boost": 5.0
                }
            }
        ]
        query_body = {"query": {"bool": {"must": [{"knn": {"embedding": {"vector": vector, "k": k_val}}}], "should": semantic_shoulds, "filter": filters, "minimum_should_match": 0}}}
    else:
        query_body = {"query": {"bool": {"must": [{"match_all": {}}], "filter": filters}}}

    # 🚀 DYNAMIC AGGREGATIONS (Safely formatted without .keyword to ensure they show up!)
    os_query = {
        "from": from_val, "size": request.page_size,
        **query_body, "sort": sort_query, "track_total_hits": True, "track_scores": True, 
        "aggs": {
            "brands": {"terms": {"field": "brand", "size": 15}}, 
            "categories": {"terms": {"field": "category", "size": 15}},
            "colors": {"terms": {"field": "attributes.color", "size": 15}},
            "sizes": {"terms": {"field": "attributes.size", "size": 15}},
            "genders": {"terms": {"field": "attributes.gender", "size": 10}}
        }
    }

    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
    except Exception as e:
        logger.error(f"❌ OpenSearch Error: {str(e)}")
        return {"error": "Search service unavailable", "results": [], "total_results": 0}
    
    hits = response.get("hits", {})
    total_hits = hits.get("total", {}).get("value", 0)
    total_pages = (total_hits + request.page_size - 1) // request.page_size if total_hits > 0 else 0

    max_score = hits.get("max_score")
    if not max_score and len(hits.get("hits", [])) > 0: max_score = hits["hits"][0].get("_score", 1.0)
    if not max_score or max_score == 0: max_score = 1.0

    results = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        brand_display = get_smart_brand(source)
        
        raw_cats = source.get("category", [])
        clean_cats = []
        if isinstance(raw_cats, str): clean_cats = [c.strip() for c in re.sub(r"[\[\]'\"]", "", raw_cats).split(",") if c.strip()]
        elif isinstance(raw_cats, list): clean_cats = [str(c).strip() for c in raw_cats if c and str(c).strip()]
        if not clean_cats or clean_cats == ["None"]: clean_cats = ["Uncategorized"]

        images = source.get("images", [])
        primary_image = images[0] if isinstance(images, list) and len(images) > 0 else None
        _pid = str(source.get("product_id", "123"))
        _demo_rating = 4.0 + (int(hashlib.md5(_pid.encode()).hexdigest(), 16) % 10) / 10.0
        _demo_sales = (int(hashlib.md5(_pid.encode()).hexdigest(), 16) % 800) + 150

        raw_score = hit.get("_score", 0) or 0
        normalized_score = min(1.0, raw_score / max_score)

        results.append({
            "id": source.get("product_id"), "name": source.get("name", "Unknown Product"),
            "description": source.get("description", ""), "brand": brand_display, 
            "category": clean_cats, "price": source.get("price", 0.0),
            "sale_price": source.get("sale_price"), "in_stock": source.get("in_stock", False),
            "sku": source.get("sku", ""), "url": source.get("url", ""),
            "primary_image": primary_image, "rating": source.get("rating") if source.get("rating", 0) > 0 else _demo_rating,
            "sales_count": source.get("sales_count") if source.get("sales_count", 0) > 0 else _demo_sales,
            "score": round(normalized_score, 2)
        })

    # Format Facets for Frontend Extraction
    aggregations = response.get("aggregations", {})
    facets = {
        "brands": [{"label": str(b.get("key", "")).strip(), "value": b.get("key"), "count": b.get("doc_count", 0)} for b in aggregations.get("brands", {}).get("buckets", []) if b.get("key")],
        "categories": [{"value": str(c.get("key")).strip(), "label": str(c.get("key")).strip(), "count": c.get("doc_count", 0)} for c in aggregations.get("categories", {}).get("buckets", []) if c.get("key")],
        "colors": [{"value": str(c.get("key")).strip(), "label": str(c.get("key")).strip(), "count": c.get("doc_count", 0)} for c in aggregations.get("colors", {}).get("buckets", []) if c.get("key")],
        "sizes": [{"value": str(s.get("key")).strip(), "label": str(s.get("key")).strip(), "count": s.get("doc_count", 0)} for s in aggregations.get("sizes", {}).get("buckets", []) if s.get("key")],
        "genders": [{"value": str(g.get("key")).strip(), "label": str(g.get("key")).strip(), "count": g.get("doc_count", 0)} for g in aggregations.get("genders", {}).get("buckets", []) if g.get("key")]
    }

    # 🚀 GENERATE THE HTML DIRECTLY IN THE BACKEND!
    sidebar_html = build_sidebar_html(facets, active_state)

    # 🤖 AI CHAT GENERATOR
    ai_chat_message = "Here are some great options I found for you:"
    if request.page_size == 10 and query_text and total_hits > 0:
        try:
            top_brands = [b["label"] for b in facets["brands"][:3]]
            top_cats = [c["label"] for c in facets["categories"][:3]]
            b_str = ", ".join(top_brands) if top_brands else "our top brands"
            c_str = ", ".join(top_cats) if top_cats else "related categories"
            
            sys_msg = "You are ATHERA, a helpful, stylish AI shopping assistant. Write exactly 1 short, friendly sentence to introduce the products the user searched for. Mention the top brands or categories provided."
            user_msg = f"User searched: '{query_text}'. We found {total_hits} matches. Top Brands: {b_str}. Categories: {c_str}."
            
            chat_resp = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}],
                max_tokens=60, temperature=0.7
            )
            ai_chat_message = chat_resp.choices[0].message.content.strip()
        except Exception as e:
            pass
    elif request.page_size == 10 and total_hits == 0:
        ai_chat_message = f"I couldn't find any exact matches for '{query_text}'. Try adjusting your search keywords!"

    return {
        "total_results": total_hits, "total_pages": total_pages, 
        "current_page": request.page, "pagination_html": build_pagination_html(total_pages, request.page), 
        "results": results, "facets": facets, 
        "sidebar_html": sidebar_html, # Passed to the frontend UI
        "ai_message": ai_chat_message
    }

# =========================================================================
# 🔎 SECTION 6: AUTOCOMPLETE ROUTE (Main Bar Suggestions)
# =========================================================================
async def execute_autocomplete(query_string: str):
    clean_query = query_string.strip()
    if not clean_query: return {"suggestions": []}
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

    return {"suggestions": suggestions}

# =========================================================================
# 🌐 SECTION 7: MEGA MENU ROUTE (Dropdown Interface)
# =========================================================================
async def get_mega_menu_widget(query_string: str, recent_searches: str = ""):
    clean_query = query_string.strip().lower()
    
    if not clean_query:
        os_query = {
            "size": 4, "query": {"match_all": {}}, "sort": [{"_score": {"order": "desc"}}],
            "track_total_hits": True, 
            "aggs": {"top_categories": {"terms": {"field": "category", "size": 3}}}
        }
    else:
        vector = None
        try:
            resp = await openai_client.embeddings.create(input=clean_query, model="text-embedding-3-small")
            vector = resp.data[0].embedding
        except Exception: pass

        matrix = extract_semantic_matrix(clean_query)
        core_query = matrix["core_query"]
            
        filters = [{"term": {"in_stock": True}}]
        
        if matrix["min_price"] is not None or matrix["max_price"] is not None:
            price_range = {}
            if matrix["min_price"] is not None: price_range["gte"] = matrix["min_price"]
            if matrix["max_price"] is not None: price_range["lte"] = matrix["max_price"]
            filters.append({"range": {"price": price_range}})

        if matrix["is_sale"]:
            filters.append({"range": {"sale_price": {"gt": 0}}})

        if vector:
            semantic_shoulds = [
                {"match_phrase": {"name": {"query": core_query, "boost": 10.0}}},
                {"match_phrase": {"category": {"query": core_query, "boost": 8.0}}},
                {
                    "multi_match": {
                        "query": core_query, 
                        "fields": ["name^4", "category^3", "brand^2"],
                        "operator": "and",
                        "fuzziness": "AUTO",
                        "boost": 5.0
                    }
                }
            ]
            for p in matrix["personas"]: semantic_shoulds.append({"multi_match": {"query": p, "fields": ["name^1.5", "category^1.5"]}})
            for o in matrix["occasions"]: semantic_shoulds.append({"multi_match": {"query": o, "fields": ["name^1.5", "attributes^1.5"]}})
            for v in matrix["visuals"]: semantic_shoulds.append({"multi_match": {"query": v, "fields": ["name^1.5", "attributes^1.5"]}})
            if matrix["size"]: semantic_shoulds.append({"multi_match": {"query": matrix["size"], "fields": ["name^3", "attributes^2"]}})

            os_query = {
                "size": 4,
                "query": {
                    "bool": {
                        "must": [{"knn": {"embedding": {"vector": vector, "k": 50}}}],
                        "should": semantic_shoulds,
                        "filter": filters,
                        "minimum_should_match": 0
                    }
                },
                "track_total_hits": True, 
                "aggs": {"top_categories": {"terms": {"field": "category", "size": 3}}}
            }
        else:
            os_query = {
                "size": 4,
                "query": {
                    "bool": {
                        "must": [{"match_all": {}}],
                        "filter": filters
                    }
                },
                "sort": [{"_score": {"order": "desc"}}],
                "track_total_hits": True, 
                "aggs": {"top_categories": {"terms": {"field": "category", "size": 3}}}
            }

    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
        hits = response.get("hits", {}).get("hits", [])
        total_products = response.get("hits", {}).get("total", {}).get("value", 0)

        cats_agg = response.get("aggregations", {}).get("top_categories", {}).get("buckets", [])
        dynamic_cats = [str(c.get("key")) for c in cats_agg if str(c.get("key")).lower() != "none"]
    except Exception as e:
        logger.error(f"❌ OpenSearch Mega Menu Error: {e}")
        hits = []
        total_products = 0
        dynamic_cats = []

    products_html = ""
    dynamic_brands_set = set()
    
    if not hits:
        products_html = "<div style='padding: 20px; color: #666;'>No products found.</div>"
    else:
        for hit in hits:
            source = hit.get("_source", {})
            name = source.get("name", "Unknown Product")
            brand_display = get_smart_brand(source)
            if brand_display != "UNKNOWN BRAND" and brand_display != "UNKNOWN": dynamic_brands_set.add(brand_display)
            price = float(source.get("price", 0.0))
            raw_sale = source.get("sale_price")
            sale_price = float(raw_sale) if raw_sale is not None else 0.0
            images = source.get("images", [])
            img_url = images[0] if isinstance(images, list) and images else "https://placehold.co/100x100?text=No+Image"

            if sale_price > 0 and sale_price < price:
                badge_html = '<div style="position: absolute; top: -6px; right: -6px; background: #CC0000; color: white; font-size: 9px; font-weight: bold; padding: 2px 6px; border-radius: 3px; z-index: 10; text-transform: uppercase; letter-spacing: 0.5px;">Sale</div>'
                price_html = f'<div class="ath-prod-price"><span style="color: #CC0000; font-weight: 800;">${sale_price:.2f}</span> <del style="color: #888; font-size: 13px; font-weight: 600; margin-left: 4px;">${price:.2f}</del></div>'
            else:
                badge_html = ""
                price_html = f'<div class="ath-prod-price">${price:.2f}</div>'

            products_html += f"""
            <div class="ath-prod-row" onclick="document.getElementById('search_query').value='{name}'; document.getElementById('searchBtn').click();">
                <div class="ath-prod-img" style="position: relative;">
                    {badge_html}
                    <img src="{img_url}" alt="{name}">
                </div>
                <div class="ath-prod-info">
                    <div class="ath-prod-brand">{brand_display}</div>
                    <div class="ath-prod-title" title="{name}">{name}</div>
                    {price_html}
                </div>
            </div>
            """

    sidebar_html = ""
    # 🚀 FIX: Dynamic Button string with Click-To-Open logic!
    if clean_query:
        sidebar_html += f"""
        <button id="ai-toggle" type="button" class="ath-assistant-box" onclick="document.getElementById('ai-panel').classList.add('open');">
            <div class="ath-assistant-left">
                <i class="fas fa-magic ath-assistant-icon"></i>
                <div class="ath-assistant-text">
                    Open "<span>{clean_query}</span>"<br>in Assistant
                </div>
            </div>
            <i class="fas fa-arrow-right" style="font-size: 14px; color: #111;"></i>
        </button>
        """
    
    if recent_searches:
        recent_list = recent_searches.split("||")[:3]
        if recent_list and recent_list[0]:
            sidebar_html += "<div class='ath-side-title'>RECENT SEARCHES</div>"
            for r in recent_list:
                sidebar_html += f"""
                <div class='ath-side-item' onclick='document.getElementById("search_query").value="{r}"; document.getElementById("searchBtn").click();'>
                    <div style="display:flex; align-items:center; gap:12px;"><i class='far fa-clock'></i> <span>{r}</span></div>
                    <div style="display:flex; gap:8px; color:#999;"><i class="fas fa-arrow-up" style="transform: rotate(45deg); font-size:10px;"></i></div>
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
            <div class='ath-side-item' onclick='document.getElementById("search_query").value="{c}"; document.getElementById("searchBtn").click();'>
                <div style='display:flex; align-items:center; gap:12px;'><i class='fas fa-search'></i> <span>{c}</span></div>
                <i class="fas fa-arrow-up" style="transform: rotate(45deg); font-size:10px; color:#999;"></i>
            </div>
            """
            
    see_all_text = ""
    if total_products > 0:
        see_all_text = f"<span onclick='document.getElementById(\"search_query\").value=\"{clean_query}\"; document.getElementById(\"searchBtn\").click();'>See all {total_products:,} results &rarr;</span>"

    master_html = f"""
    <style>
        .ath-mega-menu {{ display: flex; width: 100%; max-width: 900px; height: 500px; background: white; border-radius: 8px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); font-family: 'Inter', sans-serif; text-align: left; overflow: hidden; border: 1px solid #e5e7eb; }}
        .ath-left-col {{ width: 320px; background: #fdfdfd; padding: 24px; border-right: 1px solid #f0f0f0; overflow-y: auto; }}
        .ath-assistant-box {{ display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; cursor: pointer; margin-bottom: 24px; transition: all 0.2s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .ath-assistant-box:hover {{ border-color: #d1d5db; box-shadow: 0 4px 6px rgba(0,0,0,0.05); background: #fdfdfd; }}
        .ath-assistant-left {{ display: flex; align-items: center; gap: 12px; }}
        .ath-assistant-icon {{ font-size: 16px; color: #111; }}
        .ath-assistant-text {{ font-size: 13px; font-weight: 500; color: #111; line-height: 1.4; }}
        .ath-assistant-text span {{ font-style: italic; font-weight: 700; }}
        .ath-side-title {{ font-size: 12px; font-weight: 700; color: #111; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .ath-side-item {{ font-size: 14px; color: #111; padding: 10px 0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background 0.2s; }}
        .ath-side-item i {{ color: #111; font-size: 14px; }}
        .ath-side-item:hover {{ background: #f5f5f5; border-radius: 4px; }}
        .ath-right-col {{ flex: 1; padding: 24px 32px; background: white; overflow-y: auto; }}
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
            <div class="ath-prod-header">
                <h3>PRODUCTS</h3>
                {see_all_text}
            </div>
            {products_html}
        </div>
    </div>
    """
    return {"html": master_html}