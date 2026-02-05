# Komorebi Troubleshooting Guide

*Solutions to common problems and frequently asked questions.*

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Installation Issues](#installation-issues)
3. [Server Issues](#server-issues)
4. [Database Issues](#database-issues)
5. [CLI Issues](#cli-issues)
6. [Frontend Issues](#frontend-issues)
7. [API Issues](#api-issues)
8. [SSE Issues](#sse-issues)
9. [MCP Issues](#mcp-issues)
10. [Performance Issues](#performance-issues)
11. [FAQ](#faq)

---

## Quick Diagnostics

Run these commands to diagnose common issues:

```bash
# 1. Check Python version
python --version  # Should be 3.11+

# 2. Check if server is running
curl http://localhost:8000/health

# 3. Check environment variables
env | grep KOMOREBI

# 4. Check database file exists
ls -la komorebi.db

# 5. Check port availability
lsof -i :8000

# 6. Run tests
python -m pytest -v
```

---

## Installation Issues

### "ModuleNotFoundError: No module named 'cli'"

**Problem:** Running `python -m cli.main` fails with module not found.

**Cause:** The `komorebi` package is not installed. The CLI requires installation via pip.

**Solution:**

```bash
# Navigate to the project root directory
cd /path/to/komorebi

# Install the package in editable mode
pip install -e ".[dev]"

# Now use the 'komorebi' command (NOT python -m cli.main)
komorebi serve
komorebi capture "My first thought!"
komorebi list
```

**Verify installation:**

```bash
# Check komorebi is installed
pip show komorebi

# Check CLI is available
which komorebi
# Should output: /path/to/python/bin/komorebi
```

> **Note:** After running `pip install -e .`, the `komorebi` command becomes available globally in your Python environment. Always use `komorebi` instead of `python -m cli.main`.

### "Module not found" errors (other modules)

**Problem:** Python can't find backend or other modules.

**Solution:**

```bash
# Install in editable mode
pip install -e ".[dev]"

# Verify installation
pip show komorebi
```

### "Python version mismatch"

**Problem:** Python version is too old.

**Solution:**

```bash
# Check version
python --version

# Use specific version (if pyenv)
pyenv install 3.12
pyenv local 3.12

# Then reinstall
pip install -e ".[dev]"
komorebi serve
```

### "pip install fails"

**Problem:** Missing system dependencies.

**Solution (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install python3-dev build-essential
```

**Solution (macOS):**

```bash
xcode-select --install
```

### "node_modules issues"

**Problem:** Frontend dependencies won't install.

**Solution:**

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

## Server Issues

### "Connection refused" on port 8000

**Problem:** Server isn't running.

**Solutions:**

```bash
# Start the server
komorebi serve

# Check if something else is using the port
lsof -i :8000

# Use a different port
komorebi serve --port 9000
```

### "Address already in use"

**Problem:** Port 8000 is occupied.

**Solutions:**

```bash
# Find and kill the process
lsof -i :8000
kill -9 <PID>

# Or use a different port
komorebi serve --port 8001
```

### Server starts but immediately stops

**Problem:** Crash on startup.

**Solutions:**

```bash
# Run with verbose output
uvicorn backend.app.main:app --reload --log-level debug

# Check for import errors
python -c "from backend.app.main import app"
```

### Server hangs on startup

**Problem:** Database initialization stuck.

**Solutions:**

```bash
# Delete database and restart
rm komorebi.db
komorebi serve

# Check for locked database
fuser komorebi.db
```

---

## Database Issues

### "Database is locked"

**Problem:** SQLite write lock contention.

**Solutions:**

```bash
# Find processes using the database
fuser komorebi.db

# Kill stale connections
kill $(fuser komorebi.db 2>/dev/null)

# Or delete and recreate
rm komorebi.db komorebi.db-journal
```

### "No such table" errors

**Problem:** Database not initialized.

**Solutions:**

```bash
# Delete database (will be recreated)
rm komorebi.db

# Restart server
komorebi serve
```

### Database file too large

**Problem:** SQLite file growing indefinitely.

**Solutions:**

```bash
# Vacuum the database
sqlite3 komorebi.db "VACUUM;"

# Check size
ls -lh komorebi.db
```

### PostgreSQL connection failed

**Problem:** Can't connect to PostgreSQL.

**Solutions:**

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection
psql -h localhost -U postgres -d komorebi

# Check environment variable
echo $KOMOREBI_DATABASE_URL
```

---

## CLI Issues

### "CLI can't connect to server"

**Problem:** API URL is wrong or server isn't running.

**Solutions:**

```bash
# Check server is running
curl http://localhost:8000/health

# Set correct API URL
export KOMOREBI_API_URL=http://localhost:8000/api/v1

# Verify
komorebi stats
```

### "CLI shows error: Could not connect"

**Problem:** Network or server issue.

**Solutions:**

```bash
# Verify server is reachable
ping localhost
curl -v http://localhost:8000/health

# Check firewall
sudo ufw status
```

### CLI output is garbled

**Problem:** Terminal encoding issues.

**Solutions:**

```bash
# Set UTF-8 encoding
export LANG=en_US.UTF-8

# Or try without rich formatting
python -c "from cli.main import app; app()" --no-color
```

---

## Frontend Issues

### "npm run dev fails"

**Problem:** Build errors or missing dependencies.

**Solutions:**

```bash
cd frontend

# Clear and reinstall
rm -rf node_modules
npm install

# Check for Node version issues
node --version  # Should be 18+
```

### "Vite proxy error"

**Problem:** Backend isn't running on expected port.

**Solutions:**

```bash
# Start backend first
komorebi serve

# Then start frontend
cd frontend
npm run dev
```

### White screen / React errors

**Problem:** JavaScript errors preventing render.

**Solutions:**

1. Open browser DevTools (F12)
2. Check Console for errors
3. Clear browser cache
4. Try incognito mode

### CORS errors

**Problem:** Browser blocking cross-origin requests.

**Solutions:**

```bash
# Check CORS configuration in backend
grep -r "CORSMiddleware" backend/

# In development, backend allows all origins by default
# Verify by checking response headers
curl -v http://localhost:8000/health
```

---

## API Issues

### 404 Not Found

**Problem:** Endpoint doesn't exist or wrong URL.

**Solutions:**

```bash
# Check available endpoints
curl http://localhost:8000/openapi.json | jq '.paths | keys'

# Verify URL format
# Correct: /api/v1/chunks
# Wrong:   /chunks, /api/chunks
```

### 422 Validation Error

**Problem:** Invalid request body.

**Solutions:**

```bash
# Check the error message for details
curl -X POST http://localhost:8000/api/v1/chunks \
  -H "Content-Type: application/json" \
  -d '{"content": ""}' 2>&1 | jq

# Common issues:
# - Missing required fields
# - Wrong data types
# - Empty strings when content required
```

### 500 Internal Server Error

**Problem:** Backend crash.

**Solutions:**

```bash
# Check server logs
# If using uvicorn:
# The terminal shows the traceback

# If using systemd:
journalctl -u komorebi -n 50

# Enable debug mode for more info
KOMOREBI_DEBUG=true komorebi serve
```

---

## SSE Issues

### SSE not receiving events

**Problem:** Events not reaching the client.

**Diagnosis:**

```bash
# Test SSE directly
curl -N http://localhost:8000/api/v1/sse/events

# Should immediately show:
event: connected
data: {"message": "SSE connection established"}

# In another terminal, create a chunk
curl -X POST http://localhost:8000/api/v1/chunks \
  -H "Content-Type: application/json" \
  -d '{"content": "Test"}'

# Should see event in first terminal:
event: chunk.created
data: {...}
```

**If curl returns immediately with no output:**
- Backend generator is failing before first yield
- Check server logs for Python exceptions
- Verify `ServerSentEvent` class is being used (not raw dicts)
- Check that async generator error handling is correct

**Solutions:**

1. **Verify implementation uses ServerSentEvent:**
   ```python
   from sse_starlette.sse import ServerSentEvent
   
   # CORRECT:
   yield ServerSentEvent(event="test", data=json.dumps({...}))
   
   # WRONG (can fail silently):
   yield {"event": "test", "data": json.dumps({...})}
   ```

2. **Check subscriber count:**
   ```bash
   curl http://localhost:8000/api/v1/sse/status
   # Should show {"subscribers": 1, ...} when client connected
   ```

3. **Enable debug logging:**
   ```python
   # In main.py:
   import logging
   logging.basicConfig(level=logging.INFO)
   ```

### SSE connection drops immediately

**Problem:** Connection opens then closes right away (onerror fires immediately).

**Root Cause:** "Silent generator crash" - exception before first yield causes HTTP 200 but empty body.

**Solutions:**

1. **Protect subscriber setup:**
   ```python
   try:
       async with lock:
           subscribers.append(queue)
   except Exception as e:
       logging.error(f"Failed to add subscriber: {e}")
       return  # Exit cleanly
   ```

2. **Always yield initial message:**
   ```python
   # First yield should be simple and guaranteed to work
   yield ServerSentEvent(
       event="connected",
       data=json.dumps({"message": "connected"})
   )
   ```

3. **Check logs for errors before first yield**

### SSE timeout or keep-alive issues

**Problem:** Connection drops after 30-60 seconds.

**Solutions:**

1. **Use EventSourceResponse ping parameter:**
   ```python
   return EventSourceResponse(
       event_bus.subscribe(),
       ping=15  # Send keep-alive every 15 seconds
   )
   ```

2. **Do NOT implement manual ping with asyncio.wait_for** - this is an antipattern

3. **If behind nginx, disable buffering:**
   ```nginx
   location /api/v1/sse/ {
       proxy_buffering off;
       proxy_cache off;
       proxy_read_timeout 86400s;
       proxy_set_header X-Accel-Buffering no;
   }
   ```

### Browser shows SSE errors

**Problem:** CORS or connection issues.

**Solutions:**

1. Check browser DevTools Network tab:
   - Look for EventSource type requests
   - Check response headers (should show `text/event-stream`)
   - Look at response preview for any error messages

2. Verify CORS headers allow EventSource:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. Test from same origin first (eliminates CORS issues)

4. Check server logs for connection/disconnection messages

### Zero subscribers despite client connection

**Problem:** `/api/v1/sse/status` shows 0 subscribers but client appears connected.

**Root Cause:** Subscriber list cleanup happening too early (generator exiting immediately).

**Solutions:**

1. Check that generator has infinite loop:
   ```python
   while True:  # Should run indefinitely
       event = await queue.get()
       yield ServerSentEvent(...)
   ```

2. Verify cleanup only happens in finally block

3. Check for exceptions that exit the generator early

---

## MCP Issues

### MCP server won't connect

**Problem:** Server process can't start.

**Solutions:**

```bash
# Test MCP command directly
npx -y @modelcontextprotocol/server-github

# Check if npx is installed
which npx

# Check GitHub token (for GitHub MCP)
echo $GITHUB_TOKEN
```

### MCP tools not appearing

**Problem:** Server connected but no tools listed.

**Solutions:**

```bash
# Check server status
curl http://localhost:8000/api/v1/mcp/servers

# Try reconnecting
curl -X POST http://localhost:8000/api/v1/mcp/servers/{id}/disconnect
curl -X POST http://localhost:8000/api/v1/mcp/servers/{id}/connect
```

### MCP timeout errors

**Problem:** Server takes too long to respond.

**Solutions:**

- MCP servers can be slow on first start
- Wait for npm package download
- Check network connectivity

---

## Performance Issues

### Slow API responses

**Problem:** Requests taking too long.

**Solutions:**

```bash
# Enable SQL debugging
KOMOREBI_DEBUG=true komorebi serve

# Check for N+1 queries in logs
# Add database indexes if needed
```

### High memory usage

**Problem:** Memory growing over time.

**Solutions:**

```bash
# Monitor memory
watch -n 1 'ps aux | grep python'

# Restart server periodically
# Use Gunicorn's max_requests option
gunicorn ... --max-requests 1000
```

### Slow frontend

**Problem:** Dashboard is sluggish.

**Solutions:**

1. Check network tab for slow requests
2. Reduce items per page
3. Check for React re-render issues
4. Build production bundle: `npm run build`

---

## FAQ

### How do I reset everything?

```bash
# Stop server
# Ctrl+C or kill the process

# Delete database
rm komorebi.db

# Clear frontend state
cd frontend
rm -rf node_modules/.cache

# Restart
komorebi serve
```

### How do I backup my data?

```bash
# SQLite
cp komorebi.db komorebi.db.backup

# PostgreSQL
pg_dump -h localhost -U postgres komorebi > backup.sql
```

### How do I change the port?

```bash
# CLI flag
komorebi serve --port 9000

# Environment variable
KOMOREBI_PORT=9000 komorebi serve

# Update CLI API URL too
export KOMOREBI_API_URL=http://localhost:9000/api/v1
```

### How do I enable debug mode?

```bash
export KOMOREBI_DEBUG=true
komorebi serve --reload
```

### Where are logs stored?

- **Development:** Printed to terminal
- **Systemd:** `journalctl -u komorebi`
- **Docker:** `docker logs komorebi_backend_1`

### How do I update Komorebi?

```bash
git pull
pip install -e ".[dev]"
# Restart server
```

### Can I use MySQL instead of SQLite?

Yes, but it requires additional setup:

```bash
pip install aiomysql
export KOMOREBI_DATABASE_URL="mysql+aiomysql://user:pass@localhost/komorebi"
```

### How do I run in production?

See [DEPLOYMENT.md](./DEPLOYMENT.md) for full instructions.

---

## Getting More Help

If you can't find a solution:

1. **Search existing issues** on GitHub
2. **Create a new issue** with:
   - Error message
   - Steps to reproduce
   - Environment details
3. **Include logs** (sanitize sensitive data)

---

*For deployment help, see [DEPLOYMENT.md](./DEPLOYMENT.md). For configuration, see [CONFIGURATION.md](./CONFIGURATION.md).*
