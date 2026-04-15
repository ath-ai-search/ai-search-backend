import json
import hashlib
import time
import logging
import re
from app.config import os_client, INDEX_NAME, redis_client, openai_client
from app.models.search import SearchRequest, AIAssistantResponse, Filters, PriceFilter

# =========================================================================
# ⚙️ SYSTEM SETUP & CONFIGURATION
# =========================================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

MAX_OS_WINDOW = 10000 

# =========================================================================
# 🛠️ UTILITY FUNCTIONS
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
# 🧠 AI PART 1: ADVANCED NLP MATRIX
# =========================================================================
def extract_semantic_matrix(query_string):
    query_lower = query_string.lower()
    core_query = query_lower
    
    smart_min_price, smart_max_price, smart_discount = None, None, None
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

    disc_match = re.search(r'(\d+)%\s*(?:off|discount|sale)', query_lower)
    if disc_match: 
        smart_discount = int(disc_match.group(1))
        core_query = core_query.replace(disc_match.group(0), '')
    
    if "sale" in query_lower or "clearance" in query_lower or "discount" in query_lower or smart_discount:
        is_sale_intent = True
        core_query = re.sub(r'\b(?:with\s+sale|on\s+sale|sale|clearance|discount)\b', '', core_query)

    core_query = re.sub(r'\s+', ' ', core_query).strip()
    if not core_query:
        core_query = query_lower 

    accessory_keywords = ["case", "cover", "charger", "cable", "bag", "protector", "strap", "band", "adapter", "mount", "holder"]
    has_accessory_intent = any(acc in query_lower for acc in accessory_keywords)

    return {
        "core_query": core_query,
        "min_price": smart_min_price, "max_price": smart_max_price, 
        "discount": smart_discount, "is_sale": is_sale_intent,
        "has_accessory_intent": has_accessory_intent,
        "accessory_keywords": accessory_keywords
    }

