# Komorebi Code Conventions

**Purpose:** This document defines the actual code patterns, styles, and best practices used in the Komorebi codebase. See [copilot-instructions.md](.github/copilot-instructions.md) for vision and directives.

---

## 1. Pydantic Models (Backend)

### Base Schema Pattern
Define separate schemas for create, read, and update operations to enforce validation at each stage:

```python
# From backend/app/models/chunk.py
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class ChunkStatus(str, Enum):
    """Status of a chunk in the processing pipeline."""
    INBOX = "inbox"
    PROCESSED = "processed"
    COMPACTED = "compacted"
    ARCHIVED = "archived"

class ChunkCreate(BaseModel):
    """Schema for creating a new chunk (fast capture)."""
    content: str = Field(..., min_length=1, description="The raw content to capture")
    project_id: Optional[UUID] = Field(None, description="Optional project association")
    tags: list[str] = Field(default_factory=list, description="Optional tags")
    source: Optional[str] = Field(None, description="Where this chunk originated")

class ChunkUpdate(BaseModel):
    """Schema for updating an existing chunk."""
    content: Optional[str] = Field(None, min_length=1)
    status: Optional[ChunkStatus] = Field(None)
    summary: Optional[str] = Field(None)

class Chunk(BaseModel):
    """The fundamental unit - returned from API."""
    id: UUID = Field(default_factory=uuid4)
    content: str
    summary: Optional[str] = None
    project_id: Optional[UUID] = None
    status: ChunkStatus
    tags: list[str]
    created_at: str
    updated_at: str
```

**Rules:**
- Use `Field()` with descriptions for API documentation
- Use `Enum` for fixed value sets (status, types)
- Separate `Create` / `Update` / `Read` schemas
- Use `Optional[T]` for nullable fields, Never use `| None` syntax alone
- Always use `model_dump(mode="json")` when serializing for JSON responses

---

## 2. State Management (Frontend)

### Preact Signals Pattern
Use Preact Signals for fine-grained reactivity without context providers or heavy state management:

```typescript
// From frontend/src/store/index.ts
import { signal, computed } from '@preact/signals-react'

// Simple signals for state
export const chunks = signal<Chunk[]>([])
export const loading = signal(false)
export const error = signal<string | null>(null)

// Computed signals for derived state
export const chunkStats = computed(() => {
    const stats = {
        inbox: 0,
        processed: 0,
        compacted: 0,
        archived: 0,
        total: chunks.value.length,
    }
    chunks.value.forEach(chunk => {
        stats[chunk.status as keyof typeof stats]++
    })
    return stats
})

// Fetch function modifies signals directly
export async function fetchChunks(projectId?: string, limit = 100) {
    loading.value = true
    error.value = null
    try {
        const params = new URLSearchParams()
        if (projectId) params.append('project_id', projectId)
        params.append('limit', limit.toString())
        
        const response = await fetch(`${API_URL}/chunks?${params}`)
        const data = await response.json()
        chunks.value = data
    } catch (err) {
        error.value = err instanceof Error ? err.message : 'Unknown error'
    } finally {
        loading.value = false
    }
}
```

**Rules:**
- Signals replace useState/useReducer for most state
- Use `computed()` for derived state
- Store API data directly in signals
- Use `signal.value` to read/write synchronously
- LocalStorage for persistence: `localStorage.setItem(key, JSON.stringify(value))`

### Component Local State
Use React hooks only for UI-specific state (filters, modals, temporary UI state):

#### Signal-to-Input Bridge Pattern (MANDATORY for controlled inputs)
`@preact/signals-react` v2 intercepts `.value` access during JSX render, causing race conditions with React controlled inputs. **Always use a local `useState` bridge** when binding signals to `<input>`, `<select>`, or `<textarea>` elements:

```typescript
// ✅ CORRECT — Local state bridge
function SearchBar() {
  const [localQuery, setLocalQuery] = useState('')
  
  // Sync FROM signal when external code resets it
  useEffect(() => {
    setLocalQuery(searchQuery.value)
  }, [searchQuery.value])
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalQuery(e.target.value)        // Immediate UI update
    searchQuery.value = e.target.value   // Update signal for store
  }
  
  return <input value={localQuery} onChange={handleChange} />
}

// ❌ WRONG — Direct signal binding causes input lag/loss
function SearchBar() {
  return <input value={searchQuery.value} onChange={...} />
}
```

