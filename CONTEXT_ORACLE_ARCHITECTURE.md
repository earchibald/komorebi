# Feature Architecture: Context Oracle — MCP Server, Filesystem Awareness & Governance Engine

## Feature Overview

A secure, bidirectional context engine that transforms Komorebi from a passive capture tool into an active **MCP Server** — exposing its accumulated knowledge (chunks, entities, traces, file events) as tools that coding agents (Claude Code, Cursor, Windsurf) can invoke. Bundled with filesystem monitoring (`k watch`), execution profiles with security policies, trace lifecycle management, and an LLM cost governance dashboard.

## Architecture Summary

The system introduces **seven new subsystems** spanning the full stack:

1. **Komorebi MCP Server** — Exposes Komorebi data as MCP tools via `stdio` transport (same protocol Komorebi already speaks as a client). Coding agents connect and call `search_context`, `get_active_trace`, `read_file_metadata`, and `get_related_decisions`.
2. **Filesystem Watcher** — A daemon thread using `watchdog` that monitors paths for file events, recording lightweight `FileEvent` chunks with sha256 hashes.
3. **Execution Profiles** — YAML-defined environment wrappers with inheritance, blocking policies, and secret redaction for `k exec`.
4. **Trace Lifecycle** — Interactive create/switch with fuzzy matching and AI-suggested names, plus rename support.
5. **Redaction Service** — Regex-based secret scrubbing applied before any data leaves to cloud LLMs.
6. **LLM Cost Dashboard** — Token counting middleware, budget caps, auto-downgrade logic, and a frontend billing UI.
7. **CLI Extensions** — New `k watch`, `k exec`, `k switch`, `k trace rename` commands.

The design reuses existing infrastructure (MCP client/registry, Chunk/Entity models, CLI via Typer, Signals store) and adds no new external Python dependencies beyond `watchdog` and `pyyaml`.

---

## Acceptance Criteria

- [ ] Komorebi can serve as an MCP Server over `stdio`, responding to `initialize`, `tools/list`, and `tools/call`
- [ ] External coding agents (Claude Code) can connect to Komorebi as an MCP server and call `search_context(query)`
- [ ] `k watch ./path --recursive` starts a filesystem watcher daemon that records `FileEvent` chunks
- [ ] `k watch status` lists all active watchers globally
- [ ] Execution profiles load from `~/.komorebi/profiles.yaml` with inheritance (`parent` key)
- [ ] `k exec --profile=production` applies env vars, blocking policies, and redaction
- [ ] `k switch trace-name` creates or switches traces with fuzzy matching
- [ ] `k trace rename "New Name"` renames the active trace
- [ ] `RedactionService` scrubs AWS keys, private keys, and GitHub tokens before cloud LLM requests
- [ ] `GET /api/v1/llm/usage` returns token usage per model with cost estimates
- [ ] Budget cap enforcement auto-downgrades cloud LLM to local when exceeded
- [ ] Frontend `/settings/billing` tab shows real-time cost table and budget controls
- [ ] All new endpoints have tests; all new CLI commands have tests

---

## User Stories

- **As a coding agent**, I want to call `search_context("auth error")` via MCP so I can recover context without asking the user.
- **As a developer**, I want to run `k watch ./config` so file changes are automatically tracked as context.
- **As a developer**, I want to define execution profiles so I can safely run commands in production-like environments with secret redaction.
- **As a developer**, I want `k switch` to offer fuzzy matching so I don't need to remember exact trace names.
- **As a team lead**, I want to see LLM costs per model and set budget caps so I avoid surprise bills.

---

## Constraints

- Must use: Python 3.11+, FastAPI, SQLAlchemy async, Pydantic v2, Typer CLI, Preact Signals
- Must use: MCP Protocol Spec 2024-11-05 (same version already implemented in client)
- Cannot use: External databases (stick to SQLite for MVP)
- Cannot use: Cloud-specific SDKs for cost tracking (use heuristic token counting)
- Timeline: 3 implementation phases over ~3 sprints