# =========================================================================
# 👑 MAIN SEARCH ROUTE
# =========================================================================
async def execute_search(request: SearchRequest):
    request.page_size = 25 if request.page_size != 10 else 10
    
    # ⚡ V21 Redis Key: Flushes cache to apply all new logic
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:ai:v21:{hashlib.md5(request_str.encode()).hexdigest()}"

    try:
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
    except Exception as e:
        logger.warning(f"⚠️ Redis error: {e}")

    from_val = (request.page - 1) * request.page_size
    if from_val + request.page_size > MAX_OS_WINDOW: from_val = MAX_OS_WINDOW - request.page_size 

    query_text = request.query.strip() if request.query else ""
    vector = None

    matrix = extract_semantic_matrix(query_text)
    core_query = matrix["core_query"]

    # =========================================================================
    # 🧠 AI PART 2: LLM EMBEDDINGS
    # =========================================================================
    if query_text:
        try:
            resp = await openai_client.embeddings.create(input=query_text, model="text-embedding-3-small")
            vector = resp.data[0].embedding
        except Exception as e:
            logger.error(f"❌ OpenAI Embedding Failed: {e}")

    # =========================================================================
    # 🛡️ HARD FILTERS
    # =========================================================================
    filters = [{"term": {"in_stock": True}}]
    must_nots = []
    
    if matrix["min_price"] is not None or matrix["max_price"] is not None:
        price_range = {}
        if matrix["min_price"] is not None: price_range["gte"] = matrix["min_price"]
        if matrix["max_price"] is not None: price_range["lte"] = matrix["max_price"]
        filters.append({"range": {"price": price_range}})

    if matrix["is_sale"] or request.sort == "on_sale":
        filters.append({"range": {"sale_price": {"gt": 0}}})

    if request.filters:
        if getattr(request.filters, "brand", None): filters.append({"terms": {"brand": request.filters.brand}})
        if getattr(request.filters, "category", None): filters.append({"terms": {"category": request.filters.category}})
        if getattr(request.filters, "in_stock", None) is not None: filters.append({"term": {"in_stock": request.filters.in_stock}})
        
        if getattr(request.filters, "color", None):
            filters.append({"bool": {"should": [{"multi_match": {"query": c, "type": "phrase", "fields": ["color", "attributes*", "name"]}} for c in request.filters.color], "minimum_should_match": 1}})
        
        if getattr(request.filters, "price", None):
            p_range = {}
            if getattr(request.filters.price, "min", None) is not None: p_range["gte"] = request.filters.price.min
            if getattr(request.filters.price, "max", None) is not None: p_range["lte"] = request.filters.price.max
            if p_range: filters.append({"range": {"price": p_range}})

    sort_query = [{"_score": "desc"}]
    if request.sort == "price_asc": sort_query = [{"price": "asc"}]
    elif request.sort == "price_desc": sort_query = [{"price": "desc"}]

    # =========================================================================
    # ⚖️ AI PART 3: THE "NUCLEAR OVERRIDES" FOR HYBRID SCORING
    # =========================================================================
    semantic_shoulds = []
    
    if vector:
        k_val = max(200, from_val + request.page_size + 100)
        semantic_shoulds.append({"knn": {"embedding": {"vector": vector, "k": k_val}}})
        
    semantic_shoulds.extend([
        {
            "multi_match": {
                "query": core_query, 
                "fields": ["name^5", "brand^4", "category^3"],
                "fuzziness": "AUTO",
                "boost": 2.0
            }
        },
        {"match_phrase": {"brand": {"query": core_query, "boost": 5000.0}}},    
        {"match": {"category": {"query": core_query, "boost": 3000.0}}},        
        {"match_phrase": {"name": {"query": core_query, "boost": 500.0}}}       
    ])

    score_functions = []
    
    if not matrix["has_accessory_intent"]:
        for acc in matrix["accessory_keywords"]:
            score_functions.append({
                "filter": {"match": {"name": acc}},
                "weight": 0.001 
            })
            score_functions.append({
                "filter": {"match": {"category": acc}},
                "weight": 0.001 
            })

    if vector or core_query:
        query_body = {
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "should": semantic_shoulds,
                            "must_not": must_nots,
                            "minimum_should_match": 1,
                            "filter": filters
                        }
                    },
                    "functions": score_functions,
                    "score_mode": "multiply",
                    "boost_mode": "multiply"
                }
            }
        }
    else:
        query_body = {"query": {"bool": {"must": [{"match_all": {}}], "filter": filters, "must_not": must_nots}}}

    os_query = {
        "from": from_val, "size": request.page_size,
        **query_body,
        "sort": sort_query, 
        "track_total_hits": True,
        "track_scores": True, 
        "aggs": {"brands": {"terms": {"field": "brand", "size": 25}}, "categories": {"terms": {"field": "category", "size": 25}}}
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
    if not max_score or max_score == 0: max_score = 1.0

    results = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        brand_display = get_smart_brand(source)
        
        raw_cats = source.get("category", [])
        clean_cats = []
        if isinstance(raw_cats, str):
            clean_cats = [c.strip() for c in re.sub(r"[\[\]'\"]", "", raw_cats).split(",") if c.strip()]
        elif isinstance(raw_cats, list):
            clean_cats = [str(c).strip() for c in raw_cats if c and str(c).strip()]
        if not clean_cats or clean_cats == ["None"]: clean_cats = ["Uncategorized"]

        images = source.get("images", [])
        primary_image = images[0] if isinstance(images, list) and len(images) > 0 else None
        _pid = str(source.get("product_id", "123"))
        _demo_rating = 4.0 + (int(hashlib.md5(_pid.encode()).hexdigest(), 16) % 10) / 10.0
        _demo_sales = (int(hashlib.md5(_pid.encode()).hexdigest(), 16) % 800) + 150

        raw_score = hit.get("_score", 0) or 0
        normalized_score = min(1.0, raw_score / max_score) if max_score > 0 else 0
        
        name_lower = str(source.get("name", "")).lower()
        brand_lower = brand_display.lower()
        cat_lower = " ".join(clean_cats).lower()
        is_item_accessory = any(acc in name_lower for acc in matrix["accessory_keywords"])
        
        if core_query == brand_lower:
            display_score = 0.99
        elif core_query in cat_lower:
            display_score = 0.98
        elif core_query in name_lower and not matrix["has_accessory_intent"] and not is_item_accessory:
            display_score = 0.95 + (normalized_score * 0.03) 
        elif is_item_accessory and not matrix["has_accessory_intent"]:
            display_score = 0.40 + (normalized_score * 0.15) 
        elif core_query in name_lower:
            display_score = 0.85 + (normalized_score * 0.09)
        else:
            display_score = 0.60 + (normalized_score * 0.20)

        results.append({
            "id": source.get("product_id"), "name": source.get("name", "Unknown Product"),
            "description": source.get("description", ""), "brand": brand_display, 
            "category": clean_cats, "price": source.get("price", 0.0),
            "sale_price": source.get("sale_price"), "in_stock": source.get("in_stock", False),
            "sku": source.get("sku", ""), "url": source.get("url", ""),
            "primary_image": primary_image, "rating": source.get("rating") if source.get("rating", 0) > 0 else _demo_rating,
            "sales_count": source.get("sales_count") if source.get("sales_count", 0) > 0 else _demo_sales,
            "score": round(display_score, 2)
        })

    if request.sort not in ["price_asc", "price_desc"]:
        results.sort(key=lambda x: x["score"], reverse=True)

    aggregations = response.get("aggregations", {})
    facets = {
        "brands": [{"label": str(b.get("key", "")).strip() if b.get("key") and str(b.get("key")).strip() else "Other Brands", "value": b.get("key"), "count": b.get("doc_count", 0)} for b in aggregations.get("brands", {}).get("buckets", [])],
        "categories": [{"value": str(c.get("key")).strip(), "label": str(c.get("key")).strip(), "count": c.get("doc_count", 0)} for c in aggregations.get("categories", {}).get("buckets", []) if c.get("key")]
    }

    final_response = {
        "total_results": total_hits, "total_pages": total_pages, 
        "current_page": request.page, "pagination_html": build_pagination_html(total_pages, request.page), 
        "results": results, "facets": facets, 
        "ai_message": "" # Empty for standard searches
    }
    
    try: await redis_client.set(cache_key, json.dumps(final_response), ex=300)
    except Exception: pass
    return final_response


# =========================================================================
# ✨ NEW DYNAMIC AI METHOD: Intent & Context Shifting ✨
# =========================================================================
async def process_ai_assistant(chat_message: str, current_state: SearchRequest):
    """
    🔵 THE SOLUTION TO THE STACKING ISSUE.
    This specialized context-aware function intercepts AI chat messages and,
    instead of cumulatively adding them, it uses an LLM to decide if the user
    is refining the current search OR switching context completely.
    """
    
    current_filters = current_state.filters.model_dump() if current_state.filters else {}
    
    system_prompt = f"""
    You are ATHERA, an intelligent e-commerce AI shopping assistant.
    
    CURRENT CONTEXT:
    - User is currently searching for: "{current_state.query}"
    - Active UI Sidebar Filters applied: {json.dumps(current_filters)}

    NEW USER MESSAGE: "{chat_message}"

    YOUR TASK:
    Analyze the new user message. You must decide if the user wants to:
    1. REFINE the current search (e.g. they typed "red" or "nike" while looking at "shoes").
    2. Start a NEW SEARCH (e.g. they typed "bags" or "iphone" while looking at "shoes").

    Output ONLY a valid JSON object matching this structure:
    {{
        "intent": "refine" | "new_search",
        "search_query": "The core product noun ONLY (e.g., 'shoes', 'bags', 'dress'). NEVER include colors or brands in this field.",
        "filters": {{
            "color": ["black", "white", "blue", "red", "green", "brown"], 
            "brand": ["nike", "apple", "samsung", etc],
            "category": ["electronics", "footwear", etc]
        }},
        "ai_message": "A friendly 1-sentence reply in the style of a stylish assistant. E.g., 'Filtering your shoes to show only red Nike ones!' or 'Sure, let's explore some stylish bags!'"
    }}
    
    CRITICAL DECISION RULE:
    If the current search is 'shoes' and the new message is 'bags', this is 'new_search'.
    If the current search is 'shoes' and the new message is 'red nike', this is 'refine'.
    """

    try:
        llm_response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chat_message}
            ],
            temperature=0.0
        )
        
        parsed_intent = json.loads(llm_response.choices[0].message.content)
        
        updated_request = SearchRequest(
            query=parsed_intent.get("search_query", current_state.query),
            page=1, 
            page_size=10, 
            sort="best_matches" 
        )
        
        extracted_filters = parsed_intent.get("filters", {})
        new_filters_obj = Filters()
        
        # Initialize explicit empty lists so we can wipe filters if it's a new search
        new_filters_obj.color = []
        new_filters_obj.brand = []
        new_filters_obj.category = []
        
        if parsed_intent.get("intent") == "refine" and current_state.filters:
            new_filters_obj.brand = current_state.filters.brand or []
            new_filters_obj.category = current_state.filters.category or []
            new_filters_obj.color = current_state.filters.color or []
            new_filters_obj.price = current_state.filters.price
            new_filters_obj.in_stock = current_state.filters.in_stock

        if extracted_filters.get("color"): 
            new_filters_obj.color = list(set(new_filters_obj.color + extracted_filters["color"]))
        if extracted_filters.get("brand"): 
            new_filters_obj.brand = list(set(new_filters_obj.brand + extracted_filters["brand"]))
        if extracted_filters.get("category"): 
            new_filters_obj.category = list(set(new_filters_obj.category + extracted_filters["category"]))
        
        updated_request.filters = new_filters_obj

        final_results_dict = await execute_search(updated_request)
        
        return AIAssistantResponse(
            **final_results_dict, 
            ai_message=parsed_intent.get("ai_message", "Here is what I found for you."), 
            updated_query=updated_request.query, 
            updated_filters=new_filters_obj.model_dump() 
        )

    except Exception as e:
        logger.error(f"❌ AI Assistant Processing Error: {e}")
        fail_results = await execute_search(current_state)
        return AIAssistantResponse(**fail_results, ai_message="Here are the best matches I found:")


