---
name: write-tests
description: Generate comprehensive test suites for existing code following pytest and async patterns. Use for unit tests, integration tests, API tests.
agent: agent
tools: ['agent', 'edit', 'execute', 'read', 'search', 'todo', 'vscode', 'web', 'gitkraken/*', 'github/*', 'vscode.mermaid-chat-features/renderMermaidDiagram', 'pylance-mcp-server/*']
---

# Write Tests

## Governance (MUST Follow)

### Pre-1.0.0 Documentation Rule
**CRITICAL:** Always keep documentation synchronized with code changes.

- ✅ Update `CURRENT_STATUS.md` with version and date on every release
- ✅ Keep `CHANGELOG.md`, `CONVENTIONS.md`, `BUILD.md`, `PROGRESS.md` synchronized

### Technical Constraints

**Testing Stack:**
- `pytest` + `pytest-asyncio` for async test support
- `TestClient` from FastAPI for API testing
- Mock external dependencies (databases, APIs, MCP tools)
- Aim for >80% code coverage on new code

**Code Quality Gates:**
- ✅ All tests must pass before committing
- ✅ Use `@pytest.mark.asyncio` for async tests
- ✅ Test both happy path and error cases
- ✅ Mock external dependencies (no real API calls in tests)

---

## Task Context

You are writing comprehensive tests for existing Komorebi code. Focus on:
1. **Coverage:** Happy path + edge cases + error cases
2. **Clarity:** Test names clearly describe what they test
3. **Independence:** Tests don't depend on each other
4. **Speed:** Mock slow operations (database, network)

---

## Test Structure

### File Organization

```
backend/tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_models/
│   ├── test_chunk.py
│   └── test_project.py
├── test_api/
│   ├── test_chunks.py
│   ├── test_projects.py
│   └── test_mcp.py
├── test_services/
│   ├── test_compactor.py
│   └── test_summarizer.py
└── test_integration/
    └── test_end_to_end.py
```

### Test Naming Convention

```python
# Pattern: test_<function_name>_<scenario>
def test_create_chunk_success():           # Happy path
def test_create_chunk_validation_error():  # Error case
def test_create_chunk_duplicate():         # Edge case
def test_get_chunk_not_found():            # Error case
def test_list_chunks_pagination():         # Feature test
def test_list_chunks_empty():              # Edge case
```

---

## Backend Testing Patterns

### API Endpoint Tests

