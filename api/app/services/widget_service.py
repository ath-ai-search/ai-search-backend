"""
=====================================================================================
🌟 HYBRID MEGA MENU WIDGET (Smart Filter & Real Product Fallback)
=====================================================================================
Restores the OpenAI ChatGPT logic for perfect, human-like suggestions.
Includes a Smart Filter to block dumb/repetitive AI suggestions for long queries.
If the AI gets confused, it falls back to REAL product names from the database!
=====================================================================================
"""

import os
import json
import time
import logging
import hashlib
import re

from app.config import os_client, INDEX_NAME, openai_client
from app.nlp.semantic_matrix import extract_semantic_matrix
from app.prompts.autocomplete_suggestions_prompt import AUTOCOMPLETE_SYSTEM_PROMPT, build_autocomplete_user_prompt
from app.utils.cache import cache_get, cache_set
from app.core.constants import AI_CHAT_MODEL, AI_TEMPERATURE_BALANCED, MAX_AUTOCOMPLETE_SUGGESTIONS

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
# 🌟 HYBRID WIDGET FUNCTION
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
    cache_key = f"widget_mega_menu_hybrid_v6:{hashlib.md5(cache_string.encode()).hexdigest()}"
    
    cached_result = await cache_get(cache_key)
    if cached_result:
        _elapsed_ms = (time.perf_counter() - _start_time) * 1000
        print(f"⏱️  AUTOCOMPLETE | query='{active_search_term}' | time={_elapsed_ms:.2f}ms | mode=CACHED ⚡", flush=True)
        return cached_result
    
    # 5. FAST OPENSEARCH QUERY (Pulls Real Product Names + Images)
    os_query = {
        "size": 10,  
        "_source": ["name", "images"],  
        "query": {
            "bool": {
                "should": [
                    {"match_phrase_prefix": {"name": {"query": active_search_term, "boost": 5.0}}},
                    {"match": {"category": {"query": active_search_term, "boost": 3.0}}},
                    {"match_phrase": {"brand": {"query": active_search_term, "boost": 2.0}}}
                ],
                "minimum_should_match": 1,
                "filter": [{"term": {"in_stock": True}}]
            }
        }
    }
    
    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
        hits = response.get("hits", {}).get("hits", [])
    except Exception as e:
        logger.error(f"❌ OpenSearch Widget Error: {e}")
        hits = []
    
    # 🚀 SMART ROUTING: Speed for short queries, AI smarts for long queries
    # - 1-2 words ("shoes") → OpenSearch only (50-100ms ⚡)
    # - 3+ words ("shoes for kids running") → OpenAI (1500ms but smart)
    word_count = len(active_search_term.split())
    use_openai = word_count >= 3
    
    ai_suggestions = []
    product_thumbs = []
    
    # 6A. SMART MODE: Long queries → use OpenAI for clever suggestions
    if use_openai:
        try:
            llm_suggestion_response = await openai_client.chat.completions.create(
                model=AI_CHAT_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": AUTOCOMPLETE_SYSTEM_PROMPT},
                    {"role": "user", "content": build_autocomplete_user_prompt(active_search_term)}
                ],
                temperature=AI_TEMPERATURE_BALANCED,  
                max_tokens=200 
            )
            
            parsed_suggestions = json.loads(llm_suggestion_response.choices[0].message.content)
            raw_suggestions = parsed_suggestions.get("suggestions", [])
            
            # 🛡️ Smart filter: Block dumb repetitive AI suggestions
            q_low = active_search_term.lower()
            
            for s in raw_suggestions:
                s_low = s.lower()
                
                # Rule 1: Don't repeat "for" if already in query
                if " for " in q_low and s_low.count(" for ") > q_low.count(" for "):
                    continue
                    
                # Rule 2: Don't slap "Cheap"/"Best" on long specific queries
                if word_count >= 3 and any(s_low.startswith(x) for x in ["cheap ", "best ", "branded "]):
                    continue
                
                ai_suggestions.append(s)
                if len(ai_suggestions) >= MAX_AUTOCOMPLETE_SUGGESTIONS:
                    break

        except Exception as e:
            logger.error(f"❌ AI Suggestion Error: {e}")
    
    # 6B. FAST MODE (or AI fallback): Use real product names from OpenSearch
    # Triggered when: short query OR AI returned nothing
    if not ai_suggestions:
        seen_names = set()
        for hit in hits:
            name = hit.get("_source", {}).get("name", "")
            images = hit.get("_source", {}).get("images", [])
            
            if name:
                clean_name = re.sub(r'[^a-zA-Z0-9\s\-]', '', name)
                short_name = " ".join(clean_name.split()[:5]).title()
                
                if short_name.lower() not in seen_names:
                    seen_names.add(short_name.lower())
                    ai_suggestions.append(short_name)
                    
                    t_url = extract_clean_image_url(images)
                    product_thumbs.append(t_url)
                    
                    if len(ai_suggestions) >= MAX_AUTOCOMPLETE_SUGGESTIONS:
                        break
    else:
        # AI gave good suggestions — get images from OpenSearch hits
        seen_thumbs = set()
        for hit in hits:
            images = hit.get("_source", {}).get("images", [])
            thumb_url = extract_clean_image_url(images)
            if thumb_url and thumb_url not in seen_thumbs:
                seen_thumbs.add(thumb_url)
                product_thumbs.append(thumb_url)
                if len(product_thumbs) >= len(ai_suggestions):
                    break
    
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
            # Safe highlight: Don't awkwardly bold the whole string if it's a real product name
            highlighted = suggestion 
        
        sidebar_html += f"""
        <div class='bclouds-side-item' onclick="{click_js}">
            <div style='display:flex; align-items:center; gap:14px;'>
                {icon_html}
                <span style="font-size: 15px;">{highlighted}</span>
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
    print(f"⏱️  AUTOCOMPLETE | query='{active_search_term}' | time={_elapsed_ms:.2f}ms | mode=full", flush=True)
    
    return final_response