---

## Edge Cases

1. What if the coding agent sends malformed MCP requests? → Return JSON-RPC error responses per spec.
2. What if `watchdog` crashes or the watched path is deleted? → Graceful degradation; log error, mark watcher as inactive.
3. What if `profiles.yaml` has circular inheritance? → Detect cycles during load, raise `ConfigError`.
4. What if Ollama is down when fuzzy-match trace naming needs AI? → Fall back to simple string similarity (difflib).
5. What if the budget cap is hit mid-request? → Complete current request, block subsequent ones, notify via SSE.
6. What if the user watches `/` recursively? → Enforce max depth (default 5) and max path count (default 1000).

---

## System Design

### Component Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL CODING AGENTS                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Claude Code   │  │   Cursor     │  │  Windsurf    │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         │ MCP (stdio)     │                  │                       │
└─────────┼─────────────────┼──────────────────┼───────────────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    KOMOREBI MCP SERVER                                │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  KomorebiMCPServer (stdio transport, JSON-RPC)                 │  │
│  │                                                                │  │
│  │  Tools:                                                        │  │
│  │  ├── search_context(query, limit) → SearchResult[]             │  │
│  │  ├── get_active_trace() → TraceSummary                         │  │
│  │  ├── read_file_metadata(path) → FileEventHistory               │  │
│  │  └── get_related_decisions(topic) → Entity[]                   │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ calls                                    │
│  ┌────────────────────────▼───────────────────────────────────────┐  │
│  │                 EXISTING BACKEND (FastAPI)                      │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │  │
│  │  │ChunkRepo    │ │EntityRepo    │ │  FileEventRepo (NEW)     │ │  │
│  │  └─────────────┘ └──────────────┘ └──────────────────────────┘ │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │  │
│  │  │CostService  │ │RedactionSvc  │ │  ProfileManager          │ │  │
│  │  │(NEW)        │ │(NEW)         │ │  (NEW)                   │ │  │
│  │  └─────────────┘ └──────────────┘ └──────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │              FILESYSTEM WATCHER DAEMON                         │  │
│  │  watchdog → FileEvent chunks → active Trace                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                   CLI (Typer)                                  │  │
│  │  k watch | k exec | k switch | k trace rename                  │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                    REACT DASHBOARD                                    │
│  ┌──────────────────┐  ┌──────────────────┐                          │
│  │ BillingDashboard │  │ WatcherStatus    │                          │
│  │ (NEW)            │  │ (NEW)            │                          │
│  └──────────────────┘  └──────────────────┘                          │
└──────────────────────────────────────────────────────────────────────┘
```

---

### Pydantic Models Required

#### MCP Server Models (`backend/app/models/oracle.py`)

```python
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class TraceStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class Trace(BaseModel):
    """A named context session grouping related chunks."""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=255)
    status: TraceStatus = Field(default=TraceStatus.ACTIVE)
    meta_summary: Optional[str] = None
    created_at: str
    updated_at: str


class TraceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class TraceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[TraceStatus] = None
    meta_summary: Optional[str] = None


class TraceSummary(BaseModel):
    """Lightweight trace info returned by MCP tools."""
    id: UUID
    name: str
    status: TraceStatus
    meta_summary: Optional[str] = None
    chunk_count: int = 0
    last_activity: Optional[str] = None
