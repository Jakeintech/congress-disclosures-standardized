"""
Simple in-memory cache for Congressional Trading API

Uses Lambda execution context to cache responses across warm starts.
"""

import time
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Global cache dict (persists across Lambda warm starts)
_CACHE: Dict[str, Dict[str, Any]] = {}


def cache_response(key: str, value: Any, ttl: int = 300) -> None:
    """
    Cache a response with TTL.
    
    Args:
        key: Cache key
        value: Value to cache (should be JSON-serializable)
        ttl: Time to live in seconds (default 300 = 5 minutes)
    """
    expiry = time.time() + ttl
    _CACHE[key] = {
        'value': value,
        'expiry': expiry
    }
    logger.debug(f"Cached {key} (TTL: {ttl}s)")


def get_cached(key: str) -> Optional[Any]:
    """
    Get value from cache if not expired.
    
    Args:
        key: Cache key
    
    Returns:
        Cached value or None if not found/expired
    """
    if key not in _CACHE:
        logger.debug(f"Cache miss: {key}")
        return None
    
    entry = _CACHE[key]
    
    # Check if expired
    if time.time() > entry['expiry']:
        logger.debug(f"Cache expired: {key}")
        del _CACHE[key]
        return None
    
    logger.debug(f"Cache hit: {key}")
    return entry['value']


def invalidate_cache(pattern: Optional[str] = None) -> int:
    """
    Invalidate cache entries.
    
    Args:
        pattern: Optional pattern to match keys (simple substring match)
                If None, clears all cache
    
    Returns:
        Number of entries invalidated
    """
    global _CACHE
    
    if pattern is None:
        # Clear all
        count = len(_CACHE)
        _CACHE = {}
        logger.info(f"Cleared entire cache ({count} entries)")
        return count
    else:
        # Clear matching pattern
        keys_to_delete = [k for k in _CACHE.keys() if pattern in k]
        for key in keys_to_delete:
            del _CACHE[key]
        logger.info(f"Invalidated {len(keys_to_delete)} cache entries matching '{pattern}'")
        return len(keys_to_delete)


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Dict with cache stats (size, keys, etc.)
    """
    active_count = 0
    expired_count = 0
    current_time = time.time()
    
    for entry in _CACHE.values():
        if current_time > entry['expiry']:
            expired_count += 1
        else:
            active_count += 1
    
    return {
        'total_entries': len(_CACHE),
        'active_entries': active_count,
        'expired_entries': expired_count,
        'keys': list(_CACHE.keys())
    }


def cleanup_expired() -> int:
    """
    Remove expired entries from cache.
    
    Returns:
        Number of entries removed
    """
    global _CACHE
    current_time = time.time()
    
    keys_to_delete = [
        k for k, v in _CACHE.items()
        if current_time > v['expiry']
    ]
    
    for key in keys_to_delete:
        del _CACHE[key]
    
    if keys_to_delete:
        logger.debug(f"Cleaned up {len(keys_to_delete)} expired cache entries")
    
    return len(keys_to_delete)
