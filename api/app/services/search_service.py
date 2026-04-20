"""
=====================================================================================
🧠 venue AI SEARCH ARCHITECTURE - MASTER DOCUMENTATION 🧠
=====================================================================================

This service powers the AI search infrastructure. It combines advanced technologies
to guarantee a flawless, 0-dead-end user experience:

1. NLP (Natural Language Processing) & Intent Matrix
2. LLM Embeddings (Vectorization)
3. KNN (K-Nearest Neighbors) Semantic Search
4. NPQ (Negative Predictive Querying / Demotion Scoring)

5. 🔥 "The Equalizer" & Category Boosting:
   - Splits multi-items ("macbook | iphone") to guarantee equal billing.
   - Solves the Polysemy Problem (e.g. "Watch Cap" vs "Wrist Watch") by applying a 
     massive 200x boost if the query perfectly matches the product's official Category.

6. 🔥 LLM Chat Agent (Context-Aware Gender, Brand, & Price Engine):
   - Strict JSON extraction now includes Gender Nodes.
   - Bulletproof Float Casting: Aggressively strips $ and text from AI price outputs.
   - Bulletproof Menswear Interceptor: Prevents "Dress Socks" from showing up when 
     searching for Men's Dresses by hard-forcing the query to "suits | dress shirts".
   - 🔥 NEW Bulletproof Brand Filter: Forces case-insensitivity on all brand filters 
     to prevent the Fallback Engine from dropping brands like "Apple" vs "APPLE".
=====================================================================================
"""

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
# 🧠 NLP: SEMANTIC MATRIX EXTRACTION
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
        max_match = re.search(r'(?:under|less than|below|cheaper than|<)\s*\$?\s*(\d+)', query_lower)
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

    core_query = re.sub(r'\b\s+and\s+\b', ' | ', core_query)
    core_query = re.sub(r'[,&]', ' | ', core_query)
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
# 👑 MAIN SEARCH ROUTE (Omni-Search Engine)
# =========================================================================
async def execute_search(request: SearchRequest):
    request.page_size = 25 if request.page_size != 10 else 10
    
    # ⚡ V135 Redis Key: Flushes cache to apply the strict Case-Insensitive Brand Fix
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:ai:v135:{hashlib.md5(request_str.encode()).hexdigest()}"

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

    if "|" in core_query:
        multi_items = [item.strip() for item in core_query.split("|") if item.strip()]
        core_query_for_vector = " ".join(multi_items) 
    else:
        multi_items = [core_query]
        core_query_for_vector = core_query

    if core_query_for_vector:
        try:
            resp = await openai_client.embeddings.create(input=core_query_for_vector, model="text-embedding-3-small")
            vector = resp.data[0].embedding
        except Exception as e:
            logger.error(f"❌ OpenAI Embedding Failed: {e}")

    # --- 🛡️ APPLY HARD FILTERS ---
    filters = [{"term": {"in_stock": True}}]
    must_nots = []
    
    if matrix["min_price"] is not None or matrix["max_price"] is not None:
        price_range = {}
        if matrix["min_price"] is not None: price_range["gte"] = matrix["min_price"]
        if matrix["max_price"] is not None: price_range["lte"] = matrix["max_price"]
        filters.append({"range": {"price": price_range}})

    if matrix["is_sale"] or request.sort == "on_sale" or (request.filters and getattr(request.filters, "on_sale", False)):
        filters.append({"range": {"sale_price": {"gt": 0}}})

    if request.filters:
        if getattr(request.filters, "category", None): filters.append({"terms": {"category": request.filters.category[:5]}})
        if getattr(request.filters, "in_stock", None) is not None: filters.append({"term": {"in_stock": request.filters.in_stock}})
        
        if getattr(request.filters, "color", None):
            filters.append({"bool": {"should": [{"multi_match": {"query": c, "type": "phrase", "fields": ["color", "attributes*", "name"]}} for c in request.filters.color[:5]], "minimum_should_match": 1}})
            
        if getattr(request.filters, "size", None):
            size_shoulds = []
            for s in request.filters.size[:5]:
                size_str = str(s).strip()
                safe_size_query = size_str if "size" in size_str.lower() else f"size {size_str} {size_str}"
                size_shoulds.append({
                    "multi_match": {
                        "query": safe_size_query,
                        "fields": ["size", "attributes*", "name"],
                        "type": "best_fields"
                    }
                })
            filters.append({"bool": {"should": size_shoulds, "minimum_should_match": 1}})
        
        if getattr(request.filters, "gender", None):
            gender_shoulds = []
            for g in request.filters.gender[:3]:
                g_str = str(g).strip()
                gender_shoulds.append({
                    "multi_match": {
                        "query": g_str,
                        "fields": ["gender", "attributes.gender", "attributes.Gender", "category", "name"],
                        "type": "best_fields"
                    }
                })
            filters.append({"bool": {"should": gender_shoulds, "minimum_should_match": 1}})

        # 🟢 FIXED: Case-Insensitive Bulletproof Brand Filter
        if getattr(request.filters, "brand", None):
            brand_shoulds = []
            for b in request.filters.brand[:5]:
                b_str = str(b).strip()
                brand_shoulds.extend([
                    {"match_phrase": {"brand": b_str}},
                    {"term": {"brand": b_str}},
                    {"term": {"brand": b_str.upper()}},
                    {"term": {"brand": b_str.title()}}
                ])
            filters.append({"bool": {"should": brand_shoulds, "minimum_should_match": 1}})
            
        if getattr(request.filters, "price", None):
            p_range = {}
            if getattr(request.filters.price, "min", None) is not None: 
                try: 
                    clean_min = re.sub(r'[^\d.]', '', str(request.filters.price.min))
                    if clean_min: p_range["gte"] = float(clean_min)
                except Exception: pass
            if getattr(request.filters.price, "max", None) is not None: 
                try: 
                    clean_max = re.sub(r'[^\d.]', '', str(request.filters.price.max))
                    if clean_max: p_range["lte"] = float(clean_max)
                except Exception: pass
            if p_range: filters.append({"range": {"price": p_range}})

    sort_query = [{"_score": "desc"}]
    if request.sort == "price_asc": sort_query = [{"price": "asc"}]
    elif request.sort == "price_desc": sort_query = [{"price": "desc"}]
    elif request.sort == "on_sale": sort_query = [{"_score": "desc"}] 

    # --- ⚖️ APPLY SCORING ALGORITHMS ---
    semantic_shoulds = []
    
    if vector:
        k_val = max(200, from_val + request.page_size + 100)
        semantic_shoulds.append({"knn": {"embedding": {"vector": vector, "k": k_val}}})
        
    for item in multi_items:
        semantic_shoulds.extend([
            {
                "match_phrase": {
                    "name": {
                        "query": item,
                        "boost": 100.0 
                    }
                }
            },
            {
                "match_phrase": {
                    "brand": {
                        "query": item,
                        "boost": 300.0 
                    }
                }
            },
            {
                "match": {
                    "category": {
                        "query": item,
                        "boost": 200.0 
                    }
                }
            },
            {
                "multi_match": {
                    "query": item, 
                    "fields": ["name^10", "brand^5", "category^3", "description"],
                    "type": "cross_fields",
                    "operator": "and",
                    "boost": 20.0 
                }
            },
            {
                "multi_match": {
                    "query": item, 
                    "fields": ["name^5", "brand^3", "category^2", "description"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                    "boost": 5.0 
                }
            }
        ])

    score_functions = []
    
    if not matrix["has_accessory_intent"]:
        for acc in matrix["accessory_keywords"]:
            score_functions.append({"filter": {"match": {"name": acc}}, "weight": 0.00001})
            score_functions.append({"filter": {"match": {"category": acc}}, "weight": 0.00001})

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
        "aggs": {"categories": {"terms": {"field": "category", "size": 25}}}
    }

    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
    except Exception as e:
        logger.error(f"❌ OpenSearch Error: {str(e)}")
        return {
            "error": "Search service unavailable", 
            "results": [], 
            "total_results": 0,
            "total_pages": 0,
            "current_page": request.page,
            "pagination_html": "",
            "facets": {"categories": []}
        }
    
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

        results.append({
            "id": source.get("product_id"), "name": source.get("name", "Unknown Product"),
            "description": source.get("description", ""), "brand": brand_display, 
            "category": clean_cats, "price": source.get("price", 0.0),
            "sale_price": source.get("sale_price"), "in_stock": source.get("in_stock", False),
            "sku": source.get("sku", ""), "url": source.get("url", ""),
            "primary_image": primary_image, "rating": source.get("rating") if source.get("rating", 0) > 0 else _demo_rating,
            "sales_count": source.get("sales_count") if source.get("sales_count", 0) > 0 else _demo_sales,
            "score": round(0.85 + (normalized_score * 0.14), 2)
        })

    if request.sort not in ["price_asc", "price_desc"]:
        results.sort(key=lambda x: x["score"], reverse=True)

    aggregations = response.get("aggregations", {})
    facets = {
        "categories": [{"value": str(c.get("key")).strip(), "label": str(c.get("key")).strip(), "count": c.get("doc_count", 0)} for c in aggregations.get("categories", {}).get("buckets", []) if c.get("key")]
    }

    final_response = {
        "total_results": total_hits, "total_pages": total_pages, 
        "current_page": request.page, "pagination_html": build_pagination_html(total_pages, request.page), 
        "results": results, "facets": facets
    }
    
    try: await redis_client.set(cache_key, json.dumps(final_response), ex=300)
    except Exception: pass
    return final_response

