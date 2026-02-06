# Architecture Handoff: Phase 5 — Production Deployment & Bulk Operations

**Date:** February 7, 2026  
**Version:** v0.5.0 → v0.6.0 (target)  
**Path:** C (Hybrid) — Minimal Viable Deployment + First High-Value Feature  
**Estimated Effort:** 20–28 hours across 2 sprints

---

## Feature Overview

Deploy Komorebi to production (Docker + managed hosting) and add bulk chunk operations — the first feature driven by user value. This dual deliverable gets the system into real users' hands while addressing the most common pain point: managing chunks at scale.

## Architecture Summary

The deployment architecture uses a **single-container Docker image** that serves both the FastAPI backend and Vite-built static frontend via Uvicorn — no reverse proxy needed for MVP. The bulk operations module adds three new batch endpoints using SQLAlchemy's `update()` with `WHERE` clauses for O(1) database operations instead of N individual updates. A new `BulkAction` audit log table tracks all bulk mutations for undo and traceability.

---

## Part 1: Minimal Viable Deployment

### 1.1 Requirements

**User Stories:**
- As a developer, I want to deploy Komorebi with a single command so that I can use it on any machine
- As a user, I want Komorebi accessible at a URL so that I don't need to run a dev server
- As an operator, I want health checks so that I know the service is running

**Success Criteria:**
- [ ] `docker build` produces a working image under 200MB
- [ ] `docker-compose up` starts backend + frontend serving from one container
- [ ] Health endpoint responds at `/health` with 200 OK
- [ ] API endpoints respond at `/api/v1/...`
- [ ] Frontend loads at `/` and connects to backend
- [ ] Environment variables configure database URL, CORS origins, and log level
- [ ] Deployable to Railway/Render/Fly.io with zero custom config

**Constraints:**
- Must use: Python 3.11+, Node 20+, SQLite (keep for MVP)
- Cannot use: Kubernetes (too complex for solo dev), PostgreSQL (defer to v1.0)
- Timeline: 1 sprint (8–12 hours)

**Edge Cases:**
1. What if SQLite file path doesn't exist? → Create parent dirs on startup
2. What if port is already in use? → Configurable via `PORT` env var
3. What if frontend build fails? → Multi-stage Docker catches at build time
4. What if database needs migration? → Run `init_db()` on startup (existing pattern)

### 1.2 System Design

#### Container Architecture

```
┌─────────────────────────────────────────────┐
│              Docker Container               │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │         Uvicorn (port 8000)         │    │
│  │                                     │    │
│  │  ┌───────────┐   ┌──────────────┐   │    │
│  │  │  FastAPI   │   │  StaticFiles │   │    │
│  │  │  /api/v1   │   │  /  (Vite)   │   │    │
│  │  └───────────┘   └──────────────┘   │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  SQLite (volume: /data/komorebi.db) │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌──────────────┐  ┌───────────────────┐    │
│  │  Ollama      │  │  MCP Servers      │    │
│  │  (external)  │  │  (external)       │    │
│  └──────────────┘  └───────────────────┘    │
└─────────────────────────────────────────────┘
```

**Key Design Decision:** Serve frontend static files from FastAPI using `StaticFiles` mount. This eliminates the need for Nginx/Caddy and keeps deployment to a single process.

#### Dockerfile (Multi-Stage)

```
Stage 1: frontend-build
  FROM node:20-alpine
  COPY frontend/ .
  RUN npm ci && npm run build
  OUTPUT: /app/frontend/dist/

Stage 2: runtime
  FROM python:3.11-slim
  COPY backend/ .
  COPY --from=frontend-build /app/frontend/dist/ ./static/
  RUN pip install --no-cache-dir .
  EXPOSE 8000
  CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Server port |
| `KOMOREBI_DATABASE_URL` | `sqlite+aiosqlite:///./data/komorebi.db` | Database connection string |
| `KOMOREBI_CORS_ORIGINS` | `*` | Comma-separated CORS origins |
| `KOMOREBI_LOG_LEVEL` | `INFO` | Logging level |
| `KOMOREBI_DEBUG` | `false` | Enable SQLAlchemy echo |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama API base URL |

