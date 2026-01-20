"""Rate limiting and request throttling."""
import time
import logging
from typing import Dict, Optional
from collections import defaultdict
from threading import Lock
from backend.utils.cache import get_redis_client

logger = logging.getLogger(__name__)

# In-memory rate limiter (fallback if Redis not available)
_memory_limiter: Dict[str, list] = defaultdict(list)
_memory_lock = Lock()


class RateLimiter:
    """Rate limiter using Redis or in-memory storage."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis_client = get_redis_client()
    
    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed.
        
        Args:
            key: Rate limit key (e.g., user_id, ip_address)
            
        Returns:
            True if allowed, False if rate limited
        """
        if self.redis_client:
            return self._redis_check(key)
        else:
            return self._memory_check(key)
    
    def _redis_check(self, key: str) -> bool:
        """Check rate limit using Redis."""
        try:
            redis_key = f"ratelimit:{key}"
            current = self.redis_client.incr(redis_key)
            
            if current == 1:
                # First request in window, set expiration
                self.redis_client.expire(redis_key, self.window_seconds)
            
            return current <= self.max_requests
        except Exception as e:
            logger.error(f"Redis rate limit check error: {e}")
            # Fallback to memory
            return self._memory_check(key)
    
    def _memory_check(self, key: str) -> bool:
        """Check rate limit using in-memory storage."""
        with _memory_lock:
            now = time.time()
            # Clean old entries
            _memory_limiter[key] = [
                timestamp for timestamp in _memory_limiter[key]
                if now - timestamp < self.window_seconds
            ]
            
            # Check limit
            if len(_memory_limiter[key]) >= self.max_requests:
                return False
            
            # Add current request
            _memory_limiter[key].append(now)
            return True
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests in current window."""
        if self.redis_client:
            try:
                redis_key = f"ratelimit:{key}"
                current = int(self.redis_client.get(redis_key) or 0)
                return max(0, self.max_requests - current)
            except:
                pass
        
        with _memory_lock:
            now = time.time()
            _memory_limiter[key] = [
                timestamp for timestamp in _memory_limiter[key]
                if now - timestamp < self.window_seconds
            ]
            return max(0, self.max_requests - len(_memory_limiter[key]))


# Global rate limiters
api_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)  # 100 req/min
scraping_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)  # 10 req/min for scraping