```

#### File Event Models (`backend/app/models/file_event.py`)

```python
class CrudOp(str, Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


class FileEvent(BaseModel):
    """A lightweight record of a filesystem change."""
    id: UUID = Field(default_factory=uuid4)
    trace_id: UUID = Field(..., description="Trace this event belongs to")
    path: str = Field(..., description="Absolute file path")
    crud_op: CrudOp
    size_bytes: Optional[int] = None
    hash_prefix: Optional[str] = Field(None, description="sha256 of first 8KB")
    mime_type: Optional[str] = None
    created_at: str


class FileEventCreate(BaseModel):
    trace_id: UUID
    path: str
    crud_op: CrudOp
    size_bytes: Optional[int] = None
    hash_prefix: Optional[str] = None
    mime_type: Optional[str] = None


class FileEventHistory(BaseModel):
    """CRUD history of a single file path."""
    path: str
    events: list[FileEvent] = []
    current_hash: Optional[str] = None
    last_modified: Optional[str] = None
```

#### Execution Profile Models (`backend/app/models/profile.py`)

```python
class BlockingPolicy(BaseModel):
    """Security policies for profile execution."""
    network: bool = Field(default=False, description="Block network access")
    write_files: list[str] = Field(default_factory=list, description="Glob patterns to block writes to")


class ExecutionProfile(BaseModel):
    """An execution environment wrapper."""
    name: str
    parent: Optional[str] = None
    command: Optional[list[str]] = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    blocking: BlockingPolicy = Field(default_factory=BlockingPolicy)
    redact_secrets: bool = Field(default=True)
    stream_output: bool = Field(default=False)
    capture_stdin: bool = Field(default=False)


class ResolvedProfile(BaseModel):
    """Profile after inheritance resolution."""
    name: str
    command: Optional[list[str]] = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    blocking: BlockingPolicy = Field(default_factory=BlockingPolicy)
    redact_secrets: bool = True
    stream_output: bool = False
    capture_stdin: bool = False
```

#### LLM Cost Models (`backend/app/models/cost.py`)

```python
class ModelUsage(BaseModel):
    """Token usage for a specific model."""
    model_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    request_count: int = 0


class UsageSummary(BaseModel):
    """Aggregated usage across all models."""
    models: list[ModelUsage] = []
    total_cost_usd: float = 0.0
    budget_cap_usd: Optional[float] = None
    budget_remaining_usd: Optional[float] = None
    throttled: bool = False
    period: str = "daily"  # daily | weekly | monthly


class BudgetConfig(BaseModel):
    """Budget cap configuration."""
    daily_cap_usd: Optional[float] = None
    auto_downgrade: bool = True
    downgrade_model: str = "llama3"
```

---

### Database Schema

#### New Tables

```sql
-- Traces: named context sessions
CREATE TABLE traces (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',       -- active, paused, closed
    meta_summary TEXT,
    created_at  DATETIME NOT NULL,
    updated_at  DATETIME NOT NULL
);
CREATE INDEX idx_traces_status ON traces(status);
CREATE INDEX idx_traces_name ON traces(name);

-- File events: filesystem change log
CREATE TABLE file_events (
    id          TEXT PRIMARY KEY,
    trace_id    TEXT NOT NULL REFERENCES traces(id),
    path        TEXT NOT NULL,
    crud_op     TEXT NOT NULL,                         -- created, modified, deleted, moved
    size_bytes  INTEGER,
    hash_prefix TEXT,                                  -- sha256 of first 8KB
    mime_type   TEXT,
    created_at  DATETIME NOT NULL
);
CREATE INDEX idx_file_events_trace ON file_events(trace_id);
CREATE INDEX idx_file_events_path ON file_events(path);

-- LLM usage tracking
CREATE TABLE llm_usage (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name      TEXT NOT NULL,
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    estimated_cost  REAL NOT NULL DEFAULT 0.0,
    request_type    TEXT,                              -- compact, generate, search, etc.
    created_at      DATETIME NOT NULL
);
CREATE INDEX idx_llm_usage_model ON llm_usage(model_name);
CREATE INDEX idx_llm_usage_date ON llm_usage(created_at);
```

#### Modified Tables

```sql
-- Add trace_id to chunks for trace association
ALTER TABLE chunks ADD COLUMN trace_id TEXT REFERENCES traces(id);
CREATE INDEX idx_chunks_trace ON chunks(trace_id);
```

- New tables: `traces`, `file_events`, `llm_usage`
- Modified tables: `chunks` (add `trace_id` column)
- Migrations needed: Yes — `scripts/migrate_v1_oracle.py`
- Indexes: All foreign keys and common query paths indexed

---

### API Endpoints

#### Trace Management

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /api/v1/traces | - | Create a new trace |
| GET | /api/v1/traces | - | List all traces (with status filter) |
| GET | /api/v1/traces/active | - | Get the currently active trace |
| GET | /api/v1/traces/{id} | - | Get trace by ID |
| PATCH | /api/v1/traces/{id} | - | Update trace (rename, change status) |
| POST | /api/v1/traces/{id}/activate | - | Set trace as active (deactivates others) |

#### File Events

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | /api/v1/file-events | - | List file events (filter by trace, path) |
| GET | /api/v1/file-events/history/{path} | - | Get CRUD history for a specific file path |

#### LLM Usage & Cost

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | /api/v1/llm/usage | - | Get usage summary (period filter) |
| GET | /api/v1/llm/budget | - | Get current budget configuration |
| PUT | /api/v1/llm/budget | - | Update budget configuration |

#### Total: 11 new API endpoints

---

### MCP Server Tool Definitions

The Komorebi MCP Server exposes **4 tools** to connected coding agents:

```json
{
  "tools": [
    {
      "name": "search_context",
      "description": "Search all captured chunks and entities in Komorebi for relevant context",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": { "type": "string", "description": "Search query text" },
          "limit": { "type": "integer", "default": 10, "description": "Max results" }
        },
        "required": ["query"]
      }
    },
    {
      "name": "get_active_trace",
      "description": "Returns the currently active trace with summary and chunk count",
      "inputSchema": {
        "type": "object",
        "properties": {}
      }
    },
    {
      "name": "read_file_metadata",
      "description": "Returns CRUD event history for a specific file path tracked by k watch",
      "inputSchema": {
        "type": "object",
        "properties": {
          "path": { "type": "string", "description": "Absolute or relative file path" }
        },
        "required": ["path"]
      }
    },
    {
      "name": "get_related_decisions",
      "description": "Returns Decision entities relevant to a topic from the active trace",
      "inputSchema": {
        "type": "object",
        "properties": {
          "topic": { "type": "string", "description": "Topic or keyword to match decisions against" },
          "limit": { "type": "integer", "default": 5, "description": "Max results" }
        },
        "required": ["topic"]
      }
    }
  ]
}
```

---

### Frontend Components

#### BillingDashboard (`frontend/src/components/BillingDashboard.tsx`)
- Purpose: Real-time LLM usage table with cost per model, budget cap controls
- Signals: `llmUsage`, `budgetConfig`, `budgetLoading`
- Sub-components: `UsageTable`, `BudgetEditor`, `ThrottleAlert`

#### WatcherStatus (`frontend/src/components/WatcherStatus.tsx`)
- Purpose: Display active filesystem watchers and recent file events
- Signals: `activeWatchers`, `recentFileEvents`
- Sub-components: `WatcherList`, `FileEventTimeline`

#### New signals store (`frontend/src/store/oracle.ts`)
```typescript
import { signal, computed } from '@preact/signals-react'

