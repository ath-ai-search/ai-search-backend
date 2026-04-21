"""
=====================================================================================
🔮 AUTOCOMPLETE SUGGESTIONS PROMPT (Mega Menu Brain)
=====================================================================================
This file contains the AI prompt for generating autocomplete suggestions
in the mega menu dropdown.

EXAMPLE:
  User types: "shoes"
  AI generates: [
    "shoes for men",
    "shoes for women", 
    "running shoes",
    "nike shoes",
    "shoes on sale",
    ...
  ]

THESE SUGGESTIONS HELP USERS:
- Discover related searches
- Find deals ("shoes on sale")
- Narrow their intent ("shoes for men")
- Explore brands ("nike shoes")
=====================================================================================
"""


# =========================================================================
# 🎯 SYSTEM PROMPT (How AI should behave)
# =========================================================================
# This tells OpenAI: "You are an autocomplete engine, return JSON array of 10 strings"

AUTOCOMPLETE_SYSTEM_PROMPT = (
    "You are an e-commerce search autocomplete engine. "
    "Generate realistic, diverse search query completions. "
    "Return ONLY valid JSON with a 'suggestions' key containing an array of exactly 10 short strings."
)


def build_autocomplete_user_prompt(search_term: str) -> str:
    """
    Builds the USER prompt telling AI what to autocomplete.
    
    ARGS:
        search_term: What user typed (or default term for empty search)
    
    RETURNS:
        str: User prompt for OpenAI
    
    EXAMPLE:
        build_autocomplete_user_prompt("shoes")
        → "Generate 10 autocomplete search suggestions for: 'shoes'..."
    """
    
    return (
        f'Generate 10 autocomplete search suggestions for: "{search_term}". '
        'Include variations like "for men", "for women", "kids", specific popular brands, '
        'style types, or use cases. Keep each suggestion short and natural.'
    )


def build_fallback_suggestions(search_term: str) -> list:
    """
    Generates fallback suggestions if OpenAI API fails.
    
    These are BASIC template-based suggestions that always work.
    Not as good as AI-generated, but better than nothing.
    
    ARGS:
        search_term: What user typed
    
    RETURNS:
        list: 7 fallback suggestion strings
    
    EXAMPLE:
        build_fallback_suggestions("shoes")
        → [
            "shoes for men",
            "shoes for women",
            "shoes kids",
            "best shoes",
            "shoes on sale",
            "branded shoes",
            "cheap shoes"
          ]
    """
    
    return [
        f"{search_term} for men",
        f"{search_term} for women",
        f"{search_term} kids",
        f"best {search_term}",
        f"{search_term} on sale",
        f"branded {search_term}",
        f"cheap {search_term}",
    ]