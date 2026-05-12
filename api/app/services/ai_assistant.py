"""
=====================================================================================
🤖 AI ASSISTANT SERVICE (Chat Brain)
=====================================================================================
This file handles the AI chat assistant that refines user searches.

WORKFLOW:
  1. User types message in chat (like "show me red ones under 50")
  2. We send context (current query + filters + new message) to OpenAI
  3. OpenAI returns structured JSON:
     - intent: "refine" or "new_search"
     - updated filters
     - friendly reply message
  4. We apply interceptors (Apple always = tech brand, etc)
  5. We run the actual search with new filters
  6. If no results → drop filters step-by-step until we find something
  7. Return results + AI message + suggestions

ZERO DEAD END GUARANTEE:
  Even if every filter eliminates results, we fall back to basic search.
  User NEVER sees "0 results" page in AI chat.

FALLBACK CHAIN:
  Full filters → drop size/color/gender → drop brand → drop price → basic search
=====================================================================================
"""

import json
import logging
import re

# 🔥 EMOJI STRIPPER — removes all emojis from AI output
_EMOJI_PATTERN = re.compile(
    "[\U0001F300-\U0001F9FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U00002600-\U000027BF"
    "\U0001FA70-\U0001FAFF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "]+", flags=re.UNICODE
)

def strip_emojis(text):
    """Remove emojis/icons. Safe no-op for non-strings."""
    if not isinstance(text, str):
        return text
    return _EMOJI_PATTERN.sub('', text).strip()

# OpenAI client
from app.config import openai_client

# Models for request/response
from app.models.search import SearchRequest, AIAssistantResponse, Filters, PriceFilter

# The main search engine (we call it at the end)
from app.services.search_engine import execute_search

# AI prompt builder (we moved prompts to their own file)
from app.prompts.ai_assistant_prompt import build_ai_assistant_prompt

# Interceptors (Apple + Menswear fixes)
from app.nlp.interceptors import apply_menswear_interceptor, apply_apple_interceptor

# Constants
from app.core.constants import (
    AI_CHAT_MODEL,
    AI_TEMPERATURE_STRICT,
    MAX_AI_SUGGESTIONS,
    AI_BAD_WORDS
)

logger = logging.getLogger(__name__)