#### FastAPI Changes Required

1. **Static file serving** — Mount `StaticFiles` for frontend:
```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# After all API routers
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
```

2. **Health endpoint enhancement** — Add database connectivity check:
```python
@app.get("/health")
async def health():
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "version": VERSION}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": str(e)}
        )
```

3. **Version injection** — Read from VERSION file at startup:
```python
VERSION = Path("VERSION").read_text().strip() if Path("VERSION").exists() else "dev"
```

4. **Data directory creation** — Ensure SQLite path parent exists:
```python
db_path = DATABASE_URL.split("///")[-1]
Path(db_path).parent.mkdir(parents=True, exist_ok=True)
```

#### docker-compose.yml

```yaml
version: "3.8"
services:
  komorebi:
    build: .
    ports:
      - "${PORT:-8000}:8000"
    volumes:
      - komorebi-data:/app/data
    environment:
      - KOMOREBI_DATABASE_URL=sqlite+aiosqlite:///./data/komorebi.db
      - KOMOREBI_LOG_LEVEL=INFO
      - OLLAMA_HOST=http://host.docker.internal:11434

volumes:
  komorebi-data:
```

#### .dockerignore

```
.git
.github
__pycache__
*.pyc
venv
node_modules
.vite
*.db
*.db-journal
komorebi.egg-info
frontend/node_modules
docs/
scripts/
backend/tests/
*.md
```

### 1.3 Deployment Targets

**Primary: Railway.app** (Recommended for MVP)
- Git push deploys
- Free persistent volume for SQLite
- Auto-SSL, custom domains
- `$5/month` hobby plan

**Alternative: Fly.io**
- Dockerfile-based deploys
- Persistent volumes (Fly Volumes)
- Edge deployment (global regions)
- `$5-10/month`

**Alternative: Render.com**
- Docker or native buildpack
- Persistent disks available
- Auto-deploy from GitHub
- Free tier available (spins down)

**Not recommended:** Vercel (no persistent storage), Heroku (no SQLite volumes), AWS/GCP (overkill for MVP).

---

## Part 2: Module 5 — Bulk Operations & Data Management

### 2.1 Requirements

**User Stories:**
- As a power user, I want to tag 50 chunks at once so that I can organize large captures
- As a user, I want to archive all old "inbox" chunks so that my inbox stays manageable
- As a user, I want to undo a bulk action so that I can recover from mistakes

**Success Criteria:**
- [ ] Bulk tag: Apply tags to chunks matching a filter (max 1000 per request)
- [ ] Bulk archive: Archive chunks matching a filter
- [ ] Bulk delete: Soft-delete chunks (mark as `deleted`, recoverable for 30 days)
- [ ] Audit log: Every bulk action is recorded with timestamp, user, affected count
- [ ] Undo: Last bulk action can be reversed within 30 minutes
- [ ] Frontend: Multi-select UI with bulk action dropdown
- [ ] Performance: Bulk operations complete in < 2s for 1000 chunks

**Constraints:**
- Must use: Existing ChunkTable schema (no new chunk columns)
- Must add: New `bulk_actions` table for audit trail
- Cannot: Hard-delete chunks (only soft-delete with status change)
- Timeline: 1 sprint (10–16 hours)

**Edge Cases:**
1. What if filter matches 0 chunks? → Return 200 with `affected: 0`
2. What if filter matches >1000 chunks? → Return 400 with limit error
3. What if undo window expired? → Return 410 Gone
4. What if concurrent bulk operations on same chunks? → Last-write-wins (acceptable for MVP)
5. What if bulk tag adds duplicate tags? → Deduplicate in SQL (use JSON merge)

### 2.2 System Design

#### Component Diagram