# =========================================================================
# ✨ LLM AGENT ROUTER (Context-Aware Engine)
# =========================================================================
async def process_ai_assistant(chat_message: str, current_state: SearchRequest):
    current_filters = current_state.filters.model_dump() if current_state.filters else {}
    
    system_prompt = f"""
    You are the venue AI, an intelligent e-commerce shopping assistant.
    
    CURRENT SEARCH CONTEXT:
    - User is currently searching for: "{current_state.query}"
    - Active Filters applied: {json.dumps(current_filters)}

    NEW USER MESSAGE: "{chat_message}"

    YOUR TASK:
    Analyze the message and decide if the user wants to REFINE their current search or start a completely NEW SEARCH.

    🔥 CRITICAL LOGIC RULES:
    1. FILTERING (Refine): If the user types a color, size, price (e.g., "under 50"), or GENDER and DOES NOT name a completely different product, set intent to "refine". KEEP the 'search_query' exactly as "{current_state.query}" and extract the variables into the filters array.
    2. NEW SEARCH: If the user types a new product (e.g., current context is "shoes" but they type "iphone"), set intent to "new_search". Change 'search_query' to the new product and clear old filters.
    3. BRAND AWARENESS: "Apple" ALWAYS refers to the technology company (MacBook, iPhone, iPad). NEVER treat it as a fruit.
    4. PRICE PARSING: Extract numerical limits only. NO $ signs.

    Output ONLY a valid JSON object:
    {{
        "intent": "refine" | "new_search",
        "search_query": "The core product.",
        "filters": {{
            "color": [], 
            "size": [], 
            "brand": [], 
            "gender": [], 
            "on_sale": false, 
            "price": {{"min": null, "max": null}} 
        }},
        "ai_message": "Friendly 1-sentence reply WITH FUN EMOJIS!",
        "suggestions": ["Follow-up query 1", "Follow-up query 2", "Follow-up query 3"]
    }}
    """

    try:
        llm_response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
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
        
        new_filters_obj.color = []
        new_filters_obj.category = []
        new_filters_obj.brand = []
        new_filters_obj.size = [] 
        new_filters_obj.gender = []
        new_filters_obj.on_sale = extracted_filters.get("on_sale", False)
        
        # [Context Preservation] If refining, we carry over their existing filters.
        if parsed_intent.get("intent") == "refine" and current_state.filters:
            new_filters_obj.category = current_state.filters.category or []
            new_filters_obj.brand = current_state.filters.brand or []
            new_filters_obj.color = current_state.filters.color or []
            new_filters_obj.size = current_state.filters.size or []
            new_filters_obj.gender = getattr(current_state.filters, "gender", []) or [] 
            new_filters_obj.price = current_state.filters.price
            new_filters_obj.in_stock = current_state.filters.in_stock
            if getattr(current_state.filters, "on_sale", False) and extracted_filters.get("on_sale") is not False:
                new_filters_obj.on_sale = True

        bad_words = ["string", "example", "any", "none", "etc", "and", "or", "for"]

        if extracted_filters.get("color"):
            colors = [str(c).lower() for c in extracted_filters["color"] if str(c).lower() not in bad_words]
            new_filters_obj.color = list(set(new_filters_obj.color + colors))
            
        if extracted_filters.get("size"):
            sizes = [str(s).upper() for s in extracted_filters["size"] if str(s).lower() not in bad_words]
            new_filters_obj.size = list(set(new_filters_obj.size + sizes))
            
        if extracted_filters.get("brand"):
            brands = [str(b).upper() for b in extracted_filters["brand"] if str(b).lower() not in bad_words]
            new_filters_obj.brand = list(set(new_filters_obj.brand + brands))
            
        if extracted_filters.get("gender"):
            genders = [str(g).lower() for g in extracted_filters["gender"] if str(g).lower() not in bad_words]
            new_filters_obj.gender = list(set(getattr(new_filters_obj, "gender", []) + genders))
            
        if extracted_filters.get("price"):
            p_data = extracted_filters["price"]
            if isinstance(p_data, dict):
                try:
                    raw_min = p_data.get("min")
                    raw_max = p_data.get("max")
                    
                    min_p = None
                    if raw_min is not None and str(raw_min).strip() not in ["", "null", "None"]:
                        clean_min = re.sub(r'[^\d.]', '', str(raw_min))
                        if clean_min: min_p = float(clean_min)
                        
                    max_p = None
                    if raw_max is not None and str(raw_max).strip() not in ["", "null", "None"]:
                        clean_max = re.sub(r'[^\d.]', '', str(raw_max))
                        if clean_max: max_p = float(clean_max)
                        
                    if min_p is not None or max_p is not None:
                        new_filters_obj.price = PriceFilter(min=min_p, max=max_p)
                except Exception as e:
                    logger.error(f"AI Price extraction error: {e}")

        # 🟢 BULLETPROOF MENSWEAR INTERCEPTOR
        current_genders = [str(g).lower() for g in getattr(new_filters_obj, "gender", [])]
        is_male = any(g in ["men", "mens", "male"] for g in current_genders)
        
        if "dress" in updated_request.query.lower() and is_male:
            updated_request.query = "suits | dress shirts"
            parsed_intent["ai_message"] = "Let's find some sharp men's formal wear! 👔✨"
            parsed_intent["suggestions"] = ["Show me men's suits", "Looking for dress shirts", "Find formal ties"]
            
        # 🟢 BULLETPROOF APPLE HARDWARE INTERCEPTOR
        clean_q = updated_request.query.lower()
        is_apple_device = any(x in clean_q for x in ["iphone", "macbook", "ipad", "apple watch", "apple tv", "iphones"])
        is_apple_brand = clean_q == "apple"
        is_accessory = any(x in clean_q for x in ["case", "cover", "charger", "cable", "protector", "accessories"])
        
        if (is_apple_device or is_apple_brand) and not is_accessory:
            new_filters_obj.brand = ["Apple"]
            if is_apple_brand:
                parsed_intent["ai_message"] = "Here are the best Apple products we have in stock! 🍏✨"
                parsed_intent["suggestions"] = ["Show me iPhones", "Looking for MacBooks", "Check out iPads"]
            else:
                parsed_intent["ai_message"] = f"Exciting choice! Searching for the best {updated_request.query} items for you! 📱✨"

        updated_request.filters = new_filters_obj
        if new_filters_obj.on_sale:
            updated_request.sort = "on_sale"

        final_results_dict = await execute_search(updated_request)
        dropped_filters = []
        
        if final_results_dict.get("total_results", 0) == 0 and (new_filters_obj.size or new_filters_obj.color or getattr(new_filters_obj, "gender", [])):
            if new_filters_obj.size: dropped_filters.append("size")
            if new_filters_obj.color: dropped_filters.append("color")
            if getattr(new_filters_obj, "gender", []): dropped_filters.append("gender target")
            new_filters_obj.size = []
            new_filters_obj.color = []
            new_filters_obj.gender = []
            updated_request.filters = new_filters_obj
            final_results_dict = await execute_search(updated_request)
            
        if final_results_dict.get("total_results", 0) == 0 and new_filters_obj.brand:
            dropped_filters.append("brand")
            new_filters_obj.brand = []
            updated_request.filters = new_filters_obj
            final_results_dict = await execute_search(updated_request)

        if final_results_dict.get("total_results", 0) == 0:
            dropped_filters.append("strict price limits")
            updated_request.filters = None
            final_results_dict = await execute_search(updated_request)

        if "ai_message" in final_results_dict:
            del final_results_dict["ai_message"]
            
        ai_reply = parsed_intent.get("ai_message", "")
        
        if dropped_filters:
            dropped_str = " or ".join(dropped_filters)
            ai_reply = f"I couldn't find exact matches for that {dropped_str}, but here are the best {updated_request.query.replace('|', ' and ')} items we have in stock! ✨"
        elif not ai_reply or not isinstance(ai_reply, str):
            ai_reply = "Here are the matches I found! 🌟"
            
        suggestions = parsed_intent.get("suggestions", [])
        if not isinstance(suggestions, list):
            suggestions = ["Show me shoes", "Find jackets", "I'm looking for bags"]
        
        clean_ui_query = updated_request.query.replace("|", " and ")
        
        return AIAssistantResponse(
            **final_results_dict, 
            ai_message=ai_reply, 
            updated_query=clean_ui_query,
            updated_filters=new_filters_obj.model_dump(),
            updated_sort=updated_request.sort, 
            suggestions=suggestions[:4]
        )

    except Exception as e:
        logger.error(f"❌ AI Assistant Processing Error: {e}")
        fail_results = await execute_search(current_state)
        if "ai_message" in fail_results:
            del fail_results["ai_message"]
        return AIAssistantResponse(**fail_results, ai_message="Sorry, I encountered an error. 🚧", suggestions=["Show me shoes", "I'm looking for bags"])

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
    if clean_query == "*":
        clean_query = ""

    # 🟢 1. PULL IN THE BROWSER HISTORY
    recent_list = recent_searches.split("||")[:3] if recent_searches else []
    valid_recents = [r.strip() for r in recent_list if r.strip() and r.strip().lower() not in ["null", "undefined", "[]", ""]]

    # 🟢 2. SET THE ACTIVE SEARCH TERM
    active_search_term = clean_query
    
    # If the search bar is empty, but they have history, use their history!
    if not active_search_term and valid_recents:
        active_search_term = valid_recents[0].lower()

    # 🟢 3. NEW USER FIX: Force it to Luxury Sunglasses!
    if not active_search_term:
        active_search_term = "luxury sunglasses"

    # 🟢 4. COMPETITOR INTERCEPTOR
    if active_search_term == "best buy":
        active_search_term = "tv"
    elif active_search_term == "amazon":
        active_search_term = "macbook"
    
    vector = None
    try:
        resp = await openai_client.embeddings.create(input=active_search_term, model="text-embedding-3-small")
        vector = resp.data[0].embedding
    except Exception: pass

    matrix = extract_semantic_matrix(active_search_term)
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

    semantic_shoulds = []
    if vector:
        semantic_shoulds.append({"knn": {"embedding": {"vector": vector, "k": 200}}})
        
    semantic_shoulds.extend([
        {"match_phrase": {"brand": {"query": core_query, "boost": 5000.0}}},
        {"match": {"category": {"query": core_query, "boost": 3000.0}}},
        {"match_phrase": {"name": {"query": core_query, "boost": 500.0}}}
    ])
    
    if core_query:
        semantic_shoulds.append({
            "multi_match": {
                "query": core_query, 
                "fields": ["name^5", "brand^4", "category^3"],
                "operator": "and",
                "boost": 5.0
            }
        })
    
    score_functions = []
    if not matrix["has_accessory_intent"]:
        for acc in matrix["accessory_keywords"]:
            score_functions.append({"filter": {"match": {"name": acc}}, "weight": 0.001})
            score_functions.append({"filter": {"match": {"category": acc}}, "weight": 0.001})

    os_query = {
        "size": 10,
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "should": semantic_shoulds,
                        "minimum_should_match": 1,
                        "filter": filters,
                        "must_not": must_nots
                    }
                },
                "functions": score_functions,
                "score_mode": "multiply",
                "boost_mode": "multiply"
            }
        },
        "track_total_hits": True, 
        "aggs": {"top_categories": {"terms": {"field": "category", "size": 6}}} 
    }

    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
        hits = response.get("hits", {}).get("hits", [])
        total_products = response.get("hits", {}).get("total", {}).get("value", 0)

    except Exception as e:
        logger.error(f"❌ OpenSearch Mega Menu Error: {e}")
        hits = []
        total_products = 0

    products_html = ""
    dynamic_brands_set = set()
    
    if not hits:
        products_html = "<div style='padding: 20px; color: #666;'>No products found.</div>"
    else:
        for hit in hits:
            source = hit.get("_source", {})
            name = source.get("name", "Unknown Product")
            prod_url = source.get("url", "#") 
            brand_display = get_smart_brand(source)
            if brand_display != "UNKNOWN BRAND" and brand_display != "UNKNOWN": dynamic_brands_set.add(brand_display)
            price = float(source.get("price", 0.0))
            raw_sale = source.get("sale_price")
            sale_price = float(raw_sale) if raw_sale is not None else 0.0
            images = source.get("images", [])
            img_url = images[0] if isinstance(images, list) and images else "https://placehold.co/100x100?text=No+Image"

            if sale_price > 0 and sale_price < price:
                badge_html = '<div style="position: absolute; top: -6px; right: -6px; background: #CC0000; color: white; font-size: 9px; font-weight: bold; padding: 2px 6px; border-radius: 3px; z-index: 10; text-transform: uppercase; letter-spacing: 0.5px;">Sale</div>'
                price_html = f'<div class="bclouds-prod-price"><span style="color: #CC0000; font-weight: 800;">${sale_price:.2f}</span> <del style="color: #888; font-size: 13px; font-weight: 600; margin-left: 4px;">${price:.2f}</del></div>'
            else:
                badge_html = ""
                price_html = f'<div class="bclouds-prod-price">${price:.2f}</div>'

            products_html += f"""
            <div class="bclouds-prod-row" onclick="window.location.href='{prod_url}';" style="cursor: pointer;">
                <div class="bclouds-prod-img" style="position: relative;">
                    {badge_html}
                    <img src="{img_url}" alt="{name}">
                </div>
                <div class="bclouds-prod-info">
                    <h4 class="card-title" style="margin:0; padding:0; border:none;">
                        <a href="{prod_url}" data-instantload data-event-type="product-click" class="bclouds-prod-title" title="{name}" style="text-decoration: none; color: inherit;">
                            {name}
                        </a>
                    </h4>
                    {price_html}
                </div>
            </div>
            """

    # 🟢 EXACT POPULAR SEARCHES YOU REQUESTED (iPhone removed)
    popular_searches = ["MacBook", "Dresses", "Sunglasses", "Home & Kitchen", "Watches"]

    sidebar_html = ""
    
    # 🟢 MAKE THE AI BOX USE THE ACTIVE SEARCH TERM (Recent History)
    display_text = f'Open "<span>{active_search_term}</span>"<br>in Assistant' if active_search_term and active_search_term != "*" else 'Open <span>AI Assistant</span><br>to explore'
    
    # 🟢 FIX THE CLICK ACTION: If they click the button, secretly fill the search bar with their history!
    ai_click_js = f"document.getElementById('search_query').value='{active_search_term}';" if active_search_term else ""

    sidebar_html += f"""
    <button id='ai-toggle' type='button' class='bclouds-assistant-box glowAni' onclick="{ai_click_js}">
        <div class='bclouds-assistant-left'>
            <i class='fas fa-magic bclouds-assistant-icon'></i>
            <div class='bclouds-assistant-text'>
                {display_text}
            </div>
        </div>
        <i class='fas fa-arrow-right' style='font-size: 14px; color: #111;'></i>
    </button>
    """
    
    # 🟢 REAL HISTORY: Only show recent searches if the user actually has them!
    recent_list = recent_searches.split("||")[:3] if recent_searches else []
    valid_recents = [r.strip() for r in recent_list if r.strip() and r.strip().lower() not in ["null", "undefined", "[]", ""]]
    
    if valid_recents:
        sidebar_html += "<div class='bclouds-side-title'>RECENT SEARCHES</div>"
        for r in valid_recents:
            # 🟢 BULLETPROOF REDIRECT
            click_js = f"document.getElementById('search_query').value='{r}'; const btn=document.getElementById('searchBtn'); if(btn) btn.click(); else window.location.href='/search.php?search_query={r}&section=content';"
            sidebar_html += f"""
            <div class='bclouds-side-item' onclick="{click_js}">
                <div style="display:flex; align-items:center; gap:12px;"><i class='far fa-clock' style='color:#9ca3af;'></i> <span>{r}</span></div>
                <i class="fas fa-arrow-right arrow-hover" style="font-size:12px; color:#9ca3af;"></i>
            </div>"""

    # 🟢 RENDER THE CUSTOM POPULAR SEARCHES
    sidebar_html += "<div class='bclouds-side-title' style='margin-top:24px;'>POPULAR SEARCHES</div>"
    for c in popular_searches:
        click_js = f"document.getElementById('search_query').value='{c}'; const btn=document.getElementById('searchBtn'); if(btn) btn.click(); else window.location.href='/search.php?search_query={c}&section=content';"
        sidebar_html += f"""
        <div class='bclouds-side-item' onclick="{click_js}">
            <div style='display:flex; align-items:center; gap:12px;'><i class='fas fa-search' style='color:#9ca3af;'></i> <span>{c}</span></div>
            <i class="fas fa-arrow-right arrow-hover" style="font-size:12px; color:#9ca3af;"></i>
        </div>
        """
            
    see_all_text = ""
    if total_products > 0:
        safe_query = active_search_term if active_search_term != "*" else ""
        see_all_text = f"<span onclick='document.getElementById(\"search_query\").value=\"{safe_query}\"; document.getElementById(\"searchBtn\").click();'>See all {total_products:,} results &rarr;</span>"
    
    master_html = f"""
    <style>
    .bclouds-mega-menu {{
        display: flex;
        width: 1495px;
        max-width: 95%;
        height: 547px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
        font-family: 'Inter', sans-serif;
        overflow: hidden;
        border: 1px solid #e5e7eb;
        margin: 133px auto 0;
        background-color: #f9f9f9;
    }}

    .bclouds-left-col {{ width: 320px; background: #fdfdfd; padding: 24px; border-right: 1px solid #f0f0f0; overflow-y: auto; }}
    .bclouds-assistant-box {{ display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; cursor: pointer; margin-bottom: 24px; transition: all 0.2s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.05); width: 100%; }}
    .bclouds-assistant-box:hover {{ border-color: #d1d5db; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
    .bclouds-assistant-left {{ display: flex; align-items: center; gap: 12px; }}
    .bclouds-assistant-icon {{ font-size: 16px; color: #111; }}
    .bclouds-assistant-text {{ font-size: 13px; font-weight: 500; color: #111; }}
    .bclouds-assistant-text span {{ font-style: italic; font-weight: 700; }}

    /* 🟢 MADE SIDEBAR TEXT BIGGER AND BOLDER */
    .bclouds-side-title {{ font-size: 13px; font-weight: 800; margin-bottom: 16px; text-transform: uppercase; color: #9ca3af; padding-left: 12px; letter-spacing: 0.5px; }}
    .bclouds-side-item {{ font-size: 16px; padding: 12px 14px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; border-radius: 6px; transition: all 0.2s ease; color: #374151; font-weight: 600; margin-bottom: 4px; }}
    .bclouds-side-item:hover {{ background: #f3f4f6; color: #111827; }}
    
    /* 🟢 ADDED ARROW HOVER EFFECT BACK */
    .bclouds-side-item .arrow-hover {{ opacity: 0; transform: translateX(-5px); transition: all 0.2s ease; }}
    .bclouds-side-item:hover .arrow-hover {{ opacity: 1; transform: translateX(0); color: #111827; }}

    .bclouds-right-col {{ position: relative;
    flex: 1;
    
    padding: 57px 32px 24px 32px;
    overflow-y: auto;
    display: flex;
    flex-wrap: wrap;
    gap:10px;
    align-items: flex-start; }}

    .bclouds-prod-header h3 {{
       margin-top: 10px;
       font-size: 18px;
    }}

    .bclouds-prod-header {{   display: flex;
    justify-content: space-between;
    margin-bottom: 16px;
    position: absolute;
    width: calc(100% - 66px);
    top: 12px; }}

    .bclouds-prod-header span {{
    display: inline-block;
    height: 33px;
    margin-top: 4px;
    border: 1px solid #ccc;
    border-radius: 3px;
    padding: 5px 15px;
    background-color: #f5f5f5;
    font-size: 14px;
    cursor: pointer;
    }}
    .bclouds-prod-header span:hover {{ background-color: #e5e5e5; }}
    
    .bclouds-prod-row {{
        border-bottom: 1px solid #f5f5f5;
        flex-wrap: wrap;
        border: 1px solid #ddd;
        padding: 12px;
        width: calc(20% - 8px);
        background-color: #fff;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}   
    .bclouds-prod-row:hover {{ transform: translateY(-3px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}

    .bclouds-prod-img {{  width: 100%;
    height: 140px;
    display: flex;
    align-items: center;
    justify-content: center; }}

    .bclouds-prod-img img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}

    .bclouds-prod-title {{ font-size: 14px; color: #444; padding: 8px 0 5px 0; }}
    .bclouds-prod-price {{ font-size: 14px; font-weight: 700; font-size: 16px; }}

    /* 🔥 GLOW ANIMATION */
    .glowAni {{
        --border-angle: 0deg;
        border-radius: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0px 2px 4px hsl(0 0% 0% / 25%);
        animation: border-angle-rotate 2s infinite linear;
        border: 0.2rem solid transparent;
        background: 
            linear-gradient(white, white) padding-box,
            conic-gradient(
                from var(--border-angle),
                oklch(100% 100% 0deg),
                oklch(100% 100% 45deg),
                oklch(100% 100% 90deg),
                oklch(100% 100% 135deg),
                oklch(100% 100% 180deg),
                oklch(100% 100% 225deg),
                oklch(100% 100% 270deg),
                oklch(100% 100% 315deg),
                oklch(100% 100% 360deg)
            ) border-box;
    }}

    @keyframes border-angle-rotate {{
        from {{ --border-angle: 0deg; }}
        to {{ --border-angle: 360deg; }}
    }}

    @property --border-angle {{
        syntax: "<angle>";
        initial-value: 0deg;
        inherits: false;
    }}

    .bclouds-prod-title {{
        display: -webkit-box;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
        -webkit-line-clamp: 1;
        cursor: pointer;
        height: 29px;
    }}

      @media (max-width: 768px) {{
        .bclouds-left-col {{
           display: inline-block;
           width: 100%;
        }}
        .bclouds-right-col {{
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          width: 100%;
          overflow: scroll;
          height: 400px;
        }}
        .bclouds-mega-menu {{
          margin: 160px auto 0;
          height: 697px;
          display: inline-block;
        }}
        .bclouds-prod-img {{
          height: auto;
          min-height: 60px;
        }}
    }}

      @media (max-width: 640px) {{ 
        .bclouds-prod-row {{
          width: calc(33% - 6px);
        }}
         .bclouds-prod-price {{
          font-size: 12px;
        }}
        .bclouds-prod-price span, .bclouds-prod-price del {{
          font-size: 12px !important;
        }}
        .bclouds-prod-price del {{
          margin-left: 0 !important;
        }}
        .glowAni{{
            margin-bottom: 0;
        }}
        .bclouds-side-item, .bclouds-side-title {{
          display: none;
        }}
        .bclouds-prod-img img {{
          max-height: 60px;
          }}

          .bclouds-right-col {{
            height: 518px;
          }}
          .bclouds-prod-header h3 {{
          font-size: 16px;
        }}
        .bclouds-prod-header span {{
          height: 29px;
          padding: 4px 10px;
          font-size: 13px;
          border-radius: 5px;
        }}
    }}

    </style>

    <div class="bclouds-mega-menu">
        <div class="bclouds-left-col">
            {sidebar_html}
        </div>
        <div class="bclouds-right-col">
            <div class="bclouds-prod-header">
                <h3>PRODUCTS</h3>
                {see_all_text}
            </div>
            {products_html}
        </div>
    </div>
    """

    return {"html": master_html}