// LLM Usage
export const llmUsage = signal<ModelUsage[]>([])
export const budgetConfig = signal<BudgetConfig | null>(null)
export const budgetLoading = signal(false)

// Traces
export const activeTrace = signal<TraceSummary | null>(null)
export const traces = signal<TraceSummary[]>([])

// File Events
export const recentFileEvents = signal<FileEvent[]>([])
export const activeWatchers = signal<WatcherInfo[]>([])

// Derived
export const totalCost = computed(() =>
  llmUsage.value.reduce((sum, m) => sum + m.estimated_cost_usd, 0)
)
export const isThrottled = computed(() => {
  if (!budgetConfig.value?.daily_cap_usd) return false
  return totalCost.value >= budgetConfig.value.daily_cap_usd
})
```

---

### External Integrations

| Service | Protocol | Purpose | Fallback |
|---------|----------|---------|----------|
| Ollama | HTTP | LLM inference for trace names, compaction, resume | Template text / difflib similarity |
| watchdog | Python lib | Filesystem event monitoring | Manual `FileEvent` creation via API |
| tiktoken | Python lib | OpenAI token counting | Character-count heuristic (÷4 approximation) |
| External Coding Agents | MCP (stdio) | Consume Komorebi context tools | N/A (passive server) |

---

## Key Trade-off Decisions

### 1. MCP Server Transport: `stdio` vs SSE

**Options Considered:**
1. **stdio** — Agent spawns `komorebi mcp-serve` as a subprocess, communicates over stdin/stdout
   - Pro: Standard MCP pattern; same as existing MCP servers in ecosystem; no port conflicts
   - Con: Agent must spawn process; heavier per-connection

2. **SSE (HTTP)** — Agent connects to `http://localhost:8000/mcp` endpoint
   - Pro: Reuses existing FastAPI server; trivial deployment
   - Con: Non-standard for MCP clients (most expect stdio); requires SSE→JSON-RPC translation layer

