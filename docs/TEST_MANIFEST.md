# Komorebi Test Manifest

This document provides a comprehensive overview of all tests in the Komorebi project, including:
- **Automated Tests** - Unit tests, integration tests, and benchmarks
- **Human Tests** - Manual verification procedures for confirming functionality

## Test Infrastructure

### Test Framework
- **pytest** (>=7.4.0) - Python testing framework
- **pytest-asyncio** (>=0.23.0) - Async test support
- **pytest-httpx** (>=0.28.0) - HTTP mocking for tests

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest backend/tests/test_api.py

# Run specific test class
python -m pytest backend/tests/test_models.py::TestChunkModels

# Run specific test
python -m pytest backend/tests/test_api.py::test_create_chunk
```

---

## Test Files

### `backend/tests/test_models.py`

Tests for Pydantic data models. These tests validate the schema definitions and data validation rules.

| Test Class | Test Name | Description |
|------------|-----------|-------------|
| `TestChunkModels` | `test_chunk_create_minimal` | Verifies chunk creation with only required fields |
| `TestChunkModels` | `test_chunk_create_full` | Verifies chunk creation with all optional fields |
| `TestChunkModels` | `test_chunk_model` | Tests the full Chunk model with auto-generated fields (id, timestamps) |
| `TestChunkModels` | `test_chunk_update_partial` | Validates partial update schema (exclude_unset behavior) |
| `TestProjectModels` | `test_project_create` | Verifies project creation schema |
| `TestProjectModels` | `test_project_model` | Tests the full Project model with defaults |
| `TestMCPModels` | `test_mcp_server_config` | Validates MCP server configuration model |

### `backend/tests/test_api.py`

Integration tests for API endpoints. These tests use an async test client to make real HTTP requests against the FastAPI application.

| Test Name | Endpoint | Description |
|-----------|----------|-------------|
| `test_root_endpoint` | `GET /` | Verifies root endpoint returns service info |
| `test_health_endpoint` | `GET /health` | Validates health check endpoint |
| `test_create_chunk` | `POST /api/v1/chunks` | Tests chunk creation via API |
| `test_list_chunks` | `GET /api/v1/chunks` | Tests listing chunks with filters |
| `test_chunk_stats` | `GET /api/v1/chunks/stats` | Validates statistics endpoint |
| `test_create_project` | `POST /api/v1/projects` | Tests project creation |
| `test_list_projects` | `GET /api/v1/projects` | Validates project listing |
| `test_list_mcp_servers` | `GET /api/v1/mcp/servers` | Tests MCP server listing |
| `test_sse_status` | `GET /api/v1/sse/status` | Validates SSE status endpoint |

---

## Validation & Benchmarking

### `scripts/hammer_gen.py`

The Hammer script is the **success criteria** for the Komorebi implementation. It performs load testing and validates that the backend can handle concurrent requests.

#### Usage

```bash
# Run with defaults (50 chunks, 3 projects, 5 concurrent requests)
python scripts/hammer_gen.py

# Custom configuration
python scripts/hammer_gen.py --chunks 100 --projects 5 --concurrency 10

# Against a different server
python scripts/hammer_gen.py --base-url http://production:8000
```

#### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--base-url` | `http://localhost:8000` | Backend server URL |
| `--chunks` | `50` | Number of chunks to create |
| `--projects` | `3` | Number of projects to create |
| `--concurrency` | `5` | Concurrent request limit |

#### What It Tests

1. **Health Check** - Verifies server is running
2. **Project Creation** - Creates test projects
3. **Chunk Capture** - Creates chunks with random content and tags
4. **Read Operations** - Lists chunks and retrieves statistics

#### Success Metrics

The benchmark outputs:
- Total/Successful/Failed requests
- Requests per second throughput
- Latency statistics (avg, min, max)

**Success criteria:** 0 failed requests

---

## Test Coverage Summary

