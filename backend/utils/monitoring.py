"""Monitoring and observability utilities."""
import logging
import time
import functools
from typing import Optional, Dict, Any
from datetime import datetime
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects metrics for monitoring."""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "requests_total": 0,
            "requests_by_endpoint": {},
            "errors_total": 0,
            "errors_by_type": {},
            "response_times": [],
            "cache_hits": 0,
            "cache_misses": 0,
        }
    
    def record_request(self, endpoint: str, duration: float, success: bool = True):
        """Record a request metric."""
        self.metrics["requests_total"] += 1
        
        if endpoint not in self.metrics["requests_by_endpoint"]:
            self.metrics["requests_by_endpoint"][endpoint] = {
                "count": 0,
                "total_duration": 0,
                "errors": 0
            }
        
        self.metrics["requests_by_endpoint"][endpoint]["count"] += 1
        self.metrics["requests_by_endpoint"][endpoint]["total_duration"] += duration
        
        if not success:
            self.metrics["errors_total"] += 1
            self.metrics["requests_by_endpoint"][endpoint]["errors"] += 1
        
        self.metrics["response_times"].append(duration)
        # Keep only last 1000 response times
        if len(self.metrics["response_times"]) > 1000:
            self.metrics["response_times"] = self.metrics["response_times"][-1000:]
    
    def record_error(self, error_type: str):
        """Record an error metric."""
        self.metrics["errors_total"] += 1
        
        if error_type not in self.metrics["errors_by_type"]:
            self.metrics["errors_by_type"][error_type] = 0
        
        self.metrics["errors_by_type"][error_type] += 1
    
    def record_cache(self, hit: bool):
        """Record cache hit/miss."""
        if hit:
            self.metrics["cache_hits"] += 1
        else:
            self.metrics["cache_misses"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        avg_response_time = (
            sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
            if self.metrics["response_times"]
            else 0
        )
        
        return {
            **self.metrics,
            "avg_response_time": avg_response_time,
            "cache_hit_rate": (
                self.metrics["cache_hits"] / (self.metrics["cache_hits"] + self.metrics["cache_misses"])
                if (self.metrics["cache_hits"] + self.metrics["cache_misses"]) > 0
                else 0
            ),
            "error_rate": (
                self.metrics["errors_total"] / self.metrics["requests_total"]
                if self.metrics["requests_total"] > 0
                else 0
            ),
        }
    
    def reset(self):
        """Reset all metrics."""
        self.metrics = {
            "requests_total": 0,
            "requests_by_endpoint": {},
            "errors_total": 0,
            "errors_by_type": {},
            "response_times": [],
            "cache_hits": 0,
            "cache_misses": 0,
        }


# Global metrics collector
metrics_collector = MetricsCollector()


def monitor_performance(func):
    """Decorator to monitor function performance."""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            metrics_collector.record_error(type(e).__name__)
            raise
        finally:
            duration = time.time() - start_time
            endpoint = f"{func.__module__}.{func.__name__}"
            metrics_collector.record_request(endpoint, duration, success)
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            metrics_collector.record_error(type(e).__name__)
            raise
        finally:
            duration = time.time() - start_time
            endpoint = f"{func.__module__}.{func.__name__}"
            metrics_collector.record_request(endpoint, duration, success)
    
    # Return appropriate wrapper based on function type
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def setup_langsmith():
    """Setup LangSmith tracing if configured."""
    if settings.langchain_tracing_v2 and settings.langchain_api_key:
        import os
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        logger.info(f"LangSmith tracing enabled for project: {settings.langchain_project}")
    else:
        logger.info("LangSmith tracing not configured")
