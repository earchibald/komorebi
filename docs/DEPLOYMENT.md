# Komorebi Deployment Guide

*Complete guide to deploying Komorebi in production environments.*

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Options](#deployment-options)
4. [Local Deployment](#local-deployment)
5. [Docker Deployment](#docker-deployment)
6. [Cloud Deployment](#cloud-deployment)
7. [Reverse Proxy Setup](#reverse-proxy-setup)
8. [SSL/TLS Configuration](#ssltls-configuration)
9. [Monitoring & Logging](#monitoring--logging)
10. [Backup & Recovery](#backup--recovery)
11. [Troubleshooting Deployments](#troubleshooting-deployments)

---

## Overview

Komorebi can be deployed in several configurations:

| Deployment Type | Complexity | Best For |
|-----------------|------------|----------|
| Local (dev) | Low | Development, testing |
| Docker | Medium | Single server, containerized |
| Docker Compose | Medium | Multi-service, development |
| Kubernetes | High | Production, high availability |
| Cloud PaaS | Low | Managed infrastructure |

### Production Requirements

- **Python 3.11+** for the backend
- **Node.js 18+** for building the frontend
- **PostgreSQL 14+** (recommended for production)
- **Reverse proxy** (nginx, Caddy) for HTTPS

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 core | 2+ cores |
| RAM | 512 MB | 2+ GB |
| Storage | 1 GB | 10+ GB |
| OS | Linux, macOS, Windows | Linux (Ubuntu 22.04) |

### Software Requirements

```bash
# Check Python version
python --version  # 3.11+

# Check Node.js version (for frontend build)
node --version  # 18+

# Check PostgreSQL (production)
psql --version  # 14+
```

---

## Deployment Options

### Quick Reference

| Option | Command |
|--------|---------|
| Development | `python -m cli.main serve --reload` |
| Production (local) | `gunicorn backend.app.main:app -w 4 -k uvicorn.workers.UvicornWorker` |
| Docker | `docker-compose up -d` |
| Cloud | See platform-specific sections |

---

## Local Deployment

### Development Mode

```bash
# Clone repository
git clone https://github.com/earchibald/komorebi.git
cd komorebi

# Install dependencies
pip install -e ".[dev]"

# Start server (with hot reload)
python -m cli.main serve --reload
```

### Production Mode (Local)

```bash
# Install production dependencies
pip install -e .
pip install gunicorn

# Set environment variables
export KOMOREBI_DEBUG=false
export KOMOREBI_DATABASE_URL="sqlite+aiosqlite:///./komorebi.db"

# Start with Gunicorn
gunicorn backend.app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Systemd Service

Create `/etc/systemd/system/komorebi.service`:

```ini
[Unit]
Description=Komorebi Backend Service
After=network.target postgresql.service

[Service]
Type=simple
User=komorebi
Group=komorebi
WorkingDirectory=/opt/komorebi
Environment="KOMOREBI_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/komorebi"
Environment="KOMOREBI_DEBUG=false"
ExecStart=/opt/komorebi/venv/bin/gunicorn backend.app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable komorebi
sudo systemctl start komorebi
sudo systemctl status komorebi
```

---

## Docker Deployment

### Dockerfile

Create `Dockerfile`:

```dockerfile
# Build stage
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir build && \
    pip wheel --no-cache-dir --wheel-dir /wheels -e .

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && \
    rm -rf /wheels

# Copy application
COPY backend/ backend/
COPY cli/ cli/

# Create non-root user
RUN useradd -m -u 1000 komorebi
USER komorebi

# Environment
ENV KOMOREBI_HOST=0.0.0.0
ENV KOMOREBI_PORT=8000

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile

Create `frontend/Dockerfile`:

```dockerfile
# Build stage
FROM node:18-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Runtime stage
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - KOMOREBI_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/komorebi
      - KOMOREBI_DEBUG=false
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=komorebi
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
```

### Running with Docker Compose

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f backend

# Stop
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

---

## Cloud Deployment

### AWS (Elastic Beanstalk)

1. **Install EB CLI:**
```bash
pip install awsebcli
```

2. **Initialize:**
```bash
eb init -p python-3.11 komorebi
```

3. **Create environment:**
```bash
eb create komorebi-prod
```

4. **Set environment variables:**
```bash
eb setenv KOMOREBI_DATABASE_URL="postgresql+asyncpg://..." KOMOREBI_DEBUG=false
```

5. **Deploy:**
```bash
eb deploy
```

### Google Cloud Run

1. **Build and push image:**
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/komorebi
```

2. **Deploy:**
```bash
gcloud run deploy komorebi \
  --image gcr.io/PROJECT_ID/komorebi \
  --platform managed \
  --region us-central1 \
  --set-env-vars "KOMOREBI_DATABASE_URL=..." \
  --allow-unauthenticated
```

### Azure Container Apps

1. **Create container app:**
```bash
az containerapp create \
  --name komorebi \
  --resource-group myResourceGroup \
  --environment myEnvironment \
  --image myregistry.azurecr.io/komorebi:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars KOMOREBI_DATABASE_URL="..."
```

### Heroku

1. **Create `Procfile`:**
```
web: gunicorn backend.app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

2. **Deploy:**
```bash
heroku create komorebi
heroku config:set KOMOREBI_DATABASE_URL="..."
git push heroku main
```

### Railway

1. **Connect GitHub repository**
2. **Add PostgreSQL database**
3. **Set environment variables:**
   - `KOMOREBI_DATABASE_URL`: Use Railway's database URL
   - `KOMOREBI_DEBUG`: `false`
4. **Deploy automatically on push**

---

## Reverse Proxy Setup

### Nginx

Create `/etc/nginx/sites-available/komorebi`:

```nginx
upstream komorebi_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name komorebi.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name komorebi.example.com;
    
    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/komorebi.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/komorebi.example.com/privkey.pem;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # API backend
    location /api/ {
        proxy_pass http://komorebi_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE support
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }
    
    # SSE endpoint (special handling)
    location /api/v1/sse/ {
        proxy_pass http://komorebi_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }
    
    # Health check
    location /health {
        proxy_pass http://komorebi_backend;
    }
    
    # Frontend static files
    location / {
        root /var/www/komorebi/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/komorebi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Caddy

Create `Caddyfile`:

```caddyfile
komorebi.example.com {
    # API backend
    handle /api/* {
        reverse_proxy localhost:8000
    }
    
    # SSE with long timeout
    handle /api/v1/sse/* {
        reverse_proxy localhost:8000 {
            flush_interval -1
        }
    }
    
    # Health check
    handle /health {
        reverse_proxy localhost:8000
    }
    
    # Frontend
    handle {
        root * /var/www/komorebi/frontend/dist
        file_server
        try_files {path} /index.html
    }
}
```

---

## SSL/TLS Configuration

### Let's Encrypt with Certbot

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d komorebi.example.com

# Auto-renewal (test)
sudo certbot renew --dry-run
```

### Self-Signed (Development)

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/komorebi.key \
  -out /etc/ssl/certs/komorebi.crt \
  -subj "/CN=localhost"
```

---

## Monitoring & Logging

### Health Checks

```bash
# Simple health check
curl -f http://localhost:8000/health || exit 1

# Docker health check (in docker-compose.yml)
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Logging

```bash
# View systemd logs
journalctl -u komorebi -f

# Docker logs
docker-compose logs -f backend

# Log to file
gunicorn ... --access-logfile /var/log/komorebi/access.log \
             --error-logfile /var/log/komorebi/error.log
```

### Prometheus Metrics (Optional)

Add to requirements:
```
prometheus-client>=0.19.0
```

Add middleware for metrics collection.

### Uptime Monitoring

Use services like:
- UptimeRobot (free tier available)
- Pingdom
- Better Uptime
- Health check endpoint: `GET /health`

---

## Backup & Recovery

### SQLite Backup

```bash
# Backup
cp komorebi.db komorebi.db.backup-$(date +%Y%m%d)

# Restore
cp komorebi.db.backup-20240115 komorebi.db
```

### PostgreSQL Backup

```bash
# Backup
pg_dump -h localhost -U postgres komorebi > backup-$(date +%Y%m%d).sql

# Restore
psql -h localhost -U postgres komorebi < backup-20240115.sql
```

### Automated Backups

Create `/etc/cron.daily/komorebi-backup`:

```bash
#!/bin/bash
BACKUP_DIR=/var/backups/komorebi
DATE=$(date +%Y%m%d)

# PostgreSQL backup
pg_dump -h localhost -U postgres komorebi | gzip > $BACKUP_DIR/db-$DATE.sql.gz

# Keep last 7 days
find $BACKUP_DIR -name "db-*.sql.gz" -mtime +7 -delete
```

---

## Troubleshooting Deployments

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Server not running | Check systemd status |
| `502 Bad Gateway` | Backend crashed | Check logs, restart |
| `Database error` | Wrong connection string | Verify DATABASE_URL |
| `SSE not working` | Proxy buffering | Disable nginx buffering |
| `CORS error` | Missing origin | Add to CORS_ORIGINS |

### Debug Commands

```bash
# Check service status
systemctl status komorebi

# Check port binding
ss -tlnp | grep 8000

# Test database connection
python -c "from backend.app.db import engine; print('OK')"

# Check environment
env | grep KOMOREBI

# Test API
curl -v http://localhost:8000/health
```

### Container Debugging

```bash
# Enter container shell
docker-compose exec backend /bin/bash

# View container logs
docker-compose logs backend --tail=100

# Check container health
docker-compose ps

# Restart container
docker-compose restart backend
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Set `KOMOREBI_DEBUG=false`
- [ ] Configure PostgreSQL (not SQLite)
- [ ] Set strong database password
- [ ] Configure CORS for production domain
- [ ] Build frontend for production

### Deployment

- [ ] Deploy backend service
- [ ] Deploy frontend static files
- [ ] Configure reverse proxy
- [ ] Enable HTTPS
- [ ] Set up health checks

### Post-Deployment

- [ ] Verify health endpoint
- [ ] Test API endpoints
- [ ] Verify SSE connectivity
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Document access procedures

---

## Quick Start Commands

```bash
# Development
python -m cli.main serve --reload

# Production (local)
gunicorn backend.app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# Docker
docker-compose up -d

# Health check
curl http://localhost:8000/health
```

---

*For configuration details, see [CONFIGURATION.md](./CONFIGURATION.md). For architecture overview, see [ARCHITECTURE.md](./ARCHITECTURE.md). For security, see [SECURITY.md](./SECURITY.md).*
