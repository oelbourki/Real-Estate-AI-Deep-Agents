# Deployment Guide

## Production Deployment

### Prerequisites

- Docker and Docker Compose
- Redis (or use Docker Compose)
- Environment variables configured

### Docker Deployment

1. **Build and run with Docker Compose:**

```bash
cd docker
docker-compose up -d
```

2. **Check logs:**

```bash
docker-compose logs -f backend
```

3. **Stop services:**

```bash
docker-compose down
```

### Development Mode

For development with hot reload:

```bash
cd docker
docker-compose -f docker-compose.dev.yml up
```

### Manual Deployment

1. **Install dependencies:**

```bash
cd backend
pip install -r requirements.txt
```

2. **Set environment variables:**

```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Run migrations/initialization:**

```bash
python -c "from backends.memory import initialize_memory_files; initialize_memory_files()"
```

4. **Start Redis (if not using Docker):**

```bash
redis-server
```

5. **Run the application:**

```bash
python run.py
# Or: uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Production Considerations

1. **Use a production ASGI server:**

```bash
pip install gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

2. **Set up reverse proxy (Nginx):**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. **Enable HTTPS with Let's Encrypt:**

```bash
certbot --nginx -d your-domain.com
```

4. **Set up process manager (systemd):**

Create `/etc/systemd/system/real-estate-ai.service`:

```ini
[Unit]
Description=Enterprise Real Estate AI Agent
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/enterprise-real-estate-ai/backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable real-estate-ai
sudo systemctl start real-estate-ai
```

### Monitoring

1. **Health check endpoint:**

```bash
curl http://localhost:8000/health
```

2. **Metrics endpoint:**

```bash
curl http://localhost:8000/metrics
```

3. **Set up monitoring:**

- Prometheus for metrics collection
- Grafana for visualization
- LangSmith for LLM observability

### Scaling

1. **Horizontal scaling:**

Run multiple instances behind a load balancer:

```bash
# Instance 1
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001

# Instance 2
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8002
```

2. **Redis for shared state:**

Ensure all instances use the same Redis instance for caching and rate limiting.

### Security

1. **API Keys:**

- Store in environment variables
- Never commit to version control
- Use secret management (AWS Secrets Manager, HashiCorp Vault)

2. **Rate Limiting:**

- Configured via `utils/rate_limiter.py`
- Adjust limits based on your needs

3. **CORS:**

- Configure allowed origins in `.env`
- Restrict to your frontend domains

4. **HTTPS:**

- Always use HTTPS in production
- Set up SSL certificates

### Backup

1. **Reports and memories:**

```bash
tar -czf backup-$(date +%Y%m%d).tar.gz reports/ memories/
```

2. **Redis data:**

```bash
redis-cli BGSAVE
```

### Troubleshooting

1. **Check logs:**

```bash
# Docker
docker-compose logs -f backend

# Systemd
journalctl -u real-estate-ai -f
```

2. **Check Redis connection:**

```bash
redis-cli ping
```

3. **Check health:**

```bash
curl http://localhost:8000/health
```
