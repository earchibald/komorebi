# Komorebi: Getting Started Guide

*A complete walkthrough for understanding and using Komorebi*

---

## Table of Contents

1. [What is Komorebi?](#what-is-komorebi)
2. [Philosophy: Capture Now, Refine Later](#philosophy-capture-now-refine-later)
3. [Architecture Overview](#architecture-overview)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Quick Start](#quick-start)
7. [Using the Backend API](#using-the-backend-api)
8. [Using the CLI](#using-the-cli)
9. [Using the React Dashboard](#using-the-react-dashboard)
10. [Understanding the Core Concepts](#understanding-the-core-concepts)
11. [MCP Integration](#mcp-integration)
12. [Testing](#testing)
13. [Troubleshooting](#troubleshooting)

---

## What is Komorebi?

**Komorebi** (木漏れ日) is a Japanese word meaning "sunlight filtering through leaves." In the context of this project, it represents **cognitive infrastructure** that helps filter and organize the chaos of thoughts, tasks, and information during active work.

Komorebi provides:
- 🚀 **Fast Capture** - Instantly capture thoughts without breaking flow (✅ Working)
- 🤖 **Auto-Processing** - Background summarization of captured chunks (✅ Working)
- 📦 **Recursive Compaction** - Condense chunks into project context (⚠️ Implemented but needs LLM)
- 🔌 **MCP Aggregation** - Connect to external tools (⚠️ Infrastructure ready, needs servers)
- 📡 **Real-time Updates** - SSE-based live streaming (✅ Working, <5ms latency)
- 💾 **Smart Caching** - Instant page loads with localStorage (✅ Working)

---

## Philosophy: Capture Now, Refine Later

Traditional task managers fail when they demand order during chaos. Komorebi's core philosophy is:

> **Speed is the only metric that matters in the "heat of the moment."**

The workflow:

1. **Capture** → Raw thoughts go straight to the inbox (no categorization required)
2. **Process** → Background processing enriches and summarizes chunks
3. **Compact** → Related chunks are compressed into higher-level context
4. **Archive** → Old context is preserved but moved out of active view

This "memory pyramid" approach means you never lose context—you just summarize it.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Komorebi Stack                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   React      │  │    CLI       │  │   External Clients   │  │
│  │  Dashboard   │  │  (Typer)     │  │   (curl, scripts)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│         └─────────────────┼──────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   FastAPI Backend                         │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐ │  │
│  │  │ Chunks  │ │Projects │ │   MCP   │ │      SSE        │ │  │
│  │  │  API    │ │   API   │ │   API   │ │   Streaming     │ │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────────┬────────┘ │  │
│  │       │           │           │               │          │  │
│  │  ┌────┴───────────┴───────────┴───────────────┴────────┐ │  │
│  │  │                    Core Services                     │ │  │
│  │  │  • CompactorService (summarization)                  │ │  │
│  │  │  • EventBus (real-time events)                       │ │  │
│  │  │  • MCPRegistry (server aggregation)                  │ │  │
│  │  └──────────────────────┬──────────────────────────────┘ │  │
│  │                         │                                │  │
│  │  ┌──────────────────────┴──────────────────────────────┐ │  │
│  │  │              SQLite Database (async)                 │ │  │
│  │  │  • Chunks table                                      │ │  │
│  │  │  • Projects table                                    │ │  │
│  │  │  • MCP Servers table                                 │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- **Python 3.11+** - Required for the backend and CLI
- **Node.js 18+** - Required for the React dashboard (optional)
- **pip** - Python package manager

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/earchibald/komorebi.git
cd komorebi
```

### 2. Install Python Dependencies

```bash
# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"
```

This installs:
- FastAPI, Uvicorn (backend server)
- Pydantic (data validation)
- SQLAlchemy + aiosqlite (async database)
- Typer, Rich (CLI)
- httpx (HTTP client)
- pytest (testing)

**After installation, the `komorebi` CLI command becomes available:**

```bash
# Verify installation
komorebi --help
```

> ⚠️ **Important:** If you see `ModuleNotFoundError: No module named 'cli'`, you need to run `pip install -e ".[dev]"` first. See [Troubleshooting](TROUBLESHOOTING.md#modulenotfounderror-no-module-named-cli) for details.

### 3. (Optional) Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Quick Start

### 1. Start the Backend Server

```bash
uvicorn backend.app.main:app --reload
```

The backend will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 2. (Optional) Start the Frontend Dashboard

```bash
cd frontend
npm run dev
```

The dashboard will be available at: http://localhost:3000

### 3. Quick Test

Test the API is working:

```bash
# Check health
curl http://localhost:8000/health

# Create a chunk
curl -X POST http://localhost:8000/api/v1/chunks \
  -H "Content-Type: application/json" \
  -d '{"content":"My first thought!"}'

# Get chunks
curl http://localhost:8000/api/v1/chunks
```

---

## What Can I Do Now?

### ✅ Working Features (Ready to Use)

**1. Fast Chunk Capture**
- Capture thoughts via API, CLI, or dashboard
- Automatic background processing and summarization
- Real-time updates via SSE

**2. Dashboard UI**
- View all chunks with instant tab switching
- Filter by status: Inbox, Processed, Compacted, Archived
- Real-time updates when chunks change
- Smart caching for instant page loads

**3. Projects** 
- Create projects to organize related chunks
- Associate chunks with projects
- Track chunk counts per project

**4. Statistics**
- Real-time dashboard stats
- Breakdown by status
- Auto-updating via SSE

### ⚠️ Implemented but Needs Enhancement

**1. Compaction (Recursive Summarization)**
- Infrastructure is built
- Currently uses simple text truncation
- **Next step:** Integrate Ollama for real LLM-based summarization
- API endpoint ready: `POST /api/v1/projects/{id}/compact`

**2. MCP Integration**
- Registry system implemented
- Can connect to MCP servers
- **Next step:** Add actual MCP server configurations (GitHub, filesystem, etc.)
- API endpoints ready: `/api/v1/mcp/*`

### 🚧 Not Yet Implemented

**1. Advanced CLI**
- Basic `komorebi add` works
- Need: list, search, filter, project management commands

**2. Search & Tags**
- Tags are stored but not searchable yet
- Need: full-text search across chunks

**3. Chunk Relationships**
- No parent/child relationships yet
- Could link related chunks

---

## Recommended Next Steps

### Option 1: Integrate Ollama for Real Summarization

**Why?** This makes compaction actually useful instead of just truncating text.

**What to build:**
1. Add Ollama client to `CompactorService`
2. Use `llama3.2` or similar for chunk summarization
3. Implement map-reduce summarization for projects
4. Add streaming support for long summaries

**Impact:** Makes the "recursive compaction" feature actually work!

### Option 2: Connect Real MCP Servers

**Why?** Turns Komorebi into a universal tool aggregator.

**What to build:**
1. Add MCP server configs for:
   - GitHub (`@modelcontextprotocol/server-github`)
   - Filesystem (`@modelcontextprotocol/server-filesystem`)
   - Memory (`@modelcontextprotocol/server-memory`)
2. Build UI to browse available tools
3. Create workflow to call tools and capture results as chunks

**Impact:** Can pull GitHub issues, read files, access memory—all from one place!

### Option 3: Enhanced CLI with Rich Output

**Why?** Makes Komorebi great for terminal-based workflows.

**What to build:**
1. `komorebi list` - Beautiful table of chunks
2. `komorebi search <query>` - Full-text search
3. `komorebi project create/list/view`
4. `komorebi stats` - Terminal dashboard
5. Pipe support: `cat log.txt | komorebi add --project debugging`

**Impact:** Fast capture from anywhere in the terminal!

### Option 4: Project Context Dashboard

**Why?** Visualize the "memory pyramid" concept.

**What to build:**
1. Project detail view showing chunk hierarchy
2. Timeline view of chunk capture
3. Compaction history (raw → processed → compacted)
4. Token count tracking and compression ratio

**Impact:** See how context gets compressed over time!

---

## Using the Backend API (More Details)

```bash
# Using the CLI
komorebi serve

# Or directly with uvicorn
uvicorn backend.app.main:app --reload
```

The server starts at `http://localhost:8000`.

### Verify It's Running

```bash
curl http://localhost:8000/health
# Output: {"status":"healthy"}
```

### Capture Your First Chunk

```bash
# Using curl
curl -X POST http://localhost:8000/api/v1/chunks \
  -H "Content-Type: application/json" \
  -d '{"content": "My first thought!", "source": "curl"}'

# Using the CLI
komorebi capture "My first thought!"
```

### View Your Chunks

```bash
# Using curl
curl http://localhost:8000/api/v1/chunks

# Using the CLI
komorebi list
```

---

## Using the Backend API

### Base URL

```
http://localhost:8000/api/v1
```

This is a prefix, not a browsable endpoint. Requests must target a concrete path under it, for example:

```
http://localhost:8000/api/v1/chunks
http://localhost:8000/api/v1/projects
```

### Interactive Documentation

Visit `http://localhost:8000/docs` for Swagger UI documentation.

### Endpoints Overview

#### Chunks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chunks` | Capture a new chunk |
| `GET` | `/chunks` | List all chunks (with filters) |
| `GET` | `/chunks/inbox` | List inbox chunks only |
| `GET` | `/chunks/stats` | Get chunk statistics |
| `GET` | `/chunks/{id}` | Get a specific chunk |
| `PATCH` | `/chunks/{id}` | Update a chunk |
| `DELETE` | `/chunks/{id}` | Delete a chunk |
| `POST` | `/chunks/process-inbox` | Process inbox chunks |

#### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects` | Create a new project |
| `GET` | `/projects` | List all projects |
| `GET` | `/projects/{id}` | Get a specific project |
| `PATCH` | `/projects/{id}` | Update a project |
| `DELETE` | `/projects/{id}` | Delete a project |
| `POST` | `/projects/{id}/compact` | Compact project chunks |
| `GET` | `/projects/{id}/context` | Get project context summary |

#### MCP Servers

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/mcp/servers` | List registered MCP servers |
| `POST` | `/mcp/servers` | Register a new MCP server |
| `POST` | `/mcp/servers/{id}/connect` | Connect to an MCP server |
| `POST` | `/mcp/servers/{id}/disconnect` | Disconnect from an MCP server |
| `GET` | `/mcp/tools` | List available tools |
| `POST` | `/mcp/tools/{name}/call` | Call an MCP tool |

#### SSE (Server-Sent Events)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/sse/events` | Stream real-time events |
| `GET` | `/sse/status` | Get SSE connection status |

### Example: Creating a Chunk

```bash
curl -X POST http://localhost:8000/api/v1/chunks \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Need to implement user authentication",
    "tags": ["backend", "security"],
    "source": "api"
  }'
```

Response:
```json
{
  "id": "a1b2c3d4-...",
  "content": "Need to implement user authentication",
  "summary": null,
  "project_id": null,
  "tags": ["backend", "security"],
  "status": "inbox",
  "source": "api",
  "token_count": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

## Using the CLI

The CLI is built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/) for beautiful terminal output.

### Commands Overview

```bash
komorebi --help
```

### `capture` - Quick Capture

Instantly capture a thought to the inbox.

```bash
# Basic capture
komorebi capture "Fix the login bug"

# With project association
komorebi capture "Add validation" --project <project-id>

# With tags
komorebi capture "Research Redis caching" --tags "research,backend"
```

### `list` - View Chunks

```bash
# List all chunks (default: 20)
komorebi list

# Filter by status
komorebi list --status inbox
komorebi list --status processed

# Limit results
komorebi list --limit 50
```

### `stats` - View Statistics

```bash
komorebi stats
```

Output:
```
        Chunk Statistics
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Status           ┃  Count ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ 📥 Inbox         │     12 │
│ ⚙️  Processed    │      8 │
│ 📦 Compacted     │      5 │
│ 🗄️  Archived     │      2 │
│                  │        │
│ Total            │     27 │
└──────────────────┴────────┘
```

### `projects` - List Projects

```bash
komorebi projects
```

### `compact` - Compact a Project

```bash
komorebi compact <project-id>
```

### `serve` - Start the Server

```bash
# Default settings
komorebi serve

# Custom host and port
komorebi serve --host 0.0.0.0 --port 9000

# With auto-reload (development)
komorebi serve --reload
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KOMOREBI_API_URL` | `http://localhost:8000/api/v1` | API base URL |

---

## Using the React Dashboard

### Start the Development Server

```bash
cd frontend
npm install  # First time only
npm run dev
```

The dashboard opens at `http://localhost:3000`.

### Features

1. **Stats Overview** - Real-time statistics for all chunk statuses
2. **Inbox Tab** - Quick capture form and inbox items
3. **All Chunks Tab** - Filter and view all chunks
4. **Projects Tab** - Create and manage projects

### Real-time Updates

The dashboard connects to the SSE endpoint for live updates. When you capture a chunk via CLI or API, it appears immediately in the dashboard.

---

## Understanding the Core Concepts

### Chunks

A **Chunk** is the fundamental unit of information in Komorebi. It represents:
- A thought or idea
- A task or TODO
- A note or reference
- Any piece of context you want to preserve

Chunk statuses:
- **INBOX** - Raw, unprocessed capture
- **PROCESSED** - Analyzed and enriched
- **COMPACTED** - Summarized into higher-level context
- **ARCHIVED** - No longer active but preserved

### Projects

A **Project** groups related chunks and maintains aggregate context. The `context_summary` field contains a compacted summary of all chunks in the project.

### Compaction

The **CompactorService** implements recursive summarization:
1. Chunks are processed (tokenized, summarized)
2. Related chunks are combined into project context
3. Old context is preserved but compressed

This creates a "memory pyramid" where you never lose information—it just becomes more condensed over time.

### MCP (Model Context Protocol)

Komorebi acts as an **MCP Host of Hosts**, aggregating multiple MCP servers (GitHub, Jira, etc.) into a unified interface. This allows external tools to be accessed through a single API.

---

## MCP Integration

### Registering an MCP Server

```bash
curl -X POST http://localhost:8000/api/v1/mcp/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GitHub MCP",
    "server_type": "github",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {"GITHUB_TOKEN": "your-token"}
  }'
```

### Connecting to a Server

```bash
curl -X POST http://localhost:8000/api/v1/mcp/servers/{server-id}/connect
```

### Listing Available Tools

```bash
curl http://localhost:8000/api/v1/mcp/tools
```

---

## Testing

Komorebi includes comprehensive tests. See the [Test Manifest](./TEST_MANIFEST.md) for detailed documentation, including:
- **Automated Tests** - 16 pytest unit and integration tests
- **Benchmark Tests** - Load testing with hammer_gen.py
- **Human Tests** - 12 manual verification procedures (HT-1 through HT-12)

### Running Automated Tests

```bash
# All tests
python -m pytest -v

# With coverage
python -m pytest --cov=backend
```

### Running the Benchmark

The **Hammer** script validates the implementation:

```bash
python scripts/hammer_gen.py
```

Expected output:
```
🔨 Komorebi Hammer - Starting benchmark...
✅ Server is healthy
📁 Creating 3 projects...
📝 Capturing 50 chunks...
📊 Running read operations...

╔══════════════════════════════════════════════════════════════╗
║                    KOMOREBI HAMMER RESULTS                   ║
╠══════════════════════════════════════════════════════════════╣
║  Total Requests:           53                            ║
║  Successful:               53                            ║
║  Failed:                    0                            ║
╚══════════════════════════════════════════════════════════════╝

✅ All requests successful!
```

### Manual Verification (Human Tests)

For hands-on verification, the [Test Manifest](./TEST_MANIFEST.md) includes 12 human testing procedures. At minimum, complete:

1. **HT-1: Server Startup** - Verify the server starts and responds
2. **HT-2: CLI Capture** - Test capturing chunks via CLI
3. **HT-4: API Direct Access** - Verify REST API with curl
4. **HT-8: Hammer Benchmark** - Run the load test

For complete confidence, run all tests HT-1 through HT-12.

---

## Troubleshooting

### Server Won't Start

```bash
# Check if port is in use
lsof -i :8000

# Try a different port
komorebi serve --port 9000
```

### Database Errors

The SQLite database is created at `./komorebi.db`. To reset:

```bash
rm komorebi.db
# Restart the server (database is auto-created)
```

### CLI Can't Connect

Ensure the server is running and check the API URL:

```bash
# Verify server is up
curl http://localhost:8000/health

# Override API URL if needed
export KOMOREBI_API_URL=http://localhost:9000/api/v1
```

### Frontend Proxy Issues

The Vite dev server proxies `/api` requests to the backend. Ensure the backend is running on port 8000, or update `frontend/vite.config.ts`.

---

## Next Steps

1. **Explore the API** - Visit `http://localhost:8000/docs`
2. **Read the Pedagogy** - See `docs/PEDAGOGY.md` for design philosophy
3. **Run the Tests** - See [Test Manifest](./TEST_MANIFEST.md)
4. **Contribute** - Check the project issues and contribute!

---

*Komorebi - Capture the light filtering through the chaos.*