```
┌────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  BulkActions   │────▶│  BulkService     │────▶│  ChunkRepo     │
│  Component     │     │  (Backend)       │     │  (Database)     │
│  (Frontend)    │     │                  │     │                 │
│                │     │  Validates       │     │  Executes SQL   │
│  Multi-select  │     │  Logs action     │     │  UPDATE ... IN  │
│  Bulk menu     │     │  Returns count   │     │  (O(1) query)   │
└────────────────┘     └──────────────────┘     └────────────────┘
       │                        │
       │                        ▼
       │               ┌──────────────────┐
       │               │  BulkActionTable  │
       │               │  (Audit Log)     │
       │               │                  │
       │               │  action_type     │
       │               │  filter_used     │
       │               │  affected_ids    │
       │               │  previous_state  │
       │               │  created_at      │
       │               └──────────────────┘
       │
       ▼
┌────────────────┐
│  ChunkList     │
│  (Updated)     │
│                │
│  Checkbox per  │
│  chunk card    │
│  Select-all    │
│  Bulk actions  │
└────────────────┘
```

#### 2.2.1 Data Model

**New Table: `bulk_actions` (Audit Log)**

```python
class BulkActionTable(Base):
    """Tracks all bulk operations for audit and undo."""
    
    __tablename__ = "bulk_actions"
    
    id = Column(String(36), primary_key=True)          # UUID
    action_type = Column(String(20), nullable=False)    # tag, archive, delete, restore
    filter_used = Column(JSON, nullable=False)          # The filter criteria used
    affected_ids = Column(JSON, nullable=False)         # List of chunk IDs affected
    previous_state = Column(JSON, nullable=False)       # Snapshot for undo [{id, status, tags}, ...]
    affected_count = Column(Integer, nullable=False)    # Number of chunks affected
    undone = Column(Boolean, default=False)             # Whether this action was reversed
    created_at = Column(DateTime, nullable=False)       # When the action was performed
```

**Pydantic Models:**

```python
class BulkFilter(BaseModel):
    """Filter criteria for selecting chunks to operate on."""
    chunk_ids: list[str] | None = None           # Explicit IDs (from multi-select)
    status: str | None = None                     # Filter by status
    project_id: str | None = None                 # Filter by project
    query: str | None = None                      # Text search filter
    created_before: datetime | None = None        # Date range
    created_after: datetime | None = None         # Date range
    
    @model_validator(mode="after")
    def at_least_one_filter(self):
        """Require at least one filter to prevent accidental bulk operations."""
        if not any([self.chunk_ids, self.status, self.project_id, 
                     self.query, self.created_before, self.created_after]):
            raise ValueError("At least one filter criterion is required")
        return self

class BulkTagRequest(BaseModel):
    """Request to add tags to matching chunks."""
    filter: BulkFilter
    tags: list[str]                               # Tags to add
    
class BulkArchiveRequest(BaseModel):
    """Request to archive matching chunks."""
    filter: BulkFilter
    
class BulkDeleteRequest(BaseModel):
    """Request to soft-delete matching chunks."""
    filter: BulkFilter

class BulkActionResult(BaseModel):
    """Response from a bulk operation."""
    action_id: str                                # UUID of the bulk action (for undo)
    action_type: str                              # tag, archive, delete
    affected_count: int                           # Number of chunks affected
    undo_available: bool = True                   # Whether undo is still possible
    undo_expires_at: datetime                     # When undo window closes (30 min)
    
class BulkActionLog(BaseModel):
    """Audit log entry for a bulk action."""
    id: str
    action_type: str
    filter_used: dict
    affected_count: int
    undone: bool
    created_at: datetime
```

#### 2.2.2 API Design

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| POST | `/api/v1/chunks/bulk/tag` | BulkTagRequest | BulkActionResult | Add tags to matching chunks |
| POST | `/api/v1/chunks/bulk/archive` | BulkArchiveRequest | BulkActionResult | Archive matching chunks |
| POST | `/api/v1/chunks/bulk/delete` | BulkDeleteRequest | BulkActionResult | Soft-delete matching chunks |
| POST | `/api/v1/chunks/bulk/undo/{action_id}` | — | BulkActionResult | Undo a bulk action (within 30 min) |
| GET | `/api/v1/chunks/bulk/history` | — | list[BulkActionLog] | List recent bulk actions |

