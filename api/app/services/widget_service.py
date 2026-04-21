"""
=====================================================================================
🌐 MEGA MENU WIDGET SERVICE
=====================================================================================
This file generates the HTML for the search dropdown mega menu widget.

WORKFLOW:
  1. Determine "active search term" (user's query OR recent OR default)
  2. Generate vector embedding for semantic search
  3. Build OpenSearch query with WIDGET-SPECIFIC high boosts
  4. Execute search to get top 10 products
  5. Generate AI-powered autocomplete suggestions
  6. Build products HTML (product cards)
  7. Build sidebar HTML (AI suggestions with thumbnails)
  8. Load template files and fill placeholders
  9. Return final HTML string

WHY WIDGET USES HIGHER BOOSTS:
  Widget shows only 10 results — must be SUPER relevant.
  Main search uses boost=100 for name, widget uses boost=500.
  Main search uses boost=300 for brand, widget uses boost=5000.

SPECIAL FEATURES:
  - Competitor interceptor (Best Buy → TVs, Amazon → MacBooks)
  - Empty search fallback → "luxury sunglasses" default
  - Recent searches integration (uses user's last search if empty)
=====================================================================================
"""

import os
import logging

# External clients
from app.config import os_client, INDEX_NAME, openai_client

# Our utilities
from app.utils.brand_mapper import get_smart_brand

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
    WIDGET_TOP_CATEGORIES_SIZE,
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
    Generates the mega menu dropdown HTML.
    
    ARGS:
        query_string: What user is typing (or "" if empty)
        recent_searches: Pipe-separated recent searches ("query1||query2||query3")
    
    RETURNS:
        dict: {"html": "<style>...</style><div>...products...</div>..."}
    """
    
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
    
    # Absolute fallback: New user with empty search and no history
    # We show "luxury sunglasses" — a safe, aesthetic default
    if not active_search_term:
        active_search_term = DEFAULT_SEARCH_TERM
    
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
    # STEP 7: BUILD OPENSEARCH FILTERS
    # =====================================================================
    # Always filter for in-stock products
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
    # Widget uses MUCH HIGHER boosts than main search
    # Why? Widget shows only 10 items — must be precise
    semantic_shoulds = []
    
    # KNN semantic search
    if vector:
        semantic_shoulds.append({
            "knn": {
                "embedding": {
                    "vector": vector,
                    "k": KNN_MIN_K  # Fixed 200 neighbors for widget
                }
            }
        })
    
    # HIGH-VALUE BOOST: Brand exact match (boost: 5000)
    # If user's query matches a brand exactly, this wins everything
    semantic_shoulds.extend([
        {
            "match_phrase": {
                "brand": {
                    "query": core_query,
                    "boost": WIDGET_BOOST_BRAND
                }
            }
        },
        # Category match (boost: 3000)
        {
            "match": {
                "category": {
                    "query": core_query,
                    "boost": WIDGET_BOOST_CATEGORY
                }
            }
        },
        # Name phrase match (boost: 500)
        {
            "match_phrase": {
                "name": {
                    "query": core_query,
                    "boost": WIDGET_BOOST_NAME
                }
            }
        }
    ])
    
    # General multi-field match (boost: 5)
    # Fallback for natural language queries
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
    # If user wants "iphone", demote iPhone cases in widget results
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
        "size": 10,  # Widget shows max 10 products
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
        # Aggregations: top 6 categories for potential UI display
        "aggs": {
            "top_categories": {
                "terms": {
                    "field": "category",
                    "size": WIDGET_TOP_CATEGORIES_SIZE
                }
            }
        }
    }
    
    # =====================================================================
    # STEP 11: EXECUTE SEARCH
    # =====================================================================
    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
        hits = response.get("hits", {}).get("hits", [])
        total_products = response.get("hits", {}).get("total", {}).get("value", 0)
    except Exception as e:
        logger.error(f"❌ OpenSearch Mega Menu Error: {e}")
        hits = []
        total_products = 0
    
    # =====================================================================
    # STEP 12: BUILD PRODUCTS HTML
    # =====================================================================
    products_html = ""
    dynamic_brands_set = set()  # Collect unique brands seen
    
    if not hits:
        # No results fallback
        products_html = "<div style='padding: 20px; color: #666;'>No products found.</div>"
    else:
        for hit in hits:
            source = hit.get("_source", {})
            name = source.get("name", "Unknown Product")
            prod_url = source.get("url", "#")
            
            # Get smart brand (fallback-detected if missing)
            brand_display = get_smart_brand(source)
            if brand_display != "UNKNOWN":
                dynamic_brands_set.add(brand_display)
            
            # Price handling (with sale detection)
            price = float(source.get("price", 0.0))
            raw_sale = source.get("sale_price")
            sale_price = float(raw_sale) if raw_sale is not None else 0.0
            
            # Get primary image or use placeholder
            images = source.get("images", [])
            img_url = (
                images[0] 
                if isinstance(images, list) and images 
                else "https://placehold.co/100x100?text=No+Image"
            )
            
            # Build badge + price HTML (show SALE badge if on sale)
            if sale_price > 0 and sale_price < price:
                badge_html = (
                    '<div style="position: absolute; top: -6px; right: -6px; '
                    'background: #CC0000; color: white; font-size: 9px; '
                    'font-weight: bold; padding: 2px 6px; border-radius: 3px; '
                    'z-index: 10; text-transform: uppercase; letter-spacing: 0.5px;">'
                    'Sale</div>'
                )
                price_html = (
                    f'<div class="bclouds-prod-price">'
                    f'<span style="color: #CC0000; font-weight: 800;">${sale_price:.2f}</span> '
                    f'<del style="color: #888; font-size: 13px; font-weight: 600; margin-left: 4px;">'
                    f'${price:.2f}</del></div>'
                )
            else:
                badge_html = ""
                price_html = f'<div class="bclouds-prod-price">${price:.2f}</div>'
            
            # Build product card HTML
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
    
    # =====================================================================
    # STEP 13: GENERATE AI-POWERED AUTOCOMPLETE SUGGESTIONS
    # =====================================================================
    # Replaces old "recent searches" + "popular searches" with AI-generated
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
        
        import json
        parsed_suggestions = json.loads(llm_suggestion_response.choices[0].message.content)
        ai_suggestions = parsed_suggestions.get("suggestions", [])[:MAX_AUTOCOMPLETE_SUGGESTIONS]
    except Exception as e:
        logger.error(f"❌ AI Suggestion Error: {e}")
        # Use fallback suggestions (template-based)
        ai_suggestions = build_fallback_suggestions(active_search_term)
    
    # =====================================================================
    # STEP 14: COLLECT PRODUCT THUMBNAILS FOR SIDEBAR
    # =====================================================================
    # We mix product thumbnails INTO the AI suggestions (visual richness)
    # Each suggestion shows a real product thumbnail when possible
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
    # STEP 15: BUILD SIDEBAR HTML (AI Suggestions)
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
            icon_html = (
                '<i class="fas fa-search" style="color:#9ca3af; '
                'width:24px; font-size: 14px; text-align:center; display:inline-block;"></i>'
            )
        
        # Bold the user's typed portion within the suggestion
        # E.g., user typed "shoe" and suggestion is "shoes for men"
        # Result: <b>shoe</b>s for men (user sees highlight of match)
        q = active_search_term.lower()
        s_lower = suggestion.lower()
        
        if q in s_lower:
            idx = s_lower.index(q)
            highlighted = (
                f"<b>{suggestion[:idx+len(q)]}</b>" +
                suggestion[idx+len(q):]
            )
        else:
            # No match found (rare) — bold entire suggestion
            highlighted = f"<b>{suggestion}</b>"
        
        # Build sidebar item HTML
        sidebar_html += f"""
        <div class='bclouds-side-item' onclick="{click_js}">
            <div style='display:flex; align-items:center; gap:14px;'>
                {icon_html}
                <span style="font-size: 15px;">{highlighted}</span>
            </div>
        </div>
        """
    
    # =====================================================================
    # STEP 16: BUILD "SEE ALL" LINK
    # =====================================================================
    see_all_text = ""
    if total_products > 0:
        safe_query = active_search_term if active_search_term != "*" else ""
        see_all_text = (
            f'<span onclick=\'document.getElementById("search_query").value="{safe_query}"; '
            f'document.getElementById("searchBtn").click();\'>'
            f'See all {total_products:,} results &rarr;</span>'
        )
    
# =====================================================================
    # STEP 17: ASSEMBLE FINAL HTML FROM TEMPLATE
    # =====================================================================
    # Fill placeholders in our template with real content
    # 
    # We use .replace() instead of .format() because:
    #   - CSS contains { } characters (like: .class { color: red; })
    #   - JS contains { } characters (like: function() { return x; })
    #   - .format() would try to parse these as placeholders → CRASH
    #   - .replace() only replaces EXACT strings we specify → SAFE
    
    master_html = MEGA_MENU_TEMPLATE
    master_html = master_html.replace("<!--STYLES_PLACEHOLDER-->", MEGA_MENU_STYLES)
    master_html = master_html.replace("<!--SCRIPTS_PLACEHOLDER-->", MEGA_MENU_SCRIPTS)
    master_html = master_html.replace("<!--SIDEBAR_PLACEHOLDER-->", sidebar_html)
    master_html = master_html.replace("<!--PRODUCTS_PLACEHOLDER-->", products_html)
    master_html = master_html.replace("<!--SEE_ALL_PLACEHOLDER-->", see_all_text)
    
    return {"html": master_html}