# Komorebi Architecture

*Technical deep dive into the Komorebi cognitive infrastructure system.*

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Design Philosophy](#design-philosophy)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Database Design](#database-design)
6. [API Design](#api-design)
7. [Event System](#event-system)
8. [MCP Integration](#mcp-integration)
9. [Frontend Architecture](#frontend-architecture)
10. [Security Architecture](#security-architecture)
11. [Scalability Considerations](#scalability-considerations)
12. [Technology Decisions](#technology-decisions)

---

## System Overview

Komorebi is a cognitive infrastructure system designed for:

- **Fast Capture** - Zero-friction information capture
- **Recursive Compaction** - Intelligent summarization of context
- **Tool Aggregation** - Unified access to external MCP servers

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS                                     │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────────┐   │
│  │ React Dashboard│  │   CLI Tool    │  │    External Clients       │   │
│  │  (TypeScript)  │  │   (Typer)     │  │   (curl, httpx, etc.)     │   │
│  └───────┬───────┘  └───────┬───────┘  └────────────┬──────────────┘   │
│          │                  │                       │                   │
└──────────┼──────────────────┼───────────────────────┼───────────────────┘
           │                  │                       │
           │     HTTP/REST    │                       │
           └──────────────────┼───────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND SERVICE                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI Application                       │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │                     API Layer (Routers)                   │   │   │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐ │   │   │
│  │  │  │ Chunks  │ │Projects │ │   MCP   │ │      SSE        │ │   │   │
│  │  │  │ Router  │ │ Router  │ │ Router  │ │     Router      │ │   │   │
│  │  │  └────┬────┘ └────┬────┘ └────┬────┘ └────────┬────────┘ │   │   │
│  │  └───────┼───────────┼───────────┼───────────────┼──────────┘   │   │
│  │          │           │           │               │               │   │
│  │  ┌───────┴───────────┴───────────┴───────────────┴──────────┐   │   │
│  │  │                     Core Services                         │   │   │
│  │  │  ┌─────────────────┐  ┌─────────────────────────────────┐│   │   │
│  │  │  │  Compactor      │  │       Event Bus (SSE)           ││   │   │
│  │  │  │  Service        │  │                                 ││   │   │
│  │  │  └────────┬────────┘  └─────────────────────────────────┘│   │   │
│  │  └───────────┼──────────────────────────────────────────────┘   │   │
│  │              │                                                   │   │
│  │  ┌───────────┴──────────────────────────────────────────────┐   │   │
│  │  │                  MCP Aggregator                           │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │   │   │
│  │  │  │ MCP Client  │  │ MCP Client  │  │ MCP Client  │       │   │   │
│  │  │  │  (GitHub)   │  │ (Filesystem)│  │  (Memory)   │       │   │   │
│  │  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │   │   │
│  │  └─────────┼────────────────┼────────────────┼──────────────┘   │   │
│  │            │                │                │                   │   │
│  └────────────┼────────────────┼────────────────┼───────────────────┘   │
│               │                │                │                       │
│  ┌────────────┴────────────────┴────────────────┴───────────────────┐   │
│  │                      Data Access Layer                            │   │
│  │  ┌─────────────────────┐  ┌─────────────────────────────────────┐│   │
│  │  │  Chunk Repository   │  │        Project Repository           ││   │
│  │  └──────────┬──────────┘  └──────────────────┬──────────────────┘│   │
│  └─────────────┼────────────────────────────────┼───────────────────┘   │
│                │                                │                       │
│  ┌─────────────┴────────────────────────────────┴───────────────────┐   │
│  │                    SQLAlchemy Async ORM                           │   │
│  └───────────────────────────────┬──────────────────────────────────┘   │
│                                  │                                      │
└──────────────────────────────────┼──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATABASE                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              SQLite (dev) / PostgreSQL (prod)                    │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐  │   │
│  │  │    chunks     │ │   projects    │ │     mcp_servers       │  │   │
│  │  └───────────────┘ └───────────────┘ └───────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Design Philosophy

### Core Principles

#### 1. Capture Now, Refine Later

> Speed is the only metric that matters in the "heat of the moment."

The system is optimized for fast capture:
- Minimal required fields (just `content`)
- Background processing for enrichment
- No blocking operations on capture

#### 2. Memory Pyramid

Information flows through processing layers:

```
        ▲
       /│\        ARCHIVED
      / │ \       Long-term storage
     /──┼──\      
    /   │   \     COMPACTED
   /    │    \    Summarized context
  /─────┼─────\   
 /      │      \  PROCESSED
/       │       \ Analyzed & enriched
────────┼────────
        │         INBOX
        │         Raw capture
```

Each level contains less but more refined information.

#### 3. Async-First

All I/O operations are asynchronous:
- Async database queries (SQLAlchemy + aiosqlite)
- Async HTTP (httpx)
- Non-blocking event streaming

#### 4. Event-Driven

State changes broadcast events via SSE:
- Real-time UI updates
- Loose coupling between components
- Audit trail of operations

---

## Component Architecture

### Backend Modules

```
backend/
├── app/
│   ├── main.py           # FastAPI application entry
│   ├── api/              # HTTP endpoint routers
│   │   ├── chunks.py     # Chunk CRUD operations
│   │   ├── projects.py   # Project management
│   │   ├── mcp.py        # MCP server integration
│   │   └── sse.py        # Server-Sent Events
│   ├── core/             # Business logic
│   │   ├── compactor.py  # Summarization service
│   │   └── events.py     # Event bus for SSE
│   ├── db/               # Data access layer
│   │   ├── database.py   # SQLAlchemy setup
│   │   └── repository.py # Repository pattern
│   ├── mcp/              # MCP integration
│   │   ├── client.py     # MCP protocol client
│   │   └── registry.py   # Server registry
│   └── models/           # Pydantic schemas
│       ├── chunk.py      # Chunk model
│       ├── project.py    # Project model
│       └── mcp.py        # MCP models
└── tests/                # Test suite
```

### Dependency Injection

FastAPI's dependency injection provides:

```python
@router.post("/chunks")
async def create_chunk(
    chunk: ChunkCreate,
    repo: ChunkRepository = Depends(get_chunk_repo),  # Injected
    background_tasks: BackgroundTasks,                 # Injected
):
    ...
```

Benefits:
- Testable (easy to mock)
- Configurable (swap implementations)
- Clean separation of concerns

---

## Data Flow

### Chunk Capture Flow

```
Client                  API                 Background              Database
  │                      │                      │                      │
  │  POST /chunks        │                      │                      │
  │─────────────────────▶│                      │                      │
  │                      │  INSERT chunk        │                      │
  │                      │─────────────────────────────────────────────▶│
  │                      │                      │                      │
  │                      │  Schedule task       │                      │
  │                      │─────────────────────▶│                      │
  │                      │                      │                      │
  │  201 Created         │                      │                      │
  │◀─────────────────────│                      │                      │
  │                      │                      │                      │
  │                      │                      │  Process chunk       │
  │                      │                      │─────────────────────▶│
  │                      │                      │                      │
  │                      │      SSE: chunk.updated                     │
  │◀────────────────────────────────────────────│                      │
  │                      │                      │                      │
```

### Compaction Flow

```
Client                  API              CompactorService         Database
  │                      │                      │                      │
  │  POST /projects/     │                      │                      │
  │    {id}/compact      │                      │                      │
  │─────────────────────▶│                      │                      │
  │                      │  compact_project()   │                      │
  │                      │─────────────────────▶│                      │
  │                      │                      │                      │
  │                      │                      │  Get PROCESSED chunks│
  │                      │                      │─────────────────────▶│
  │                      │                      │◀─────────────────────│
  │                      │                      │                      │
  │                      │                      │  Summarize chunks    │
  │                      │                      │  (Map-Reduce)        │
  │                      │                      │                      │
  │                      │                      │  Update project      │
  │                      │                      │  context_summary     │
  │                      │                      │─────────────────────▶│
  │                      │                      │                      │
  │                      │                      │  Mark chunks         │
  │                      │                      │  as COMPACTED        │
  │                      │                      │─────────────────────▶│
  │                      │                      │                      │
  │  200 OK              │◀─────────────────────│                      │
  │◀─────────────────────│                      │                      │
```

---

## Database Design

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                           CHUNKS                                 │
├─────────────────────────────────────────────────────────────────┤
│ id           VARCHAR(36)  PK                                    │
│ content      TEXT         NOT NULL                              │
│ summary      TEXT                                               │
│ project_id   VARCHAR(36)  FK → projects.id                      │
│ tags         JSON         DEFAULT []                            │
│ status       VARCHAR(20)  DEFAULT 'inbox'  INDEX                │
│ source       VARCHAR(100)                                       │
│ token_count  INTEGER                                            │
│ created_at   DATETIME     NOT NULL                              │
│ updated_at   DATETIME     NOT NULL                              │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ N:1
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                          PROJECTS                                │
├─────────────────────────────────────────────────────────────────┤
│ id               VARCHAR(36)  PK                                │
│ name             VARCHAR(255) NOT NULL                          │
│ description      TEXT                                           │
│ context_summary  TEXT                                           │
│ chunk_count      INTEGER      DEFAULT 0                         │
│ created_at       DATETIME     NOT NULL                          │
│ updated_at       DATETIME     NOT NULL                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        MCP_SERVERS                               │
├─────────────────────────────────────────────────────────────────┤
│ id           VARCHAR(36)  PK                                    │
│ name         VARCHAR(255) NOT NULL                              │
│ server_type  VARCHAR(100) NOT NULL                              │
│ command      VARCHAR(500) NOT NULL                              │
│ args         JSON         DEFAULT []                            │
│ env          JSON         DEFAULT {}                            │
│ enabled      BOOLEAN      DEFAULT TRUE                          │
│ status       VARCHAR(20)  DEFAULT 'disconnected'                │
│ last_error   TEXT                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Indexes

| Table | Column | Type | Purpose |
|-------|--------|------|---------|
| chunks | status | B-Tree | Filter by status |
| chunks | project_id | B-Tree | Filter by project |
| chunks | created_at | B-Tree | Sort by date |

---

## API Design

### RESTful Principles

| Principle | Implementation |
|-----------|----------------|
| **Resources** | `/chunks`, `/projects`, `/mcp/servers` |
| **HTTP Methods** | GET (read), POST (create), PATCH (update), DELETE (remove) |
| **Status Codes** | 200, 201, 204, 400, 404, 422, 500 |
| **JSON** | All requests/responses |
| **HATEOAS** | Link to docs at root endpoint |

### Versioning

API is versioned via URL path: `/api/v1/`

### Pagination

```
GET /api/v1/chunks?limit=20&offset=40
```

### Filtering

```
GET /api/v1/chunks?status=inbox&project_id=abc123
```

---

## Event System

### Event Bus Architecture

Komorebi uses Server-Sent Events (SSE) for real-time updates, with an async event bus pattern:

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   API Handler   │────▶│   EventBus   │────▶│  SSE Endpoint   │
└─────────────────┘     └──────────────┘     └────────┬────────┘
                               │                      │
                               │              ┌───────┴───────┐
                               │              ▼               ▼
                        AsyncIO Queue    Client 1       Client 2
```

### Implementation Details

**Libraries:**
- `sse-starlette` for SSE response streaming
- `EventSourceResponse` with built-in keep-alive
- Async generators for event streaming

**Key Design Patterns:**

1. **Per-Subscriber Queue Pattern**
   - Each client gets its own `asyncio.Queue`
   - Events are broadcast to all queues asynchronously
   - Slow clients don't block fast clients

2. **Explicit ServerSentEvent Objects**
   ```python
   from sse_starlette.sse import ServerSentEvent
   
   yield ServerSentEvent(
       event="chunk.created",
       data=json.dumps({...})
   )
   ```
   - Always use `ServerSentEvent` class, not raw dictionaries
   - Ensures proper serialization and error messages

3. **Built-in Keep-Alive**
   ```python
   EventSourceResponse(
       generator,
       ping=15  # Comment line every 15 seconds
   )
   ```
   - Server sends `: ping\n\n` automatically
   - Browsers ignore comment lines
   - No manual timeout handling needed

4. **Robust Error Handling**
   ```python
   try:
       # Setup subscriber
       yield ServerSentEvent(...)  # Initial message
       while True:
           event = await queue.get()
           yield ServerSentEvent(...)
   except asyncio.CancelledError:
       raise  # Client disconnect - let cleanup happen
   except Exception as e:
       logging.error(f"SSE Error: {e}")
       # Don't re-raise - prevents error loops
   finally:
       # Robust cleanup with defensive checks
       if queue in subscribers:
           subscribers.remove(queue)
   ```

**Performance Characteristics:**
- Connection establishment: ~10ms
- Event delivery latency: <5ms
- Keep-alive overhead: ~20 bytes every 15s
- Memory per subscriber: ~1KB + queued events
- Expected capacity: 1000+ concurrent connections per worker

### Event Types

| Event | Trigger | Payload |
|-------|---------|---------|
| `chunk.created` | New chunk captured | Full chunk object |
| `chunk.updated` | Chunk modified | Full chunk object |
| `chunk.deleted` | Chunk removed | Chunk ID |
| `project.updated` | Project modified | Full project object |
| `compaction.started` | Compaction begins | Project ID |
| `compaction.completed` | Compaction ends | Project ID, summary |
| `mcp.status_changed` | MCP connection change | Server ID, status |

### Event Format

```json
{
  "type": "chunk.created",
  "chunk_id": "a1b2c3d4-...",
  "data": { ... },
  "timestamp": "2024-01-15T10:30:00.000000"
}
```

---

## MCP Integration

### MCP Aggregator Pattern

Komorebi acts as an "MCP Host of Hosts":

```
┌─────────────────────────────────────────────────────────────────┐
│                      Komorebi (MCP Host)                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    MCP Registry                          │   │
│  │  ┌─────────────────────────────────────────────────────┐│   │
│  │  │              Unified Tool Interface                  ││   │
│  │  │  list_tools() → All tools from all servers          ││   │
│  │  │  call_tool(name, args) → Route to correct server    ││   │
│  │  └─────────────────────────────────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│  ┌───────────────┐ ┌─────────────────┐ ┌────────────────────┐  │
│  │  MCP Client   │ │   MCP Client    │ │    MCP Client      │  │
│  │   (GitHub)    │ │  (Filesystem)   │ │    (Memory)        │  │
│  └───────┬───────┘ └────────┬────────┘ └─────────┬──────────┘  │
│          │                  │                    │              │
└──────────┼──────────────────┼────────────────────┼──────────────┘
           │ stdio            │ stdio              │ stdio
           ▼                  ▼                    ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
    │ GitHub MCP   │  │ Filesystem   │  │    Memory MCP        │
    │   Server     │  │ MCP Server   │  │      Server          │
    └──────────────┘  └──────────────┘  └──────────────────────┘
```

### MCP Client Protocol

Communication uses JSON-RPC 2.0 over stdio:

```python
# Request
{"jsonrpc": "2.0", "method": "tools/list", "id": 1}

# Response
{"jsonrpc": "2.0", "result": [...], "id": 1}
```

---

## Frontend Architecture

### Technology Stack

| Layer | Technology |
|-------|------------|
| Framework | React 18 |
| Language | TypeScript |
| State | Preact Signals |
| Build | Vite |
| Styling | CSS Variables |

### Component Hierarchy

```
App
├── Header
├── Stats
│   └── StatCard (×5)
├── TabNavigation
├── Content
│   ├── Inbox
│   │   ├── CaptureForm
│   │   └── ChunkList
│   ├── AllChunks
│   │   ├── FilterBar
│   │   └── ChunkList
│   └── Projects
│       ├── ProjectForm
│       └── ProjectList
└── Footer
```

### State Management

Using Preact Signals for reactive state:

```typescript
// Signals (reactive atoms)
const chunks = signal<Chunk[]>([]);
const stats = signal<Stats>({ inbox: 0, ... });

// Effects (automatic reactions)
effect(() => {
  console.log(`Total chunks: ${stats.value.total}`);
});

// Actions
async function captureChunk(content: string) {
  const response = await fetch('/api/v1/chunks', {...});
  chunks.value = [...chunks.value, await response.json()];
}
```

### Real-Time Updates

SSE integration for live updates:

```typescript
function connectSSE() {
  const es = new EventSource('/api/v1/sse/events');
  
  es.onmessage = (event) => {
    const { type, data } = JSON.parse(event.data);
    
    switch (type) {
      case 'chunk.created':
        chunks.value = [...chunks.value, data];
        break;
      case 'chunk.updated':
        chunks.value = chunks.value.map(c => 
          c.id === data.id ? data : c
        );
        break;
    }
  };
}
```

---

## Security Architecture

### Current Security Posture

| Aspect | Status | Notes |
|--------|--------|-------|
| Authentication | ❌ Not implemented | Add before production |
| Authorization | ❌ Not implemented | Add before production |
| HTTPS | ⚠️ Via reverse proxy | Use nginx/Caddy |
| CORS | ⚠️ Open by default | Restrict in production |
| Rate Limiting | ❌ Not implemented | Add before production |
| Input Validation | ✅ Pydantic | All inputs validated |
| SQL Injection | ✅ ORM | Parameterized queries |

### Recommended Security Stack

```
┌──────────────────────────────────────────────────────────────┐
│                     Reverse Proxy (nginx)                     │
│  • SSL/TLS termination                                       │
│  • Rate limiting                                              │
│  • Request filtering                                          │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────┴─────────────────────────────────┐
│                   Authentication Layer                        │
│  • JWT validation                                             │
│  • API key verification                                       │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────┴─────────────────────────────────┐
│                     Komorebi Backend                          │
│  • Input validation (Pydantic)                               │
│  • ORM (SQL injection protection)                            │
└──────────────────────────────────────────────────────────────┘
```

---

## Scalability Considerations

### Current Limitations

| Component | Limitation | Scale Factor |
|-----------|------------|--------------|
| SQLite | Single writer | Single instance |
| In-memory EventBus | Single process | Single instance |
| MCP Clients | Process-bound | Single instance |

### Scaling Strategies

**Vertical Scaling (Single Instance):**
- Increase server resources
- Optimize database queries
- Add caching layer

**Horizontal Scaling (Multiple Instances):**
- Switch to PostgreSQL
- Use Redis for event bus
- Separate MCP aggregator service

```
┌─────────────────────────────────────────────────────────────────┐
│                      Load Balancer                               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌───────────┐       ┌───────────┐       ┌───────────┐
    │ Komorebi  │       │ Komorebi  │       │ Komorebi  │
    │ Instance 1│       │ Instance 2│       │ Instance 3│
    └─────┬─────┘       └─────┬─────┘       └─────┬─────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              ┌───────────┐       ┌───────────┐
              │ PostgreSQL│       │   Redis   │
              │  (shared) │       │  (events) │
              └───────────┘       └───────────┘
```

---

## Technology Decisions

### Why FastAPI?

| Requirement | FastAPI Feature |
|-------------|-----------------|
| Async support | Native async/await |
| Performance | One of fastest Python frameworks |
| Validation | Pydantic integration |
| Documentation | Auto-generated OpenAPI |
| Type hints | First-class support |

### Why SQLAlchemy Async?

| Requirement | SQLAlchemy Feature |
|-------------|-------------------|
| Async queries | Full async support |
| ORM | Object-relational mapping |
| Migrations | Alembic integration |
| Portability | SQLite/PostgreSQL/MySQL |

### Why Pydantic?

| Requirement | Pydantic Feature |
|-------------|-----------------|
| Validation | Automatic input validation |
| Serialization | JSON encode/decode |
| Type safety | Runtime type checking |
| FastAPI | Native integration |

### Why Preact Signals?

| Requirement | Signals Feature |
|-------------|-----------------|
| Reactivity | Fine-grained updates |
| Performance | Minimal re-renders |
| Simplicity | No boilerplate |
| Size | Tiny bundle size |

---

*For API documentation, see [API_REFERENCE.md](./API_REFERENCE.md). For deployment, see [DEPLOYMENT.md](./DEPLOYMENT.md).*
