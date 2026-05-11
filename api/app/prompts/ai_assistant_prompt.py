"""
=====================================================================================
🤖 AI ASSISTANT PROMPT (Chat Refinement Brain)
=====================================================================================
This file contains the INSTRUCTIONS we give to OpenAI when user chats with
our AI search assistant.

WHY THIS FILE EXISTS:
- Prompts are the "soul" of AI behavior — small changes have BIG effects
- Keeping them separate makes tuning easier
- You can A/B test different prompts without touching logic

WHEN THIS PROMPT IS USED:
Every time user types in the AI chat panel, like:
  - "show me red ones"           (refine current search)
  - "under $50"                  (refine current search)
  - "actually show me iphones"   (new search)
=====================================================================================
"""

import json


def build_ai_assistant_prompt(
    current_query: str,
    current_filters: dict,
    chat_message: str
) -> str:
    """
    Builds the system prompt for the AI chat assistant.
    
    ARGS:
        current_query: What user was searching before (like "shoes")
        current_filters: Currently applied filters (dict)
        chat_message: What user just typed in chat
    
    RETURNS:
        str: Full system prompt ready to send to OpenAI
    
    EXAMPLE:
        build_ai_assistant_prompt(
            current_query="shoes",
            current_filters={"color": ["red"]},
            chat_message="under 100"
        )
        → Returns a long string starting with "You are the venue AI..."
    """
    
    return f"""
    You are the venue AI, an intelligent e-commerce shopping assistant.
    
    CURRENT SEARCH CONTEXT:
    - User is currently searching for: "{current_query}"
    - Active Filters applied: {json.dumps(current_filters)}

    NEW USER MESSAGE: "{chat_message}"

    YOUR TASK:
    Analyze the message and decide if the user wants to REFINE their current search or start a completely NEW SEARCH.

    🔥 CRITICAL LOGIC RULES:
    1. FILTERING (Refine): If the user types a color, size, price (e.g., "under 50"), or GENDER and DOES NOT name a completely different product, set intent to "refine". KEEP the 'search_query' exactly as "{current_query}" and extract the variables into the filters array.
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
        "ai_message": "Friendly 1-sentence reply in plain text. NEVER use emojis, icons, or unicode symbols.",
        "suggestions": ["Follow-up query 1", "Follow-up query 2", "Follow-up query 3"]
    }}
    """