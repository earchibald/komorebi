---
name: implement-feature
description: Fast-track feature implementation from specification to working code using TDD workflow. Use for new CRUD features, API endpoints, React components.
agent: agent
tools: ['search/codebase', 'editFiles', 'runTerminalCommand']
---

# Implement Feature

## Governance (MUST Follow)

### Pre-1.0.0 Documentation Rule
**CRITICAL:** Always keep documentation synchronized with code changes.

- ✅ Update `CURRENT_STATUS.md` with version and date on every release
- ✅ Synchronize all documentation: `CHANGELOG.md`, `CONVENTIONS.md`, `BUILD.md`, `PROGRESS.md`
- ✅ Document new features, fixes, and breaking changes immediately
- ✅ Keep documentation in `docs/` reflecting current system state

### Prime Directives (The "Amicus" Protocol)

1. **Capture-First Architecture:** Priority #1 is ingestion speed. Ingestion endpoints must never block. Use `202 Accepted` and offload to background workers (FastAPI BackgroundTasks or Celery).

2. **Strict State Isolation:**
   - **Main:** Immutable, production-ready code.
   - **Develop:** The "Hammer" ground. Code must survive high-volume synthetic load testing here.
   - **Feature Branches:** The only place where "Red" (failing) tests are acceptable.

3. **Agentic Autonomy:** Assume the role of **Senior Engineer**. Do not stop for trivial ambiguities. If a design decision is non-critical, choose the industry-standard "High-Density/Operational" pattern. Log blockers in `ELICITATIONS.md`.

### Technical Stack Constraints

**Backend (Python 3.11+):**
- Framework: FastAPI (Async-first)
- Database: SQLAlchemy with async support (aiosqlite for dev, PostgreSQL for prod)
- Validation: Pydantic v2 (Use `model_validate`, NOT `from_orm`)
- Events: `sse-starlette` for server-sent events
- Background Jobs: `asyncio.Queue` for MVP simplicity (scale to Celery/Redis in v2.0)
- Testing: `pytest` + `pytest-asyncio`
- Linting: `ruff` (formatting and linting)
- Secrets: Environment variables only (no hardcoded secrets)

**Frontend (React 18.2):**
- Build: Vite + TypeScript
- Styling: CSS Variables + Custom CSS (Tailwind CSS planned for v1.0)
- State Management:
  - Server State: localStorage + simple fetch (TanStack Query planned when scaling)
  - High-Frequency UI: `@preact/signals-react` for metrics and reactive updates
  - Global UI: Preact Signals only (no separate Zustand layer needed for MVP)

**Protocol:**
- MCP: Model Context Protocol (2025-11-25 Spec) for all external tool aggregations

### Code Quality Gates

Before completing this task, verify:
- ✅ Type hints on all functions
- ✅ Async/await used correctly for all I/O operations
- ✅ No hardcoded secrets or API keys
- ✅ Imports organized (stdlib, third-party, local)
- ✅ Tests pass locally (`pytest`)
- ✅ No incomplete TODO comments (implement or use `NotImplementedError`)
- ✅ Ruff linting passes (`ruff check .`)

---

## Task Context

You are implementing a new feature in the Komorebi project. Follow the **TDD workflow: Red → Green → Refactor → Hammer**.

### TDD Workflow

1. **Red (Write Failing Tests):**
   - Create test file: `backend/tests/test_<feature_name>.py`
   - Write tests for expected behavior (happy path + edge cases)
   - Run tests → Verify they fail (no implementation yet)

2. **Green (Minimal Implementation):**
   - Write minimal code to make tests pass
   - Backend: Pydantic schemas → Repository → API endpoint
   - Frontend: Signals → Fetch functions → Component
   - Run tests → Verify they pass

3. **Refactor (Clean Up):**
   - Extract duplicated logic
   - Apply consistent naming conventions
   - Improve readability without changing behavior
   - Run tests → Verify they still pass

4. **Hammer (Stress Test):**
   - For ingestion features: Update `scripts/hammer_gen.py`
   - Run synthetic load test with `--size 500`
   - Verify no hallucination or crashes in recursive summarization

---

## Backend Implementation Patterns

### Pydantic Model Structure

```python
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

# Enums for fixed value sets
class ItemStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

# Create schema (input validation)
class ItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)

# Update schema (partial updates)
class ItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    status: Optional[ItemStatus] = None

# Read schema (API response)
class Item(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    content: str
    status: ItemStatus
    tags: list[str]
    created_at: str
    updated_at: str
```

**Rules:**
- Separate schemas for Create/Update/Read
- Use `Field()` with descriptions for API documentation
- Use `Enum` for fixed value sets
- Use `Optional[T]` for nullable fields
- Always use `model_dump(mode="json")` when serializing

