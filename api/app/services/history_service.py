"""
=====================================================================================
🕐 SEARCH HISTORY SERVICE (Redis-Backed)
=====================================================================================
This file manages the user's recent search history.

HOW IT WORKS:
  - Each user has a Redis list key: "history:{user_id}"
  - We push new searches to the FRONT (most recent first)
  - Keep only last 5 searches (auto-trim older ones)
  - Expire entire history after 30 days of inactivity
  - Duplicates are removed (typing same search moves it to top)

WHY REDIS?
  - Super fast reads (<1ms)
  - Built-in list operations (lpush, lrange, lrem, ltrim)
  - Auto-expiration (no manual cleanup needed)

⚠️ KNOWN LIMITATION:
  Currently user_id = IP address (from request.client.host)
  This is NOT reliable for production:
    - Users behind NAT share same IP
    - Mobile users have changing IPs
    - VPN users have random IPs
  
  TODO: Replace with proper session-based user ID in future
=====================================================================================
"""

import logging
from app.config import redis_client
from app.core.constants import (
    HISTORY_MAX_ITEMS,
    HISTORY_EXPIRY_SECONDS
)

logger = logging.getLogger(__name__)


# =========================================================================
# 💾 SAVE SEARCH HISTORY
# =========================================================================
async def save_search_history(user_id: str, query: str) -> dict:
    """
    Saves a search query to user's history.
    
    LOGIC:
      1. If query exists in history already → remove it
      2. Push new query to FRONT of list
      3. Trim list to keep only last 5 items
      4. Refresh 30-day expiration
    
    ARGS:
        user_id: User identifier (currently IP address)
        query: The search query to save
    
    RETURNS:
        dict: {"status": "saved"} or {"status": "skipped"} or {"status": "error"}
    """
    
    # =====================================================================
    # STEP 1: VALIDATE INPUT
    # =====================================================================
    # Skip empty or very short queries (like single letters)
    if not query or len(query.strip()) < 2:
        return {"status": "skipped"}
    
    clean_query = query.strip()
    
    # Redis key for this user
    key = f"history:{user_id}"
    
    try:
        # =====================================================================
        # STEP 2: REMOVE DUPLICATE (if exists)
        # =====================================================================
        # lrem = remove ALL occurrences of this query
        # 0 = no limit on how many to remove
        # This prevents duplicates in history
        await redis_client.lrem(key, 0, clean_query)
        
        # =====================================================================
        # STEP 3: PUSH NEW QUERY TO FRONT
        # =====================================================================
        # lpush = push to LEFT (front) of list
        # Most recent searches appear first
        await redis_client.lpush(key, clean_query)
        
        # =====================================================================
        # STEP 4: TRIM LIST TO MAX SIZE
        # =====================================================================
        # ltrim keeps items from index 0 to HISTORY_MAX_ITEMS-1
        # Older items (beyond limit) are automatically discarded
        await redis_client.ltrim(key, 0, HISTORY_MAX_ITEMS - 1)
        
        # =====================================================================
        # STEP 5: REFRESH EXPIRATION (30 days from NOW)
        # =====================================================================
        # Every time user searches, their history TTL resets
        # Only inactive users lose history after 30 days
        await redis_client.expire(key, HISTORY_EXPIRY_SECONDS)
        
        return {"status": "saved"}
        
    except Exception as e:
        # Redis error? Log it but don't crash
        logger.error(f"❌ Save History Error: {e}")
        return {"status": "error"}


# =========================================================================
# 📖 GET SEARCH HISTORY
# =========================================================================
async def get_search_history(user_id: str) -> dict:
    """
    Retrieves user's recent search history.
    
    ARGS:
        user_id: User identifier (currently IP address)
    
    RETURNS:
        dict: {
            "history": ["recent search 1", "recent search 2", ...]
        }
        Empty list if no history or Redis error.
    """
    
    # Redis key for this user
    key = f"history:{user_id}"
    
    try:
        # lrange = get items from index 0 to HISTORY_MAX_ITEMS-1
        # Returns list in insertion order (most recent first)
        history = await redis_client.lrange(key, 0, HISTORY_MAX_ITEMS - 1)
        
        # Decode bytes to strings (Redis returns bytes by default)
        # decode_responses=True in config should handle this, but we double-check
        clean_history = [
            h.decode() if isinstance(h, bytes) else h
            for h in history
        ]
        
        return {"history": clean_history}
        
    except Exception as e:
        logger.error(f"❌ Get History Error: {e}")
        return {"history": []}


# =========================================================================
# 🗑️ DELETE HISTORY ITEM
# =========================================================================
async def delete_search_history_item(user_id: str, query: str) -> dict:
    """
    Deletes a SPECIFIC query from user's history.
    
    USE CASE:
      User clicks "X" next to a recent search to remove it
    
    ARGS:
        user_id: User identifier (currently IP address)
        query: The exact query to delete
    
    RETURNS:
        dict: {"status": "deleted"} or {"status": "error"}
    """
    
    key = f"history:{user_id}"
    
    try:
        # lrem with count=0 removes ALL occurrences of this query
        await redis_client.lrem(key, 0, query.strip())
        
        return {"status": "deleted"}
        
    except Exception as e:
        logger.error(f"❌ Delete History Error: {e}")
        return {"status": "error"}