```python
# backend/tests/test_api/test_chunks.py
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_create_chunk_success():
    """Test that POST /chunks creates a chunk in inbox status."""
    response = client.post("/api/v1/chunks", json={
        "content": "Test chunk content",
        "tags": ["test", "pytest"],
        "source": "test_suite"
    })
    
    # Assert response
    assert response.status_code == 201
    data = response.json()
    
    # Assert structure
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    
    # Assert values
    assert data["content"] == "Test chunk content"
    assert data["status"] == "inbox"
    assert data["tags"] == ["test", "pytest"]
    assert data["source"] == "test_suite"

@pytest.mark.asyncio
async def test_create_chunk_validation_error():
    """Test that POST /chunks validates required fields."""
    response = client.post("/api/v1/chunks", json={
        "content": "",  # Empty content should fail
        "tags": []
    })
    
    assert response.status_code == 422  # Unprocessable Entity
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_create_chunk_missing_field():
    """Test that POST /chunks requires content field."""
    response = client.post("/api/v1/chunks", json={
        "tags": ["test"]
        # Missing required "content" field
    })
    
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_get_chunk_success():
    """Test that GET /chunks/{id} returns chunk details."""
    # Create a chunk first
    create_response = client.post("/api/v1/chunks", json={
        "content": "Test chunk for retrieval",
        "tags": ["test"]
    })
    chunk_id = create_response.json()["id"]
    
    # Retrieve it
    response = client.get(f"/api/v1/chunks/{chunk_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == chunk_id
    assert data["content"] == "Test chunk for retrieval"

@pytest.mark.asyncio
async def test_get_chunk_not_found():
    """Test that GET /chunks/{id} returns 404 for missing chunk."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/chunks/{fake_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_get_chunk_invalid_uuid():
    """Test that GET /chunks/{id} handles invalid UUID format."""
    response = client.get("/api/v1/chunks/not-a-valid-uuid")
    
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_list_chunks_pagination():
    """Test that GET /chunks supports limit and offset."""
    # Create 10 chunks
    for i in range(10):
        client.post("/api/v1/chunks", json={
            "content": f"Test chunk {i}",
            "tags": ["pagination-test"]
        })
    
    # Test limit
    response = client.get("/api/v1/chunks?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5
    
    # Test offset
    response = client.get("/api/v1/chunks?limit=5&offset=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5

@pytest.mark.asyncio
async def test_list_chunks_filter_by_status():
    """Test that GET /chunks supports status filtering."""
    # Create chunks with different statuses
    create_response = client.post("/api/v1/chunks", json={
        "content": "Inbox chunk",
        "tags": []
    })
    chunk_id = create_response.json()["id"]
    
    # Update to processed
    client.patch(f"/api/v1/chunks/{chunk_id}", json={
        "status": "processed"
    })
    
    # Filter by status
    response = client.get("/api/v1/chunks?status=processed")
    assert response.status_code == 200
    data = response.json()
    assert all(chunk["status"] == "processed" for chunk in data)

@pytest.mark.asyncio
async def test_list_chunks_empty():
    """Test that GET /chunks returns empty list when no chunks exist."""
    # Note: This test assumes a clean database or proper teardown
    response = client.get("/api/v1/chunks?limit=1000")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_update_chunk_success():
    """Test that PATCH /chunks/{id} updates chunk fields."""
    # Create chunk
    create_response = client.post("/api/v1/chunks", json={
        "content": "Original content",
        "tags": ["original"]
    })
    chunk_id = create_response.json()["id"]
    
    # Update it
    response = client.patch(f"/api/v1/chunks/{chunk_id}", json={
        "content": "Updated content",
        "status": "processed",
        "summary": "Test summary"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Updated content"
    assert data["status"] == "processed"
    assert data["summary"] == "Test summary"

@pytest.mark.asyncio
async def test_update_chunk_not_found():
    """Test that PATCH /chunks/{id} returns 404 for missing chunk."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.patch(f"/api/v1/chunks/{fake_id}", json={
        "content": "Updated content"
    })
    
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_chunk_success():
    """Test that DELETE /chunks/{id} removes chunk."""
    # Create chunk
    create_response = client.post("/api/v1/chunks", json={
        "content": "Chunk to delete",
        "tags": []
    })
    chunk_id = create_response.json()["id"]
    
    # Delete it
    response = client.delete(f"/api/v1/chunks/{chunk_id}")
    assert response.status_code == 204  # No Content
    
    # Verify it's gone
    get_response = client.get(f"/api/v1/chunks/{chunk_id}")
    assert get_response.status_code == 404

@pytest.mark.asyncio
async def test_delete_chunk_not_found():
    """Test that DELETE /chunks/{id} returns 404 for missing chunk."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.delete(f"/api/v1/chunks/{fake_id}")
    
    assert response.status_code == 404
```

### Pydantic Model Tests