# =========================================================================
# 🤖 MAIN AI ASSISTANT FUNCTION
# =========================================================================
async def process_ai_assistant(
    chat_message: str,
    current_state: SearchRequest
) -> AIAssistantResponse:
    """
    Processes a user's AI chat message and returns refined search results.
    
    ARGS:
        chat_message: What user typed in chat (like "under 50")
        current_state: Current search state (query + filters + sort + page)
    
    RETURNS:
        AIAssistantResponse with:
            - All search results fields (products, pagination, facets)
            - ai_message: Friendly reply from AI
            - updated_query: New search query (for UI to update)
            - updated_filters: New filter state (for UI to update)
            - updated_sort: New sort order (if AI changed it)
            - suggestions: Follow-up suggestion chips
    """
    
    # =====================================================================
    # STEP 1: EXTRACT CURRENT FILTERS AS DICT
    # =====================================================================
    # Convert current filter object to dict for the AI prompt
    current_filters = (
        current_state.filters.model_dump() 
        if current_state.filters 
        else {}
    )
    
    # =====================================================================
    # STEP 2: BUILD THE AI PROMPT
    # =====================================================================
    # Uses our separated prompt file (easy to tune AI behavior)
    system_prompt = build_ai_assistant_prompt(
        current_query=current_state.query,
        current_filters=current_filters,
        chat_message=chat_message
    )
    
    # =====================================================================
    # STEP 3: CALL OPENAI API
    # =====================================================================
    try:
        llm_response = await openai_client.chat.completions.create(
            model=AI_CHAT_MODEL,
            # Force JSON response format (prevents AI from returning plain text)
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chat_message}
            ],
            # Temperature 0.0 = deterministic (same input → same output)
            # Important for filter extraction — we don't want random filters
            temperature=AI_TEMPERATURE_STRICT
        )
        
        # Parse AI's JSON response
        parsed_intent = json.loads(llm_response.choices[0].message.content)
        
        # =====================================================================
        # STEP 4: BUILD NEW SEARCH REQUEST
        # =====================================================================
        # AI tells us the new query (or keeps old one if just filtering)
        updated_request = SearchRequest(
            query=parsed_intent.get("search_query", current_state.query),
            page=1,                 # Always start at page 1 for new refinement
            page_size=10,           # AI results show 10 at a time (compact view)
            sort="best_matches"     # Reset sort to default
        )
        
        # =====================================================================
        # STEP 5: EXTRACT FILTERS FROM AI RESPONSE
        # =====================================================================
        extracted_filters = parsed_intent.get("filters", {})
        
        # Start with empty filter object
        new_filters_obj = Filters()
        new_filters_obj.color = []
        new_filters_obj.category = []
        new_filters_obj.brand = []
        new_filters_obj.size = []
        new_filters_obj.gender = []
        new_filters_obj.on_sale = extracted_filters.get("on_sale", False)
        
        # -----------------------------------------------------------------
        # CONTEXT PRESERVATION (for "refine" intent)
        # -----------------------------------------------------------------
        # If user is refining (not starting fresh), KEEP their existing filters
        # So "shoes red size 10" stays, and user adds "under 100" on top
        if parsed_intent.get("intent") == "refine" and current_state.filters:
            new_filters_obj.category = current_state.filters.category or []
            new_filters_obj.brand = current_state.filters.brand or []
            new_filters_obj.color = current_state.filters.color or []
            new_filters_obj.size = current_state.filters.size or []
            new_filters_obj.gender = getattr(current_state.filters, "gender", []) or []
            new_filters_obj.price = current_state.filters.price
            new_filters_obj.in_stock = current_state.filters.in_stock
            
            # Keep on_sale if it was already on AND AI didn't explicitly turn it off
            if (
                getattr(current_state.filters, "on_sale", False) 
                and extracted_filters.get("on_sale") is not False
            ):
                new_filters_obj.on_sale = True
        
        # =====================================================================
        # STEP 6: APPLY EACH EXTRACTED FILTER (with cleanup)
        # =====================================================================
        # We filter out AI "bad words" like "string", "example", "any"
        # These sometimes appear when AI misunderstands the user
        
        # ---------------------- COLOR ----------------------
        if extracted_filters.get("color"):
            colors = [
                str(c).lower() 
                for c in extracted_filters["color"] 
                if str(c).lower() not in AI_BAD_WORDS
            ]
            # Merge with existing colors (if any) using set to remove dupes
            new_filters_obj.color = list(set(new_filters_obj.color + colors))
        
        # ---------------------- SIZE ----------------------
        if extracted_filters.get("size"):
            sizes = [
                str(s).upper()  # Sizes are stored UPPERCASE in DB
                for s in extracted_filters["size"] 
                if str(s).lower() not in AI_BAD_WORDS
            ]
            new_filters_obj.size = list(set(new_filters_obj.size + sizes))
        
        # ---------------------- BRAND ----------------------
        if extracted_filters.get("brand"):
            brands = [
                str(b).upper()  # Brands are stored UPPERCASE in DB
                for b in extracted_filters["brand"] 
                if str(b).lower() not in AI_BAD_WORDS
            ]
            new_filters_obj.brand = list(set(new_filters_obj.brand + brands))
        
        # ---------------------- GENDER ----------------------
        if extracted_filters.get("gender"):
            genders = [
                str(g).lower() 
                for g in extracted_filters["gender"] 
                if str(g).lower() not in AI_BAD_WORDS
            ]
            new_filters_obj.gender = list(set(
                getattr(new_filters_obj, "gender", []) + genders
            ))
        
        # ---------------------- PRICE ----------------------
        # AI sometimes returns prices like "$50" or "50 dollars"
        # We aggressively clean them to get pure numbers
        if extracted_filters.get("price"):
            p_data = extracted_filters["price"]
            
            if isinstance(p_data, dict):
                try:
                    raw_min = p_data.get("min")
                    raw_max = p_data.get("max")
                    
                    # Parse min price
                    min_p = None
                    if raw_min is not None and str(raw_min).strip() not in ["", "null", "None"]:
                        # Strip all non-numeric chars (keeps digits and dots only)
                        clean_min = re.sub(r'[^\d.]', '', str(raw_min))
                        if clean_min:
                            min_p = float(clean_min)
                    
                    # Parse max price
                    max_p = None
                    if raw_max is not None and str(raw_max).strip() not in ["", "null", "None"]:
                        clean_max = re.sub(r'[^\d.]', '', str(raw_max))
                        if clean_max:
                            max_p = float(clean_max)
                    
                    # Only set price filter if we got at least one valid value
                    if min_p is not None or max_p is not None:
                        new_filters_obj.price = PriceFilter(min=min_p, max=max_p)
                        
                except Exception as e:
                    logger.error(f"AI Price extraction error: {e}")
        
        # =====================================================================
        # STEP 7: APPLY INTERCEPTORS (Bulletproof Fixes)
        # =====================================================================
        
        # ---------------- MENSWEAR INTERCEPTOR ----------------
        # Fixes: "men's dress" → "suits | dress shirts"
        menswear_result = apply_menswear_interceptor(
            query=updated_request.query,
            genders=getattr(new_filters_obj, "gender", []),
            ai_message=parsed_intent.get("ai_message", ""),
            suggestions=parsed_intent.get("suggestions", [])
        )
        # Update values (if interceptor didn't trigger, values are unchanged)
        updated_request.query = menswear_result["query"]
        parsed_intent["ai_message"] = menswear_result["ai_message"]
        parsed_intent["suggestions"] = menswear_result["suggestions"]
        
        # ---------------- APPLE INTERCEPTOR ----------------
        # Fixes: "apple" → force brand=Apple (tech company, not fruit)
        apple_result = apply_apple_interceptor(
            query=updated_request.query,
            ai_message=parsed_intent.get("ai_message", ""),
            suggestions=parsed_intent.get("suggestions", [])
        )
        # If Apple interceptor triggered, force the brand filter
        if apple_result["should_force_apple_brand"]:
            new_filters_obj.brand = ["Apple"]
            parsed_intent["ai_message"] = apple_result["ai_message"]
            parsed_intent["suggestions"] = apple_result["suggestions"]
        
        # =====================================================================
        # STEP 8: ATTACH FILTERS AND DETERMINE SORT
        # =====================================================================
        updated_request.filters = new_filters_obj
        
        # 🔥 EXTRACT SORT FROM AI (handles asc/desc/cheapest/newest/popular/rating)
        ai_sort = parsed_intent.get("sort", "best_matches")
        ALLOWED_SORTS = {"best_matches", "price_asc", "price_desc", "newest", "popularity", "rating", "on_sale"}
        if isinstance(ai_sort, str) and ai_sort in ALLOWED_SORTS:
            updated_request.sort = ai_sort
        
        # If user wants sale AND didn't pick another sort, default to on_sale ordering
        if new_filters_obj.on_sale and updated_request.sort == "best_matches":
            updated_request.sort = "on_sale"
        
        # =====================================================================
        # STEP 9: EXECUTE SEARCH (Primary Attempt)
        # =====================================================================
        final_results_dict = await execute_search(updated_request)
        
        # Track which filters we had to drop for fallback message
        dropped_filters = []
        
        # =====================================================================
        # STEP 10: ZERO-DEAD-END FALLBACK CHAIN
        # =====================================================================
        # If no results, progressively drop filters until we find something
        
        # ---------- FALLBACK 1: Drop size, color, gender ----------
        if (
            final_results_dict.get("total_results", 0) == 0 
            and (
                new_filters_obj.size 
                or new_filters_obj.color 
                or getattr(new_filters_obj, "gender", [])
            )
        ):
            # Track what we dropped for user-friendly message
            if new_filters_obj.size:
                dropped_filters.append("size")
            if new_filters_obj.color:
                dropped_filters.append("color")
            if getattr(new_filters_obj, "gender", []):
                dropped_filters.append("gender target")
            
            # Clear these filters
            new_filters_obj.size = []
            new_filters_obj.color = []
            new_filters_obj.gender = []
            updated_request.filters = new_filters_obj
            
            # Try search again
            final_results_dict = await execute_search(updated_request)
        
        # ---------- FALLBACK 2: Drop brand ----------
        if final_results_dict.get("total_results", 0) == 0 and new_filters_obj.brand:
            dropped_filters.append("brand")
            new_filters_obj.brand = []
            updated_request.filters = new_filters_obj
            final_results_dict = await execute_search(updated_request)
        
        # ---------- FALLBACK 3: Drop ALL filters (price too) ----------
        if final_results_dict.get("total_results", 0) == 0:
            dropped_filters.append("strict price limits")
            updated_request.filters = None  # Clear everything
            final_results_dict = await execute_search(updated_request)
        
        # =====================================================================
        # STEP 11: BUILD FINAL AI MESSAGE
        # =====================================================================
        # Remove any stray ai_message from search results (wrong place)
        if "ai_message" in final_results_dict:
            del final_results_dict["ai_message"]
        
        ai_reply = parsed_intent.get("ai_message", "")
        
        # If we dropped filters, explain to user (transparent UX)
        if dropped_filters:
            dropped_str = " or ".join(dropped_filters)
            ai_reply = (
                f"I couldn't find exact matches for that {dropped_str}, "
                f"but here are the best {updated_request.query.replace('|', ' and ')} "
                f"items we have in stock."
            )
        elif not ai_reply or not isinstance(ai_reply, str):
            # Fallback message if AI didn't provide one
            ai_reply = "Here are the matches I found."
        
        # 🔥 STRIP ANY EMOJIS the AI might have slipped in
        ai_reply = strip_emojis(ai_reply)
        
        # =====================================================================
        # STEP 12: PREPARE SUGGESTIONS
        # =====================================================================
        suggestions = parsed_intent.get("suggestions", [])
        
        # Fallback suggestions if AI returned garbage
        if not isinstance(suggestions, list):
            suggestions = [
                "Show me shoes",
                "Find jackets",
                "I'm looking for bags"
            ]
        
        # 🔥 STRIP EMOJIS from every suggestion chip
        suggestions = [strip_emojis(s) if isinstance(s, str) else s for s in suggestions]
        
        # =====================================================================
        # STEP 13: CLEAN QUERY FOR UI DISPLAY
        # =====================================================================
        # Convert internal "|" separator to natural "and" for display
        # "macbook | iphone" → "macbook and iphone" (nicer to show user)
        clean_ui_query = updated_request.query.replace("|", " and ")
        
        # =====================================================================
        # STEP 14: BUILD FINAL RESPONSE
        # =====================================================================
        return AIAssistantResponse(
            **final_results_dict,  # Spread all search result fields
            ai_message=ai_reply,
            updated_query=clean_ui_query,
            updated_filters=new_filters_obj.model_dump(),
            updated_sort=updated_request.sort,
            # Cap suggestions at max allowed (4)
            suggestions=suggestions[:MAX_AI_SUGGESTIONS]
        )
    
    except Exception as e:
        # =====================================================================
        # SAFETY NET: Something went wrong
        # =====================================================================
        # Don't crash! Return results from user's CURRENT state (no change)
        # So user at least sees their existing search
        logger.error(f"❌ AI Assistant Processing Error: {e}")
        
        fail_results = await execute_search(current_state)
        
        # Remove any stray ai_message
        if "ai_message" in fail_results:
            del fail_results["ai_message"]
        
        return AIAssistantResponse(
            **fail_results,
            ai_message="Sorry, I encountered an error.",
            suggestions=["Show me shoes", "I'm looking for bags"]
        )