**Selected:** `stdio`

**Rationale:** All existing MCP client implementations (Claude Code, Cursor, VS Code) expect `stdio` transport. SSE transport exists in spec but has limited client support. Using `stdio` also decouples the MCP server from the web API lifecycle — they can run independently.

**Reversibility:** Medium — SSE transport can be added later as a second transport option without breaking `stdio`.

---

### 2. Trace-Chunk Association: Foreign Key vs Tag-Based

**Options Considered:**
1. **Foreign Key** — Add `trace_id` column to `chunks` table
   - Pro: Fast queries, referential integrity, simple JOINs
   - Con: Schema migration needed

2. **Tag-Based** — Add `trace:name` to chunk tags
   - Pro: Zero migration, works immediately
   - Con: No referential integrity, tag string parsing, slower queries

**Selected:** Foreign Key (`trace_id` column)

**Rationale:** Traces are a first-class concept (not a workaround). FK gives us query performance, integrity, and clean data modeling. Migration is straightforward — nullable column addition.

**Reversibility:** Hard — once data uses FK, switching to tags requires data migration.

---

### 3. Filesystem Watcher: In-Process vs Separate Daemon

**Options Considered:**
1. **In-Process** — watchdog runs inside the FastAPI server
   - Pro: Single process; direct DB access; simpler deployment
   - Con: Crashes affect API; watcher lifecycle tied to server

2. **Separate Daemon** — `k watch` starts an independent background process
   - Pro: Isolated failure domain; can watch without running server; long-lived
   - Con: IPC needed (HTTP calls to API or direct DB writes)

**Selected:** Separate Daemon (CLI-managed background process)

**Rationale:** Filesystem watching is a long-running concern orthogonal to the API server. Users may want to watch files without running the dashboard. The daemon writes `FileEvent` chunks via the REST API, keeping data flow unidirectional.

**Reversibility:** Easy — daemon could be moved in-process later since it communicates via HTTP.

---

### 4. Token Counting: tiktoken vs Heuristic

**Options Considered:**
1. **tiktoken** — Accurate BPE tokenization for OpenAI models
   - Pro: Exact counts; matches billing
   - Con: New dependency; only accurate for OpenAI models

2. **Character heuristic** — `len(text) / 4` approximation
   - Pro: Zero dependencies; works for any model
   - Con: ~15-20% error margin

**Selected:** Heuristic for MVP, with `tiktoken` as optional upgrade

**Rationale:** Komorebi primarily uses Ollama (local Llama3) where exact token counts don't matter for billing. For cloud models, the heuristic is close enough for budget capping. `tiktoken` can be added as an optional dependency for users who need exact OpenAI billing.

**Reversibility:** Easy — `CostService` abstracts counting behind an interface.

---

### 5. Secret Redaction: Pre-Send vs Proxy Layer

**Options Considered:**
1. **Pre-Send** — Redact in `RedactionService` before calling LLM
   - Pro: Simple; no infrastructure; works everywhere
   - Con: Must be called explicitly; can be forgotten