```python
# backend/tests/test_models/test_chunk.py
import pytest
from pydantic import ValidationError
from backend.app.models.chunk import ChunkCreate, ChunkUpdate, Chunk, ChunkStatus

def test_chunk_create_valid():
    """Test that ChunkCreate accepts valid data."""
    chunk = ChunkCreate(
        content="Test content",
        tags=["test", "valid"],
        source="test_suite"
    )
    
    assert chunk.content == "Test content"
    assert chunk.tags == ["test", "valid"]
    assert chunk.source == "test_suite"

def test_chunk_create_minimal():
    """Test that ChunkCreate works with only required fields."""
    chunk = ChunkCreate(content="Minimal chunk")
    
    assert chunk.content == "Minimal chunk"
    assert chunk.tags == []
    assert chunk.source is None

def test_chunk_create_empty_content_fails():
    """Test that ChunkCreate rejects empty content."""
    with pytest.raises(ValidationError) as exc_info:
        ChunkCreate(content="")
    
    assert "content" in str(exc_info.value).lower()

def test_chunk_create_invalid_type_fails():
    """Test that ChunkCreate validates field types."""
    with pytest.raises(ValidationError):
        ChunkCreate(content=123)  # Should be string
    
    with pytest.raises(ValidationError):
        ChunkCreate(content="Valid", tags="not-a-list")  # Should be list

def test_chunk_update_partial():
    """Test that ChunkUpdate allows partial updates."""
    update = ChunkUpdate(content="New content")
    
    assert update.content == "New content"
    assert update.status is None
    assert update.summary is None

def test_chunk_status_enum():
    """Test that ChunkStatus enum has expected values."""
    assert ChunkStatus.INBOX == "inbox"
    assert ChunkStatus.PROCESSED == "processed"
    assert ChunkStatus.COMPACTED == "compacted"
    assert ChunkStatus.ARCHIVED == "archived"

def test_chunk_full_model():
    """Test that Chunk model serializes correctly."""
    from uuid import uuid4
    from datetime import datetime
    
    chunk = Chunk(
        id=uuid4(),
        content="Test content",
        summary="Test summary",
        project_id=None,
        status=ChunkStatus.INBOX,
        tags=["test"],
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    )
    
    # Test serialization
    data = chunk.model_dump(mode="json")
    assert "id" in data
    assert data["content"] == "Test content"
    assert data["status"] == "inbox"
```

### Service/Business Logic Tests

```python
# backend/tests/test_services/test_compactor.py
import pytest
from backend.app.services.compactor import CompactionService

@pytest.mark.asyncio
async def test_compact_single_chunk():
    """Test that compactor handles single chunk."""
    service = CompactionService()
    chunks = [{"content": "Test content", "id": "1"}]
    
    result = await service.compact(chunks)
    
    assert result is not None
    assert "summary" in result
    assert len(result["summary"]) < len(chunks[0]["content"])

@pytest.mark.asyncio
async def test_compact_multiple_chunks():
    """Test that compactor merges multiple chunks."""
    service = CompactionService()
    chunks = [
        {"content": "First chunk", "id": "1"},
        {"content": "Second chunk", "id": "2"},
        {"content": "Third chunk", "id": "3"},
    ]
    
    result = await service.compact(chunks)
    
    assert result is not None
    assert "summary" in result
    assert "merged_ids" in result
    assert len(result["merged_ids"]) == 3

@pytest.mark.asyncio
async def test_compact_empty_chunks():
    """Test that compactor handles empty input."""
    service = CompactionService()
    chunks = []
    
    result = await service.compact(chunks)
    
    assert result is None or result == {}

@pytest.mark.asyncio
async def test_compact_preserves_context():
    """Test that compactor includes System Anchor to prevent drift."""
    service = CompactionService()
    chunks = [{"content": "Random content", "id": "1"}]
    
    result = await service.compact(chunks)
    
    # Verify system anchor was injected
    assert "system_anchor" in result or "context" in result
```

### Fixture Examples

```python
# backend/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.db.database import Base, get_db

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db():
    """Create a fresh test database for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
def client(test_db):
    """Create a test client with test database."""
    def override_get_db():
        return test_db
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
async def sample_chunk(test_db):
    """Create a sample chunk for testing."""
    from backend.app.models.chunk import ChunkCreate
    from backend.app.repositories.chunk import ChunkRepository
    
    repo = ChunkRepository(test_db)
    chunk = await repo.create(ChunkCreate(
        content="Sample chunk for testing",
        tags=["sample", "fixture"]
    ))
    return chunk
```

---

## Frontend Testing Patterns

### Component Tests (Future)

