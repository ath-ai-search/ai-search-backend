"""
=====================================================================================
💾 REDIS CACHE HELPERS
=====================================================================================
This file provides safe Redis operations.

WHY WE NEED THIS:
In the old code, every function had its own try/except for Redis like:

    try:
        cached = await redis_client.get(key)
        if cached: return json.loads(cached)
    except Exception: pass

This was repeated 5+ times in search_service.py. 
Now we have ONE clean helper that handles errors properly.

IMPORTANT:
- If Redis is DOWN, app still works (just slower — no cache)
- Errors are LOGGED (not silently hidden)
- Cache miss returns None (not an error)
=====================================================================================
"""

import json
import logging
from app.config import redis_client

logger = logging.getLogger(__name__)


async def cache_get(key: str):
    """
    Gets a value from Redis cache and parses it as JSON.
    
    ARGS:
        key: The Redis cache key (like "search:ai:v135:abc123")
    
    RETURNS:
        dict/list: The cached data (parsed from JSON)
        None: If cache miss OR Redis error
    
    EXAMPLE:
        cached = await cache_get("search:abc123")
        if cached:
            return cached  # Cache hit! Use cached data
        # else: cache miss, do fresh search
    """
    try:
        cached_result = await redis_client.get(key)
        
        # Cache MISS — key doesn't exist
        if not cached_result:
            return None
        
        # Cache HIT — parse JSON and return
        return json.loads(cached_result)
        
    except Exception as e:
        # Redis error (connection lost, timeout, etc)
        # Don't crash — just log and return None (treat as cache miss)
        logger.warning(f"⚠️ Redis GET error for key '{key}': {e}")
        return None


async def cache_set(key: str, value, ttl_seconds: int) -> bool:
    """
    Saves a value to Redis cache as JSON with expiration time.
    
    ARGS:
        key: The Redis cache key
        value: The data to cache (will be JSON-serialized)
        ttl_seconds: How long to keep it in cache (like 300 = 5 minutes)
    
    RETURNS:
        bool: True if saved successfully, False if error
    
    EXAMPLE:
        await cache_set("search:abc123", results, ttl_seconds=300)
    """
    try:
        # Convert Python dict/list to JSON string before saving
        json_value = json.dumps(value)
        
        # 'ex' parameter = expiration in seconds
        # After ttl_seconds, Redis auto-deletes this key
        await redis_client.set(key, json_value, ex=ttl_seconds)
        
        return True
        
    except Exception as e:
        # Cache save failed — app still works, just won't be cached
        logger.warning(f"⚠️ Redis SET error for key '{key}': {e}")
        return False


async def cache_delete(key: str) -> bool:
    """
    Deletes a single key from Redis cache.
    
    ARGS:
        key: The Redis cache key to delete
    
    RETURNS:
        bool: True if deleted successfully, False if error
    """
    try:
        await redis_client.delete(key)
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Redis DELETE error for key '{key}': {e}")
        return False