**Route placement:** Add to existing `chunks.py` router (keep cohesive with chunk operations).

#### 2.2.3 Repository Layer

```python
class BulkRepository:
    """Handles bulk chunk operations with audit logging."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def _resolve_filter(self, filter: BulkFilter) -> Tuple[list[str], list[dict]]:
        """
        Resolve a BulkFilter into a list of chunk IDs and their current state.
        Returns (chunk_ids, previous_state_snapshots).
        Enforces max 1000 chunks per operation.
        """
        ...
    
    async def bulk_tag(self, filter: BulkFilter, tags: list[str]) -> BulkActionResult:
        """Add tags to all chunks matching filter."""
        # 1. Resolve filter → chunk IDs + current state
        # 2. For each chunk: merge tags (deduplicate)
        # 3. Execute single UPDATE ... WHERE id IN (...)
        # 4. Log to bulk_actions table
        # 5. Return result with action_id for undo
        ...
    
    async def bulk_archive(self, filter: BulkFilter) -> BulkActionResult:
        """Set status='archived' for all chunks matching filter."""
        # 1. Resolve filter → chunk IDs + current state
        # 2. Execute UPDATE chunks SET status='archived' WHERE id IN (...)
        # 3. Log with previous statuses for undo
        ...
    
    async def bulk_delete(self, filter: BulkFilter) -> BulkActionResult:
        """Soft-delete: set status='deleted' for matching chunks."""
        # Same pattern as archive but with status='deleted'
        ...
    
    async def undo(self, action_id: str) -> BulkActionResult:
        """
        Reverse a bulk action using stored previous_state.
        Only available within 30 minutes of the original action.
        """
        # 1. Load BulkActionTable row
        # 2. Check undo window (created_at + 30 min > now)
        # 3. Restore each chunk to previous_state (status, tags)
        # 4. Mark action as undone=True
        ...
```

**Performance Strategy:**

The critical insight is that SQLAlchemy's `update()` with a `WHERE id IN (...)` clause generates a **single SQL statement** — not N individual updates:

```python
# O(1) database operation for bulk status change
stmt = (
    update(ChunkTable)
    .where(ChunkTable.id.in_(chunk_ids))
    .values(status="archived", updated_at=datetime.utcnow())
)
await self.db.execute(stmt)
```

For tags (which require merging, not overwriting), we need per-chunk updates since SQLite doesn't support JSON array merge operations. Strategy: batch into groups of 100 and update in a single transaction.

#### 2.2.4 Frontend State Management

```typescript
// New signals for bulk selection
export const selectedChunkIds = signal<Set<string>>(new Set())
export const bulkMode = signal(false)
export const bulkLoading = signal(false)

// Computed
export const selectedCount = computed(() => selectedChunkIds.value.size)
export const hasSelection = computed(() => selectedChunkIds.value.size > 0)

// Actions
export function toggleChunkSelection(id: string): void { ... }
export function selectAllVisible(): void { ... }
export function clearSelection(): void { ... }
export async function bulkTag(tags: string[]): Promise<BulkActionResult> { ... }
export async function bulkArchive(): Promise<BulkActionResult> { ... } 
export async function bulkDelete(): Promise<BulkActionResult> { ... }
export async function undoBulkAction(actionId: string): Promise<BulkActionResult> { ... }
```

#### 2.2.5 Frontend Components

**New: `BulkActions.tsx`**
- Floating action bar appears when `hasSelection` is true
- Shows selected count: "5 chunks selected"
- Action buttons: Tag, Archive, Delete
- Undo toast notification after action completes (30-minute countdown)

**Modified: `ChunkList.tsx`**
- Add checkbox to each `chunk-item` card (left side)
- Add "Select All" toggle at top of list
- Pass `selectedChunkIds` signal to control checkbox state
- Shift+click for range selection

**New: `TagInput.tsx`**
- Reusable tag input component with comma-separated entry
- Autocomplete from existing tags (via future GET /tags endpoint)
- Used in bulk tag modal and capture form