2. **Proxy Layer** — HTTP middleware redacts all outbound LLM requests
   - Pro: Cannot be bypassed; transparent
   - Con: Complex; must parse/modify HTTP bodies; fragile

**Selected:** Pre-Send with enforcement via `CostService` middleware

**Rationale:** The `CostService` already wraps every LLM call for token counting. Adding redaction there guarantees coverage without the complexity of an HTTP proxy. The `CompactorService` and `KomorebiLLM` both go through this middleware.

**Reversibility:** Easy — middleware can be enhanced or replaced independently.

---

### 6. Profile Dangerous Env Vars: Whitelist vs Blacklist

**Options Considered:**
1. **Blacklist** — Block known dangerous vars (LD_PRELOAD, DYLD_INSERT_LIBRARIES, etc.)
   - Pro: Permissive; allows most env vars
   - Con: Can miss new attack vectors

2. **Whitelist** — Only allow explicitly approved env var patterns
   - Pro: Secure by default
   - Con: Overly restrictive; poor DX

**Selected:** Blacklist with explicit override in `~/.komorebi/config.yaml`

**Rationale:** Users define profiles for their own environments. A blacklist catches known dangerous vars while remaining flexible. Power users can explicitly whitelist blocked vars in the config, which serves as an intentional opt-in.

**Reversibility:** Easy — switching to whitelist is an additive config change.

---

## Implementation Tasks (Estimated)

### Phase 1: Security & Profiles (8 hours)

#### Backend (5 hours)
- [ ] `RedactionService` (`backend/app/core/redaction.py`) — regex scrubbers for AWS keys, GH tokens, private keys, API keys
- [ ] `ProfileManager` (`backend/app/core/profiles.py`) — YAML parser, inheritance resolution, cycle detection, env var blacklist
- [ ] Pydantic models: `ExecutionProfile`, `ResolvedProfile`, `BlockingPolicy` (`backend/app/models/profile.py`)
- [ ] Tests: redaction patterns, profile inheritance, cycle detection, blacklist enforcement

#### CLI (3 hours)
- [ ] `k exec --profile=<name> [-- command]` — load profile, apply env, enforce blocking, redact
- [ ] `k exec --list-profiles` — list available profiles
- [ ] Tests: CLI profile loading, command execution with env overlay

### Phase 2: The Context Oracle — MCP Server (12 hours)

#### Backend (8 hours)
- [ ] `KomorebiMCPServer` (`backend/app/mcp/server.py`) — stdio transport, JSON-RPC handler, tool dispatch
- [ ] Pydantic models: `Trace`, `TraceCreate`, `TraceSummary` (`backend/app/models/oracle.py`)
- [ ] Database: `TraceTable`, `FileEventTable` SQLAlchemy models, migration script
- [ ] `TraceRepository` (`backend/app/db/trace_repository.py`) — CRUD, active trace management
- [ ] `FileEventRepository` (`backend/app/db/file_event_repository.py`) — CRUD, path history queries
- [ ] API routes: Trace CRUD + File Event queries (`backend/app/api/traces.py`, `backend/app/api/file_events.py`)
- [ ] MCP tool implementations: `search_context`, `get_active_trace`, `read_file_metadata`, `get_related_decisions`
- [ ] Tests: MCP server protocol, tool handlers, trace lifecycle, file event queries

#### CLI (4 hours)
- [ ] `k mcp-serve` — start Komorebi as an MCP server (stdio mode)
- [ ] `k switch <trace-name>` — create/switch traces with fuzzy matching (difflib + optional Ollama)
- [ ] `k trace rename <new-name> [--id=uuid]` — rename active or specific trace
- [ ] `k watch <path> [--recursive]` — start filesystem watcher daemon
- [ ] `k watch status` — list active watchers globally
- [ ] Tests: CLI commands, trace switching, watcher lifecycle

### Phase 3: Filesystem Watcher & Cost Governance (10 hours)