**When this pattern applies:**
- Any `<input>`, `<select>`, or `<textarea>` backed by a Preact signal
- All filter fields, search inputs, form controls reading from signals
- Does NOT apply to read-only signal display (`{count.value}` in text is fine)

**Reference implementations:** `SearchBar.tsx`, `FilterPanel.tsx` (5 fields), `Inbox.tsx` (already correct)

#### Signal Reads in useMemo/useCallback (MANDATORY)
`@preact/signals-react` v2 does NOT create subscriptions for `.value` reads inside `useMemo` or `useCallback` callbacks. **Always read signal values in the component render body**, then pass them as plain deps:

```typescript
// ✅ CORRECT — Signals read in render body, subscriptions established
function ChunkList() {
  const allChunks = chunks.value          // subscription created here
  const results = searchResults.value     // subscription created here
  const searchActive = isSearchActive.value

  const displayChunks = useMemo(() => {
    if (searchActive && results) return results.items
    return allChunks
  }, [allChunks, searchActive, results])  // plain values, React tracks changes

  return <div>{displayChunks.map(...)}</div>
}

// ❌ WRONG — Reads inside useMemo, no subscription, component never re-renders
function ChunkList() {
  const displayChunks = useMemo(() => {
    if (searchResults.value) return searchResults.value.items  // no subscription!
    return chunks.value                                         // no subscription!
  }, [searchResults.value, chunks.value])  // deps look right but won't trigger

  return <div>{displayChunks.map(...)}</div>
}
```

**Reference implementations:** `ChunkList.tsx` (searchActive, results, allChunks read in render body)

**Rules:**
- useState for local UI state (filters, tab selection)
- useEffect on mount to trigger data fetching from store functions
- useMemo for derived/filtered data to avoid re-renders
- Never use useEffect for data fetching with dependencies that cause loops
- **Always read signal `.value` in render body, never inside hook callbacks**

---

## 3. Async Patterns (Backend)

### FastAPI Async Endpoints
All endpoints must be async for optimal performance with I/O-heavy operations:

```python
# From backend/app/api/chunks.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/chunks", tags=["chunks"])

async def get_db() -> AsyncSession:
    """Dependency injection for database sessions."""
    async with async_session() as session:
        yield session

@router.post("", response_model=Chunk, status_code=201)
async def capture_chunk(
    chunk_create: ChunkCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Chunk:
    """Fast capture endpoint - returns immediately, processes in background."""
    chunk = await chunk_repo.create(chunk_create)
    
    # Send event for real-time updates
    await event_bus.publish(ChunkEvent(...))
    
    # Schedule background work
    background_tasks.add_task(_process_chunk_background, chunk.id)
    
    return chunk

async def _process_chunk_background(chunk_id: UUID) -> None:
    """Background tasks run outside the request cycle."""
    async with async_session() as session:
        # Do expensive work here
        pass
```

**Rules:**
- Use `async def` for all endpoints
- Use `BackgroundTasks` for non-critical work (not Celery)
- Use `Depends()` for async context managers (database sessions)
- Return `202 Accepted` for long-running operations
- Always use `await` with async I/O operations

### Background Task Queue Pattern
Use `asyncio.Queue` for MVP simplicity:

```python
# Simple in-memory queue for background work
import asyncio

background_queue: asyncio.Queue = asyncio.Queue()

async def background_worker():
    """Worker that processes items from queue."""
    while True:
        task = await background_queue.get()
        try:
            await task()
        except Exception as e:
            logger.error(f"Background task failed: {e}")
        finally:
            background_queue.task_done()
```

**Rules:**
- Use `asyncio.Queue` for MVP (scale to Redis/Celery later)
- Keep queue items simple and serializable
- Always wrap task execution in try/except
- Log failures but don't crash the worker

---

## 4. Backend Router Structure (FastAPI)

