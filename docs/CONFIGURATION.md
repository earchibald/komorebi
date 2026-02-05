# Komorebi Configuration Guide

*Complete guide to configuring the Komorebi cognitive infrastructure.*

---

## Table of Contents

1. [Overview](#overview)
2. [Environment Variables](#environment-variables)
3. [Database Configuration](#database-configuration)
4. [Server Configuration](#server-configuration)
5. [Logging Configuration](#logging-configuration)
6. [Frontend Configuration](#frontend-configuration)
7. [MCP Server Configuration](#mcp-server-configuration)
8. [Secrets Management](#secrets-management)
9. [Development vs Production](#development-vs-production)
10. [Configuration Examples](#configuration-examples)
11. [Configuration Validation](#configuration-validation)

---

## Overview

Komorebi uses environment variables for configuration, following the [12-Factor App](https://12factor.net/config) methodology. This allows the same codebase to run in development, staging, and production environments.

### Configuration Hierarchy

```
┌─────────────────────────────────────────┐
│         Environment Variables            │  ← Highest priority
├─────────────────────────────────────────┤
│           .env file (local)              │
├─────────────────────────────────────────┤
│         Default values in code           │  ← Lowest priority
└─────────────────────────────────────────┘
```

---

## Environment Variables

### Quick Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `KOMOREBI_DATABASE_URL` | `sqlite+aiosqlite:///./komorebi.db` | Database connection string |
| `KOMOREBI_DEBUG` | `false` | Enable debug mode |
| `KOMOREBI_API_URL` | `http://localhost:8000/api/v1` | API base URL (for CLI) |
| `KOMOREBI_HOST` | `0.0.0.0` | Server bind host |
| `KOMOREBI_PORT` | `8000` | Server bind port |
| `KOMOREBI_CORS_ORIGINS` | `*` | Allowed CORS origins |
| `KOMOREBI_LOG_LEVEL` | `INFO` | Logging level |

### Variable Details

#### `KOMOREBI_DATABASE_URL`

The async database connection string.

**SQLite (default):**
```bash
KOMOREBI_DATABASE_URL="sqlite+aiosqlite:///./komorebi.db"
```

**PostgreSQL:**
```bash
KOMOREBI_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/komorebi"
```

**MySQL:**
```bash
KOMOREBI_DATABASE_URL="mysql+aiomysql://user:pass@localhost:3306/komorebi"
```

> ⚠️ **Note:** PostgreSQL and MySQL require installing additional drivers (`asyncpg` or `aiomysql`).

#### `KOMOREBI_DEBUG`

Enable debug mode for development.

```bash
KOMOREBI_DEBUG=true
```

When enabled:
- SQLAlchemy echoes all SQL queries
- More verbose error messages
- Hot reload enabled (with `--reload` flag)

#### `KOMOREBI_API_URL`

The API base URL used by the CLI.

```bash
KOMOREBI_API_URL="http://localhost:8000/api/v1"
```

Override for remote servers:
```bash
KOMOREBI_API_URL="https://komorebi.example.com/api/v1"
```

---

## Database Configuration

### SQLite (Default)

SQLite is the default database, ideal for development and single-instance deployments.

**Location:** The database file is created at `./komorebi.db` in the current working directory.

**Configuration:**
```bash
# Default - file in current directory
KOMOREBI_DATABASE_URL="sqlite+aiosqlite:///./komorebi.db"

# Absolute path
KOMOREBI_DATABASE_URL="sqlite+aiosqlite:////var/data/komorebi.db"

# In-memory (testing only)
KOMOREBI_DATABASE_URL="sqlite+aiosqlite:///:memory:"
```

**Pros:**
- Zero configuration
- Single file backup
- No external dependencies

**Cons:**
- Single writer at a time
- Not suitable for multiple instances

### PostgreSQL

For production deployments with high concurrency.

**Installation:**
```bash
pip install asyncpg
```

**Configuration:**
```bash
KOMOREBI_DATABASE_URL="postgresql+asyncpg://user:password@host:5432/database"
```

**Connection pooling:**
```bash
# With connection pool settings
KOMOREBI_DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db?pool_size=20&max_overflow=10"
```

### Database Reset

To reset the database:

```bash
# SQLite - delete the file
rm komorebi.db

# PostgreSQL - drop and recreate
psql -U postgres -c "DROP DATABASE komorebi; CREATE DATABASE komorebi;"
```

The database is automatically initialized when the server starts.

---

## Server Configuration

### Development Server

```bash
# Using CLI
python -m cli.main serve --host 0.0.0.0 --port 8000 --reload

# Using uvicorn directly
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Server

```bash
# With multiple workers
uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --no-access-log

# With Gunicorn (recommended for production)
gunicorn backend.app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000
```

### CORS Configuration

By default, CORS allows all origins (`*`). For production:

```python
# In backend/app/main.py, modify:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Logging Configuration

### Log Levels

| Level | Description |
|-------|-------------|
| `DEBUG` | Detailed debugging information |
| `INFO` | General operational messages |
| `WARNING` | Warning messages |
| `ERROR` | Error conditions |
| `CRITICAL` | Critical failures |

### Configuration

```bash
# Set log level
KOMOREBI_LOG_LEVEL=INFO

# Enable SQL query logging (verbose)
KOMOREBI_DEBUG=true
```

### Log Output Format

Logs follow this format:
```
2024-01-15 10:30:00 - komorebi - INFO - Server started on 0.0.0.0:8000
2024-01-15 10:30:01 - komorebi - DEBUG - Processing chunk a1b2c3d4...
```

### Log Aggregation

For production, configure log shipping:

```bash
# Write logs to file
python -m cli.main serve 2>&1 | tee /var/log/komorebi/app.log

# Or configure structured JSON logging (requires modification)
KOMOREBI_LOG_FORMAT=json
```

---

## Frontend Configuration

### Vite Development Server

The frontend uses Vite with a proxy to the backend.

**Configuration:** `frontend/vite.config.ts`

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### Environment Variables

Create `frontend/.env` for frontend-specific settings:

```bash
# API URL (for production builds)
VITE_API_URL=http://localhost:8000

# Enable debug logging
VITE_DEBUG=true
```

### Production Build

```bash
cd frontend
npm run build
```

The build output is in `frontend/dist/` and can be served by any static file server.

---

## MCP Server Configuration

MCP servers are configured via the API at runtime.

### Registering an MCP Server

```bash
curl -X POST http://localhost:8000/api/v1/mcp/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GitHub MCP",
    "server_type": "github",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {"GITHUB_TOKEN": "ghp_..."},
    "enabled": true
  }'
```

### Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name |
| `server_type` | string | Yes | Type identifier |
| `command` | string | Yes | Executable to run |
| `args` | string[] | No | Command arguments |
| `env` | object | No | Environment variables |
| `enabled` | boolean | No | Auto-connect on startup |

### Common MCP Servers

**GitHub:**
```json
{
  "name": "GitHub",
  "server_type": "github",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {"GITHUB_TOKEN": "ghp_..."}
}
```

**Filesystem:**
```json
{
  "name": "Filesystem",
  "server_type": "filesystem",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
}
```

**Memory:**
```json
{
  "name": "Memory",
  "server_type": "memory",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-memory"]
}
```

---

## Secrets Management

### Best Practices

1. **Never commit secrets to version control**
2. **Use environment variables for all secrets**
3. **Rotate secrets regularly**
4. **Use different secrets per environment**

### Local Development

Use a `.env` file (excluded from git):

```bash
# .env (add to .gitignore!)
KOMOREBI_DATABASE_URL=sqlite+aiosqlite:///./komorebi.db
GITHUB_TOKEN=ghp_your_dev_token
```

### Production Secrets

**Option 1: Environment Variables**
```bash
export KOMOREBI_DATABASE_URL="postgresql+asyncpg://..."
export GITHUB_TOKEN="ghp_..."
```

**Option 2: Docker Secrets**
```yaml
# docker-compose.yml
secrets:
  db_password:
    file: ./secrets/db_password.txt

services:
  backend:
    secrets:
      - db_password
    environment:
      - KOMOREBI_DATABASE_URL_FILE=/run/secrets/db_password
```

**Option 3: Cloud Secret Managers**
```bash
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id komorebi/prod

# GCP Secret Manager
gcloud secrets versions access latest --secret=komorebi-db-password

# HashiCorp Vault
vault kv get secret/komorebi/database
```

### Secrets for MCP Servers

MCP server tokens (like `GITHUB_TOKEN`) are stored in the database when registered. For security:

1. Use tokens with minimal required permissions
2. Rotate tokens periodically
3. Use separate tokens for each environment

---

## Development vs Production

### Development Settings

Create a `.env` file in the project root:

```bash
# .env (development)
KOMOREBI_DEBUG=true
KOMOREBI_DATABASE_URL=sqlite+aiosqlite:///./komorebi.db
KOMOREBI_LOG_LEVEL=DEBUG
```

Start the server:
```bash
python -m cli.main serve --reload
```

### Production Settings

```bash
# .env.production
KOMOREBI_DEBUG=false
KOMOREBI_DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/komorebi
KOMOREBI_LOG_LEVEL=WARNING
KOMOREBI_CORS_ORIGINS=https://yourdomain.com
```

### Security Checklist for Production

- [ ] Set `KOMOREBI_DEBUG=false`
- [ ] Use PostgreSQL instead of SQLite
- [ ] Restrict CORS origins
- [ ] Enable HTTPS (via reverse proxy)
- [ ] Set strong database passwords
- [ ] Implement authentication
- [ ] Enable rate limiting
- [ ] Set up monitoring and logging

---

## Configuration Examples

### Minimal Development

```bash
# Just run it - defaults are fine
python -m cli.main serve
```

### Docker Compose

```yaml
# docker-compose.yml
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
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=komorebi
    volumes:
      - postgres_data:/var/lib/postgresql/data

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://backend:8000

volumes:
  postgres_data:
```

### Systemd Service

```ini
# /etc/systemd/system/komorebi.service
[Unit]
Description=Komorebi Backend Service
After=network.target

[Service]
Type=simple
User=komorebi
WorkingDirectory=/opt/komorebi
Environment=KOMOREBI_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/komorebi
Environment=KOMOREBI_DEBUG=false
ExecStart=/opt/komorebi/venv/bin/gunicorn backend.app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Environment File Template

```bash
# .env.template - Copy to .env and customize

# ===================
# Database
# ===================
# SQLite (development)
KOMOREBI_DATABASE_URL=sqlite+aiosqlite:///./komorebi.db

# PostgreSQL (production)
# KOMOREBI_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/komorebi

# ===================
# Server
# ===================
KOMOREBI_HOST=0.0.0.0
KOMOREBI_PORT=8000
KOMOREBI_DEBUG=false
KOMOREBI_LOG_LEVEL=INFO

# ===================
# CORS
# ===================
# Development - allow all
KOMOREBI_CORS_ORIGINS=*

# Production - restrict to your domain
# KOMOREBI_CORS_ORIGINS=https://yourdomain.com

# ===================
# CLI
# ===================
KOMOREBI_API_URL=http://localhost:8000/api/v1
```

---

## Loading Configuration

Configuration is loaded automatically from environment variables. To use a `.env` file:

```bash
# Install python-dotenv (already included)
pip install python-dotenv

# The app automatically loads .env if present
python -m cli.main serve
```

Or load explicitly:

```python
from dotenv import load_dotenv
load_dotenv()

# Now environment variables are available
import os
db_url = os.getenv("KOMOREBI_DATABASE_URL")
```

---

## Configuration Validation

### Validating Your Configuration

Run these checks to verify your configuration:

```bash
# 1. Check environment variables
env | grep KOMOREBI

# 2. Verify database connection
python -c "
from backend.app.db import engine
import asyncio
async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT 1')
        print('Database: OK')
asyncio.run(test())
"

# 3. Test the server starts
python -m cli.main serve &
sleep 2
curl http://localhost:8000/health
kill %1
```

### Common Configuration Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Server not running | Start with `python -m cli.main serve` |
| `Database not found` | Invalid DATABASE_URL | Check path and permissions |
| `CORS error` | Mismatched origins | Add frontend URL to CORS_ORIGINS |
| `Module not found` | Missing dependencies | Run `pip install -e ".[dev]"` |

### Configuration Dump

Print current configuration for debugging:

```python
# config_dump.py
import os

config_vars = [
    "KOMOREBI_DATABASE_URL",
    "KOMOREBI_DEBUG",
    "KOMOREBI_API_URL",
    "KOMOREBI_HOST",
    "KOMOREBI_PORT",
    "KOMOREBI_LOG_LEVEL",
    "KOMOREBI_CORS_ORIGINS",
]

print("Komorebi Configuration:")
print("=" * 40)
for var in config_vars:
    value = os.getenv(var, "(not set)")
    # Mask sensitive values
    if "URL" in var and value != "(not set)":
        value = value.split("@")[0] + "@..." if "@" in value else value[:20] + "..."
    print(f"{var}: {value}")
```

---

*For deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md). For API details, see [API_REFERENCE.md](./API_REFERENCE.md).*
