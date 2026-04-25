"""
=====================================================================================
⚡ ULTRA-FAST MEGA MENU WIDGET SERVICE
=====================================================================================
This file generates the HTML for the search dropdown autocomplete widget.
We have STRIPPED OUT all slow OpenAI calls. It now uses pure OpenSearch 
Prefix Matching to return results in under 50ms!
=====================================================================================
"""

import os
import json
import time
import logging
import hashlib
import re

from app.config import os_client, INDEX_NAME
from app.nlp.semantic_matrix import extract_semantic_matrix
from app.prompts.autocomplete_suggestions_prompt import build_fallback_suggestions
from app.utils.cache import cache_get, cache_set
from app.core.constants import MAX_AUTOCOMPLETE_SUGGESTIONS

logger = logging.getLogger(__name__)

# =====================================================================
# 🖼️ SMART URL EXTRACTOR
# =====================================================================
def extract_clean_image_url(image_data):
    if not image_data:
        return None
    raw_str = str(image_data[0]) if isinstance(image_data, list) and len(image_data) > 0 else str(image_data)
    
    match = re.search(r'(https?://[^\s\'"\]]+)', raw_str)
    if match: return match.group(1)
        
    match_rel = re.search(r'(/wp-content/[^\s\'"\]]+)', raw_str)
    if match_rel: return f"https://venuemarketplace.xyz{match_rel.group(1)}"
        
    clean_img = raw_str.strip("['\"] ")
    if clean_img.startswith("/"): return f"https://venuemarketplace.xyz{clean_img}"
    if clean_img.startswith("//"): return f"https:{clean_img}"
        
    return clean_img if len(clean_img) > 5 else None

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
# ⚡ FAST WIDGET FUNCTION
# =========================================================================
async def get_mega_menu_widget(query_string: str, recent_searches: str = "") -> dict:
    _start_time = time.perf_counter()
    
    # 1. CLEAN INPUT
    clean_query = query_string.strip().lower()
    if clean_query == "*": clean_query = ""
    
    # 2. RECENT SEARCHES
    recent_list = recent_searches.split("||")[:3] if recent_searches else []
    valid_recents = [r.strip() for r in recent_list if r.strip() and r.strip().lower() not in ["null", "undefined", "[]", ""]]
    
    active_search_term = clean_query
    if not active_search_term and valid_recents:
        active_search_term = valid_recents[0].lower()
    
    if not active_search_term:
        _elapsed_ms = (time.perf_counter() - _start_time) * 1000
        print(f"⏱️  AUTOCOMPLETE | query='(empty)' | time={_elapsed_ms:.2f}ms | mode=empty", flush=True)
        return {"html": ""}
    
    # 3. COMPETITOR INTERCEPTOR
    if active_search_term == "best buy": active_search_term = "tv"
    elif active_search_term == "amazon": active_search_term = "macbook"

    # 4. CACHE SHIELD
    cache_string = f"{active_search_term}|{recent_searches}"
    cache_key = f"widget_mega_menu_fast_v2:{hashlib.md5(cache_string.encode()).hexdigest()}"
    
    cached_result = await cache_get(cache_key)
    if cached_result:
        _elapsed_ms = (time.perf_counter() - _start_time) * 1000
        print(f"⚡ CACHE HIT | query='{active_search_term}' | time={_elapsed_ms:.2f}ms", flush=True)
        return cached_result
    
    matrix = extract_semantic_matrix(active_search_term)
    core_query = matrix["core_query"]
    
    # 5. BUILD ULTRA-FAST TEXT SEARCH (NO OPENAI)
    filters = [{"term": {"in_stock": True}}]
    if matrix["min_price"] is not None or matrix["max_price"] is not None:
        price_range = {}
        if matrix["min_price"] is not None: price_range["gte"] = matrix["min_price"]
        if matrix["max_price"] is not None: price_range["lte"] = matrix["max_price"]
        filters.append({"range": {"price": price_range}})
    
    if matrix["is_sale"]: filters.append({"range": {"sale_price": {"gt": 0}}})
    
    # Fast Prefix Matching
    text_shoulds = []
    if core_query:
        text_shoulds.extend([
            {"match_phrase_prefix": {"name": {"query": core_query, "boost": 5.0}}},
            {"match_phrase_prefix": {"category": {"query": core_query, "boost": 3.0}}},
            {"match_phrase_prefix": {"brand": {"query": core_query, "boost": 2.0}}}
        ])
    else:
        text_shoulds.append({"match_all": {}})
        
    os_query = {
        "size": 15,  
        "_source": ["name", "images"],  
        "query": {
            "bool": {
                "should": text_shoulds,
                "minimum_should_match": 1,
                "filter": filters
            }
        }
    }
    
    # 6. EXECUTE OPENSEARCH
    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
        hits = response.get("hits", {}).get("hits", [])
    except Exception as e:
        logger.error(f"❌ OpenSearch Widget Error: {e}")
        hits = []
    
    # 7. EXTRACT SUGGESTIONS DIRECTLY FROM DATABASE HITS (Bypasses LLM)
    ai_suggestions = []
    product_thumbs = []
    seen_suggestions = set()
    
    for hit in hits:
        source = hit.get("_source", {})
        name = source.get("name", "")
        if not name: continue
            
        # Clean up name to make it look like a short suggestion
        words = name.split()
        short_name = " ".join(words[:6]).lower() # Take first 6 words
        
        if short_name not in seen_suggestions:
            seen_suggestions.add(short_name)
            ai_suggestions.append(short_name)
            
            images = source.get("images", [])
            product_thumbs.append(extract_clean_image_url(images))
            
            if len(ai_suggestions) >= MAX_AUTOCOMPLETE_SUGGESTIONS:
                break
                
    if not ai_suggestions:
        ai_suggestions = build_fallback_suggestions(active_search_term)
        product_thumbs = [None] * len(ai_suggestions)
    
    # 8. BUILD SIDEBAR HTML
    sidebar_html = ""
    fallback_js = "this.onerror=null; this.outerHTML='<i class=&quot;fas fa-search&quot; style=&quot;color:#9ca3af; width:24px; font-size:14px; text-align:center; display:inline-block;&quot;></i>';"
    
    for i, suggestion in enumerate(ai_suggestions):
        safe_suggestion = suggestion.replace("'", "\\'")
        click_js = f"document.getElementById('search_query').value='{safe_suggestion}'; const btn=document.getElementById('searchBtn'); if(btn) btn.click(); else window.location.href='/search.php?search_query={safe_suggestion}&section=content';"
        
        thumb_url = product_thumbs[i] if i < len(product_thumbs) else None
        
        if thumb_url:
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
                <span style="font-size: 15px; text-transform: capitalize;">{highlighted}</span>
            </div>
        </div>
        """
    
    # 9. ASSEMBLE FINAL HTML
    master_html = MEGA_MENU_TEMPLATE
    master_html = master_html.replace("__STYLES__", MEGA_MENU_STYLES)
    master_html = master_html.replace("__SCRIPTS__", MEGA_MENU_SCRIPTS)
    master_html = master_html.replace("__SIDEBAR__", sidebar_html)
    
    final_response = {"html": master_html}
    await cache_set(cache_key, final_response, ttl_seconds=3600)
    
    _elapsed_ms = (time.perf_counter() - _start_time) * 1000
    print(f"🚀 FAST AUTOCOMPLETE | query='{active_search_term}' | time={_elapsed_ms:.2f}ms", flush=True)
    
    return final_response