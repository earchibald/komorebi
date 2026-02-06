# Komorebi Security Guide

*Security considerations, best practices, and vulnerability reporting.*

---

## Table of Contents

1. [Security Status](#security-status)
2. [Security Architecture](#security-architecture)
3. [Authentication & Authorization](#authentication--authorization)
4. [Data Protection](#data-protection)
5. [Network Security](#network-security)
6. [Input Validation](#input-validation)
7. [Dependency Security](#dependency-security)
8. [MCP Security](#mcp-security)
9. [Production Hardening](#production-hardening)
10. [Vulnerability Reporting](#vulnerability-reporting)

---

## Security Status

### Current Security Posture (v0.1.0)

| Feature | Status | Notes |
|---------|--------|-------|
| Authentication | ⚠️ Not implemented | **Add before production** |
| Authorization | ⚠️ Not implemented | **Add before production** |
| HTTPS/TLS | ⚠️ Via proxy | Use nginx/Caddy |
| CORS | ⚠️ Open by default | Restrict in production |
| Rate Limiting | ⚠️ Not implemented | **Add before production** |
| Input Validation | ✅ Implemented | Pydantic validation |
| SQL Injection | ✅ Protected | SQLAlchemy ORM |
| XSS | ✅ Protected | React escaping |
| CSRF | ✅ N/A | Stateless API |

### Security Disclaimer

> ⚠️ **Important:** Komorebi v0.1.0 is designed for development and trusted environments. Before deploying to production with sensitive data:
> 1. Implement authentication
> 2. Enable HTTPS
> 3. Restrict CORS origins
> 4. Add rate limiting
> 5. Review access controls

---

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Internet                                      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                         Firewall/WAF                                     │
│  • Block malicious IPs                                                  │
│  • Rate limiting                                                        │
│  • DDoS protection                                                      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                    Reverse Proxy (nginx/Caddy)                           │
│  • TLS termination                                                      │
│  • Request filtering                                                    │
│  • Header sanitization                                                  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                    Authentication Layer                                  │
│  • JWT validation                                                       │
│  • API key verification                                                 │
│  • Session management                                                   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                      Komorebi Backend                                    │
│  • Input validation (Pydantic)                                          │
│  • Parameterized queries (SQLAlchemy)                                   │
│  • Output encoding                                                      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                         Database                                         │
│  • Encrypted at rest                                                    │
│  • Network isolation                                                    │
│  • Least privilege access                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Authentication & Authorization

### Current State

Komorebi v0.1.0 does not implement authentication. All endpoints are publicly accessible.

### Recommended Implementation

#### Option 1: JWT Authentication

```python
# Add to requirements
# pyjwt>=2.8.0

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=["HS256"]
        )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Apply to routes
@router.post("/chunks")
async def create_chunk(
    chunk: ChunkCreate,
    user: dict = Depends(verify_token),  # Require auth
):
    ...
```

#### Option 2: API Key Authentication

```python
from fastapi import Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return api_key
```

#### Authorization

After authentication, implement role-based access:

```python
class UserRole(str, Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"

def require_role(role: UserRole):
    async def check_role(user: dict = Depends(verify_token)):
        if user.get("role") != role and user.get("role") != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    return check_role
```

---

## Data Protection

### Data at Rest

**SQLite:**
- By default, SQLite files are unencrypted
- Consider SQLCipher for encryption
- Protect file permissions: `chmod 600 komorebi.db`

**PostgreSQL:**
- Enable TDE (Transparent Data Encryption) if available
- Use encrypted volumes

### Data in Transit

Always use HTTPS in production:

```nginx
server {
    listen 443 ssl http2;
    
    ssl_certificate /etc/ssl/certs/komorebi.crt;
    ssl_certificate_key /etc/ssl/private/komorebi.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:...;
    ssl_prefer_server_ciphers off;
}
```

### Sensitive Data

| Data Type | Storage | Protection |
|-----------|---------|------------|
| Chunk content | Database | Access control |
| MCP tokens | Database (env field) | Encrypt at rest |
| Database password | Environment variable | Never in code |
| API keys | Environment variable | Rotate regularly |

### Data Retention

Consider implementing:
- Automatic archival after N days
- Hard deletion for GDPR compliance
- Audit logs for data access

---

## Network Security

### CORS Configuration

**Development (default):**
```python
allow_origins=["*"]  # Open - OK for development
```

**Production:**
```python
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

### Firewall Rules

Recommended iptables rules:

```bash
# Allow HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Block direct access to backend port (use reverse proxy)
iptables -A INPUT -p tcp --dport 8000 -j DROP

# Allow localhost
iptables -A INPUT -i lo -j ACCEPT
```

### Rate Limiting

Add rate limiting in production:

**Option 1: nginx**
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://backend;
}
```

**Option 2: FastAPI middleware**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/v1/chunks")
@limiter.limit("100/minute")
async def list_chunks(request: Request):
    ...
```

---

## Input Validation

### Pydantic Validation

All inputs are validated using Pydantic:

```python
class ChunkCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=100000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        for tag in v:
            if len(tag) > 50:
                raise ValueError("Tag too long")
        return v
```

### SQL Injection Prevention

SQLAlchemy ORM uses parameterized queries:

```python
# Safe - parameterized
result = await session.execute(
    select(ChunkTable).where(ChunkTable.id == chunk_id)
)

# Never do this
# result = await session.execute(f"SELECT * FROM chunks WHERE id = '{chunk_id}'")
```

### XSS Prevention

React automatically escapes content:

```tsx
// Safe - React escapes this
<div>{chunk.content}</div>

// Dangerous - avoid unless necessary
<div dangerouslySetInnerHTML={{__html: chunk.content}} />
```

---

## Dependency Security

### Keeping Dependencies Updated

```bash
# Check for vulnerabilities
pip audit

# Update dependencies
pip install --upgrade -e ".[dev]"

# NPM audit
cd frontend
npm audit
npm audit fix
```

### Pinning Versions

In production, pin dependency versions:

```toml
# pyproject.toml
dependencies = [
    "fastapi==0.109.0",
    "uvicorn[standard]==0.27.0",
    # ... pin all versions
]
```

### Known Vulnerabilities

Check before deploying:
- [PyPI Advisory Database](https://pypi.org/security/)
- [NPM Advisories](https://www.npmjs.com/advisories)
- [GitHub Security Advisories](https://github.com/advisories)

---

## MCP Security

### Token Security

MCP servers may require tokens (e.g., GitHub token):

```json
{
  "env": {"GITHUB_TOKEN": "ghp_..."}
}
```

**Best Practices:**
- Use tokens with minimal required permissions
- Rotate tokens regularly (every 90 days)
- Use separate tokens per environment
- Store tokens encrypted in database

### MCP Server Trust

Only register trusted MCP servers:

```python
# Validate server source before registration
ALLOWED_MCP_PACKAGES = [
    "@modelcontextprotocol/server-github",
    "@modelcontextprotocol/server-filesystem",
    "@modelcontextprotocol/server-memory",
]
```

### Process Isolation

MCP servers run as child processes. Consider:
- Running in containers for isolation
- Limiting resource usage
- Monitoring for unusual activity

---

## Production Hardening

### Checklist

- [ ] **Authentication** - Implement JWT or API keys
- [ ] **HTTPS** - Use TLS 1.2+
- [ ] **CORS** - Restrict to your domains
- [ ] **Rate Limiting** - Prevent abuse
- [ ] **Logging** - Monitor for suspicious activity
- [ ] **Secrets** - Use environment variables or secrets manager
- [ ] **Updates** - Keep dependencies current
- [ ] **Backups** - Regular encrypted backups
- [ ] **Monitoring** - Alert on anomalies
- [ ] **Firewall** - Block unnecessary ports

### Security Headers

Add via reverse proxy:

```nginx
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
add_header Content-Security-Policy "default-src 'self'";
```

### Logging for Security

Log security-relevant events:

```python
import logging

security_logger = logging.getLogger("security")

# Log authentication attempts
security_logger.info(f"Login attempt: user={username}, ip={ip}")

# Log access to sensitive data
security_logger.info(f"Chunk accessed: id={chunk_id}, user={user}")

# Log administrative actions
security_logger.warning(f"MCP server registered: {server_name}")
```

---

## Vulnerability Reporting

### Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. **Email** security concerns to the maintainers
3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

| Action | Timeline |
|--------|----------|
| Acknowledgment | 48 hours |
| Initial assessment | 7 days |
| Fix development | 30 days |
| Public disclosure | After fix released |

### Security Advisories

Security fixes will be documented in:
- CHANGELOG.md
- GitHub Security Advisories
- Release notes

---

## Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/20/core/security.html)
- [React Security](https://reactjs.org/docs/dom-elements.html#dangerouslysetinnerhtml)

---

*For deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md). For configuration, see [CONFIGURATION.md](./CONFIGURATION.md).*
