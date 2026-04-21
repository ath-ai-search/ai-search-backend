"""
=====================================================================================
🔧 CENTRAL CONSTANTS FILE
=====================================================================================
This file stores ALL the magic numbers used in search.

WHY WE MADE THIS FILE:
- Before: boost numbers like 100.0, 200.0, 5000.0 were scattered across 1376 lines
- Now: all numbers are here in ONE place
- If you want to tune search quality, just change numbers here
- No need to hunt through the big search_service.py file
=====================================================================================
"""

# =========================================================================
# 🔍 OPENSEARCH LIMITS
# =========================================================================

# OpenSearch has a hard limit: from + size cannot exceed 10000
# This is a rule from OpenSearch itself, not our choice
MAX_OS_WINDOW = 10000


# =========================================================================
# 📄 PAGINATION SETTINGS
# =========================================================================

# How many products to show per page on the main search results
DEFAULT_PAGE_SIZE = 100

# Smaller page size used by AI Assistant chat (shows compact results)
SMALL_PAGE_SIZE = 10

# How many page number buttons to show at once (like: 1 2 [3] 4 5)
PAGINATION_VISIBLE_PAGES = 5


# =========================================================================
# ⚖️ SEARCH BOOST VALUES — MAIN SEARCH
# =========================================================================
# What is "boost"?
# When OpenSearch finds matching products, it gives each product a score.
# Higher boost = that type of match is more important.
# Example: if user types "Apple", matching the BRAND field is more important
# than matching the DESCRIPTION field, so brand gets higher boost.

# When user's query EXACTLY matches the brand name (like "Apple", "Nike")
BOOST_BRAND_PHRASE = 300.0

# When user's query matches a product CATEGORY (like "Shoes", "Watches")
# This solves the "Watch Cap vs Wrist Watch" problem — category match wins
BOOST_CATEGORY_MATCH = 200.0

# When user's query matches the product NAME exactly (like "iPhone 15 Pro")
BOOST_NAME_PHRASE = 100.0

# When query matches across multiple fields at once (name + brand + category)
BOOST_CROSS_FIELDS = 20.0

# Fallback matching with typo tolerance (like "iphon" still finds "iphone")
BOOST_FUZZY_FALLBACK = 5.0


# =========================================================================
# ⚖️ SEARCH BOOST VALUES — MEGA MENU WIDGET
# =========================================================================
# The dropdown widget uses HIGHER boosts because:
# - It shows only 10 results (quick preview)
# - Results must be MORE relevant than main search
# - Less room for error, so we crank up the importance

WIDGET_BOOST_BRAND = 5000.0       # Brand match in widget
WIDGET_BOOST_CATEGORY = 3000.0    # Category match in widget
WIDGET_BOOST_NAME = 500.0         # Name match in widget
WIDGET_BOOST_MULTI_MATCH = 5.0    # General multi-field match


# =========================================================================
# 🚫 NEGATIVE BOOST (Demotion)
# =========================================================================

# When user searches "iphone" but NOT for accessories,
# we DEMOTE accessory products (cases, covers, chargers) by this tiny weight
# Very small number = very low score = pushed to bottom of results
ACCESSORY_DEMOTION_WEIGHT = 0.00001

# Same idea but for mega menu widget (slightly stronger demotion)
WIDGET_ACCESSORY_DEMOTION_WEIGHT = 0.001


# =========================================================================
# 🔢 KNN (K-NEAREST NEIGHBORS) SEMANTIC SEARCH
# =========================================================================

# K = how many similar products to find using vector search
# Minimum we always want (even for page 1)
KNN_MIN_K = 200

# Extra buffer added to handle pagination properly
# Formula used: max(200, from_val + page_size + 100)
KNN_BUFFER = 100


# =========================================================================
# ⏰ REDIS CACHE EXPIRATION TIMES (in seconds)
# =========================================================================

# How long main search results are cached (5 minutes)
# Short because prices/stock can change quickly
SEARCH_CACHE_TTL = 300

# How long autocomplete suggestions are cached (1 hour)
# Longer because these change less often
AUTOCOMPLETE_CACHE_TTL = 3600

# How long to keep user search history (30 days)
# After 30 days of inactivity, history gets auto-deleted by Redis
HISTORY_EXPIRY_SECONDS = 60 * 60 * 24 * 30  # = 2,592,000 seconds

# How many recent searches to keep per user (for history dropdown)
HISTORY_MAX_ITEMS = 5


# =========================================================================
# 🎨 CACHE KEY VERSIONS
# =========================================================================

# Cache key version — BUMP this number when search logic changes
# Bumping invalidates all old cached results so users get fresh results
# Example: if you change boost values, bump v135 → v136
CACHE_VERSION = "v138"


# =========================================================================
# 🔍 OPENSEARCH INDEX SETTINGS
# =========================================================================

# How many category buckets to return in facets (filter sidebar)
# Lower number = only MOST relevant categories shown
# 15 is a good balance (not too few, not cluttered)
FACET_CATEGORIES_SIZE = 15

# Minimum products a category must have to appear in sidebar
# Prevents irrelevant categories (like "Kitchen" when searching shoes)
# from showing up just because 1-2 products have weird tags
FACET_MIN_DOC_COUNT = 3

# How many top categories to show in mega menu widget
WIDGET_TOP_CATEGORIES_SIZE = 6