| Category | Test File | Test Count | Status |
|----------|-----------|------------|--------|
| Models | `test_models.py` | 7 | ✅ Passing |
| API | `test_api.py` | 9 | ✅ Passing |
| Benchmark | `hammer_gen.py` | N/A | ✅ Validated |
| **Total** | | **16** | **All Passing** |

---

## Adding New Tests

### Model Tests

Add tests to `backend/tests/test_models.py`:

```python
from backend.app.models import YourModel

class TestYourModel:
    def test_your_model_creation(self):
        model = YourModel(field="value")
        assert model.field == "value"
```

### API Tests

Add tests to `backend/tests/test_api.py`:

```python
@pytest.mark.asyncio
async def test_your_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/your-endpoint")
    assert response.status_code == 200
```

### Test Fixtures

The `client` fixture provides an async HTTP client for API testing:

```python
@pytest.fixture
async def client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

---

## Continuous Integration

Tests are configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["backend/tests"]
```

Run the full test suite before committing:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest -v

# Run benchmark
python scripts/hammer_gen.py
```

---

## Human Testing Procedures

These manual tests should be performed by a human to verify that the system works correctly end-to-end. Complete each test and check off the box when verified.

### Prerequisites Checklist

Before running human tests, ensure:

- [ ] Python 3.11+ is installed (`python --version`)
- [ ] Dependencies are installed (`pip install -e ".[dev]"`)
- [ ] No other service is running on port 8000
- [ ] You have a terminal/command prompt open

---

### HT-1: Server Startup Test

**Purpose:** Verify the backend server starts correctly.

| Step | Action | Expected Result | ✓ |
|------|--------|-----------------|---|
| 1 | Run `python -m cli.main serve` | Server starts without errors | ☐ |
| 2 | Observe terminal output | Shows "Uvicorn running on http://0.0.0.0:8000" | ☐ |
| 3 | Open browser to `http://localhost:8000` | Returns JSON with name "Komorebi" | ☐ |
| 4 | Open browser to `http://localhost:8000/health` | Returns `{"status": "healthy"}` | ☐ |
| 5 | Open browser to `http://localhost:8000/docs` | Swagger UI documentation loads | ☐ |

**Cleanup:** Press `Ctrl+C` to stop the server (keep it running for remaining tests).

---

### HT-2: CLI Capture Test

**Purpose:** Verify the CLI can capture chunks to the inbox.

*Prerequisite: Server must be running (HT-1)*

| Step | Action | Expected Result | ✓ |
|------|--------|-----------------|---|
| 1 | Run `python -m cli.main capture "Test thought from CLI"` | Shows "✅ Captured: [id]..." with status "inbox" | ☐ |
| 2 | Run `python -m cli.main capture "Another thought" --tags "test,manual"` | Shows success with tags | ☐ |
| 3 | Run `python -m cli.main list` | Table shows both captured chunks | ☐ |
| 4 | Verify first chunk shows status "inbox" or "processed" | Status column displays correctly | ☐ |
| 5 | Verify second chunk shows tags "test, manual" | Tags column shows the tags | ☐ |

---

### HT-3: CLI Statistics Test

**Purpose:** Verify statistics are calculated correctly.

*Prerequisite: Complete HT-2 first*

| Step | Action | Expected Result | ✓ |
|------|--------|-----------------|---|
| 1 | Run `python -m cli.main stats` | Statistics table displays | ☐ |
| 2 | Check "Inbox" or "Processed" count | Count is ≥ 2 (from previous test) | ☐ |
| 3 | Check "Total" count | Total matches sum of all statuses | ☐ |

---

### HT-4: API Direct Access Test

**Purpose:** Verify the REST API works directly via curl/HTTP.

*Prerequisite: Server must be running*

