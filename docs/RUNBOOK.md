# Operations Runbook

## Common Issues and Solutions

### Issue: High Error Rate

**Symptoms:**
- Error rate > 5% in metrics
- Users reporting failures

**Diagnosis:**
1. Check `/metrics` endpoint for error breakdown
2. Review error logs
3. Check Redis connection
4. Check API key validity

**Solutions:**
- If Redis errors: Check Redis connection and restart if needed
- If API errors: Verify API keys and rate limits
- If LLM errors: Check LLM API key and quota
- Restart service if needed

### Issue: Slow Response Times

**Symptoms:**
- Average response time > 5s
- Users reporting slow performance

**Diagnosis:**
1. Check `/metrics` for response time distribution
2. Check cache hit rate
3. Check Redis performance
4. Review agent execution traces in LangSmith

**Solutions:**
- Clear cache if corrupted
- Restart Redis if slow
- Check for rate limiting
- Optimize agent prompts if LLM is slow
- Scale horizontally if needed

### Issue: Redis Connection Failure

**Symptoms:**
- Health check shows Redis disconnected
- Cache not working
- Rate limiting not working

**Diagnosis:**
1. Check Redis server status
2. Check Redis URL configuration
3. Check network connectivity

**Solutions:**
- Restart Redis: `redis-cli shutdown && redis-server`
- Check Redis logs
- Verify Redis URL in `.env`
- System will fallback to memory (degraded mode)

### Issue: Rate Limit Violations

**Symptoms:**
- 429 errors in logs
- Users reporting rate limit errors

**Diagnosis:**
1. Check rate limit headers in responses
2. Review rate limit configuration
3. Check for abuse or legitimate high usage

**Solutions:**
- Adjust rate limits if legitimate high usage
- Investigate for abuse
- Implement per-user rate limits if needed
- Scale horizontally to handle more load

### Issue: Agent Not Responding

**Symptoms:**
- Chat endpoint timing out
- No response from agent

**Diagnosis:**
1. Check agent logs
2. Check LLM API status
3. Check LangSmith for traces
4. Check for stuck subagents

**Solutions:**
- Restart service
- Check LLM API quota
- Review agent execution in LangSmith
- Check for infinite loops in agent logic

## Maintenance Procedures

### Backup

**Create Backup:**
```bash
cd backend
python scripts/backup.py
```

**Restore Backup:**
```bash
cd backend
python scripts/backup.py restore backups/backup_YYYYMMDD_HHMMSS.tar.gz
```

### Clear Cache

**Clear All Cache:**
```python
from utils.cache import cache_clear_pattern
cache_clear_pattern("*")
```

**Clear Specific Cache:**
```python
cache_clear_pattern("realty_us:*")
```

### Restart Service

**Docker:**
```bash
docker-compose restart backend
```

**Systemd:**
```bash
sudo systemctl restart real-estate-ai
```

### View Logs

**Docker:**
```bash
docker-compose logs -f backend
```

**Systemd:**
```bash
journalctl -u real-estate-ai -f
```

### Health Check

```bash
curl http://localhost:8000/health
```

### Metrics

```bash
curl http://localhost:8000/metrics | jq
```

## Scaling Procedures

### Horizontal Scaling

1. **Add New Instance:**
   - Deploy new instance with same configuration
   - Ensure shared Redis instance
   - Add to load balancer

2. **Verify:**
   - Check health of new instance
   - Monitor metrics
   - Verify load distribution

### Vertical Scaling

1. **Increase Resources:**
   - Increase CPU/memory limits
   - Adjust worker count
   - Restart service

2. **Monitor:**
   - Check performance improvements
   - Monitor resource usage

## Emergency Procedures

### Service Down

1. **Check Status:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Restart Service:**
   ```bash
   # Docker
   docker-compose restart backend
   
   # Systemd
   sudo systemctl restart real-estate-ai
   ```

3. **Check Logs:**
   - Review recent errors
   - Check for crash logs

### Data Loss

1. **Stop Service:**
   - Prevent further data loss

2. **Restore Backup:**
   ```bash
   python scripts/backup.py restore <backup_file>
   ```

3. **Verify Data:**
   - Check reports and memories
   - Verify integrity

4. **Restart Service:**
   - Resume normal operations

### Security Incident

1. **Isolate Service:**
   - Take service offline
   - Block suspicious IPs

2. **Investigate:**
   - Review logs
   - Check for unauthorized access
   - Review API key usage

3. **Remediate:**
   - Rotate API keys
   - Update security configurations
   - Patch vulnerabilities

4. **Resume:**
   - Restore service
   - Monitor closely

## Performance Tuning

### Optimize Cache

- Adjust TTL based on data freshness needs
- Monitor cache hit rate
- Clear stale cache entries

### Optimize Rate Limits

- Adjust based on actual usage patterns
- Implement per-user limits if needed
- Monitor rate limit violations

### Optimize Agent

- Review agent prompts for efficiency
- Optimize subagent delegation
- Use appropriate models for tasks

## Monitoring Queries

### Check Error Rate
```bash
curl http://localhost:8000/metrics | jq '.error_rate'
```

### Check Cache Hit Rate
```bash
curl http://localhost:8000/metrics | jq '.cache_hit_rate'
```

### Check Average Response Time
```bash
curl http://localhost:8000/metrics | jq '.avg_response_time'
```

## Contact Information

- **On-Call Engineer:** [Contact Info]
- **DevOps Team:** [Contact Info]
- **Security Team:** [Contact Info]
