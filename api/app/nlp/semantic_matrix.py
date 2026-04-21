"""
=====================================================================================
🧠 SEMANTIC MATRIX EXTRACTOR (NLP Brain)
=====================================================================================
This file reads the user's search query and extracts STRUCTURED information.

WHY WE NEED THIS:
Users type messy queries like:
  - "macbook under 2000"
  - "red shoes between 50 and 100"
  - "iphone and ipad on sale"
  - "nike shoes 50% off"

We need to understand:
  - What product they want (the "core query")
  - Price limits (min/max)
  - Discount requirements
  - Sale intent
  - Multiple items at once (using "and" or "|" separator)

EXAMPLE:
  INPUT:  "macbook under 2000 on sale"
  OUTPUT: {
    "core_query": "macbook",
    "min_price": None,
    "max_price": 2000,
    "discount": None,
    "is_sale": True,
    "has_accessory_intent": False,
    "accessory_keywords": [...]
  }

This structured data is then used to build OpenSearch queries with filters.
=====================================================================================
"""

import re
from app.core.constants import ACCESSORY_KEYWORDS


def extract_semantic_matrix(query_string: str) -> dict:
    """
    Extracts structured information from a raw user query.
    
    ARGS:
        query_string: Raw user input (like "iphone under 500 on sale")
    
    RETURNS:
        dict with keys:
            - core_query: The cleaned product query (price/sale words removed)
            - min_price: Minimum price if user specified (or None)
            - max_price: Maximum price if user specified (or None)
            - discount: Discount % if user said "20% off" etc (or None)
            - is_sale: True if user wants sale items
            - has_accessory_intent: True if user wants accessories
            - accessory_keywords: List of accessory words
    
    EXAMPLE:
        extract_semantic_matrix("iphone under 500 on sale")
        → {
            "core_query": "iphone",
            "min_price": None,
            "max_price": 500.0,
            "discount": None,
            "is_sale": True,
            "has_accessory_intent": False,
            "accessory_keywords": ["case", "cover", ...]
          }
    """
    
    # =====================================================================
    # STEP 1: Lowercase everything for consistent matching
    # =====================================================================
    # "IPHONE Under 500" → "iphone under 500"
    # Makes regex patterns simpler (no need to handle uppercase)
    query_lower = query_string.lower()
    
    # We'll keep modifying 'core_query' by removing extracted pieces
    # (price, sale words, etc) — what's LEFT is the actual product
    core_query = query_lower
    
    # Initialize all extracted values as None (meaning: not found yet)
    smart_min_price = None
    smart_max_price = None
    smart_discount = None
    is_sale_intent = False
    
    # =====================================================================
    # STEP 2: Extract PRICE RANGE (like "between 50 and 100", "50-100")
    # =====================================================================
    # This regex matches patterns like:
    #   "between 50 and 100"
    #   "from $50 to $100"
    #   "50 - 100"
    #   "$50 to $100"
    range_match = re.search(
        r'(?:between|from)?\s*\$?\s*(\d+)\s*(?:to|and|-)\s*\$?\s*(\d+)',
        query_lower
    )
    
    if range_match:
        # Found a range! Group 1 = min, Group 2 = max
        smart_min_price = float(range_match.group(1))
        smart_max_price = float(range_match.group(2))
        
        # Remove the matched price text from core_query
        # So "red shoes between 50 and 100" → "red shoes"
        core_query = core_query.replace(range_match.group(0), '')
    
    else:
        # No range found — try for "under X" or "over X" patterns instead
        
        # ---------------------------------------------------------------
        # STEP 2A: Look for "under X" / "less than X" / "below X"
        # ---------------------------------------------------------------
        max_match = re.search(
            r'(?:under|less than|below|cheaper than|<)\s*\$?\s*(\d+)',
            query_lower
        )
        
        if max_match:
            smart_max_price = float(max_match.group(1))
            core_query = core_query.replace(max_match.group(0), '')
        
        # ---------------------------------------------------------------
        # STEP 2B: Look for "over X" / "more than X" / "above X"
        # ---------------------------------------------------------------
        min_match = re.search(
            r'(?:over|more than|above|>)\s*\$?\s*(\d+)',
            query_lower
        )
        
        if min_match:
            smart_min_price = float(min_match.group(1))
            core_query = core_query.replace(min_match.group(0), '')
    
    # =====================================================================
    # STEP 3: Extract DISCOUNT PERCENTAGE (like "20% off", "50% discount")
    # =====================================================================
    disc_match = re.search(r'(\d+)%\s*(?:off|discount|sale)', query_lower)
    
    if disc_match:
        smart_discount = int(disc_match.group(1))
        core_query = core_query.replace(disc_match.group(0), '')
    
    # =====================================================================
    # STEP 4: Detect SALE INTENT
    # =====================================================================
    # If user types ANY of: "sale", "clearance", "discount"
    # OR they specified a discount % (from Step 3)
    # Then we know they want sale items
    
    if (
        "sale" in query_lower 
        or "clearance" in query_lower 
        or "discount" in query_lower 
        or smart_discount  # They specified "% off"
    ):
        is_sale_intent = True
        
        # Remove sale-related words from core_query
        # So "iphone on sale" → "iphone"
        core_query = re.sub(
            r'\b(?:with\s+sale|on\s+sale|sale|clearance|discount)\b',
            '',
            core_query
        )
    
    # =====================================================================
    # STEP 5: Handle MULTI-ITEM queries (user wants 2+ things at once)
    # =====================================================================
    # Examples:
    #   "macbook and iphone" → "macbook | iphone"
    #   "shoes, bags" → "shoes | bags"
    #   "nike & adidas" → "nike | adidas"
    #
    # We use "|" as our internal separator for multi-item queries.
    # Later in search logic, we split by "|" and boost each item equally.
    
    # Convert "and" → "|"
    core_query = re.sub(r'\b\s+and\s+\b', ' | ', core_query)
    
    # Convert "," and "&" → "|"
    core_query = re.sub(r'[,&]', ' | ', core_query)
    
    # Clean up multiple spaces into single space
    core_query = re.sub(r'\s+', ' ', core_query).strip()
    
    # =====================================================================
    # STEP 6: SAFETY NET — Never return empty core_query
    # =====================================================================
    # If removing price/sale words left us with NOTHING,
    # fall back to the original query (better than searching for empty)
    if not core_query:
        core_query = query_lower
    
    # =====================================================================
    # STEP 7: Detect ACCESSORY INTENT
    # =====================================================================
    # If user types "iphone case" → they WANT accessories
    # If user types "iphone" alone → they want the device (not accessories)
    #
    # This flag is used LATER to DEMOTE accessories when user wants device only
    # (so searching "iphone" doesn't show 100 iPhone cases before actual iPhone)
    
    has_accessory_intent = any(
        acc in query_lower 
        for acc in ACCESSORY_KEYWORDS
    )
    
    # =====================================================================
    # RETURN: Everything the search engine needs to know
    # =====================================================================
    return {
        "core_query": core_query,
        "min_price": smart_min_price,
        "max_price": smart_max_price,
        "discount": smart_discount,
        "is_sale": is_sale_intent,
        "has_accessory_intent": has_accessory_intent,
        # Include the keyword list so search engine can use it for demotion
        "accessory_keywords": ACCESSORY_KEYWORDS
    }