```typescript
// frontend/src/components/__tests__/ChunkList.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { ChunkList } from '../ChunkList'
import { chunks, loading } from '../../store/chunks'

describe('ChunkList', () => {
    beforeEach(() => {
        // Reset signals
        chunks.value = []
        loading.value = false
    })
    
    it('renders loading state', () => {
        loading.value = true
        render(<ChunkList />)
        expect(screen.getByText(/loading/i)).toBeInTheDocument()
    })
    
    it('renders chunks when loaded', () => {
        chunks.value = [
            { id: '1', content: 'Test chunk 1', status: 'inbox' },
            { id: '2', content: 'Test chunk 2', status: 'processed' },
        ]
        render(<ChunkList />)
        expect(screen.getByText(/Test chunk 1/)).toBeInTheDocument()
        expect(screen.getByText(/Test chunk 2/)).toBeInTheDocument()
    })
    
    it('filters chunks by status', async () => {
        chunks.value = [
            { id: '1', content: 'Inbox chunk', status: 'inbox' },
            { id: '2', content: 'Processed chunk', status: 'processed' },
        ]
        render(<ChunkList />)
        
        // Click "processed" filter
        const processedButton = screen.getByText(/processed/i)
        processedButton.click()
        
        await waitFor(() => {
            expect(screen.getByText(/Processed chunk/)).toBeInTheDocument()
            expect(screen.queryByText(/Inbox chunk/)).not.toBeInTheDocument()
        })
    })
})
```

---

## Test Coverage Goals

### Coverage Targets

| Module Type | Target Coverage | Priority |
|-------------|----------------|----------|
| API Endpoints | >90% | Critical |
| Pydantic Models | >85% | High |
| Business Logic | >80% | High |
| Repositories | >75% | Medium |
| Utilities | >70% | Medium |

### Coverage Commands

```bash
# Run tests with coverage
pytest --cov=backend/app --cov-report=html

# Open coverage report
open htmlcov/index.html

# Run tests with coverage threshold
pytest --cov=backend/app --cov-fail-under=80
```

---

## Test Execution Workflow

### Step 1: Identify Code to Test

1. Review the module/function to be tested
2. Identify all code paths (happy path, error cases, edge cases)
3. List external dependencies that need mocking
4. Plan test structure

### Step 2: Write Test Cases

For each function/endpoint, write tests for:
1. **Happy path:** Normal, expected usage
2. **Validation errors:** Invalid input data
3. **Not found errors:** Missing resources
4. **Edge cases:** Empty data, boundary conditions
5. **Error handling:** Database errors, network failures

### Step 3: Implement Tests

1. Create test file in appropriate directory
2. Write test functions with descriptive names
3. Use fixtures for setup/teardown
4. Assert all relevant aspects (status codes, data structure, values)
5. Run tests: `pytest backend/tests/test_<module>.py -v`

### Step 4: Verify Coverage

1. Run with coverage: `pytest --cov=backend/app/<module>`
2. Check coverage percentage
3. Identify uncovered lines
4. Add tests for uncovered code paths

### Step 5: Refactor Tests

1. Extract common setup into fixtures
2. Reduce duplication with parameterized tests
3. Improve test names for clarity
4. Verify tests still pass after refactoring

---

## Common Testing Patterns

### Parameterized Tests

```python
@pytest.mark.parametrize("content,expected_status", [
    ("Valid content", 201),
    ("", 422),                    # Empty content
    ("A" * 100000, 422),          # Too long
])
@pytest.mark.asyncio
async def test_create_chunk_validation(content, expected_status):
    """Test chunk creation with various inputs."""
    response = client.post("/api/v1/chunks", json={"content": content})
    assert response.status_code == expected_status
```

### Mocking External Dependencies

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
@patch('backend.app.services.mcp.MCPClient.query')
async def test_mcp_query_success(mock_query):
    """Test MCP query with mocked client."""
    mock_query.return_value = AsyncMock(return_value={"result": "mocked"})
    
    service = MCPService()
    result = await service.query("test query")
    
    assert result == {"result": "mocked"}
    mock_query.assert_called_once_with("test query")
