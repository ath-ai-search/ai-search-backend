"""
=====================================================================================
🌐 MEGA MENU WIDGET SERVICE (0.2s Ultra-Fast Vector AI)
=====================================================================================
"""

import os
import json
import time
import logging
import hashlib
import re

# External clients
from app.config import os_client, INDEX_NAME, openai_client
from app.nlp.semantic_matrix import extract_semantic_matrix
from app.prompts.autocomplete_suggestions_prompt import build_fallback_suggestions
from app.utils.cache import cache_get, cache_set

# Constants
from app.core.constants import (
    WIDGET_BOOST_BRAND,
    WIDGET_BOOST_CATEGORY,
    WIDGET_BOOST_NAME,
    WIDGET_BOOST_MULTI_MATCH,
    WIDGET_ACCESSORY_DEMOTION_WEIGHT,
    KNN_MIN_K,
    AI_EMBEDDING_MODEL,
    MAX_AUTOCOMPLETE_SUGGESTIONS,
    DEFAULT_SEARCH_TERM,
    AUTOCOMPLETE_CACHE_TTL  
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


# =====================================================================
# 🚀 SMART URL EXTRACTOR
# =====================================================================
def extract_clean_image_url(image_data):
    if not image_data:
        return None
        
    raw_str = str(image_data[0]) if isinstance(image_data, list) and len(image_data) > 0 else str(image_data)
    
    match = re.search(r'(https?://[^\s\'"\]]+)', raw_str)
    if match:
        return match.group(1)
        
    match_rel = re.search(r'(/wp-content/[^\s\'"\]]+)', raw_str)
    if match_rel:
        return f"https://venuemarketplace.xyz{match_rel.group(1)}"
        
    clean_img = raw_str.strip("['\"] ")
    if clean_img.startswith("/"):
        return f"https://venuemarketplace.xyz{clean_img}"
    if clean_img.startswith("//"):
        return f"https:{clean_img}"
        
    return clean_img if len(clean_img) > 5 else None


# =========================================================================
# 🌐 MAIN WIDGET FUNCTION
# =========================================================================
async def get_mega_menu_widget(query_string: str, recent_searches: str = "") -> dict:
    
    _start_time = time.perf_counter()
    
    clean_query = query_string.strip().lower()
    if clean_query == "*": clean_query = ""
    
    recent_list = recent_searches.split("||")[:3] if recent_searches else []
    valid_recents = [r.strip() for r in recent_list if r.strip() and r.strip().lower() not in ["null", "undefined", "[]", ""]]
    
    active_search_term = clean_query
    if not active_search_term and valid_recents:
        active_search_term = valid_recents[0].lower()
    
    if not active_search_term:
        return {"html": ""}
    
    if active_search_term == "best buy": active_search_term = "tv"
    elif active_search_term == "amazon": active_search_term = "macbook"
    
    # 🚀 CACHE BUSTER V6 (Forces instant update for new speed logic)
    cache_string = f"{active_search_term}|{recent_searches}"
    cache_key = f"widget_mega_menu_v6:{hashlib.md5(cache_string.encode()).hexdigest()}"
    
    cached_result = await cache_get(cache_key)
    if cached_result:
        return cached_result

    # STEP 4: FAST VECTOR EMBEDDING (Takes ~150ms)
    vector = None
    try:
        resp = await openai_client.embeddings.create(input=active_search_term, model=AI_EMBEDDING_MODEL)
        vector = resp.data[0].embedding
    except Exception:
        pass
        
    matrix = extract_semantic_matrix(active_search_term)
    core_query = matrix["core_query"]
    
    # STEP 5: FAST OPENSEARCH QUERY (Takes ~20ms)
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
        semantic_shoulds.append({"knn": {"embedding": {"vector": vector, "k": KNN_MIN_K}}})
        
    semantic_shoulds.extend([
        {"match_phrase_prefix": {"name": {"query": core_query, "max_expansions": 10, "boost": 10}}},
        {"match": {"category": {"query": core_query, "boost": 8}}},
        {"match": {"brand": {"query": core_query, "boost": 5}}},
        {"multi_match": {"query": core_query, "fields": ["name^5", "brand^4", "category^3"], "operator": "and"}}
    ])
    
    score_functions = []
    if not matrix["has_accessory_intent"]:
        for acc in matrix["accessory_keywords"]:
            score_functions.append({"filter": {"match": {"name": acc}}, "weight": WIDGET_ACCESSORY_DEMOTION_WEIGHT})
            score_functions.append({"filter": {"match": {"category": acc}}, "weight": WIDGET_ACCESSORY_DEMOTION_WEIGHT})
    
    os_query = {
        "size": 15,  
        "_source": ["name", "images"], 
        "query": {
            "function_score": {
                "query": {"bool": {"should": semantic_shoulds, "minimum_should_match": 1, "filter": filters, "must_not": must_nots}},
                "functions": score_functions, "score_mode": "multiply", "boost_mode": "multiply"
            }
        }
    }
    
    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
        hits = response.get("hits", {}).get("hits", [])
    except Exception as e:
        logger.error(f"❌ OpenSearch Widget Error: {e}")
        hits = []
    
    # =====================================================================
    # 🧠 THE 0.2 SECOND AI SMART SWITCH (No Slow Chat AI)
    # =====================================================================
    word_count = len(active_search_term.split())
    is_complex_query = word_count >= 3
    
    ai_suggestions = []

    if is_complex_query:
        # --- MODE 1: PURE VECTOR AI (~200ms) ---
        seen_names = set()
        for hit in hits:
            name = hit.get("_source", {}).get("name", "")
            clean_name = str(name).strip()
            lower_name = clean_name.lower()
            
            if lower_name and lower_name not in seen_names:
                seen_names.add(lower_name)
                # For complex queries, show a slightly longer, highly relevant product name
                short_title = " ".join(clean_name.split()[:6]) 
                ai_suggestions.append(short_title)
                
                if len(ai_suggestions) >= MAX_AUTOCOMPLETE_SUGGESTIONS:
                    break
                    
        if not ai_suggestions:
            ai_suggestions = build_fallback_suggestions(active_search_term)
            
    else:
        # --- MODE 2: LIGHTNING FAST PREFIX (~20ms) ---
        seen_names = set()
        for hit in hits:
            name = hit.get("_source", {}).get("name", "")
            clean_name = str(name).strip()
            lower_name = clean_name.lower()
            
            if lower_name and lower_name not in seen_names:
                seen_names.add(lower_name)
                # Shorten simple queries to 4 words
                short_title = " ".join(clean_name.split()[:4])
                ai_suggestions.append(short_title)
                
                if len(ai_suggestions) >= MAX_AUTOCOMPLETE_SUGGESTIONS:
                    break

        if not ai_suggestions:
            ai_suggestions = build_fallback_suggestions(active_search_term)

    # =====================================================================
    # 🚀 BULLETPROOF IMAGE COLLECTOR
    # =====================================================================
    product_thumbs = []
    seen_thumbs = set()
    
    for hit in hits:
        images = hit.get("_source", {}).get("images", [])
        thumb_url = extract_clean_image_url(images)
        
        if thumb_url and thumb_url not in seen_thumbs:
            seen_thumbs.add(thumb_url)
            product_thumbs.append(thumb_url)
            if len(product_thumbs) >= len(ai_suggestions):
                break
    
    # =====================================================================
    # 🚀 SIDEBAR HTML BUILDER
    # =====================================================================
    sidebar_html = ""
    thumb_used = 0
    
    fallback_js = "this.onerror=null; this.outerHTML='<i class=&quot;fas fa-search&quot; style=&quot;color:#9ca3af; width:24px; font-size:14px; text-align:center; display:inline-block;&quot;></i>';"
    
    for i, suggestion in enumerate(ai_suggestions):
        safe_suggestion = suggestion.replace("'", "\\'")
        click_js = f"document.getElementById('search_query').value='{safe_suggestion}'; const btn=document.getElementById('searchBtn'); if(btn) btn.click(); else window.location.href='/search.php?search_query={safe_suggestion}&section=content';"
        
        if thumb_used < len(product_thumbs):
            thumb_url = product_thumbs[thumb_used]
            thumb_used += 1
            icon_html = f'<img src="{thumb_url}" onerror="{fallback_js}" style="width:24px; height:24px; object-fit:contain; border-radius:3px; flex-shrink:0;">'
        else:
            icon_html = '<i class="fas fa-search" style="color:#9ca3af; width:24px; font-size: 14px; text-align:center; display:inline-block;"></i>'
        
        q = active_search_term.lower()
        s_lower = suggestion.lower()
        
        if q in s_lower:
            idx = s_lower.index(q)
            highlighted = f"{suggestion[:idx+len(q)]}<b>{suggestion[idx+len(q):]}</b>"
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
    
    master_html = MEGA_MENU_TEMPLATE
    master_html = master_html.replace("__STYLES__", MEGA_MENU_STYLES)
    master_html = master_html.replace("__SCRIPTS__", MEGA_MENU_SCRIPTS)
    master_html = master_html.replace("__SIDEBAR__", sidebar_html)
    
    final_response = {"html": master_html}
    await cache_set(cache_key, final_response, ttl_seconds=AUTOCOMPLETE_CACHE_TTL)
    
    _elapsed_ms = (time.perf_counter() - _start_time) * 1000
    print(f"🚀 AUTOCOMPLETE (0.2s VECTOR AI) | query='{active_search_term}' | time={_elapsed_ms:.2f}ms", flush=True)

    return final_response