#### 2.2.6 Integration Points

| System | Protocol | Purpose | Fallback |
|--------|----------|---------|----------|
| SQLite | SQL | Bulk UPDATE/SELECT | — (core dependency) |
| SSE EventBus | Server-sent events | Broadcast "chunks_updated" after bulk ops | Silent (UI refreshes on next fetch) |
| Search API | HTTP | Resolve text query filters into chunk IDs | Return error if search unavailable |

---

## Part 3: Trade-off Analysis

### Decision 1: Single Container vs. Separate Frontend/Backend

**Options:**
1. **Single container** — Uvicorn serves API + static files
   - Pro: Simple deployment, one process to manage, one port
   - Con: Frontend can't be deployed to CDN, slight overhead serving static files
   
2. **Separate containers** — Nginx for frontend, Uvicorn for backend
   - Pro: CDN-ready frontend, proper reverse proxy
   - Con: Two containers to manage, CORS complexity, docker-compose required

**Selected:** Single container

**Rationale:** For a solo-dev MVP, operational simplicity trumps CDN performance. FastAPI's `StaticFiles` is production-ready for serving Vite builds. Migration to separate containers is trivial when needed (extract static mount, add Nginx config).

**Reversibility:** Easy — extract static files to separate container in 1-2 hours.

### Decision 2: SQLite vs. PostgreSQL for Production

**Options:**
1. **Keep SQLite** — Use Docker volume for persistence
   - Pro: Zero additional dependencies, existing code works unchanged, fine for 1 user
   - Con: No concurrent writes, no `pg_dump`, no cloud-managed option
   
2. **Migrate to PostgreSQL** — Use managed DB (Neon, Supabase, RDS)
   - Pro: Concurrent access, proper scaling, managed backups
   - Con: 6-8 hours migration effort, new dependency, $$$ for managed service

**Selected:** Keep SQLite for v0.6.0

**Rationale:** Komorebi is single-user for now. SQLite handles reads well and our write rate (capture pipeline) is low. The `KOMOREBI_DATABASE_URL` environment variable already supports swapping to PostgreSQL later — just change the connection string and install `asyncpg`.

**Reversibility:** Medium — SQLAlchemy abstracts 90% of the difference, but JSON column behavior and LIKE vs ILIKE need testing.

### Decision 3: Soft Delete vs. Hard Delete for Bulk Delete

**Options:**
1. **Soft delete** — Set status to `deleted`, keep in database
   - Pro: Undo is trivial (restore previous status), no data loss
   - Con: "Deleted" chunks still count in queries unless filtered, storage never freed
   
2. **Hard delete** — Remove rows from database
   - Pro: Clean database, storage freed
   - Con: Undo requires backup table or audit log with full content

**Selected:** Soft delete (new status: `deleted`)

**Rationale:** Aligns with "Capture-First" philosophy — never lose data unless explicitly purged. Add a future `purge` endpoint for permanent removal after 30 days.

**Reversibility:** Easy — add hard delete endpoint later.

### Decision 4: Bulk Tag Implementation — Batch Update vs. Individual

**Options:**
1. **Single SQL UPDATE** — Use `JSON_SET` or equivalent
   - Pro: O(1) database operation
   - Con: SQLite doesn't support `JSON_ARRAY_APPEND` or merge operations natively
   
2. **Batch individual updates** — Load chunks, merge tags in Python, update in transaction
   - Pro: Works with SQLite JSON columns, full control over deduplication
   - Con: N reads + N writes inside transaction, slower for large batches

**Selected:** Batch individual updates (groups of 100, single transaction)

**Rationale:** SQLite's JSON support is too limited for in-database array merging. Python-side tag merging is correct and the 100-per-batch approach keeps memory bounded. For 1000 chunks, this is ~10 batches × ~5ms each = 50ms total — well within our 2-second target.

**Reversibility:** Easy — migrate to PostgreSQL's `jsonb_array_elements` + `array_agg` when switching databases.

### Decision 5: Undo Strategy — Previous State Snapshot vs. Event Sourcing

