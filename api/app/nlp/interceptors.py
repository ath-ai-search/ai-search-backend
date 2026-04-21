"""
=====================================================================================
🛡️ INTERCEPTORS — Bulletproof Query Fixers
=====================================================================================
This file fixes TRICKY query problems where AI might misunderstand.

WHY WE NEED INTERCEPTORS:
AI chatbots sometimes get confused with ambiguous words. Examples:
  - "Apple" → fruit or tech company?
  - "Men's Dress" → women's dress with male model? Or menswear?
  - "Watch" → wrist watch, or verb "to watch"?

Interceptors catch these edge cases AFTER the AI processes the query,
but BEFORE we send it to OpenSearch.

CURRENT INTERCEPTORS:
  1. Menswear Interceptor — "Men's Dress" → "Suits + Dress Shirts"
  2. Apple Interceptor — "Apple" always means the tech brand
=====================================================================================
"""


def apply_menswear_interceptor(
    query: str, 
    genders: list, 
    ai_message: str, 
    suggestions: list
) -> dict:
    """
    Fixes the 'Men's Dress' problem.
    
    THE PROBLEM:
    If a man searches "dress" with gender=men, our system might return:
      - Dress SOCKS (because they have "dress" in name)
      - Dress SHIRTS
      - Women's dresses (accidentally)
    
    THE FIX:
    Force-rewrite the query to "suits | dress shirts" — what men ACTUALLY want
    when they say "dress" (formal wear).
    
    ARGS:
        query: The current search query (like "dress")
        genders: List of gender filters (like ["men"])
        ai_message: Current AI response message
        suggestions: Current AI follow-up suggestions
    
    RETURNS:
        dict with possibly-updated query, ai_message, and suggestions
        If interceptor doesn't trigger, returns original values unchanged
    """
    
    # Normalize gender list to lowercase strings
    clean_genders = [str(g).lower() for g in genders]
    
    # Check if user is male (handles "men", "mens", "male" variations)
    is_male = any(g in ["men", "mens", "male"] for g in clean_genders)
    
    # TRIGGER CONDITION: query contains "dress" AND user is male
    if "dress" in query.lower() and is_male:
        # INTERCEPT! Rewrite query to what men actually want
        return {
            "query": "suits | dress shirts",  # The "|" means multi-item search
            "ai_message": "Let's find some sharp men's formal wear! 👔✨",
            "suggestions": [
                "Show me men's suits",
                "Looking for dress shirts",
                "Find formal ties"
            ]
        }
    
    # No interception needed — return original values
    return {
        "query": query,
        "ai_message": ai_message,
        "suggestions": suggestions
    }


def apply_apple_interceptor(
    query: str, 
    ai_message: str, 
    suggestions: list
) -> dict:
    """
    Fixes the 'Apple' ambiguity problem.
    
    THE PROBLEM:
    If user types "Apple", AI might think:
      - The fruit
      - Apple-flavored products
      - Random products with "apple" in description
    
    THE FIX:
    Force-set brand filter to "Apple" (tech company) so we only return
    iPhones, MacBooks, iPads, AirPods, etc.
    
    EXCEPTION:
    If user wants accessories (case, cover, charger) — don't force Apple brand,
    because they might want a generic charger that works with Apple.
    
    ARGS:
        query: The current search query (like "iphone", "apple", "macbook")
        ai_message: Current AI response message
        suggestions: Current AI follow-up suggestions
    
    RETURNS:
        dict with:
            - should_force_apple_brand: True/False — caller uses this to set filter
            - ai_message: Updated message
            - suggestions: Updated suggestions
    """
    
    clean_q = query.lower()
    
    # Check if query is an Apple device name (iphone, macbook, etc)
    is_apple_device = any(
        x in clean_q 
        for x in ["iphone", "macbook", "ipad", "apple watch", "apple tv", "iphones"]
    )
    
    # Check if query is literally just "apple"
    is_apple_brand = clean_q == "apple"
    
    # Check if user wants accessories (case, charger, cable, etc)
    is_accessory = any(
        x in clean_q 
        for x in ["case", "cover", "charger", "cable", "protector", "accessories"]
    )
    
    # TRIGGER CONDITION: Apple-related query AND NOT looking for accessories
    if (is_apple_device or is_apple_brand) and not is_accessory:
        
        # Customize message based on what exactly they searched
        if is_apple_brand:
            # They just typed "apple" — show full Apple product range
            new_message = "Here are the best Apple products we have in stock! 🍏✨"
            new_suggestions = [
                "Show me iPhones",
                "Looking for MacBooks",
                "Check out iPads"
            ]
        else:
            # They typed specific product (iphone, macbook, etc)
            new_message = f"Exciting choice! Searching for the best {query} items for you! 📱✨"
            new_suggestions = suggestions  # Keep AI's original suggestions
        
        return {
            "should_force_apple_brand": True,  # Caller should set brand=["Apple"]
            "ai_message": new_message,
            "suggestions": new_suggestions
        }
    
    # No interception needed
    return {
        "should_force_apple_brand": False,
        "ai_message": ai_message,
        "suggestions": suggestions
    }