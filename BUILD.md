# Komorebi Build Blueprint

**Version:** 0.5.0  
**Architecture:** Python Monolith (FastAPI) + React (Vite) + MCP Aggregator  
**Database:** SQLite (async via aiosqlite)

---

## Quick Start (Development)

```bash
# Prerequisites: Python 3.11+, Node 20+, Ollama (optional)

# 1. Backend
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
uvicorn backend.app.main:app --reload --port 8000

# 2. Frontend (separate terminal)
cd frontend && npm install && npm run dev

# 3. Run tests
pytest backend/tests/ -v
cd frontend && npx playwright test
```

**URLs:** Frontend → `http://localhost:3000` | API → `http://localhost:8000` | Docs → `http://localhost:8000/docs`

---

## Quick Start (Docker — v0.6.0+)

```bash
docker-compose up --build        # Build and run
docker-compose up -d             # Detached mode
docker-compose down              # Stop
```

Data persists in `komorebi-data` Docker volume.

---

## Project Structure

```
komorebi/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point, CORS, routers
│   │   ├── api/                 # Route handlers
│   │   │   ├── chunks.py        # 9 endpoints — CRUD + search + bulk (v0.6.0)
│   │   │   ├── projects.py      # 7 endpoints — CRUD + assign/unassign
│   │   │   ├── entities.py      # 3 endpoints — CRUD for entities
│   │   │   ├── mcp.py           # 10 endpoints — MCP server management
│   │   │   └── sse.py           # 2 endpoints — SSE event stream
│   │   ├── core/                # Business logic
│   │   │   ├── compactor.py     # Recursive summarization engine
│   │   │   ├── events.py        # SSE event bus
│   │   │   └── ollama_client.py # Ollama LLM integration
│   │   ├── db/
│   │   │   ├── database.py      # SQLAlchemy async setup, table definitions
│   │   │   └── repository.py    # Data access layer (ChunkRepository)
│   │   ├── mcp/                 # MCP aggregator ("Muxer")
│   │   │   ├── auth.py          # Credential resolution
│   │   │   ├── client.py        # MCP client abstraction
│   │   │   ├── config.py        # Server configuration loader
│   │   │   └── registry.py      # Server lifecycle management
│   │   ├── models/              # Pydantic schemas
│   │   │   ├── chunk.py         # Chunk, ChunkCreate, SearchResult
│   │   │   ├── project.py       # Project, ProjectCreate
│   │   │   ├── entity.py        # Entity, EntityCreate
│   │   │   └── mcp.py           # MCPServer schemas
│   │   └── services/
│   │       └── mcp_service.py   # MCP orchestration service
│   └── tests/                   # pytest + pytest-asyncio (45 tests)
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main app shell
│   │   ├── main.tsx             # React entry point
│   │   ├── components/          # 8 components (Inbox, ChunkList, etc.)
│   │   └── store/               # Preact signals state management
│   └── e2e/                     # Playwright E2E tests
├── cli/                         # Typer CLI (komorebi command)
├── config/
│   └── mcp_servers.json         # MCP server declarations
├── scripts/                     # Hammer tests, migrations, version tools
├── docs/                        # Full documentation suite
├── pyproject.toml               # Python project config (v0.5.0)
├── VERSION                      # Single source of truth for version
└── NEW_FEATURE_ARCHITECTURE.md  # Next-phase design document
```

---

## Module Inventory

| Module | Version | Status | Endpoints | Tests |
|--------|---------|--------|-----------|-------|
| **M1: Capture Pipeline** | v0.1.0 | ✅ Complete | 9 (chunks CRUD) | 15 |
| **M2: Project Backbone** | v0.2.0 | ✅ Complete | 7 (projects CRUD) + 3 (entities) | 12 |
| **M3: MCP Aggregator** | v0.3.0 | ✅ Complete | 10 (MCP management) + 2 (SSE) | 10 |
| **M4: Search & Filtering** | v0.4.0 | ✅ Complete | 1 (GET /chunks/search) | 8 |
| **M5: Bulk Operations** | v0.6.0 | 🔲 Designed | 5 planned | — |
| **M6: User Data API** | v0.7.0 | 🔲 Designed | 2 new + 1 enhanced | — |
| **M9: Context Oracle (MCP Server)** | v1.0.0 | 🔲 Designed | 8 (traces + file events) | — |
| **M10: Security & Profiles** | v1.0.0 | 🔲 Designed | 0 (CLI only) | — |
| **M11: Cost Governance** | v1.0.0 | 🔲 Designed | 3 (usage + budget) | — |

**Total:** 30 API endpoints + 11 planned, 4 database tables + 3 planned, 45 backend tests

**Architecture:** See [CONTEXT_ORACLE_ARCHITECTURE.md](CONTEXT_ORACLE_ARCHITECTURE.md) for M9-M11 design.

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KOMOREBI_DATABASE_URL` | `sqlite+aiosqlite:///./komorebi.db` | Database connection string |
| `KOMOREBI_CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `KOMOREBI_LOG_LEVEL` | `INFO` | Python logging level |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API base URL |
| `GITHUB_TOKEN` | — | GitHub MCP server token |
| `GITKRAKEN_API_KEY` | — | GitKraken MCP server token |

### MCP Servers

Configured in `config/mcp_servers.json`. Secrets use `env://VARIABLE_NAME` pattern — never hardcode tokens.

---

## Testing

```bash
# Backend unit tests
pytest backend/tests/ -v

# Backend with coverage
pytest backend/tests/ --cov=backend --cov-report=term

# Frontend E2E (requires running backend + frontend)
cd frontend && npx playwright test

# Hammer stress test (ingestion pipeline)
python scripts/hammer_gen.py --size 500

# MCP integration test
python scripts/hammer_mcp.py
```

---

## Versioning

Single source of truth: `VERSION` file.

Sync all version references:
```bash
./scripts/sync-versions.sh
```

Validate before release:
```bash
./scripts/check-version.sh
./scripts/validate-changelog.sh
```

See [VERSIONING.md](VERSIONING.md) for full protocol.

---

## Deployment (v0.6.0+)

Target: **Railway.app** (managed PaaS with persistent volumes).

See [NEW_FEATURE_ARCHITECTURE.md](NEW_FEATURE_ARCHITECTURE.md) for deployment architecture:
- Multi-stage Docker build (Node → Python)
- Single-container serving (FastAPI + StaticFiles)
- SQLite on persistent volume
- Environment-based configuration

---

## Key Architecture Decisions

1. **Single-process serving** — FastAPI serves both API and static frontend (no Nginx needed for MVP)
2. **SQLite for persistence** — Async via aiosqlite, swappable to PostgreSQL via `DATABASE_URL`
3. **Preact Signals for state** — High-frequency UI updates without React re-renders
4. **MCP Protocol** — Standard tool aggregation for AI agent integration
5. **Capture-first** — Ingestion never blocks, always returns 202 immediately
6. **Soft-delete only** — Chunks are archived/deleted by status, never removed from database

See [NEW_FEATURE_ARCHITECTURE.md](NEW_FEATURE_ARCHITECTURE.md) for detailed trade-off analysis.