# =========================================================================
# 🔎 AUTOCOMPLETE ROUTE
# =========================================================================
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

# =========================================================================
# 🌐 HTML MEGA MENU ROUTE
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
        must_nots = []
        
        if matrix["min_price"] is not None or matrix["max_price"] is not None:
            price_range = {}
            if matrix["min_price"] is not None: price_range["gte"] = matrix["min_price"]
            if matrix["max_price"] is not None: price_range["lte"] = matrix["max_price"]
            filters.append({"range": {"price": price_range}})

        if matrix["is_sale"]:
            filters.append({"range": {"sale_price": {"gt": 0}}})

        if vector:
            semantic_shoulds = [
                {"match_phrase": {"brand": {"query": core_query, "boost": 5000.0}}},
                {"match": {"category": {"query": core_query, "boost": 3000.0}}},
                {"match_phrase": {"name": {"query": core_query, "boost": 500.0}}},
                {
                    "multi_match": {
                        "query": core_query, 
                        "fields": ["name^5", "brand^4", "category^3"],
                        "operator": "and",
                        "fuzziness": "AUTO",
                        "boost": 5.0
                    }
                }
            ]
            
            score_functions = []
            if not matrix["has_accessory_intent"]:
                for acc in matrix["accessory_keywords"]:
                    score_functions.append({
                        "filter": {"match": {"name": acc}},
                        "weight": 0.001 
                    })
                    score_functions.append({
                        "filter": {"match": {"category": acc}},
                        "weight": 0.001 
                    })

            os_query = {
                "size": 4,
                "query": {
                    "function_score": {
                        "query": {
                            "bool": {
                                "must": [{"knn": {"embedding": {"vector": vector, "k": 50}}}],
                                "should": semantic_shoulds,
                                "filter": filters,
                                "must_not": must_nots,
                                "minimum_should_match": 0
                            }
                        },
                        "functions": score_functions,
                        "score_mode": "multiply",
                        "boost_mode": "multiply"
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
                        "filter": filters,
                        "must_not": must_nots
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
    if clean_query:
        # 🟢 UPDATED: Using the exact button structure requested by your Sir
        sidebar_html += f"""
        <button id='ai-toggle' type='button' class='ath-assistant-box'>
            <div class='ath-assistant-left'>
                <i class='fas fa-magic ath-assistant-icon'></i>
                <div class='ath-assistant-text'>
                    Open "<span>{clean_query}</span>"<br>in Assistant
                </div>
            </div>
            <i class='fas fa-arrow-right' style='font-size: 14px; color: #111;'></i>
        </button>
        """
    
    if recent_searches:
        recent_list = recent_searches.split("||")[:3]
        if recent_list and recent_list[0]:
            sidebar_html += "<div class='ath-side-title'>RECENT SEARCHES</div>"
            for r in recent_list:
                sidebar_html += f"""
                <div class='ath-side-item' onclick='document.getElementById("search_query").value="{r}"; document.getElementById('searchBtn').click();'>
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
            <div class='ath-side-item' onclick='document.getElementById("search_query").value="{c}"; document.getElementById('searchBtn').click();'>
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
        
        /* 🟢 UPDATED CSS: Added width, text-align, and font-family so the <button> acts exactly like a block element */
        .ath-assistant-box {{ display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; cursor: pointer; margin-bottom: 24px; transition: all 0.2s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.05); width: 100%; text-align: left; font-family: inherit; }}
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