"""Redis caching layer for API responses and expensive operations."""
import redis
import json
import hashlib
import logging
from typing import Optional, Any
from functools import wraps
from backend.config.settings import settings
import pickle

logger = logging.getLogger(__name__)

# Global Redis client (lazy initialization)
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client."""
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    try:
        if settings.redis_url:
            _redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=False,  # We'll handle encoding/decoding
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis client connected successfully")
            return _redis_client
        else:
            logger.warning("Redis URL not configured, caching disabled")
            return None
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
        return None


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments."""
    key_data = {
        "args": args,
        "kwargs": sorted(kwargs.items())
    }
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: int = 3600, prefix: str = "cache"):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds (default: 1 hour)
        prefix: Cache key prefix
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client = get_redis_client()
            if not client:
                # Redis not available, execute function directly
                return func(*args, **kwargs)
            
            # Generate cache key
            key = f"{prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            
            try:
                # Try to get from cache
                cached_value = client.get(key)
                if cached_value:
                    logger.debug(f"Cache hit for {key}")
                    return pickle.loads(cached_value)
                
                # Cache miss, execute function
                logger.debug(f"Cache miss for {key}")
                result = func(*args, **kwargs)
                
                # Store in cache
                client.setex(key, ttl, pickle.dumps(result))
                logger.debug(f"Cached result for {key} (TTL: {ttl}s)")
                
                return result
            except Exception as e:
                logger.error(f"Cache error for {key}: {e}")
                # On cache error, execute function directly
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    """Set a value in cache."""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        client.setex(key, ttl, pickle.dumps(value))
        return True
    except Exception as e:
        logger.error(f"Cache set error for {key}: {e}")
        return False


def cache_get(key: str) -> Optional[Any]:
    """Get a value from cache."""
    client = get_redis_client()
    if not client:
        return None
    
    try:
        cached_value = client.get(key)
        if cached_value:
            return pickle.loads(cached_value)
        return None
    except Exception as e:
        logger.error(f"Cache get error for {key}: {e}")
        return None


def cache_delete(key: str) -> bool:
    """Delete a value from cache."""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error for {key}: {e}")
        return False


def cache_clear_pattern(pattern: str) -> int:
    """Clear all cache keys matching a pattern."""
    client = get_redis_client()
    if not client:
        return 0
    
    try:
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.error(f"Cache clear pattern error for {pattern}: {e}")
        return 0
