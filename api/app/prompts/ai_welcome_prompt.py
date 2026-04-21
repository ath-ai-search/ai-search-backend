"""
=====================================================================================
👋 AI WELCOME PROMPT (First-Hello Generator)
=====================================================================================
This file contains the instruction for OpenAI to generate a welcome message
when user opens the AI chat panel.

TWO SCENARIOS:
1. User has empty search → Generic welcome like "Welcome! Ready to explore? ✨"
2. User was searching "shoes" → Contextual welcome like 
   "I see you're looking at shoes! Want help finding specific styles? 👟"

WHY CONTEXTUAL WELCOMES MATTER:
- Makes user feel the AI "understands" them
- Provides better follow-up suggestions
- Increases engagement with AI assistant
=====================================================================================
"""


def build_ai_welcome_prompt(current_query: str) -> str:
    """
    Builds the system prompt for the AI welcome message generator.
    
    ARGS:
        current_query: What user was searching (empty "" if fresh)
    
    RETURNS:
        str: Full system prompt for OpenAI
    
    EXAMPLE:
        build_ai_welcome_prompt("shoes")
        → Prompt that asks AI to welcome user and suggest shoe-related follow-ups
        
        build_ai_welcome_prompt("")
        → Prompt that asks AI to give a general welcome
    """
    
    return f"""
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


# =========================================================================
# 🛟 FALLBACK CONTENT (if OpenAI fails)
# =========================================================================
# If OpenAI API is down or errors out, we use these defaults
# so user ALWAYS sees a welcome message

WELCOME_FALLBACK_MESSAGE = "Welcome to venue! Ready to explore some great finds? 🛍️"

WELCOME_FALLBACK_SUGGESTIONS = [
    "Show me dresses",
    "Find shoes",
    "Looking for bags"
]

# Default welcome if AI returns malformed response
WELCOME_DEFAULT_MESSAGE = "Welcome to venue! How can I help you today? ✨"

WELCOME_DEFAULT_SUGGESTIONS = [
    "Show me new arrivals",
    "Find shoes",
    "I need a dress"
]