### Organized Router Pattern
Each domain (chunks, projects, mcp) has its own router module:

```python
# backend/app/api/chunks.py structure
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/chunks", tags=["chunks"])

# 1. Dependency functions (lazy-loaded via Depends)
async def get_chunk_repo(db: AsyncSession = Depends(get_db)) -> ChunkRepository:
    return ChunkRepository(db)

# 2. Endpoint definitions
@router.post("", response_model=Chunk, status_code=201)
async def capture_chunk(...) -> Chunk: ...

@router.get("/{chunk_id}", response_model=Chunk)
async def get_chunk(...) -> Chunk: ...

@router.get("", response_model=list[Chunk])
async def list_chunks(...) -> list[Chunk]: ...

# 3. Background tasks
async def _process_chunk_background(...) -> None: ...
```

Then in `backend/app/main.py`:

```python
from .api import chunks_router, projects_router, mcp_router

app = FastAPI()
app.include_router(chunks_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(mcp_router, prefix="/api/v1")
```

**Rules:**
- One router file per domain
- Status codes: 201 for POST (create), 200 for GET, 204 for DELETE, 400+ for errors
- Always return the scalar model, not a wrapper (not `{"data": chunk}`)
- Group dependencies at top of router file
- Use type hints on all parameters and return values

---

## 5. Error Handling (Backend)

### Exception Handling Pattern
Convert application errors to HTTP responses:

```python
from fastapi import HTTPException

# In endpoints, raise HTTPException with appropriate status codes
@router.get("/{chunk_id}", response_model=Chunk)
async def get_chunk(chunk_id: UUID, repo: ChunkRepository = Depends(...)):
    chunk = await repo.get(chunk_id)
    if not chunk:
        raise HTTPException(
            status_code=404,
            detail=f"Chunk {chunk_id} not found"
        )
    return chunk
```

**API Status Codes:**
- `200`: Success with data
- `201`: Created (POST)
- `204`: No Content (DELETE)
- `400`: Bad Request (validation failed)
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `409`: Conflict (duplicate)
- `500`: Server Error

