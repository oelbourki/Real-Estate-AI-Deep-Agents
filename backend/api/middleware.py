"""API middleware for rate limiting, monitoring, error handling, and security headers."""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import time
import logging
from utils.rate_limiter import api_rate_limiter
from utils.monitoring import metrics_collector

logger = logging.getLogger(__name__)

# Security headers (production best practice; minimal CSP to avoid breaking frontends)
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
# HSTS only in production (avoid forcing HTTPS in dev)
HSTS_HEADER = "max-age=31536000; includeSubDomains; preload"


async def security_headers_middleware(request: Request, call_next):
    """Add security headers to every response. HSTS only in production."""
    response = await call_next(request)
    for key, value in SECURITY_HEADERS.items():
        response.headers[key] = value
    try:
        from config.settings import settings

        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = HSTS_HEADER
    except Exception:
        pass
    return response


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    # Get client identifier (IP address or user ID)
    client_id = request.client.host if request.client else "unknown"

    # Check rate limit
    if not api_rate_limiter.is_allowed(client_id):
        remaining = api_rate_limiter.get_remaining(client_id)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": 60,
            },
        )

    response = await call_next(request)

    # Add rate limit headers
    remaining = api_rate_limiter.get_remaining(client_id)
    response.headers["X-RateLimit-Limit"] = str(api_rate_limiter.max_requests)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(
        int(time.time()) + api_rate_limiter.window_seconds
    )

    return response


async def monitoring_middleware(request: Request, call_next):
    """Monitoring middleware for metrics collection."""
    start_time = time.time()
    endpoint = f"{request.method} {request.url.path}"

    try:
        response = await call_next(request)
        duration = time.time() - start_time
        success = 200 <= response.status_code < 400

        metrics_collector.record_request(endpoint, duration, success)

        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response
    except Exception as e:
        duration = time.time() - start_time
        metrics_collector.record_request(endpoint, duration, False)
        metrics_collector.record_error(type(e).__name__)
        raise


async def error_handling_middleware(request: Request, call_next):
    """Error handling middleware."""
    try:
        return await call_next(request)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later.",
                "type": type(e).__name__,
            },
        )