#### Backend (5 hours)
- [ ] `FileWatcherDaemon` (`backend/app/core/watcher.py`) — watchdog integration, hash computation, FileEvent creation via API
- [ ] `CostService` (`backend/app/services/cost_service.py`) — token counting, cost estimation, budget enforcement, auto-downgrade
- [ ] Database: `LLMUsageTable` SQLAlchemy model
- [ ] API routes: LLM usage + budget endpoints (`backend/app/api/billing.py`)
- [ ] Wire `CostService` into `CompactorService` and `KomorebiLLM` as middleware
- [ ] Tests: token counting heuristic, budget enforcement, auto-downgrade logic

#### Frontend (4 hours)
- [ ] Signals store: `frontend/src/store/oracle.ts` — usage, budget, traces, file events
- [ ] `BillingDashboard` component — usage table, budget cap editor, throttle alert
- [ ] `WatcherStatus` component — active watchers, recent file events timeline
- [ ] New tab integration in `App.tsx` (Settings → Billing sub-tab)

#### Integration (1 hour)
- [ ] End-to-end: Agent connects via MCP → calls `search_context` → gets results
- [ ] End-to-end: `k watch` → file change → `FileEvent` in DB → visible in dashboard
- [ ] Documentation updates: ARCHITECTURE.md, API_REFERENCE.md, GETTING_STARTED.md

---

### Total Estimated: ~30 hours across 3 phases

| Phase | Backend | CLI | Frontend | Integration | Total |
|-------|---------|-----|----------|-------------|-------|
| Phase 1: Security & Profiles | 5h | 3h | — | — | 8h |
| Phase 2: Context Oracle (MCP) | 8h | 4h | — | — | 12h |
| Phase 3: Watcher & Cost | 5h | — | 4h | 1h | 10h |
| **Total** | **18h** | **7h** | **4h** | **1h** | **30h** |

---

## Known Constraints

- **SQLite concurrency**: The filesystem watcher daemon and API server may write concurrently. SQLite handles this with WAL mode, but under extreme load (>100 events/sec), events may queue. Acceptable for MVP; PostgreSQL upgrade path exists.
- **MCP protocol version**: Locked to 2024-11-05 spec. If clients upgrade to a newer spec, the server must be updated.
- **Token counting accuracy**: Heuristic counting (÷4) is ~15-20% off for OpenAI models. Acceptable for budget alerting; not suitable for exact billing reconciliation.
- **Watcher platform support**: `watchdog` works on macOS (FSEvents), Linux (inotify), and Windows (ReadDirectoryChangesW). Behavior varies slightly per OS.
- **Profile security**: Blacklist cannot prevent all possible env var attacks. Users must not run untrusted profiles.

---

## Blockers or Open Questions

1. **Trace ↔ Project relationship**: Should traces be 1:1 with projects, or orthogonal? → **Provisional decision:** Orthogonal. A trace can span multiple projects (e.g., an incident trace touches multiple codebases). Chunks link to both `project_id` and `trace_id` independently. Logged in `ELICITATIONS.md`.

2. **MCP Server auth**: Should the MCP server require authentication? → **Provisional decision:** No auth for MVP (local-only `stdio` transport). Auth can be added for SSE transport in v2.

3. **Watcher persistence**: Should watcher registrations survive server restart? → **Provisional decision:** Yes — store in a simple JSON file (`~/.komorebi/watchers.json`). The daemon re-registers on boot.

---

## Module Assignment

| Module | Version | Component |
|--------|---------|-----------|
| **M9: Context Oracle (MCP Server)** | v1.0.0 | MCP Server, Traces, File Events |
| **M10: Security & Profiles** | v1.0.0 | RedactionService, ProfileManager, k exec |
| **M11: Cost Governance** | v1.0.0 | CostService, BillingDashboard, Budget Caps |

---

## Next Phase

Code is ready for implementation via `/implement-feature` prompt.
All design decisions documented above. No further architectural questions.

Implementation order: **Phase 1 (Security)** → **Phase 2 (MCP Server)** → **Phase 3 (Watcher & Cost)**.

Each phase is independently shippable, testable, and deployable.