**Options:**
1. **Previous state snapshot** — Store `[{id, status, tags}]` in bulk_actions table
   - Pro: Simple, undo is just restoring saved state, self-contained
   - Con: Storage grows with action size (1000 chunks × ~200 bytes = ~200KB per action)
   
2. **Event sourcing** — Store operations as events, replay backwards for undo
   - Pro: Elegant, composable, supports chained undos
   - Con: Complex implementation, requires event replay engine

**Selected:** Previous state snapshot

**Rationale:** Simplicity wins. 200KB per bulk action is negligible. The snapshot approach makes undo a deterministic restore operation with no replay logic. We can garbage-collect old snapshots (>30 days) later.

**Reversibility:** Hard — event sourcing would require rewriting the audit infrastructure.

---

## Part 4: Implementation Plan

### Sprint 1: Deployment (8–12 hours)

#### Backend (4 hours)
- [ ] Add `StaticFiles` mount to `main.py` (conditional, when `static/` exists)
- [ ] Enhance `/health` endpoint with database check and version info
- [ ] Add `KOMOREBI_CORS_ORIGINS` environment variable parsing
- [ ] Add `PORT` environment variable support
- [ ] Ensure `data/` directory auto-creation for SQLite
- [ ] Read `VERSION` file for API version response

#### Infrastructure (4 hours)
- [ ] Create `Dockerfile` (multi-stage: node build → python runtime)
- [ ] Create `docker-compose.yml` (single service + volume)
- [ ] Create `.dockerignore` (exclude tests, docs, git, venv)
- [ ] Test `docker build && docker run` locally
- [ ] Verify frontend loads from container via browser

#### Deployment (2 hours)
- [ ] Create `railway.toml` or `fly.toml` configuration
- [ ] Configure persistent volume for SQLite
- [ ] Set environment variables
- [ ] Deploy and verify end-to-end

#### Tests (2 hours)
- [ ] Test health endpoint returns database status
- [ ] Test static file serving (frontend loads from FastAPI)
- [ ] Test environment variable configuration
- [ ] Docker build integration test (build succeeds)

### Sprint 2: Bulk Operations (10–16 hours)

#### Backend (6 hours)
- [ ] Create Pydantic models: `BulkFilter`, `BulkTagRequest`, `BulkArchiveRequest`, `BulkDeleteRequest`, `BulkActionResult`, `BulkActionLog`
- [ ] Add `BulkActionTable` to database schema
- [ ] Create `BulkRepository` with `_resolve_filter()`, `bulk_tag()`, `bulk_archive()`, `bulk_delete()`, `undo()`
- [ ] Add bulk endpoints to `chunks.py` router (5 endpoints)
- [ ] Add migration script for `bulk_actions` table
- [ ] Broadcast SSE event after bulk operations

#### Backend Tests (3 hours)
- [ ] Test bulk tag: adds tags, deduplicates, logs action
- [ ] Test bulk archive: changes status, stores previous state
- [ ] Test bulk delete: soft-deletes, undo restores
- [ ] Test undo: within window succeeds, expired returns 410
- [ ] Test filter validation: empty filter rejected, >1000 limit enforced
- [ ] Test bulk history: returns recent actions
- [ ] Hammer test: 1000-chunk bulk operation under 2 seconds

#### Frontend (6 hours)
- [ ] Add bulk selection signals to store
- [ ] Create `BulkActions.tsx` floating bar component
- [ ] Create `TagInput.tsx` reusable component
- [ ] Modify `ChunkList.tsx`: add checkboxes, select-all, shift-click
- [ ] Add undo toast notification (30-min countdown)
- [ ] Style bulk selection and action components

#### Frontend Tests (1 hour)
- [ ] E2E: Select multiple chunks, apply tag, verify
- [ ] E2E: Bulk archive, verify status change
- [ ] E2E: Undo action, verify restoration

---

## Part 5: Database Schema

### New Table: `bulk_actions`