| Step | Action | Expected Result | ✓ |
|------|--------|-----------------|---|
| 1 | Run: `curl http://localhost:8000/api/v1/chunks/stats` | JSON with inbox, processed, compacted, archived, total | ☐ |
| 2 | Run: `curl -X POST http://localhost:8000/api/v1/chunks -H "Content-Type: application/json" -d '{"content": "API test chunk"}'` | Returns chunk JSON with id and status "inbox" | ☐ |
| 3 | Run: `curl http://localhost:8000/api/v1/chunks` | Returns array including the new chunk | ☐ |
| 4 | Run: `curl http://localhost:8000/api/v1/chunks/inbox` | Returns only inbox chunks | ☐ |

---

### HT-5: Project Management Test

**Purpose:** Verify projects can be created and managed.

*Prerequisite: Server must be running*

| Step | Action | Expected Result | ✓ |
|------|--------|-----------------|---|
| 1 | Run: `curl -X POST http://localhost:8000/api/v1/projects -H "Content-Type: application/json" -d '{"name": "Test Project", "description": "For manual testing"}'` | Returns project JSON with id | ☐ |
| 2 | Copy the project `id` from the response | ID is a UUID format | ☐ |
| 3 | Run: `python -m cli.main projects` | Table shows "Test Project" | ☐ |
| 4 | Run: `curl http://localhost:8000/api/v1/projects` | Returns array with the project | ☐ |

---

### HT-6: Chunk-to-Project Association Test

**Purpose:** Verify chunks can be associated with projects.

*Prerequisite: Complete HT-5, have a project ID*

| Step | Action | Expected Result | ✓ |
|------|--------|-----------------|---|
| 1 | Run: `curl -X POST http://localhost:8000/api/v1/chunks -H "Content-Type: application/json" -d '{"content": "Chunk for project", "project_id": "<PROJECT_ID>"}'` | Chunk created with project_id set | ☐ |
| 2 | Run: `curl "http://localhost:8000/api/v1/chunks?project_id=<PROJECT_ID>"` | Returns only chunks for that project | ☐ |
| 3 | Run: `python -m cli.main capture "CLI project chunk" --project <PROJECT_ID>` | Success message shown | ☐ |

---

### HT-7: SSE Real-Time Updates Test

**Purpose:** Verify Server-Sent Events work for real-time updates.

*Prerequisite: Server must be running*

| Step | Action | Expected Result | ✓ |
|------|--------|-----------------|---|
| 1 | In Terminal 1, run: `curl -N http://localhost:8000/api/v1/sse/events` | Connection stays open, waiting for events | ☐ |
| 2 | In Terminal 2, run: `python -m cli.main capture "SSE test event"` | Capture succeeds | ☐ |
| 3 | Check Terminal 1 | Shows `data: {...}` with chunk.created event | ☐ |
| 4 | Press `Ctrl+C` in Terminal 1 | SSE connection closes cleanly | ☐ |

---

### HT-8: Hammer Benchmark Test

**Purpose:** Verify the system handles load correctly.

*Prerequisite: Server must be running*

| Step | Action | Expected Result | ✓ |
|------|--------|-----------------|---|
| 1 | Run: `python scripts/hammer_gen.py --chunks 20 --projects 2` | Benchmark starts, shows progress | ☐ |
| 2 | Observe "Server is healthy" message | Health check passes | ☐ |
| 3 | Observe "Creating X projects" | Projects created successfully | ☐ |
| 4 | Observe "Capturing X chunks" with progress | All chunks captured | ☐ |
| 5 | Check final results | "Failed: 0" in results table | ☐ |
| 6 | Verify "✅ All requests successful!" | Benchmark passed | ☐ |

---

### HT-9: Frontend Dashboard Test (Optional)

**Purpose:** Verify the React dashboard works correctly.

*Prerequisites: Server running, Node.js 18+ installed*