# =========================================================================
# ✨ FULLY DYNAMIC AI WELCOME ENGINE ✨
# =========================================================================
async def generate_ai_welcome(current_query: str):
    system_prompt = f"""
    You are the venue, a high-end, intelligent e-commerce shopping assistant.
    The user just opened the AI chat panel. 
    
    CURRENT SEARCH CONTEXT: "{current_query}"
    
    YOUR TASK:
    Generate a highly dynamic, conversational welcome message and 3-4 clickable suggestion chips.
    
    RULES:
    1. If CURRENT SEARCH CONTEXT is empty (or ""), write a general, stylish welcome. E.g., "Welcome! Ready to explore some great fashion finds? ✨"
    2. If CURRENT SEARCH CONTEXT contains a product, acknowledge it and offer highly relevant refinements or complementary accessories specifically for that product! 
    3. The "suggestions" array MUST contain 3 to 4 realistic, clickable follow-up questions formatted as natural user requests.
    
    Output ONLY a valid JSON object matching this structure:
    {{
        "ai_message": "Your conversational welcome text WITH 1 OR 2 RELEVANT EMOJIS! 🛍️",
        "suggestions": ["Suggestion 1", "Suggestion 2", "Suggestion 3"]
    }}
    """

    try:
        llm_response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={ "type": "json_object" },
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7 
        )
        
        parsed = json.loads(llm_response.choices[0].message.content)
        
        return {
            "ai_message": parsed.get("ai_message", "Welcome to venue! How can I help you today? ✨"),
            "suggestions": parsed.get("suggestions", ["Show me new arrivals", "Find shoes", "I need a dress"])[:4]
        }
        
    except Exception as e:
        logger.error(f"❌ AI Welcome Error: {e}")
        return {
            "ai_message": "Welcome to venue! Ready to explore some great finds? 🛍️",
            "suggestions": ["Show me dresses", "Find shoes", "Looking for bags"]
        }