# Monitoring and Observability Guide

## Overview

The Enterprise Real Estate AI Agent includes comprehensive monitoring and observability features.

## Metrics Collection

### Built-in Metrics

The system collects the following metrics:

- **Requests Total**: Total number of API requests
- **Requests by Endpoint**: Breakdown by endpoint
- **Errors Total**: Total number of errors
- **Errors by Type**: Breakdown by error type
- **Response Times**: Response time distribution
- **Cache Hits/Misses**: Cache performance
- **Error Rate**: Percentage of requests that resulted in errors
- **Average Response Time**: Average response time across all requests

### Accessing Metrics

**Endpoint:** `GET /metrics`

```bash
curl http://localhost:8000/metrics
```

**Response:**
```json
{
  "requests_total": 1234,
  "requests_by_endpoint": {
    "POST /api/v1/chat": {
      "count": 500,
      "total_duration": 123.45,
      "errors": 5
    }
  },
  "errors_total": 10,
  "errors_by_type": {
    "ValueError": 3,
    "HTTPException": 7
  },
  "response_times": [0.123, 0.456, ...],
  "avg_response_time": 0.234,
  "cache_hits": 800,
  "cache_misses": 434,
  "cache_hit_rate": 0.648,
  "error_rate": 0.008
}
```

## LangSmith Integration

### Setup

1. **Get LangSmith API key:**

   - Sign up at https://smith.langchain.com
   - Get your API key from settings

2. **Configure environment variables:**

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=enterprise-real-estate-ai
```

3. **View traces:**

   - Visit https://smith.langchain.com
   - Navigate to your project
   - View agent execution traces, tool calls, and LLM interactions

### What's Tracked

- Agent execution flow
- Tool calls and results
- LLM prompts and responses
- Subagent delegation
- Error traces
- Performance metrics

## Logging

### Log Levels

Configure log level in `.env`:

```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Log Format

```
2025-01-27 10:30:45 - api.main - INFO - Processing chat request for conversation thread_123
```

### Structured Logging

The system uses structured logging with context:

```python
logger.info("Processing request", extra={
    "endpoint": "/api/v1/chat",
    "conversation_id": "thread_123",
    "user_name": "John"
})
```

## Health Checks

### Health Endpoint

**Endpoint:** `GET /health`

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "redis": "connected",
  "timestamp": 1706359845.123
}
```

### Health Check Status

- **healthy**: All systems operational
- **degraded**: Some systems unavailable (e.g., Redis disconnected)
- **unhealthy**: Critical systems down

## Rate Limiting Monitoring

### Rate Limit Headers

All responses include rate limit headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706360400
```

### Monitoring Rate Limits

Track rate limit violations in metrics:

```json
{
  "errors_by_type": {
    "RateLimitExceeded": 5
  }
}
```

## Cache Monitoring

### Cache Metrics

Monitor cache performance:

- **Cache Hits**: Number of cache hits
- **Cache Misses**: Number of cache misses
- **Cache Hit Rate**: Percentage of requests served from cache

### Cache Keys

Cache keys follow patterns:

- `realty_us:realty_us_search_buy:<hash>` - Property search results
- `cache:<function_name>:<hash>` - General function results

### Clearing Cache

```python
from utils.cache import cache_clear_pattern

# Clear all RealtyUS cache
cache_clear_pattern("realty_us:*")

# Clear all cache
cache_clear_pattern("*")
```

## Performance Monitoring

### Response Time Tracking

Response times are tracked per endpoint:

```json
{
  "requests_by_endpoint": {
    "POST /api/v1/chat": {
      "count": 100,
      "total_duration": 45.67,
      "avg_duration": 0.457
    }
  }
}
```

### Performance Headers

All responses include performance headers:

```
X-Response-Time: 0.234s
```

## Error Monitoring

### Error Tracking

Errors are tracked by type:

```json
{
  "errors_total": 10,
  "errors_by_type": {
    "ValueError": 3,
    "HTTPException": 5,
    "RateLimitExceeded": 2
  }
}
```

### Error Rate

Calculate error rate:

```python
error_rate = errors_total / requests_total
```

## External Monitoring Tools

### Prometheus

Export metrics to Prometheus:

```python
# Add to api/main.py
from prometheus_client import Counter, Histogram, generate_latest

requests_counter = Counter('http_requests_total', 'Total HTTP requests')
response_time = Histogram('http_response_time_seconds', 'HTTP response time')

@app.get("/metrics/prometheus")
async def prometheus_metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Grafana

Create dashboards for:

- Request rate
- Error rate
- Response times
- Cache hit rate
- Rate limit violations

### Sentry

For error tracking:

```python
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=1.0,
)
```

## Best Practices

1. **Monitor Key Metrics:**
   - Error rate should be < 1%
   - Average response time should be < 2s
   - Cache hit rate should be > 50%

2. **Set Up Alerts:**
   - High error rate (> 5%)
   - Slow response times (> 5s)
   - Redis connection failures
   - Rate limit violations

3. **Regular Reviews:**
   - Review metrics weekly
   - Analyze error patterns
   - Optimize slow endpoints
   - Adjust cache TTLs

4. **Log Retention:**
   - Keep logs for 30 days minimum
   - Archive old logs
   - Use log aggregation (ELK, Loki)
