"""
=====================================================================================
🌐 MEGA MENU WIDGET SERVICE (Amazon-Style)
=====================================================================================
This file generates the HTML for the search dropdown autocomplete widget.

DESIGN: Pure Amazon-style
  - Only text suggestions with search icons
  - Bold highlighting of typed portion
  - NO product cards grid (removed for clean UX)

WORKFLOW:
  1. Determine "active search term" (user's query OR recent OR default)
  2. CHECK REDIS CACHE (Super fast response if already searched)
  3. Run quick OpenSearch query ONLY to extract product thumbnails
  4. Generate AI-powered autocomplete suggestions
  5. Build sidebar HTML with suggestions + bold highlighting
  6. Return final HTML string
=====================================================================================
"""

import os
import json
import time
import logging
import hashlib  # 🚀 SHUBAM WE ADDED THIS: Needed for Cache keys

# External clients
from app.config import os_client, INDEX_NAME, openai_client

# NLP brain
from app.nlp.semantic_matrix import extract_semantic_matrix

# AI prompts
from app.prompts.autocomplete_suggestions_prompt import (
    AUTOCOMPLETE_SYSTEM_PROMPT,
    build_autocomplete_user_prompt,
    build_fallback_suggestions,
)

# 🚀 SHUBAM WE ADDED THIS: Import our Cache functions!
from app.utils.cache import cache_get, cache_set

# Constants
from app.core.constants import (
    WIDGET_BOOST_BRAND,
    WIDGET_BOOST_CATEGORY,
    WIDGET_BOOST_NAME,
    WIDGET_BOOST_MULTI_MATCH,
    WIDGET_ACCESSORY_DEMOTION_WEIGHT,
    KNN_MIN_K,
    AI_CHAT_MODEL,
    AI_EMBEDDING_MODEL,
    AI_TEMPERATURE_BALANCED,
    MAX_AUTOCOMPLETE_SUGGESTIONS,
    DEFAULT_SEARCH_TERM,
    AUTOCOMPLETE_CACHE_TTL  # 🚀 SHUBAM WE ADDED THIS: Cache time limit
)

logger = logging.getLogger(__name__)


# =========================================================================
# 📂 TEMPLATE FILE LOADER
# =========================================================================
TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
    "mega_menu"
)

def _load_template_file(filename: str) -> str:
    filepath = os.path.join(TEMPLATE_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"❌ Failed to load template '{filename}': {e}")
        return ""

MEGA_MENU_TEMPLATE = _load_template_file("template.html")
MEGA_MENU_STYLES = _load_template_file("styles.css")
MEGA_MENU_SCRIPTS = _load_template_file("scripts.js")