```

### Testing Async Functions

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function with await."""
    result = await some_async_function()
    assert result == expected_value
```

### Testing Exceptions

```python
@pytest.mark.asyncio
async def test_function_raises_exception():
    """Test that function raises expected exception."""
    with pytest.raises(ValueError, match="Invalid input"):
        await function_that_should_raise("invalid")
```

---

## Output Format

**Provide the following deliverables:**

1. **Test File(s):**
   - Path: `backend/tests/test_<module>.py`
   - Organized by function/endpoint
   - Clear, descriptive test names
   - Comprehensive coverage (happy path + edge cases + errors)

2. **Fixtures (if needed):**
   - Path: `backend/tests/conftest.py`
   - Reusable setup/teardown logic
   - Sample data generators

3. **Coverage Report:**
   - Run: `pytest --cov=backend/app/<module> --cov-report=term`
   - Document coverage percentage
   - Identify any gaps

4. **Summary:**
   - List of test cases added
   - Coverage improvement (before → after)
   - Any limitations or areas not tested

**Do NOT:**
- Write tests that depend on execution order
- Include real API calls or database queries (mock instead)
- Leave commented-out test code
- Write tests without assertions

---

## Example: Complete Test Suite

**Target:** `backend/app/api/chunks.py` with endpoints for CRUD operations

```python
# backend/tests/test_api/test_chunks.py
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

# CREATE
@pytest.mark.asyncio
async def test_create_chunk_success():
    response = client.post("/api/v1/chunks", json={
        "content": "Test chunk",
        "tags": ["test"]
    })
    assert response.status_code == 201
    assert response.json()["content"] == "Test chunk"

@pytest.mark.asyncio
async def test_create_chunk_validation_error():
    response = client.post("/api/v1/chunks", json={"content": ""})
    assert response.status_code == 422

# READ
@pytest.mark.asyncio
async def test_get_chunk_success():
    create_resp = client.post("/api/v1/chunks", json={"content": "Test"})
    chunk_id = create_resp.json()["id"]
    
    response = client.get(f"/api/v1/chunks/{chunk_id}")
    assert response.status_code == 200
    assert response.json()["id"] == chunk_id

@pytest.mark.asyncio
async def test_get_chunk_not_found():
    response = client.get("/api/v1/chunks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404

# LIST
@pytest.mark.asyncio
async def test_list_chunks_pagination():
    for i in range(10):
        client.post("/api/v1/chunks", json={"content": f"Chunk {i}"})
    
    response = client.get("/api/v1/chunks?limit=5")
    assert response.status_code == 200
    assert len(response.json()) <= 5

# UPDATE
@pytest.mark.asyncio
async def test_update_chunk_success():
    create_resp = client.post("/api/v1/chunks", json={"content": "Original"})
    chunk_id = create_resp.json()["id"]
    
    response = client.patch(f"/api/v1/chunks/{chunk_id}", json={"content": "Updated"})
    assert response.status_code == 200
    assert response.json()["content"] == "Updated"

@pytest.mark.asyncio
async def test_update_chunk_not_found():
    response = client.patch(
        "/api/v1/chunks/00000000-0000-0000-0000-000000000000",
        json={"content": "Updated"}
    )
    assert response.status_code == 404

# DELETE
@pytest.mark.asyncio
async def test_delete_chunk_success():
    create_resp = client.post("/api/v1/chunks", json={"content": "To delete"})
    chunk_id = create_resp.json()["id"]
    
    response = client.delete(f"/api/v1/chunks/{chunk_id}")
    assert response.status_code == 204
    
    get_resp = client.get(f"/api/v1/chunks/{chunk_id}")
    assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_chunk_not_found():
    response = client.delete("/api/v1/chunks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
```

**Coverage Result:**
```
backend/app/api/chunks.py    95%    ✅
```

---

**Ready to write comprehensive tests!** Follow the patterns above and aim for >80% coverage.