# =========================================================================
# 🛡️ FILTER LIMITS (Security/Sanity)
# =========================================================================
# These prevent abuse where someone sends 1000 filter values

MAX_CATEGORY_FILTERS = 5    # Max categories user can filter by at once
MAX_COLOR_FILTERS = 5       # Max colors
MAX_SIZE_FILTERS = 5        # Max sizes
MAX_BRAND_FILTERS = 5       # Max brands
MAX_GENDER_FILTERS = 3      # Max genders (men/women/kids)


# =========================================================================
# 🎯 AI ASSISTANT SETTINGS
# =========================================================================

# OpenAI model used for AI chat assistant (cheap + fast)
AI_CHAT_MODEL = "gpt-3.5-turbo-0125"

# OpenAI model used for embeddings (creating vectors for semantic search)
AI_EMBEDDING_MODEL = "text-embedding-3-small"

# Temperature controls AI creativity:
# 0.0 = very strict, same answer every time (used for extracting filters)
# 0.7 = more creative (used for welcome messages, suggestions)
AI_TEMPERATURE_STRICT = 0.0
AI_TEMPERATURE_CREATIVE = 0.7
AI_TEMPERATURE_BALANCED = 0.4

# Max suggestions to show user at once
MAX_AI_SUGGESTIONS = 4
MAX_AUTOCOMPLETE_SUGGESTIONS = 10


# =========================================================================
# 🎲 DEMO DATA (Fake ratings/sales for products that don't have real ones)
# =========================================================================
# These generate FAKE but consistent ratings/sales based on product ID
# Same product ID always gets same rating — looks realistic to users

DEMO_RATING_BASE = 4.0          # Minimum fake rating (4.0 stars)
DEMO_RATING_RANGE = 10          # Adds 0.0 to 0.9 to base (so 4.0 to 4.9)
DEMO_SALES_BASE = 150           # Minimum fake sales count
DEMO_SALES_RANGE = 800          # Adds 0 to 799 to base (so 150 to 949)


# =========================================================================
# 📊 SCORE NORMALIZATION
# =========================================================================
# Raw scores from OpenSearch can be huge (like 5000, 300, etc)
# We normalize them to 0.0 - 1.0 for display
# Then we show it as "relevance %" to user (like 0.85 - 0.99)

SCORE_DISPLAY_MIN = 0.85    # Minimum displayed score
SCORE_DISPLAY_RANGE = 0.14  # Range added on top (so 0.85 to 0.99)


# =========================================================================
# 🚨 ACCESSORY KEYWORDS (for demotion logic)
# =========================================================================
# If user types any of these, we assume they WANT accessories
# If user types "iphone" WITHOUT these words, we demote accessories

ACCESSORY_KEYWORDS = [
    "case", "cover", "charger", "cable", "bag", 
    "protector", "strap", "band", "adapter", 
    "mount", "holder"
]


# =========================================================================
# 🏷️ BRAND MAPPING (Product Name → Brand Detection)
# =========================================================================
# If product brand field is empty, we guess brand from product name
# Example: product named "MacBook Pro 16" → brand = "APPLE"

BRAND_MAPPINGS = {
    # Apple products
    "iphone": "APPLE",
    "ipad": "APPLE",
    "macbook": "APPLE",
    "airpods": "APPLE",
    "imac": "APPLE",
    
    # Samsung products
    "galaxy": "SAMSUNG",
    "s20": "SAMSUNG",
    "s21": "SAMSUNG",
    "s22": "SAMSUNG",
    "s23": "SAMSUNG",
    "s24": "SAMSUNG",
    
    # Lenovo products
    "thinkpad": "LENOVO",
    "yoga": "LENOVO",
    "ideapad": "LENOVO",
    
    # Acer products
    "predator": "ACER",
    "aspire": "ACER",
    
    # HP products
    "pavilion": "HP",
    "envy": "HP",
    "omen": "HP",
    "spectre": "HP",
    
    # Asus products
    "rog": "ASUS",
    "zenbook": "ASUS",
    "vivobook": "ASUS",
    
    # Sony products
    "playstation": "SONY",
    "bravia": "SONY",
    
    # Microsoft products
    "xbox": "MICROSOFT",
    "surface": "MICROSOFT",
    
    # Google / Amazon
    "pixel": "GOOGLE",
    "kindle": "AMAZON",
    "echo": "AMAZON"
}

# Known brand names — if found anywhere in product title
KNOWN_BRANDS = [
    "nike", "adidas", "puma", "reebok", 
    "sony", "dell", "asus", "acer", "lenovo", 
    "hp", "microsoft", "apple", "samsung", 
    "viking", "u-line"
]

# Words to ignore when guessing brand from first word of product name
BRAND_STOP_WORDS = ["THE", "FOR", "AND", "WITH"]


# =========================================================================
# 🧹 BAD WORDS (AI filter cleanup)
# =========================================================================
# Sometimes AI returns garbage like "string", "example", "any"
# We filter these out so they don't become real filter values

AI_BAD_WORDS = [
    "string", "example", "any", "none", 
    "etc", "and", "or", "for"
]


# =========================================================================
# 🔒 DEFAULT SEARCH TERM (For empty search bar)
# =========================================================================
# When a new user opens the mega menu with empty search,
# we show this as a nice starting point
DEFAULT_SEARCH_TERM = "luxury sunglasses"