# =========================================================================
# 🌐 MAIN WIDGET FUNCTION
# =========================================================================
async def get_mega_menu_widget(query_string: str, recent_searches: str = "") -> dict:
    
    # 🆕 START TIMING
    _start_time = time.perf_counter()
    
    # =====================================================================
    # STEP 1: CLEAN AND PARSE INPUT
    # =====================================================================
    clean_query = query_string.strip().lower()
    
    if clean_query == "*":
        clean_query = ""
    
    # =====================================================================
    # STEP 2: PARSE RECENT SEARCHES
    # =====================================================================
    recent_list = recent_searches.split("||")[:3] if recent_searches else []
    valid_recents = [
        r.strip()
        for r in recent_list
        if r.strip() and r.strip().lower() not in ["null", "undefined", "[]", ""]
    ]
    
    # =====================================================================
    # STEP 3: DETERMINE ACTIVE SEARCH TERM
    # =====================================================================
    active_search_term = clean_query
    
    if not active_search_term and valid_recents:
        active_search_term = valid_recents[0].lower()
    
    if not active_search_term:
        _elapsed_ms = (time.perf_counter() - _start_time) * 1000
        print(f"⏱️  AUTOCOMPLETE | query='(empty)' | recents={len(valid_recents)} | time={_elapsed_ms:.2f}ms | mode=empty", flush=True)
        return {"html": ""}
    
    if active_search_term == "best buy":
        active_search_term = "tv"
    elif active_search_term == "amazon":
        active_search_term = "macbook"
    
    # =====================================================================
    # 🚀 SHUBAM WE ADDED THIS: THE CACHE SHIELD 🚀
    # =====================================================================
    # Check if we already created this exact dropdown recently.
    cache_string = f"{active_search_term}|{recent_searches}"
    cache_key = f"widget_mega_menu:{hashlib.md5(cache_string.encode()).hexdigest()}"
    
    cached_result = await cache_get(cache_key)
    if cached_result:
        _elapsed_ms = (time.perf_counter() - _start_time) * 1000
        print(f"⚡ CACHE HIT | query='{active_search_term}' | time={_elapsed_ms:.2f}ms | mode=FAST", flush=True)
        return cached_result
    # =====================================================================

    # =====================================================================
    # STEP 5: GENERATE VECTOR EMBEDDING
    # =====================================================================
    vector = None
    try:
        resp = await openai_client.embeddings.create(
            input=active_search_term,
            model=AI_EMBEDDING_MODEL
        )
        vector = resp.data[0].embedding
    except Exception as e:
        logger.warning(f"⚠️ Widget embedding failed: {e}")
    
    # =====================================================================
    # STEP 6: EXTRACT SEMANTIC MATRIX
    # =====================================================================
    matrix = extract_semantic_matrix(active_search_term)
    core_query = matrix["core_query"]
    
    # =====================================================================
    # STEP 7: BUILD OPENSEARCH FILTERS (for thumbnail fetch)
    # =====================================================================
    filters = [{"term": {"in_stock": True}}]
    must_nots = []
    
    if matrix["min_price"] is not None or matrix["max_price"] is not None:
        price_range = {}
        if matrix["min_price"] is not None:
            price_range["gte"] = matrix["min_price"]
        if matrix["max_price"] is not None:
            price_range["lte"] = matrix["max_price"]
        filters.append({"range": {"price": price_range}})
    
    if matrix["is_sale"]:
        filters.append({"range": {"sale_price": {"gt": 0}}})
    
    # =====================================================================
    # STEP 8: BUILD SCORING (BOOST) CLAUSES
    # =====================================================================
    semantic_shoulds = []
    
    if vector:
        semantic_shoulds.append({
            "knn": {
                "embedding": {
                    "vector": vector,
                    "k": KNN_MIN_K
                }
            }
        })
    
    semantic_shoulds.extend([
        {
            "match_phrase": {
                "brand": {
                    "query": core_query,
                    "boost": WIDGET_BOOST_BRAND
                }
            }
        },
        {
            "match": {
                "category": {
                    "query": core_query,
                    "boost": WIDGET_BOOST_CATEGORY
                }
            }
        },
        {
            "match_phrase": {
                "name": {
                    "query": core_query,
                    "boost": WIDGET_BOOST_NAME
                }
            }
        }
    ])
    
    if core_query:
        semantic_shoulds.append({
            "multi_match": {
                "query": core_query,
                "fields": ["name^5", "brand^4", "category^3"],
                "operator": "and",
                "boost": WIDGET_BOOST_MULTI_MATCH
            }
        })
    
    # =====================================================================
    # STEP 9: ACCESSORY DEMOTION
    # =====================================================================
    score_functions = []
    if not matrix["has_accessory_intent"]:
        for acc in matrix["accessory_keywords"]:
            score_functions.append({
                "filter": {"match": {"name": acc}},
                "weight": WIDGET_ACCESSORY_DEMOTION_WEIGHT
            })
            score_functions.append({
                "filter": {"match": {"category": acc}},
                "weight": WIDGET_ACCESSORY_DEMOTION_WEIGHT
            })
    
    # =====================================================================
    # STEP 10: FINAL OPENSEARCH QUERY
    # =====================================================================
    os_query = {
        "size": 10,  
        "_source": ["images"],  
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
        }
    }
    
    # =====================================================================
    # STEP 11: EXECUTE SEARCH
    # =====================================================================
    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
        hits = response.get("hits", {}).get("hits", [])
    except Exception as e:
        logger.error(f"❌ OpenSearch Widget Error: {e}")
        hits = []
    
    # =====================================================================
    # STEP 12: GENERATE AI SUGGESTIONS
    # =====================================================================
    ai_suggestions = []
    try:
        llm_suggestion_response = await openai_client.chat.completions.create(
            model=AI_CHAT_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": AUTOCOMPLETE_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": build_autocomplete_user_prompt(active_search_term)
                }
            ],
            temperature=AI_TEMPERATURE_BALANCED,  
            max_tokens=400
        )
        
        parsed_suggestions = json.loads(llm_suggestion_response.choices[0].message.content)
        ai_suggestions = parsed_suggestions.get("suggestions", [])[:MAX_AUTOCOMPLETE_SUGGESTIONS]
    except Exception as e:
        logger.error(f"❌ AI Suggestion Error: {e}")
        ai_suggestions = build_fallback_suggestions(active_search_term)
    
    # =====================================================================
    # STEP 13: COLLECT THUMBNAILS
    # =====================================================================
    product_thumbs = []
    seen_thumbs = set()
    
    for hit in hits:
        source = hit.get("_source", {})
        images = source.get("images", [])
        thumb = images[0] if isinstance(images, list) and images else None
        
        if thumb and thumb not in seen_thumbs:
            seen_thumbs.add(thumb)
            product_thumbs.append(thumb)
            
            if len(product_thumbs) >= len(ai_suggestions):
                break
    
    # =====================================================================
    # STEP 14: BUILD SIDEBAR HTML
    # =====================================================================
    sidebar_html = ""
    thumb_used = 0
    
    for i, suggestion in enumerate(ai_suggestions):
        safe_suggestion = suggestion.replace("'", "\\'")
        
        click_js = (
            f"document.getElementById('search_query').value='{safe_suggestion}'; "
            f"const btn=document.getElementById('searchBtn'); "
            f"if(btn) btn.click(); "
            f"else window.location.href='/search.php?search_query={safe_suggestion}&section=content';"
        )
        
        if thumb_used < len(product_thumbs):
            thumb_url = product_thumbs[thumb_used]
            thumb_used += 1
            icon_html = (
                f'<img src="{thumb_url}" style="width:24px; height:24px; '
                f'object-fit:contain; border-radius:3px; flex-shrink:0;">'
            )
        else:
            icon_html = (
                '<i class="fas fa-search" style="color:#9ca3af; '
                'width:24px; font-size: 14px; text-align:center; display:inline-block;"></i>'
            )
        
        q = active_search_term.lower()
        s_lower = suggestion.lower()
        
        if q in s_lower:
            idx = s_lower.index(q)
            highlighted = (
                f"{suggestion[:idx+len(q)]}" +           
                f"<b>{suggestion[idx+len(q):]}</b>"      
            )
        else:
            highlighted = f"<b>{suggestion}</b>"
        
        sidebar_html += f"""
        <div class='bclouds-side-item' onclick="{click_js}">
            <div style='display:flex; align-items:center; gap:14px;'>
                {icon_html}
                <span style="font-size: 15px;">{highlighted}</span>
            </div>
        </div>
        """
    
    # =====================================================================
    # STEP 15: ASSEMBLE HTML AND SAVE TO CACHE
    # =====================================================================
    master_html = MEGA_MENU_TEMPLATE
    master_html = master_html.replace("__STYLES__", MEGA_MENU_STYLES)
    master_html = master_html.replace("__SCRIPTS__", MEGA_MENU_SCRIPTS)
    master_html = master_html.replace("__SIDEBAR__", sidebar_html)
    
    final_response = {"html": master_html}
    
    # 🚀 SHUBAM WE ADDED THIS: Save to Redis Cache so next time it is instant!
    await cache_set(cache_key, final_response, ttl_seconds=AUTOCOMPLETE_CACHE_TTL)

    _elapsed_ms = (time.perf_counter() - _start_time) * 1000
    print(f"⏱️  AUTOCOMPLETE | query='{active_search_term}' | recents={len(valid_recents)} | time={_elapsed_ms:.2f}ms | mode=full", flush=True)
    
    return final_response