**Backend Logging:**
```python
import logging

logger = logging.getLogger(__name__)

try:
    result = await expensive_operation()
except ValueError as e:
    logger.error(f"Validation failed: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.exception(f"Unexpected error in operation")
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

## 6. Database Access (Backend)

### SQLAlchemy Async Pattern
Use async SQLAlchemy with aiosqlite for development, PostgreSQL for production:

```python
# From backend/app/db/database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = "sqlite+aiosqlite:///./komorebi.db"  # Development
# DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"  # Production

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Repository pattern for data access
class ChunkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, chunk_create: ChunkCreate) -> Chunk:
        """Create and return new chunk."""
        db_chunk = ChunkTable(
            id=str(uuid4()),
            content=chunk_create.content,
            project_id=chunk_create.project_id,
            tags=chunk_create.tags,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(db_chunk)
        await self.session.commit()
        await self.session.refresh(db_chunk)
        return self._to_model(db_chunk)
    
    async def get(self, chunk_id: UUID) -> Optional[Chunk]:
        """Get chunk by ID."""
        result = await self.session.execute(
            select(ChunkTable).where(ChunkTable.id == str(chunk_id))
        )
        db_chunk = result.scalar_one_or_none()
        return self._to_model(db_chunk) if db_chunk else None
    
    def _to_model(self, db_chunk: ChunkTable) -> Chunk:
        """Convert ORM model to Pydantic model."""
        return Chunk(
            id=UUID(db_chunk.id),
            content=db_chunk.content,
            status=ChunkStatus(db_chunk.status),
            # ... other fields
        )
```

**Rules:**
- Always use async/await for database operations
- Use Repository pattern for data access layer
- Never expose SQLAlchemy models in API responses (convert to Pydantic)
- Use `await session.commit()` to persist changes
- Always provide `.refresh()` after create/update to get timestamps

---

## 7. API Response Format

### Response Envelope Pattern
Return Data directly (not wrapped in `{"data": ...}`):

```python
# ✅ CORRECT
@router.get("/chunks", response_model=list[Chunk])
async def list_chunks() -> list[Chunk]:
    chunks = await repo.list()
    return chunks  # Returns: [Chunk, Chunk, ...]

# ❌ WRONG
@router.get("/chunks")
async def list_chunks() -> dict:
    chunks = await repo.list()
    return {"data": chunks}  # Don't wrap
```

### Error Response Format (automatic via FastAPI)
```json
{
  "detail": "Error message here"
}
```

### Pagination (for future use)
```python
class PaginatedResponse(BaseModel):
    items: list[Chunk]
    total: int
    limit: int
    offset: int

@router.get("/chunks", response_model=PaginatedResponse)
async def list_chunks(limit: int = 100, offset: int = 0):
    items = await repo.list(limit=limit, offset=offset)
    total = await repo.count()
    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
```

---

## 8. Component Structure (React/Preact)

### Component Pattern
Use functional components with hooks and signals:

```tsx
// From frontend/src/components/ChunkList.tsx
import { useEffect, useState, useMemo } from 'react'
import { chunks, loading, fetchChunks } from '../store'
import type { Chunk } from '../store'

type StatusFilter = 'all' | 'inbox' | 'processed' | 'compacted' | 'archived'

export function ChunkList() {
  // Local UI state
  const [filter, setFilter] = useState<StatusFilter>('all')

  // Fetch on mount
  useEffect(() => {
    fetchChunks(undefined, 500)
  }, [])

  // Derived state (filtered list)
  const filteredChunks = useMemo(() => {
    if (filter === 'all') return chunks.value
    return chunks.value.filter(c => c.status === filter)
  }, [chunks.value, filter])

  return (
    <div>
      {/* Control section */}
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        {(['all', 'inbox', 'processed', 'compacted', 'archived'] as StatusFilter[]).map(status => (
          <button
            key={status}
            className={`tab ${filter === status ? 'active' : ''}`}
            onClick={() => setFilter(status)}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {/* Content section */}
      {loading.value && chunks.value.length === 0 ? (
        <div className="loading">Loading chunks...</div>
      ) : filteredChunks.length === 0 ? (
        <div className="empty-state">
          <p>No chunks found with filter: {filter}</p>
        </div>
      ) : (
        <div className="chunk-list">
          {filteredChunks.map((chunk: Chunk) => (
            <ChunkItem key={chunk.id} chunk={chunk} />
          ))}
        </div>
      )}
    </div>
  )
}
```

**Rules:**
- Separate components by domain (ChunkList, ProjectDetail, etc.)
- Read signals via `.value` in render
- Use `useMemo` for expensive computations
- Use `useState` only for UI-local state
- Use `useEffect` only for side effects (fetching data, subscriptions)

---

## 9. Naming Conventions

### Backend Python
```python
# Files: snake_case
database.py
chunk_repository.py

# Classes: PascalCase
class ChunkRepository: pass
class ChunkService: pass

# Functions & Methods: snake_case
async def get_chunk(chunk_id: UUID): pass
def _private_helper(): pass

# Constants: UPPER_SNAKE_CASE
MAX_CHUNK_SIZE = 10000
DEFAULT_TIMEOUT = 30

# Enums: PascalCase names, UPPER_SNAKE_CASE values
class ChunkStatus(str, Enum):
    INBOX = "inbox"
```

### Frontend TypeScript/React
```typescript
// Files: kebab-case for components, camelCase for utilities
ChunkList.tsx
useChunks.ts
api-client.ts

// Components: PascalCase
function ChunkList() {}
function ProjectDetail() {}

// Functions & Variables: camelCase
function fetchChunks() {}
const chunkStats = signal([])

// Constants: UPPER_SNAKE_CASE
const DEFAULT_CHUNK_LIMIT = 100

// Types & Interfaces: PascalCase
interface ChunkStats {}
type StatusFilter = 'all' | 'inbox' | ...
```

---

## 10. Testing Strategy

### Backend Unit Tests
```python
# backend/tests/test_chunks.py
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_capture_chunk_creates_new_chunk():
    """Test that POST /chunks creates a chunk in inbox."""
    response = client.post("/api/v1/chunks", json={
        "content": "Test chunk",
        "tags": ["test"],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Test chunk"
    assert data["status"] == "inbox"

@pytest.mark.asyncio
async def test_get_chunk_not_found():
    """Test that GET /chunks/{id} returns 404 for missing chunk."""
    response = client.get("/api/v1/chunks/nonexistent")
    assert response.status_code == 404
```

**Rules:**
- Test files in `backend/tests/test_*.py`
- Use `pytest` + `pytest-asyncio`
- Test both happy path and error cases
- Mock external dependencies
- Run with `pytest` before committing

---

## 11. Git Workflow Checklist

Before committing:
- ✅ Code follows patterns in this document
- ✅ Type hints on all functions
- ✅ Async/await used correctly
- ✅ No hardcoded secrets or API keys
- ✅ Imports organized (stdlib, third-party, local)
- ✅ Tests pass locally
- ✅ No TODO comments left incomplete

Before pushing:
- ✅ Branch name matches `feature/` or `fix/`
- ✅ PR description links to GitHub Issue
- ✅ All CI checks pass (linting, tests, build)

---

## 12. Versioning Governance

### Version Management
Komorebi follows semantic versioning with strict governance. See [VERSIONING.md](VERSIONING.md) for complete details.

**Quick Reference:**
- **Development:** Use `{version}+buildN` format during feature development
- **Release:** Remove `+buildN` when complete and ready
- **Validation:** Run `./scripts/check-version.sh` before committing
- **Syncing:** Use `./scripts/sync-versions.sh` to update all version files

**Commit Format (Required):**
```
<type>: v<version> - <description>

Examples:
feat: v0.3.0+build1 - add entity extraction
fix: v0.2.1+build2 - resolve cold start issue
release: v0.3.0 - recursive compaction complete
```

**Version Sources:**
- `VERSION` file (canonical)
- `pyproject.toml` (Python package)  
- `frontend/package.json` (React package)
- `docs/CHANGELOG.md` (must have entry for releases)

### Pre-commit Validation
- Version consistency across all files
- CHANGELOG entry for non-build versions
- Proper semantic version format
- Commit message includes version

---

## 13. MCP Tool Ecosystem

Komorebi integrates with external MCP servers for agentic tool access. Configuration lives in `config/mcp_servers.json` using `env://` URI references for secrets.

### Registered MCP Servers

| Server | Package | Purpose | Secrets |
|--------|---------|---------|--------|
| **GitHub** | `@modelcontextprotocol/server-github` | Repository ops, issues, PRs, code search | `GITHUB_TOKEN` |
| **GitKraken** | `@gitkraken/mcp-server-gitkraken` | Advanced Git operations, visual diffs, repo management | `GITKRAKEN_API_KEY` |
| **Playwright** | `@playwright/mcp@latest` | Browser automation, E2E testing, visual verification | None |
| **Filesystem** | `@modelcontextprotocol/server-filesystem` | Local file read/write in sandboxed directories | None |

### Security Rules
- NEVER hardcode MCP server tokens in config files or source code
- Use `env://VARIABLE_NAME` pattern in `config/mcp_servers.json` for secret injection
- Secrets are resolved at runtime from environment variables only
- New servers start `disabled: true` until explicitly enabled

### VS Code Prompt Tools

All prompts have access to the full builtin tool set:
- `search/codebase` — Semantic codebase search
- `editFiles` — File creation and editing
- `runTerminalCommand` — Terminal command execution
- `githubRepo` — GitHub repository operations (issues, PRs)
- `fetch` — HTTP requests for external resources

MCP servers (GitHub, GitKraken, Playwright, Filesystem) are available as additional tools when configured and enabled.

---

## 14. Resources & References

- See [copilot-instructions.md](.github/copilot-instructions.md) for project vision and directives
- [VERSIONING.md](VERSIONING.md) - Complete versioning governance
- FastAPI Docs: https://fastapi.tiangolo.com/
- SQLAlchemy Async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Preact Signals: https://preactjs.com/guide/v10/signals/
- React 18 Docs: https://react.dev/
- MCP Specification: https://modelcontextprotocol.io/specification/2025-11-25

---

**Last Updated:** February 7, 2026