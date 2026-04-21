"""
=====================================================================================
🏷️ BRAND MAPPER UTILITY
=====================================================================================
This file has ONE job: figure out the BRAND NAME of a product.

WHY IT EXISTS:
In our product database, the 'brand' field is often missing or messy.
Examples of bad brand data: None, "", "null", "unknown", "other brands"

SO WE USE A 4-STEP FALLBACK SYSTEM:
Step 1: Try the product's 'brand' field (if clean)
Step 2: Try 'supplier' from attributes
Step 3: Guess from product NAME using BRAND_MAPPINGS (iphone → APPLE)
Step 4: Check if any KNOWN_BRAND appears in the name
Step 5: Use the first word of the product name as last resort

This guarantees EVERY product gets a brand name displayed.
=====================================================================================
"""

import re
from app.core.constants import (
    BRAND_MAPPINGS,      # Dictionary: "iphone" → "APPLE"
    KNOWN_BRANDS,        # List: ["nike", "adidas", "sony"...]
    BRAND_STOP_WORDS     # List: ["THE", "FOR", "AND", "WITH"]
)


def get_smart_brand(source: dict) -> str:
    """
    Figures out the brand name of a product using smart fallback logic.
    
    ARGS:
        source: The product data dictionary from OpenSearch (_source field)
    
    RETURNS:
        str: Brand name in UPPERCASE (like "APPLE", "NIKE", "SAMSUNG")
             Returns "UNKNOWN" if absolutely nothing can be detected
    
    EXAMPLE:
        product = {"name": "MacBook Pro 16", "brand": ""}
        get_smart_brand(product)  →  "APPLE"
    """
    
    # =====================================================================
    # STEP 1: Try the 'brand' field first (cleanest source)
    # =====================================================================
    raw_brand = source.get("brand", "")
    
    # Check if brand is valid (not empty, not "none", not "unknown" etc)
    if raw_brand and str(raw_brand).strip().lower() not in [
        "none", "", "null", "other brands", "unknown"
    ]:
        # Brand is valid! Return it in UPPERCASE for consistency
        return str(raw_brand).strip().upper()
    
    # =====================================================================
    # STEP 2: Brand field was bad. Try 'supplier' from attributes
    # =====================================================================
    # Some products store brand under attributes.supplier instead
    attrs = source.get("attributes", {})
    
    if isinstance(attrs, dict):
        supplier = attrs.get("supplier", "")
        
        # Same validation as before
        if supplier and str(supplier).strip().lower() not in [
            "none", "", "null", "unknown"
        ]:
            return str(supplier).strip().upper()
    
    # =====================================================================
    # STEP 3: Still no brand. Guess from product NAME using BRAND_MAPPINGS
    # =====================================================================
    # Example: name="MacBook Pro 16" → we find "macbook" → return "APPLE"
    title = str(source.get("name", "")).strip()
    title_lower = title.lower()
    
    # Loop through our brand mapping dictionary
    # (constants.py → BRAND_MAPPINGS)
    for keyword, mapped_brand in BRAND_MAPPINGS.items():
        # \b means "word boundary" — prevents "iphone" matching "iphoney"
        # re.search looks for this keyword as a whole word in the title
        if re.search(rf'\b{keyword}\b', title_lower):
            return mapped_brand
    
    # =====================================================================
    # STEP 4: Check if any KNOWN_BRAND name appears in the title
    # =====================================================================
    # Example: "Men's Nike Air Jordan" → we find "nike" → return "NIKE"
    for brand in KNOWN_BRANDS:
        if re.search(rf'\b{brand}\b', title_lower):
            return brand.upper()
    
    # =====================================================================
    # STEP 5: LAST RESORT — use the first word of product name
    # =====================================================================
    # Example: "Gucci Leather Wallet" → first word = "GUCCI"
    words = title.split()
    
    if words:
        # Strip out punctuation from first word
        # (removes characters like: " , ' ( ) [ ] { } ! @ # $ % -)
        first_word = words[0].strip('",\'()[]{}!@#$%-').upper()
        
        # Validate the first word:
        # - Must be longer than 2 characters (avoid junk like "a", "to")
        # - Must NOT be a number (avoid "2023 Collection" → "2023")
        # - Must NOT be a stop word like "THE", "FOR", "AND", "WITH"
        if (
            len(first_word) > 2 
            and not first_word.isnumeric() 
            and first_word not in BRAND_STOP_WORDS
        ):
            return first_word
    
    # =====================================================================
    # ABSOLUTE FALLBACK: Nothing worked
    # =====================================================================
    # This should almost never happen, but just in case
    return "UNKNOWN"