| Step | Action | Expected Result | ✓ |
|------|--------|-----------------|---|
| 1 | Run: `cd frontend && npm install` | Dependencies installed | ☐ |
| 2 | Run: `npm run dev` | Vite dev server starts on port 3000 | ☐ |
| 3 | Open browser to `http://localhost:3000` | Dashboard loads with dark theme | ☐ |
| 4 | Check Stats section at top | Shows Inbox, Processed, Compacted, Archived, Total counts | ☐ |
| 5 | Click "📥 Inbox" tab | Shows inbox chunks (if any) | ☐ |
| 6 | Type in capture box and click "📝 Capture" | New chunk appears in list | ☐ |
| 7 | Click "📋 All Chunks" tab | Shows all chunks with filter buttons | ☐ |
| 8 | Click different status filters | List updates to show filtered chunks | ☐ |
| 9 | Click "📁 Projects" tab | Shows project list | ☐ |
| 10 | Click "+ New Project" and create one | Project appears in list | ☐ |

**Cleanup:** Press `Ctrl+C` to stop the frontend dev server.

---

### HT-10: Database Persistence Test

**Purpose:** Verify data persists across server restarts.

| Step | Action | Expected Result | ✓ |
|------|--------|-----------------|---|
| 1 | Run: `python -m cli.main stats` | Note the total count | ☐ |
| 2 | Stop the server (`Ctrl+C`) | Server stops | ☐ |
| 3 | Restart: `python -m cli.main serve` | Server starts again | ☐ |
| 4 | Run: `python -m cli.main stats` | Same total count as step 1 | ☐ |
| 5 | Run: `python -m cli.main list` | Previous chunks still exist | ☐ |

---

### HT-11: Error Handling Test

**Purpose:** Verify the system handles errors gracefully.

| Step | Action | Expected Result | ✓ |
|------|--------|-----------------|---|
| 1 | Stop the server if running | Server stopped | ☐ |
| 2 | Run: `python -m cli.main capture "Test"` | Shows "Error: Could not connect to server" | ☐ |
| 3 | Start the server again | Server running | ☐ |
| 4 | Run: `curl http://localhost:8000/api/v1/chunks/invalid-uuid` | Returns 404 or validation error | ☐ |
| 5 | Run: `curl -X POST http://localhost:8000/api/v1/chunks -H "Content-Type: application/json" -d '{}'` | Returns 422 validation error (content required) | ☐ |

---

### HT-12: Clean Slate Test

**Purpose:** Verify the system can be reset cleanly.

| Step | Action | Expected Result | ✓ |
|------|--------|-----------------|---|
| 1 | Stop the server | Server stopped | ☐ |
| 2 | Run: `rm komorebi.db` | Database file deleted | ☐ |
| 3 | Start server: `python -m cli.main serve` | Server starts, creates new DB | ☐ |
| 4 | Run: `python -m cli.main stats` | All counts are 0 | ☐ |
| 5 | Run: `python -m cli.main list` | Shows "No chunks found" | ☐ |

---

## Human Test Summary

| Test ID | Test Name | Component | Priority |
|---------|-----------|-----------|----------|
| HT-1 | Server Startup | Backend | Critical |
| HT-2 | CLI Capture | CLI | Critical |
| HT-3 | CLI Statistics | CLI | High |
| HT-4 | API Direct Access | Backend API | Critical |
| HT-5 | Project Management | Backend API | High |
| HT-6 | Chunk-to-Project Association | Backend API | Medium |
| HT-7 | SSE Real-Time Updates | Backend SSE | Medium |
| HT-8 | Hammer Benchmark | Backend | Critical |
| HT-9 | Frontend Dashboard | Frontend | Medium |
| HT-10 | Database Persistence | Backend DB | High |
| HT-11 | Error Handling | All | High |
| HT-12 | Clean Slate | Backend DB | Low |

### Minimum Verification

For a quick smoke test, complete at minimum:
- ☐ HT-1 (Server Startup)
- ☐ HT-2 (CLI Capture)
- ☐ HT-4 (API Direct Access)
- ☐ HT-8 (Hammer Benchmark)

### Full Verification

For complete confidence, run all tests HT-1 through HT-12.
