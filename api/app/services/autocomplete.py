"""
=====================================================================================
🔎 AUTOCOMPLETE SERVICE
=====================================================================================
This file provides REAL-TIME search suggestions as user types.

HOW IT WORKS:
  1. User types "iph" in search bar
  2. Frontend calls this API
  3. We search OpenSearch for product names starting with "iph"
  4. Return top 10 suggestions with thumbnails
  5. Frontend shows them in dropdown

PERFORMANCE:
  - Heavily cached in Redis (1 hour TTL)
  - Same query returns same results super fast
  - Uses "match_phrase_prefix" for prefix matching (faster than wildcard)
=====================================================================================
"""

import hashlib
import logging
from app.config import os_client, INDEX_NAME
from app.utils.cache import cache_get, cache_set
from app.core.constants import AUTOCOMPLETE_CACHE_TTL

logger = logging.getLogger(__name__)


# =========================================================================
# 🔎 AUTOCOMPLETE FUNCTION
# =========================================================================
async def execute_autocomplete(query_string: str) -> dict:
    """
    Returns autocomplete suggestions for search dropdown.
    
    ARGS:
        query_string: What user has typed so far (like "iph")
    
    RETURNS:
        dict: {
            "suggestions": [
                {"text": "iPhone 15", "thumbnail": "https://..."},
                {"text": "iPhone 14", "thumbnail": "https://..."},
                ...
            ]
        }
    """
    
    # =====================================================================
    # STEP 1: CLEAN THE INPUT
    # =====================================================================
    clean_query = query_string.strip()
    
    # Empty query? Return empty suggestions
    if not clean_query:
        return {"suggestions": []}
    
    # =====================================================================
    # STEP 2: CHECK CACHE
    # =====================================================================
    # Use MD5 hash of query as cache key (unique per query)
    cache_key = f"auto:{hashlib.md5(clean_query.encode()).hexdigest()}"
    
    cached_result = await cache_get(cache_key)
    if cached_result:
        return cached_result
    
    # =====================================================================
    # STEP 3: BUILD OPENSEARCH QUERY
    # =====================================================================
    # match_phrase_prefix = match all products whose NAME starts with query
    # Example: query "iph" → matches "iPhone 15", "iPhone 14 Pro", etc.
    os_query = {
        "size": 10,  # Return max 10 suggestions
        "_source": ["name", "images"],  # Only fetch name & images (faster)
        "query": {
            "match_phrase_prefix": {
                "name": {
                    "query": clean_query,
                    "max_expansions": 50  # Max variations to consider
                }
            }
        }
    }
    
    # =====================================================================
    # STEP 4: EXECUTE SEARCH
    # =====================================================================
    try:
        response = os_client.search(index=INDEX_NAME, body=os_query)
    except Exception as e:
        # OpenSearch error? Return empty (don't crash)
        logger.error(f"❌ Autocomplete OpenSearch error: {e}")
        return {"suggestions": []}
    
    # =====================================================================
    # STEP 5: DEDUPLICATE & BUILD SUGGESTIONS LIST
    # =====================================================================
    # Products often have duplicate names in different categories
    # We show each unique name only ONCE
    seen_names = set()
    suggestions = []
    
    for hit in response.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        name = source.get("name", "")
        
        # Normalize name for deduplication (lowercase)
        normalized_name = str(name).strip().lower()
        
        # Skip empty or already-seen names
        if normalized_name and normalized_name not in seen_names:
            seen_names.add(normalized_name)
            
            # Get first image as thumbnail
            images = source.get("images", [])
            thumbnail = images[0] if isinstance(images, list) and len(images) > 0 else None
            
            suggestions.append({
                "text": name,
                "thumbnail": thumbnail
            })
    
    # =====================================================================
    # STEP 6: CACHE & RETURN
    # =====================================================================
    final_response = {"suggestions": suggestions}
    
    # Cache for 1 hour (autocomplete doesn't change much)
    await cache_set(cache_key, final_response, ttl_seconds=AUTOCOMPLETE_CACHE_TTL)
    
    return final_response