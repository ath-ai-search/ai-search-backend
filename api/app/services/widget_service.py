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
  2. Run quick OpenSearch query ONLY to extract product thumbnails
     (thumbnails are mixed into suggestions for visual richness)
  3. Generate AI-powered autocomplete suggestions
  4. Build sidebar HTML with suggestions + bold highlighting
  5. Load template files and fill placeholders
  6. Return final HTML string

WHY WE STILL RUN OPENSEARCH:
  Even though we don't show products, we use their thumbnails
  as icons for some suggestions (makes dropdown more engaging).
  This is a BACKGROUND task — user doesn't see the products.

SPECIAL FEATURES:
  - Competitor interceptor (Best Buy → TVs, Amazon → MacBooks)
  - Empty search fallback → "luxury sunglasses" default
  - Recent searches integration (uses user's last search if empty)
=====================================================================================
"""

import os
import json
import time
import logging

# External clients
from app.config import os_client, INDEX_NAME, openai_client

# NLP brain
from app.nlp.semantic_matrix import extract_semantic_matrix

# AI prompts (separated)
from app.prompts.autocomplete_suggestions_prompt import (
    AUTOCOMPLETE_SYSTEM_PROMPT,
    build_autocomplete_user_prompt,
    build_fallback_suggestions,
)

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
)

logger = logging.getLogger(__name__)


# =========================================================================
# 📂 TEMPLATE FILE LOADER (Cached at Module Load)
# =========================================================================
# We load template files ONCE when module starts (not per request)
# This saves disk I/O on every widget request

# Path to templates folder: api/app/templates/mega_menu/
TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
    "mega_menu"
)


def _load_template_file(filename: str) -> str:
    """
    Loads a template file from disk.
    
    ARGS:
        filename: Name of file in templates/mega_menu/ folder
    
    RETURNS:
        str: File contents as string
    """
    filepath = os.path.join(TEMPLATE_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"❌ Failed to load template '{filename}': {e}")
        return ""


# Load all template files ONCE at startup
# These stay in memory for entire server lifetime (fast!)
MEGA_MENU_TEMPLATE = _load_template_file("template.html")
MEGA_MENU_STYLES = _load_template_file("styles.css")
MEGA_MENU_SCRIPTS = _load_template_file("scripts.js")


# =========================================================================
# 🌐 MAIN WIDGET FUNCTION
# =========================================================================
async def get_mega_menu_widget(query_string: str, recent_searches: str = "") -> dict:
    """
    Generates the Amazon-style autocomplete dropdown HTML.
    
    ARGS:
        query_string: What user is typing (or "" if empty)
        recent_searches: Pipe-separated recent searches ("query1||query2||query3")
    
    RETURNS:
        dict: {"html": "<style>...</style><div>...suggestions...</div>..."}
    """
    
    # 🆕 START TIMING
    _start_time = time.perf_counter()
    
    # =====================================================================
    # STEP 1: CLEAN AND PARSE INPUT
    # =====================================================================
    clean_query = query_string.strip().lower()
    
    # Special case: "*" means "empty/wildcard" from some frontends
    if clean_query == "*":
        clean_query = ""
    
    # =====================================================================
    # STEP 2: PARSE RECENT SEARCHES
    # =====================================================================
    # Frontend sends history as "search1||search2||search3" (pipe-separated)
    # We take first 3 only, skip empty/invalid ones
    recent_list = recent_searches.split("||")[:3] if recent_searches else []
    valid_recents = [
        r.strip()
        for r in recent_list
        if r.strip() and r.strip().lower() not in ["null", "undefined", "[]", ""]
    ]
    
    # =====================================================================
    # STEP 3: DETERMINE ACTIVE SEARCH TERM
    # =====================================================================
    # Priority: current typing > most recent search > default fallback
    active_search_term = clean_query
    
    # If search is empty BUT user has history, use their most recent search
    if not active_search_term and valid_recents:
        active_search_term = valid_recents[0].lower()
    
    # 🆕 NEW USER WITH NO HISTORY: Return empty response (no suggestions)
    # Old behavior: showed "luxury sunglasses" default — confused users
    # New behavior: show NOTHING until user types or has history
    if not active_search_term:
        _elapsed_ms = (time.perf_counter() - _start_time) * 1000
        print(f"⏱️  AUTOCOMPLETE | query='(empty)' | recents={len(valid_recents)} | time={_elapsed_ms:.2f}ms | mode=empty", flush=True)
        return {"html": ""}
    
    # =====================================================================
    # STEP 4: COMPETITOR INTERCEPTOR
    # =====================================================================
    # If user types competitor name, redirect to a relevant product category
    # Smart move — prevents showing "nothing found" for competitor names
    if active_search_term == "best buy":
        active_search_term = "tv"
    elif active_search_term == "amazon":
        active_search_term = "macbook"
    
    # =====================================================================
    # STEP 5: GENERATE VECTOR EMBEDDING
    # =====================================================================
    # For semantic KNN search (finds products with similar MEANING)
    # We use this to get relevant product thumbnails for suggestion icons
    vector = None
    try:
        resp = await openai_client.embeddings.create(
            input=active_search_term,
            model=AI_EMBEDDING_MODEL
        )
        vector = resp.data[0].embedding
    except Exception as e:
        # OpenAI down? Continue without vector (keyword search still works)
        logger.warning(f"⚠️ Widget embedding failed: {e}")
    
    # =====================================================================
    # STEP 6: EXTRACT SEMANTIC MATRIX
    # =====================================================================
    # Parse price, sale intent, etc from the search term
    matrix = extract_semantic_matrix(active_search_term)
    core_query = matrix["core_query"]
    
    # =====================================================================
    # STEP 7: BUILD OPENSEARCH FILTERS (for thumbnail fetch)
    # =====================================================================
    # We query products JUST to get their thumbnails for the sidebar
    # User never sees these products as cards — only as icons
    filters = [{"term": {"in_stock": True}}]
    must_nots = []
    
    # Apply price range if user specified (e.g. "tv under 500")
    if matrix["min_price"] is not None or matrix["max_price"] is not None:
        price_range = {}
        if matrix["min_price"] is not None:
            price_range["gte"] = matrix["min_price"]
        if matrix["max_price"] is not None:
            price_range["lte"] = matrix["max_price"]
        filters.append({"range": {"price": price_range}})
    
    # Apply sale filter if user wants sale items
    if matrix["is_sale"]:
        filters.append({"range": {"sale_price": {"gt": 0}}})
    
    # =====================================================================
    # STEP 8: BUILD SCORING (BOOST) CLAUSES
    # =====================================================================
    # High boosts for precise matching (we only need top 10 for thumbnails)
    semantic_shoulds = []
    
    # KNN semantic search
    if vector:
        semantic_shoulds.append({
            "knn": {
                "embedding": {
                    "vector": vector,
                    "k": KNN_MIN_K
                }
            }
        })
    
    # HIGH-VALUE BOOSTS: Brand, Category, Name matches
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
    
    # General multi-field match
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
    # If user wants "iphone", demote iPhone cases in results
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
    # STEP 10: FINAL OPENSEARCH QUERY (for thumbnails only)
    # =====================================================================
    # We only need images — skip all other fields for speed
    os_query = {
        "size": 10,  # Need max 10 thumbnails for suggestions
        "_source": ["images"],  # Only fetch images (much faster!)
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
    # STEP 11: EXECUTE SEARCH (background — for thumbnails)
    # =====================================================================
    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
        hits = response.get("hits", {}).get("hits", [])
    except Exception as e:
        logger.error(f"❌ OpenSearch Widget Error: {e}")
        hits = []
    
    # =====================================================================
    # STEP 12: GENERATE AI-POWERED AUTOCOMPLETE SUGGESTIONS
    # =====================================================================
    # This is the MAIN content shown to the user
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
            temperature=AI_TEMPERATURE_BALANCED,  # 0.4 = balanced creativity
            max_tokens=400
        )
        
        parsed_suggestions = json.loads(llm_suggestion_response.choices[0].message.content)
        ai_suggestions = parsed_suggestions.get("suggestions", [])[:MAX_AUTOCOMPLETE_SUGGESTIONS]
    except Exception as e:
        logger.error(f"❌ AI Suggestion Error: {e}")
        # Use fallback suggestions (template-based)
        ai_suggestions = build_fallback_suggestions(active_search_term)
    
    # =====================================================================
    # STEP 13: COLLECT PRODUCT THUMBNAILS FOR SIDEBAR ICONS
    # =====================================================================
    # We mix product thumbnails INTO some suggestions (visual richness)
    # Like Amazon shows a Nike logo next to "shoes for woman"
    product_thumbs = []
    seen_thumbs = set()
    
    for hit in hits:
        source = hit.get("_source", {})
        images = source.get("images", [])
        thumb = images[0] if isinstance(images, list) and images else None
        
        # Avoid duplicate thumbnails in different suggestions
        if thumb and thumb not in seen_thumbs:
            seen_thumbs.add(thumb)
            product_thumbs.append(thumb)
            
            # Stop collecting once we have enough for all suggestions
            if len(product_thumbs) >= len(ai_suggestions):
                break
    
    # =====================================================================
    # STEP 14: BUILD SIDEBAR HTML (AI Suggestions — Amazon Style)
    # =====================================================================
    sidebar_html = ""
    thumb_used = 0
    
    for i, suggestion in enumerate(ai_suggestions):
        # Escape single quotes for safe JS embedding
        safe_suggestion = suggestion.replace("'", "\\'")
        
        # Build JS click handler
        # 1. Fill search bar with suggestion
        # 2. Click search button OR fall back to URL redirect
        click_js = (
            f"document.getElementById('search_query').value='{safe_suggestion}'; "
            f"const btn=document.getElementById('searchBtn'); "
            f"if(btn) btn.click(); "
            f"else window.location.href='/search.php?search_query={safe_suggestion}&section=content';"
        )
        
        # Use product thumbnail if available, else fallback to search icon
        if thumb_used < len(product_thumbs):
            thumb_url = product_thumbs[thumb_used]
            thumb_used += 1
            icon_html = (
                f'<img src="{thumb_url}" style="width:24px; height:24px; '
                f'object-fit:contain; border-radius:3px; flex-shrink:0;">'
            )
        else:
            # Amazon uses a magnifying glass icon for most suggestions
            icon_html = (
                '<i class="fas fa-search" style="color:#9ca3af; '
                'width:24px; font-size: 14px; text-align:center; display:inline-block;"></i>'
            )
        
        # Bold the REST of the suggestion (Amazon-style)
        # User typed "shoe" and suggestion is "shoes for men"
        # Result: shoe<b>s for men</b> (typed part normal, rest bold)
        # This guides user's eye to what's being ADDED to their search
        q = active_search_term.lower()
        s_lower = suggestion.lower()
        
        if q in s_lower:
            idx = s_lower.index(q)
            highlighted = (
                f"{suggestion[:idx+len(q)]}" +           # Normal (typed part)
                f"<b>{suggestion[idx+len(q):]}</b>"      # Bold (rest)
            )
        else:
            # No match found (rare) — bold entire suggestion
            highlighted = f"<b>{suggestion}</b>"
        
        # Build sidebar item HTML (Amazon-style row)
        sidebar_html += f"""
        <div class='bclouds-side-item' onclick="{click_js}">
            <div style='display:flex; align-items:center; gap:14px;'>
                {icon_html}
                <span style="font-size: 15px;">{highlighted}</span>
            </div>
        </div>
        """
    
# =====================================================================
    # STEP 15: ASSEMBLE FINAL HTML FROM TEMPLATE
    # =====================================================================
    # Fill placeholders in our template with real content
    # 
    # We use .replace() instead of .format() because:
    #   - CSS contains { } characters (like: .class { color: red; })
    #   - JS contains { } characters (like: function() { return x; })
    #   - .format() would try to parse these as placeholders → CRASH
    #   - .replace() only replaces EXACT strings we specify → SAFE
    #
    # Placeholder format: __NAME__
    #   - Valid inside CSS (treated as unknown token, harmless)
    #   - Valid inside JS (treated as identifier, harmless)
    #   - VS Code doesn't show false errors on template.html
    
    master_html = MEGA_MENU_TEMPLATE
    master_html = master_html.replace("__STYLES__", MEGA_MENU_STYLES)
    master_html = master_html.replace("__SCRIPTS__", MEGA_MENU_SCRIPTS)
    master_html = master_html.replace("__SIDEBAR__", sidebar_html)
    
# 🆕 LOG TIMING
    _elapsed_ms = (time.perf_counter() - _start_time) * 1000
    print(f"⏱️  AUTOCOMPLETE | query='{active_search_term}' | recents={len(valid_recents)} | time={_elapsed_ms:.2f}ms | mode=full", flush=True)
    
    return {"html": master_html}