```sql
CREATE TABLE bulk_actions (
    id VARCHAR(36) PRIMARY KEY,
    action_type VARCHAR(20) NOT NULL,     -- 'tag', 'archive', 'delete', 'restore'
    filter_used JSON NOT NULL,             -- The filter criteria used
    affected_ids JSON NOT NULL,            -- List of chunk IDs affected
    previous_state JSON NOT NULL,          -- [{id, status, tags}, ...] for undo
    affected_count INTEGER NOT NULL,       -- Denormalized count
    undone BOOLEAN DEFAULT FALSE,          -- Whether reversed
    created_at DATETIME NOT NULL           -- Action timestamp
);

CREATE INDEX idx_bulk_actions_created ON bulk_actions(created_at);
CREATE INDEX idx_bulk_actions_type ON bulk_actions(action_type);
```

### Modified Table: `chunks`

No schema changes needed. The `status` column already supports string values — we add `deleted` as a new status value in the application layer.

**Updated status enum:** `inbox`, `processed`, `compacted`, `archived`, `deleted`

### Migration

```python
# scripts/migrate_module5.py
"""Migration: Add bulk_actions table and 'deleted' status support."""

async def migrate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # Creates bulk_actions if missing
        # No ALTER TABLE needed — 'deleted' is a string value, not an enum column
```

---

## Part 6: Known Constraints

1. **SQLite JSON limitations** — No `JSON_ARRAY_APPEND`, requires Python-side tag merging. Acceptable for MVP, transparent fix when migrating to PostgreSQL.
2. **Single-writer** — SQLite only allows one writer at a time. Bulk operations use a single transaction, so concurrent bulk ops will serialize. Acceptable for single-user deployment.
3. **No authentication** — Bulk operations have no user context. The audit log records the action but not "who". Add auth in v1.0.
4. **Undo window is per-action** — Cannot undo multiple actions in sequence (e.g., undo the undo). Acceptable for MVP.
5. **Tag merging is additive only** — Bulk tag adds tags but doesn't support removing tags in bulk. Add a `bulk/untag` endpoint in v0.7.0 if needed.

---

## Part 7: Blockers & Open Questions

1. **Railway persistent volume** — Need to verify SQLite works reliably on Railway's volume storage (potential journaling issues). Test with a writeahead journal (`PRAGMA journal_mode=WAL`).
2. **Ollama connectivity** — From Docker, Ollama on host requires `host.docker.internal` (macOS/Windows) or `--network=host` (Linux). Document both patterns.
3. **Frontend bundle size** — Current build is 176KB gzipped. Adding bulk UI components should keep it under 200KB. Monitor during implementation.
4. **SSE reconnection** — When deployed behind a load balancer, SSE connections may timeout. Add `retry` field in SSE events and client-side reconnection logic.

---

## Part 8: Quality Gates

Before merging:

### Schema Review
- [ ] Pydantic models complete with validators
- [ ] Database migration tested (fresh DB and existing DB)
- [ ] API contract documented in NEW_FEATURE_ARCHITECTURE.md

### Security Review
- [ ] No secrets in Dockerfile or docker-compose.yml
- [ ] CORS origins configurable (not hardcoded `*` in production)
- [ ] Bulk operations have rate limiting (max 10 per minute)
- [ ] Filter validation prevents empty bulk operations

### Performance Review
- [ ] Docker image < 200MB
- [ ] Container startup < 5 seconds
- [ ] Bulk operation (1000 chunks) < 2 seconds
- [ ] Health endpoint < 50ms

### Testing Strategy
- [ ] Backend unit tests: 10+ new tests for bulk operations
- [ ] Backend integration: Hammer test for bulk performance
- [ ] Frontend E2E: Playwright tests for multi-select and bulk actions
- [ ] Docker: Build and run integration test
- [ ] Deployment: Smoke test on target platform

---

## Next Phase

After v0.6.0 ships:
- Collect user feedback from alpha deployment
- Prioritize Module 6 features based on real usage patterns
- Consider PostgreSQL migration if multiple users needed
- Consider FTS5 migration if search volume warrants it

Code is ready for implementation via `/implement-feature` prompt.
All design decisions documented above. No further architectural questions.