### FastAPI Endpoint Pattern

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/items", tags=["items"])

async def get_db() -> AsyncSession:
    """Dependency injection for database sessions."""
    async with async_session() as session:
        yield session

@router.post("", response_model=Item, status_code=201)
async def create_item(
    item_create: ItemCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Item:
    """Fast capture endpoint - returns immediately, processes in background."""
    # 1. Create item
    item = await item_repo.create(item_create)
    
    # 2. Send event for real-time updates
    await event_bus.publish(ItemEvent(...))
    
    # 3. Schedule background work
    background_tasks.add_task(_process_item_background, item.id)
    
    return item

@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: UUID, db: AsyncSession = Depends(get_db)) -> Item:
    """Get item by ID."""
    item = await item_repo.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return item

@router.get("", response_model=list[Item])
async def list_items(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[Item]:
    """List items with pagination."""
    return await item_repo.list(limit=limit, offset=offset)

async def _process_item_background(item_id: UUID) -> None:
    """Background tasks run outside the request cycle."""
    async with async_session() as session:
        # Do expensive work here
        pass
```

**Rules:**
- All endpoints must be `async def`
- Use `Depends()` for dependency injection
- Use `BackgroundTasks` for non-critical work
- Return Pydantic models directly (not wrapped in `{"data": ...}`)
- Status codes: 201 (POST), 200 (GET), 204 (DELETE), 400+ (errors)

### Repository Pattern

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class ItemRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, item_create: ItemCreate) -> Item:
        """Create and return new item."""
        db_item = ItemTable(
            id=str(uuid4()),
            title=item_create.title,
            content=item_create.content,
            status=ItemStatus.DRAFT,
            tags=item_create.tags,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(db_item)
        await self.session.commit()
        await self.session.refresh(db_item)
        return self._to_model(db_item)
    
    async def get(self, item_id: UUID) -> Optional[Item]:
        """Get item by ID."""
        result = await self.session.execute(
            select(ItemTable).where(ItemTable.id == str(item_id))
        )
        db_item = result.scalar_one_or_none()
        return self._to_model(db_item) if db_item else None
    
    def _to_model(self, db_item: ItemTable) -> Item:
        """Convert ORM model to Pydantic model."""
        return Item(
            id=UUID(db_item.id),
            title=db_item.title,
            content=db_item.content,
            status=ItemStatus(db_item.status),
            tags=db_item.tags,
            created_at=db_item.created_at.isoformat(),
            updated_at=db_item.updated_at.isoformat(),
        )
```

**Rules:**
- Always use async/await for database operations
- Use Repository pattern for data access layer
- Never expose SQLAlchemy models in API responses (convert to Pydantic)
- Use `await session.commit()` to persist changes
- Always `.refresh()` after create/update to get timestamps

---

## Frontend Implementation Patterns

### Preact Signals State Management

```typescript
// src/store/items.ts
import { signal, computed } from '@preact/signals-react'
import type { Item } from './types'

// State signals
export const items = signal<Item[]>([])
export const loading = signal(false)
export const error = signal<string | null>(null)

// Computed signals (derived state)
export const itemsByStatus = computed(() => {
    const grouped: Record<string, Item[]> = {}
    items.value.forEach(item => {
        if (!grouped[item.status]) grouped[item.status] = []
        grouped[item.status].push(item)
    })
    return grouped
})

// Fetch function (modifies signals directly)
export async function fetchItems(limit = 100) {
    loading.value = true
    error.value = null
    try {
        const response = await fetch(`${API_URL}/items?limit=${limit}`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data = await response.json()
        items.value = data
    } catch (err) {
        error.value = err instanceof Error ? err.message : 'Unknown error'
    } finally {
        loading.value = false
    }
}

// Create function
export async function createItem(itemData: ItemCreate) {
    loading.value = true
    error.value = null
    try {
        const response = await fetch(`${API_URL}/items`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(itemData),
        })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const newItem = await response.json()
        items.value = [...items.value, newItem]
        return newItem
    } catch (err) {
        error.value = err instanceof Error ? err.message : 'Unknown error'
        throw err
    } finally {
        loading.value = false
    }
}
```

**Rules:**
- Use `signal()` for state that changes
- Use `computed()` for derived state
- Store API data directly in signals (no intermediate state)
- Access via `.value` (read/write)
- LocalStorage for persistence: `localStorage.setItem(key, JSON.stringify(value))`

### React Component Pattern

```typescript
// src/components/ItemList.tsx
import { useEffect, useState, useMemo } from 'react'
import { items, loading, fetchItems } from '../store/items'
import type { Item } from '../store/types'

type StatusFilter = 'all' | 'draft' | 'active' | 'archived'

export function ItemList() {
    // Local UI state (not shared)
    const [filter, setFilter] = useState<StatusFilter>('all')
    
    // Fetch on mount
    useEffect(() => {
        fetchItems(500)
    }, [])
    
    // Derived state (filtered list)
    const filteredItems = useMemo(() => {
        if (filter === 'all') return items.value
        return items.value.filter(item => item.status === filter)
    }, [items.value, filter])
    
    return (
        <div>
            {/* Filter controls */}
            <div style={{ display: 'flex', gap: '0.5rem' }}>
                {(['all', 'draft', 'active', 'archived'] as StatusFilter[]).map(status => (
                    <button
                        key={status}
                        className={`tab ${filter === status ? 'active' : ''}`}
                        onClick={() => setFilter(status)}
                    >
                        {status.charAt(0).toUpperCase() + status.slice(1)}
                    </button>
                ))}
            </div>
            
            {/* Content */}
            {loading.value && items.value.length === 0 ? (
                <div className="loading">Loading items...</div>
            ) : filteredItems.length === 0 ? (
                <div className="empty-state">
                    <p>No items found with filter: {filter}</p>
                </div>
            ) : (
                <div className="item-list">
                    {filteredItems.map((item: Item) => (
                        <ItemCard key={item.id} item={item} />
                    ))}
                </div>
            )}
        </div>
    )
}
```

**Rules:**
- Use `useState` only for UI-local state (filters, modals, etc.)
- Use `useEffect` on mount to trigger data fetching
- Use `useMemo` for expensive computations or filtering
- Read signals via `.value` in render
- Never use `useEffect` for data fetching with dependencies that cause loops

---

## Testing Patterns

### Backend Unit Tests

```python
# backend/tests/test_items.py
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_create_item_success():
    """Test that POST /items creates an item."""
    response = client.post("/api/v1/items", json={
        "title": "Test Item",
        "content": "Test content",
        "tags": ["test"],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Item"
    assert data["status"] == "draft"
    assert "id" in data
    assert "created_at" in data

@pytest.mark.asyncio
async def test_create_item_validation_error():
    """Test that POST /items validates input."""
    response = client.post("/api/v1/items", json={
        "title": "",  # Empty title should fail
        "content": "Test content",
    })
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_get_item_not_found():
    """Test that GET /items/{id} returns 404 for missing item."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/items/{fake_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_list_items_pagination():
    """Test that GET /items supports pagination."""
    # Create 5 items
    for i in range(5):
        client.post("/api/v1/items", json={
            "title": f"Item {i}",
            "content": f"Content {i}",
        })
    
    # Test limit
    response = client.get("/api/v1/items?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
```

**Rules:**
- Test files in `backend/tests/test_*.py`
- Use `@pytest.mark.asyncio` for async tests
- Test both happy path and error cases
- Use TestClient for API tests
- Mock external dependencies
- Run with `pytest` before committing

---

## Execution Workflow

### Step 1: Understand Requirements

Before writing any code:
1. Clarify feature scope and acceptance criteria
2. Identify affected modules (backend only, frontend only, or both)
3. Check for existing similar features to follow established patterns
4. Log any significant design decisions in `ELICITATIONS.md`

### Step 2: Write Tests First (Red)

1. Create test file: `backend/tests/test_<feature_name>.py`
2. Write test for happy path (main use case)
3. Write tests for edge cases (validation errors, not found, etc.)
4. Run tests: `pytest backend/tests/test_<feature_name>.py`
5. **Verify tests fail** (expected, no implementation yet)

### Step 3: Implement Feature (Green)

**For Backend:**
1. Create Pydantic schemas in `backend/app/models/<feature_name>.py`
2. Create repository in `backend/app/repositories/<feature_name>.py` (if needed)
3. Create API endpoints in `backend/app/api/<feature_name>.py`
4. Register router in `backend/app/main.py`
5. Run tests: `pytest backend/tests/test_<feature_name>.py`
6. **Verify tests pass**

**For Frontend:**
1. Create signals and fetch functions in `frontend/src/store/<feature_name>.ts`
2. Create component in `frontend/src/components/<FeatureName>.tsx`
3. Add component to appropriate page/route
4. Test manually: `npm run dev`
5. Verify UI works as expected

### Step 4: Refactor (Clean)

1. Extract duplicated logic into helper functions
2. Apply consistent naming conventions
3. Add type hints to all functions
4. Organize imports (stdlib, third-party, local)
5. Run tests again: `pytest backend/tests/test_<feature_name>.py`
6. **Verify tests still pass**

### Step 5: Verify Governance Compliance

Update these documentation files (edit them directly, do not skip):
- `CURRENT_STATUS.md` — update version/date if this is a release
- `CHANGELOG.md` — add entry if user-facing change
- `CONVENTIONS.md` — update if new pattern introduced
- `PROGRESS.md` — update if major milestone
- `ELICITATIONS.md` — log any design decisions or trade-offs

Verify code quality (review the code you wrote):
- No hardcoded secrets or API keys
- Type hints on all functions
- Imports organized (stdlib, third-party, local)

### Step 6: Run Verification Commands

**You MUST execute these commands in the terminal — do not list them for the user.**

1. Run the feature tests: `pytest backend/tests/test_<feature_name>.py -v`
2. Run linting: `ruff check backend/`
3. Run frontend build (if frontend changes): `cd frontend && npm run build`
4. If any command fails, fix the issue and re-run until green.

**Do NOT end your turn by listing commands for the user to run.** If you cannot run a command (e.g., terminal tools unavailable), state that explicitly and explain why, rather than presenting commands as a "Verify with:" block.

---

## Output Format

**Provide the following deliverables:**

1. **Test File(s):**
   - Path: `backend/tests/test_<feature_name>.py`
   - Comprehensive coverage (happy path + edge cases)
   - All tests initially failing (Red), then passing (Green)

2. **Implementation File(s):**
   - Backend: Pydantic schemas, repository (if needed), API endpoints
   - Frontend: Signals + fetch functions, React component
   - Following all conventions in CONVENTIONS.md

3. **Documentation Updates:**
   - `CHANGELOG.md` entry (if user-facing change)
   - `CONVENTIONS.md` update (if new pattern introduced)
   - `PROGRESS.md` update (if major milestone)
   - `ELICITATIONS.md` entry (if design decisions made)

4. **Verification Results:**
   - Test results (pass/fail count from terminal output)
   - Lint results (clean or issues found)
   - Build results (success or errors)
   - If a verification step cannot be run, state why explicitly

**Do NOT provide:**
- A "Verify with:" section listing commands for the user to run
- Incomplete TODO comments (implement fully or use `NotImplementedError`)
- Hardcoded secrets or API keys
- Non-async FastAPI endpoints
- `useEffect` hooks for data fetching (use signals + fetch functions)
- Wrapped responses like `{"data": item}` (return item directly)

---

## Common Pitfalls to Avoid

1. **Forgetting async/await:** All I/O operations must use async/await
2. **Using `from_orm`:** Use Pydantic v2's `model_validate` instead
3. **Wrapping responses:** Return Pydantic models directly, not `{"data": model}`
4. **useEffect loops:** Don't use useEffect with dependencies for data fetching
5. **Hardcoded secrets:** Always use environment variables
6. **Missing type hints:** Every function needs parameter and return type hints
7. **Skipping tests:** Write tests first (TDD workflow)
8. **Incomplete TODOs:** Implement fully or raise `NotImplementedError`

---

## Example: Complete Feature Implementation

**Requirement:** Add a "favorite" flag to items

### Step 1: Write Tests (Red)

```python
# backend/tests/test_items.py

@pytest.mark.asyncio
async def test_favorite_item_success():
    """Test that PATCH /items/{id}/favorite marks item as favorite."""
    # Create item
    create_response = client.post("/api/v1/items", json={
        "title": "Test Item",
        "content": "Test content",
    })
    item_id = create_response.json()["id"]
    
    # Favorite it
    response = client.patch(f"/api/v1/items/{item_id}/favorite")
    assert response.status_code == 200
    data = response.json()
    assert data["is_favorite"] is True

@pytest.mark.asyncio
async def test_favorite_item_not_found():
    """Test that PATCH /items/{id}/favorite returns 404 for missing item."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.patch(f"/api/v1/items/{fake_id}/favorite")
    assert response.status_code == 404
```

Run: `pytest backend/tests/test_items.py` → **Tests fail** ✅

### Step 2: Implement (Green)

```python
# backend/app/models/item.py (add field)
class Item(BaseModel):
    # ... existing fields ...
    is_favorite: bool = False

# backend/app/api/items.py (add endpoint)
@router.patch("/{item_id}/favorite", response_model=Item)
async def favorite_item(item_id: UUID, db: AsyncSession = Depends(get_db)) -> Item:
    """Mark item as favorite."""
    item = await item_repo.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    updated_item = await item_repo.update(item_id, ItemUpdate(is_favorite=True))
    return updated_item
```

Run: `pytest backend/tests/test_items.py` → **Tests pass** ✅

### Step 3: Refactor (Clean)

- Extract `get_or_404` helper if pattern repeats
- Add type hints to all new functions
- Organize imports

### Step 4: Update Documentation

```markdown
# CHANGELOG.md
## [0.3.0+build2] - 2026-02-05
### Added
- Favorite flag for items (PATCH /items/{id}/favorite)
```

Done! Feature complete with tests, implementation, and docs.

---

**Ready to implement your feature!** Follow the workflow above step-by-step.
