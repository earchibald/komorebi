# Module 3: MCP Aggregator Integration

**Version:** 0.3.0  
**Status:** Specification  
**Date:** 2026-02-05  
**Author:** GitHub Copilot (Claude Sonnet 4.5)  
**Purpose:** Comprehensive specification for implementing the MCP (Model Context Protocol) Aggregator subsystem

---

## Executive Summary

### What is Module 3?
Module 3 implements the **MCP Aggregator** - the third pillar of Komorebi's architecture (after Ollama LLM integration and Recursive Compaction). It enables Komorebi to connect to external tools via the Model Context Protocol (MCP), aggregate their capabilities, and automatically capture tool outputs as chunks for processing.

### Why Now?
- **Modules 1 & 2 Complete:** Ollama integration (v0.1.0) and recursive compaction with entity extraction (v0.2.0) are fully operational
- **Infrastructure Exists:** MCP backend code is ~70% complete but has 6 critical bugs preventing operation
- **Architecture Mandate:** The project's stated architecture is "Python Monolith (FastAPI) + React (Vite) + **MCP Aggregator**"
- **Closes the Loop:** MCP → Tool Calls → Chunks → Compaction → Knowledge Graph

### Scope Boundaries
**IN SCOPE:**
- Fix 6 critical bugs in existing MCP backend code
- Implement configuration loading from `config/mcp_servers.json`
- Add "Tool Result → Chunk" auto-capture pipeline
- Build frontend MCP Panel with real-time status display
- Write 25+ new tests for MCP subsystem
- Update protocol version from "2024-11-05" to "2025-11-25"

**OUT OF SCOPE:**
- Custom MCP server implementations (use existing npx/pip servers)
- Advanced routing/orchestration (e.g., multi-step tool chains)
- Alternative protocols (OpenAI function calling, Anthropic tools)
- MCP server discovery/marketplace features

---

## Current State Audit

### Version Context
- **Current Version:** v0.2.1+build1 (PyPI: `pyproject.toml`, NPM: `frontend/package.json`)
- **Target Version:** v0.3.0 (Module 3 completion)
- **Last Release:** v0.2.1 (Entity system integration - 2026-02-04)

### Module Completion Matrix

| Module | Version | Status | Evidence |
|--------|---------|--------|----------|
| Module 1: Ollama Integration | v0.1.0 | ✅ Complete | `backend/app/core/ollama_client.py` (117 lines), 4 methods fully tested |
| Module 2: Recursive Compaction | v0.2.0 | ✅ Complete | `backend/app/core/compactor.py` (296 lines), recursive_reduce implemented, 67+ req/sec validated |
| Entity System | v0.2.1 | ✅ Complete | `backend/app/models/entity.py`, `EntityRepository.create_many`, 2 API endpoints |
| Module 3: MCP Aggregator | v0.3.0 | 🔴 Incomplete | Backend 70% coded with 6 bugs, 0% frontend, minimal tests |

### Existing MCP Backend Infrastructure

#### ✅ Models (`backend/app/models/mcp.py`)
```python
class MCPServerStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

class MCPServerConfig(BaseModel):
    id: str
    name: str
    command: str  # e.g., "npx", "python"
    args: list[str]  # e.g., ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    env: dict[str, str] | None = None
    description: str | None = None

class MCPTool(BaseModel):
    name: str
    description: str
    server_id: str
    input_schema: dict[str, Any]
```
**Status:** ✅ Fully implemented, Pydantic v2 compliant

#### 🟡 Client (`backend/app/mcp/client.py` - 220 lines)
```python
class MCPClient:
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._responses: dict[int, asyncio.Future] = {}
        
    async def connect(self) -> MCPServerStatus:
        """Start subprocess and initialize MCP protocol"""
        
    async def disconnect(self):
        """Gracefully terminate subprocess"""
        
    async def list_tools(self) -> list[MCPTool]:
        """Call tools/list JSON-RPC method"""
        
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call tools/call JSON-RPC method"""
```
**Status:** 🟡 Fully coded but contains critical bugs (see Bug Report section)

#### 🟡 Registry (`backend/app/mcp/registry.py`)
```python
class MCPRegistry:
    def __init__(self):
        self._clients: dict[str, MCPClient] = {}
        
    def register(self, config: MCPServerConfig) -> MCPClient:
        """Add server to registry"""
        
    async def connect_all(self):
        """Connect all registered servers sequentially"""
        
    async def list_tools(self, server_id: str | None = None) -> list[MCPTool]:
        """List tools from one or all servers"""
        
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Find tool by name and call it"""
```
**Status:** 🟡 Fully coded but missing parallelization and reconnection logic

#### 🟡 API (`backend/app/api/mcp.py` - 117 lines, 10 endpoints)
```python
# Server Management
POST   /api/v1/mcp/servers                    # Register new server
GET    /api/v1/mcp/servers                    # List all servers
GET    /api/v1/mcp/servers/{id}               # Get server details
DELETE /api/v1/mcp/servers/{id}               # Unregister server
POST   /api/v1/mcp/servers/{id}/connect       # Connect server
POST   /api/v1/mcp/servers/{id}/disconnect    # Disconnect server

# Tool Management
GET    /api/v1/mcp/tools                      # List all tools
GET    /api/v1/mcp/tools/{name}               # Get tool details
POST   /api/v1/mcp/tools/{name}/call          # Call tool
POST   /api/v1/mcp/tools/batch                # Call multiple tools
```
**Status:** 🟡 Fully coded but missing "Tool Result → Chunk" capture

#### ❌ Missing Components
1. **`backend/app/mcp/auth.py`** - Referenced in copilot-instructions but doesn't exist
2. **`config/mcp_servers.json`** - Config directory is empty
3. **Config Loader Module** - No startup configuration loading
4. **Frontend MCP UI** - Zero React components for MCP management
5. **MCP Store Signals** - No `mcpServers` or `mcpTools` signals in `frontend/src/store/index.ts`
6. **SSE MCP Events** - Handler ignores `mcp.status_changed` events

### Critical Bugs Report

#### 🔴 BUG-1: Environment Variable Merging (CRITICAL)
**File:** `backend/app/mcp/client.py` (approx line 75)  
**Severity:** CRITICAL - Breaks all npx-based servers  
**Current Code:**
```python
env = config.env if config.env else None
self._process = await asyncio.create_subprocess_exec(
    config.command, *config.args,
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env=env  # ⚠️ Replaces entire environment instead of merging
)
```
**Impact:** When `config.env` is non-empty, subprocess loses `PATH`, `HOME`, and all system variables. `npx` command fails with "command not found".

**Fix:**
```python
import os

env = os.environ.copy()
if config.env:
    env.update(config.env)  # Merge instead of replace

self._process = await asyncio.create_subprocess_exec(
    config.command, *config.args,
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env=env
)
```

#### 🟡 BUG-2: Protocol Version Mismatch (MEDIUM)
**File:** `backend/app/mcp/client.py` (line ~85 in `_initialize` method)  
**Severity:** MEDIUM - Incompatible with newer MCP servers  
**Current Code:**
```python
response = await self._request("initialize", {
    "protocolVersion": "2024-11-05",  # ⚠️ Outdated
    "capabilities": {}
})
```
**Impact:** MCP protocol was updated to "2025-11-25" spec. Servers may reject old protocol version.

**Fix:**
```python
response = await self._request("initialize", {
    "protocolVersion": "2025-11-25",  # Updated to latest spec
    "capabilities": {}
})
```

#### 🟡 BUG-3: Missing Entity Repository Parameter (MEDIUM)
**File:** `backend/app/api/projects.py` (line ~114 in `compact_project` endpoint)  
**Severity:** MEDIUM - Crashes compaction for projects  
**Current Code:**
```python
@router.post("/projects/{project_id}/compact")
async def compact_project(project_id: int, session: AsyncSession = Depends(get_db)):
    chunk_repo = ChunkRepository(session)
    project_repo = ProjectRepository(session)
    compactor = CompactorService(chunk_repo, project_repo)  # ⚠️ Missing entity_repo
```
**Impact:** `CompactorService.__init__` requires 3 parameters: `(chunk_repo, project_repo, entity_repo)`. Endpoint crashes on initialization.

**Fix:**
```python
@router.post("/projects/{project_id}/compact")
async def compact_project(project_id: int, session: AsyncSession = Depends(get_db)):
    chunk_repo = ChunkRepository(session)
    project_repo = ProjectRepository(session)
    entity_repo = EntityRepository(session)  # Added
    compactor = CompactorService(chunk_repo, project_repo, entity_repo)
```

#### 🔵 BUG-4: Private Member Access in API (LOW)
**File:** `backend/app/api/mcp.py` (line ~45)  
**Severity:** LOW - Code smell, breaks encapsulation  
**Current Code:**
```python
@router.get("/mcp/servers")
async def list_servers():
    return [
        {"id": id, "config": client.config, "status": client._status}
        for id, client in mcp_registry._clients.items()  # ⚠️ Accessing private _clients
    ]
```
**Impact:** Directly accesses `MCPRegistry._clients` private dict. Should use public method.

**Fix:** Add public method to `MCPRegistry`:
```python
# In backend/app/mcp/registry.py
def list_servers(self) -> list[dict]:
    return [
        {"id": id, "config": client.config, "status": client._status}
        for id, client in self._clients.items()
    ]

# In backend/app/api/mcp.py
@router.get("/mcp/servers")
async def list_servers():
    return mcp_registry.list_servers()
```

#### 🔵 BUG-5: Dead Code (LOW)
**File:** `backend/app/mcp/client.py` (line ~20)  
**Severity:** LOW - Code clutter  
**Current Code:**
```python
from uuid import uuid4  # ⚠️ Never used

@dataclass
class MCPMessage:  # ⚠️ Defined but never instantiated
    id: str
    method: str
    params: dict[str, Any]
```
**Impact:** None, but violates "no dead code" principle.

**Fix:** Delete `MCPMessage` dataclass and `uuid4` import.

#### 🔵 BUG-6: Deprecated asyncio Pattern (LOW)
**File:** `backend/app/mcp/client.py` (line ~150 in `_read_responses`)  
**Severity:** LOW - Future deprecation warning  
**Current Code:**
```python
asyncio.get_event_loop().create_task(self._handle_notification(msg))  # ⚠️ Deprecated
```
**Impact:** `asyncio.get_event_loop()` is deprecated in Python 3.10+. Should use `asyncio.create_task()`.

**Fix:**
```python
asyncio.create_task(self._handle_notification(msg))
```

---

## Target Deliverables

### Backend Deliverables (12 items)

#### B1. Fix Subprocess Environment Merging
- **File:** `backend/app/mcp/client.py`
- **Action:** Update `connect()` method to merge `config.env` with `os.environ.copy()`
- **Test:** `tests/test_mcp_client.py::test_env_merging_preserves_path`
- **Priority:** P0 (blocks all npx servers)

#### B2. Update Protocol Version
- **File:** `backend/app/mcp/client.py`
- **Action:** Change `protocolVersion` from "2024-11-05" to "2025-11-25"
- **Test:** `tests/test_mcp_client.py::test_protocol_version`
- **Priority:** P0

#### B3. Create `backend/app/mcp/auth.py` Module
- **File:** NEW
- **Purpose:** Environment variable resolution and secret management
- **Functions:**
  - `resolve_env_keys(config: MCPServerConfig) -> dict[str, str]`: Resolve `env_keys` to actual values
  - `validate_command(command: str, args: list[str])`: Whitelist validation to prevent command injection
- **Test:** `tests/test_mcp_auth.py`
- **Priority:** P1

#### B4. Create `backend/app/mcp/config_loader.py` Module
- **File:** NEW
- **Purpose:** Load MCP servers from `config/mcp_servers.json` at startup
- **Functions:**
  - `load_mcp_config(path: Path) -> list[MCPServerConfig]`
  - `validate_config_schema(data: dict) -> bool`
  - `register_all_servers(registry: MCPRegistry, configs: list[MCPServerConfig])`
- **Test:** `tests/test_config_loader.py`
- **Priority:** P1

#### B5. Create `config/mcp_servers.json` Config File
- **File:** NEW
- **Format:**
```json
{
  "version": "1.0",
  "servers": [
    {
      "id": "filesystem",
      "name": "Filesystem Tools",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "env_keys": ["HOME", "USER"],
      "description": "Read/write files in /tmp directory"
    },
    {
      "id": "github",
      "name": "GitHub API",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env_keys": ["GITHUB_TOKEN"],
      "description": "GitHub repository operations"
    }
  ]
}
```
- **Security:** Use `env_keys` (references) instead of `env` (values)
- **Priority:** P1

#### B6. Add Startup Auto-Connect
- **File:** `backend/app/main.py`
- **Action:** Add lifespan event to load config and connect all servers
```python
from contextlib import asynccontextmanager
from backend.app.mcp.config_loader import load_and_register_servers

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Loading MCP servers from config...")
    await load_and_register_servers(mcp_registry, Path("config/mcp_servers.json"))
    yield
    # Shutdown
    logger.info("Disconnecting all MCP servers...")
    await mcp_registry.disconnect_all()

app = FastAPI(lifespan=lifespan)
```
- **Test:** `tests/test_integration_mcp.py::test_startup_auto_connect`
- **Priority:** P1

#### B7. Implement "Tool Result → Chunk" Pipeline
- **File:** `backend/app/api/mcp.py`
- **Action:** Update `call_tool` endpoint to optionally capture result as chunk
```python
@router.post("/mcp/tools/{name}/call")
async def call_tool(
    name: str,
    request: ToolCallRequest,
    capture: bool = Query(False, description="Auto-capture result as chunk"),
    project_id: int | None = Query(None),
    session: AsyncSession = Depends(get_db)
):
    result = await mcp_registry.call_tool(name, request.arguments)
    
    if capture:
        chunk_repo = ChunkRepository(session)
        chunk = await chunk_repo.create(ChunkCreate(
            content=json.dumps({
                "tool": name,
                "arguments": request.arguments,
                "result": result,
                "timestamp": datetime.now(UTC).isoformat()
            }),
            source=f"mcp:{name}",
            status=ChunkStatus.INBOX,
            project_id=project_id
        ))
        event_bus.publish(Event(
            type=EventType.CHUNK_CREATED,
            data={"chunk_id": chunk.id, "source": "mcp"}
        ))
        return {"result": result, "chunk_id": chunk.id}
    
    return {"result": result}
```
- **Test:** `tests/test_mcp_api.py::test_tool_call_auto_capture`
- **Priority:** P2

#### B8. Add `MCPRegistry.disconnect_all()` Method
- **File:** `backend/app/mcp/registry.py`
- **Action:** Implement graceful shutdown for all servers
```python
async def disconnect_all(self):
    """Disconnect all registered servers"""
    tasks = [client.disconnect() for client in self._clients.values()]
    await asyncio.gather(*tasks, return_exceptions=True)
    self._clients.clear()
```
- **Priority:** P2

#### B9. Add Reconnection Logic to `MCPClient`
- **File:** `backend/app/mcp/client.py`
- **Action:** Implement exponential backoff reconnection on subprocess crash
```python
async def _monitor_process(self):
    """Monitor subprocess and reconnect on crash"""
    while self._status != MCPServerStatus.DISCONNECTED:
        if self._process and self._process.returncode is not None:
            logger.warning(f"MCP server {self.config.id} crashed, reconnecting...")
            await asyncio.sleep(min(2 ** self._reconnect_attempts, 60))
            self._reconnect_attempts += 1
            await self.connect()
        await asyncio.sleep(1)
```
- **Test:** `tests/test_mcp_client.py::test_auto_reconnect`
- **Priority:** P3

#### B10. Parallelize `MCPRegistry.connect_all()`
- **File:** `backend/app/mcp/registry.py`
- **Current:** Sequential connection (slow)
- **Target:** Parallel with `asyncio.gather()`
```python
async def connect_all(self):
    """Connect all registered servers in parallel"""
    tasks = [client.connect() for client in self._clients.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for (server_id, client), result in zip(self._clients.items(), results):
        if isinstance(result, Exception):
            logger.error(f"Failed to connect {server_id}: {result}")
```
- **Test:** `tests/test_mcp_registry.py::test_parallel_connect`
- **Priority:** P2

#### B11. Fix `compact_project` Endpoint
- **File:** `backend/app/api/projects.py`
- **Action:** Add `entity_repo` parameter (see BUG-3)
- **Priority:** P0 (blocking production use)

#### B12. Remove Dead Code
- **File:** `backend/app/mcp/client.py`
- **Action:** Delete `MCPMessage` dataclass and `uuid4` import (see BUG-5)
- **Priority:** P3

### Frontend Deliverables (5 items)

#### F1. Add MCP Types to Store
- **File:** `frontend/src/store/index.ts`
- **Action:**
```typescript
export type MCPServerStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface MCPServer {
  id: string;
  name: string;
  status: MCPServerStatus;
  tool_count?: number;
  error?: string;
}

export interface MCPTool {
  name: string;
  description: string;
  server_id: string;
}

export const mcpServers = signal<MCPServer[]>([]);
export const mcpTools = signal<MCPTool[]>([]);
```
- **Priority:** P1

#### F2. Add MCP Signals Actions
- **File:** `frontend/src/store/index.ts`
- **Actions:**
  - `fetchMCPServers()`: GET `/api/v1/mcp/servers`
  - `connectServer(id: string)`: POST `/api/v1/mcp/servers/${id}/connect`
  - `disconnectServer(id: string)`: POST `/api/v1/mcp/servers/${id}/disconnect`
  - `fetchMCPTools()`: GET `/api/v1/mcp/tools`
  - `callTool(name: string, args: object, capture: boolean)`: POST `/api/v1/mcp/tools/${name}/call?capture={capture}`
- **Priority:** P1

#### F3. Update SSE Handler for MCP Events
- **File:** `frontend/src/store/index.ts`
- **Action:** Handle `mcp.status_changed` events
```typescript
function handleSSEEvent(event: MessageEvent) {
  const data = JSON.parse(event.data);
  
  if (data.type === 'mcp.status_changed') {
    const server = data.data as MCPServer;
    mcpServers.value = mcpServers.value.map(s => 
      s.id === server.id ? server : s
    );
  }
  // ... existing chunk handlers
}
```
- **Priority:** P2

#### F4. Create `MCPPanel.tsx` Component
- **File:** NEW `frontend/src/components/MCPPanel.tsx`
- **Features:**
  - Display table of registered servers with status badges
  - Connect/Disconnect buttons per server
  - Tool browser with search/filter
  - "Call Tool" modal with JSON schema form
  - "Capture as Chunk" checkbox
- **Size:** ~150-200 lines
- **Priority:** P2

#### F5. Add MCP Tab to App
- **File:** `frontend/src/App.tsx`
- **Action:**
```typescript
type TabType = 'inbox' | 'chunks' | 'projects' | 'mcp';  // Added 'mcp'

{activeTab === 'mcp' && <MCPPanel />}
```
- **Priority:** P2

### Testing Deliverables (7 items)

#### T1. Unit Tests for `MCPClient`
- **File:** NEW `backend/tests/test_mcp_client.py`
- **Tests:**
  - `test_env_merging_preserves_path`: Verify BUG-1 fix
  - `test_protocol_version`: Verify "2025-11-25" version
  - `test_connect_disconnect_lifecycle`: Basic connection flow
  - `test_list_tools_returns_tools`: Mock JSON-RPC response
  - `test_call_tool_with_arguments`: Mock tool call
  - `test_subprocess_crash_handling`: Verify process monitoring
  - `test_auto_reconnect`: Verify reconnection with backoff
- **Priority:** P1

#### T2. Unit Tests for `MCPRegistry`
- **File:** NEW `backend/tests/test_mcp_registry.py`
- **Tests:**
  - `test_register_server`: Add server to registry
  - `test_parallel_connect`: Verify `asyncio.gather()` usage
  - `test_find_tool_by_name`: Tool discovery across servers
  - `test_call_tool_routing`: Route to correct server
  - `test_disconnect_all`: Graceful shutdown
- **Priority:** P1

#### T3. Unit Tests for `auth.py`
- **File:** NEW `backend/tests/test_mcp_auth.py`
- **Tests:**
  - `test_resolve_env_keys_success`: Resolve existing env vars
  - `test_resolve_env_keys_missing_raises`: Error on missing var
  - `test_validate_command_whitelist`: Accept safe commands (npx, python, node)
  - `test_validate_command_rejects_injection`: Reject shell operators (`;`, `|`, `&&`)
- **Priority:** P1

#### T4. Unit Tests for Config Loader
- **File:** NEW `backend/tests/test_config_loader.py`
- **Tests:**
  - `test_load_valid_config`: Parse `config/mcp_servers.json`
  - `test_load_invalid_json_raises`: Handle malformed JSON
  - `test_validate_schema_missing_fields`: Require all fields
  - `test_register_all_servers`: Bulk registration
- **Priority:** P1

#### T5. Integration Tests for MCP API
- **File:** `backend/tests/test_api.py` (extend existing)
- **Tests:**
  - `test_list_tools_endpoint`: GET `/api/v1/mcp/tools`
  - `test_call_tool_endpoint`: POST `/api/v1/mcp/tools/{name}/call`
  - `test_tool_call_auto_capture`: Verify chunk creation with `capture=True`
  - `test_connect_server_endpoint`: POST `/api/v1/mcp/servers/{id}/connect`
  - `test_disconnect_server_endpoint`: POST `/api/v1/mcp/servers/{id}/disconnect`
- **Priority:** P2

#### T6. E2E Tests for Frontend MCP Panel
- **File:** NEW `frontend/e2e/mcp.spec.ts`
- **Tests:**
  - `test_mcp_tab_displays_servers`: Navigate to MCP tab, verify server list
  - `test_connect_server_button`: Click connect, verify status change
  - `test_tool_browser_search`: Search tools by name
  - `test_call_tool_modal`: Open modal, fill form, call tool
  - `test_capture_as_chunk_checkbox`: Verify chunk appears in Inbox
- **Priority:** P3

#### T7. Load Test for MCP Tool Calls
- **File:** `scripts/hammer_gen.py` (extend)
- **Action:** Add `mcp_tool_call` generator
```python
def generate_mcp_tool_calls(count: int, servers: list[str]) -> list[dict]:
    """Generate synthetic MCP tool calls for load testing"""
    tools = ["filesystem.read", "github.search_repos", "web.fetch"]
    return [
        {
            "tool": random.choice(tools),
            "arguments": {"path": f"/tmp/file_{i}.txt"},
            "capture": True,
            "project_id": random.randint(1, 10)
        }
        for i in range(count)
    ]
```
- **Test:** 100 tool calls/sec, verify no crashes, all chunks captured
- **Priority:** P3

---

## Architecture Deep Dive

### MCP Protocol Overview
**Model Context Protocol (MCP)** is a JSON-RPC 2.0 protocol over stdio for LLM-tool integration. Komorebi acts as an **MCP Client** connecting to external **MCP Servers** (e.g., filesystem, GitHub, web scraping).

**Message Flow:**
```
┌────────────────┐    stdio    ┌─────────────────┐
│  Komorebi      │◄────────────►│   MCP Server    │
│  (FastAPI)     │   JSON-RPC   │   (subprocess)  │
└────────────────┘              └─────────────────┘
       │                                 │
     Request                          Response
  {"jsonrpc": "2.0",              {"jsonrpc": "2.0",
   "method": "tools/list",         "result": {"tools": [...]}}
   "id": 1}
```

### Subprocess Management Strategy
- **Process Lifecycle:** `connect()` → `subprocess.Popen` → `_initialize()` → `initialized` notification → Ready
- **Communication:** JSON-RPC messages via `stdin`/`stdout`, log output via `stderr`
- **Monitoring:** Background task `_monitor_process()` detects crashes and reconnects
- **Cleanup:** `disconnect()` sends SIGTERM, waits 5s, then SIGKILL

### Security Model
1. **No Secrets in Config:** Use `env_keys: ["GITHUB_TOKEN"]` (reference) instead of `env: {"GITHUB_TOKEN": "ghp_..."}`
2. **Secret Resolution:** `auth.resolve_env_keys()` reads from environment at runtime
3. **Command Whitelist:** Only allow `["npx", "node", "python", "python3", "uvx"]`
4. **Argument Validation:** Reject shell operators (`;`, `|`, `&&`, `>`, `<`)
5. **Subprocess Isolation:** Use `env=merged_env` to avoid shell execution

### Data Flow: Tool Call → Chunk → Compaction
```
1. User calls tool via API/UI
   POST /api/v1/mcp/tools/filesystem.read/call?capture=true
   
2. MCPRegistry routes to correct server
   registry.call_tool("filesystem.read", {"path": "/tmp/log.txt"})
   
3. MCPClient sends JSON-RPC request
   {"method": "tools/call", "params": {"name": "filesystem.read", ...}}
   
4. Result captured as Chunk (if capture=true)
   ChunkCreate(content=json.dumps(result), source="mcp:filesystem.read", status=INBOX)
   
5. SSE event notified
   EventType.CHUNK_CREATED → Frontend updates Inbox
   
6. User triggers compaction
   POST /api/v1/chunks/{id}/compact
   
7. Entity extraction
   CompactorService.extract_entities() → EntityRepository.create_many()
   
8. Recursive summarization
   CompactorService.recursive_reduce() → KomorebiLLM.summarize()
```

---

## Implementation Plan (5 Phases)

### Phase 1: Critical Bug Fixes (v0.3.0+build1)
**Goal:** Make existing MCP backend operational  
**Duration:** 1-2 days  
**Version:** v0.3.0+build1

**Tasks:**
1. ✅ Fix subprocess env merging (B1) - BUG-1
2. ✅ Update protocol version (B2) - BUG-2
3. ✅ Fix `compact_project` endpoint (B11) - BUG-3
4. ✅ Remove dead code (B12) - BUG-5/BUG-6

**Validation:**
- All existing 27 tests still pass
- Manual test: Connect to `@modelcontextprotocol/server-filesystem` via npx
- Manual test: Call `filesystem.read_file` tool

**Deliverables:**
- Updated `backend/app/mcp/client.py`
- Updated `backend/app/api/projects.py`
- Git commit: `fix: MCP subprocess env merging + protocol version (closes BUG-1, BUG-2, BUG-3)`

### Phase 2: Configuration System (v0.3.0+build2)
**Goal:** Enable declarative server configuration  
**Duration:** 2-3 days  
**Version:** v0.3.0+build2

**Tasks:**
1. ✅ Create `backend/app/mcp/auth.py` (B3)
2. ✅ Create `backend/app/mcp/config_loader.py` (B4)
3. ✅ Create `config/mcp_servers.json` (B5)
4. ✅ Add startup auto-connect to `main.py` (B6)
5. ✅ Parallelize `connect_all()` (B10)
6. ✅ Write unit tests (T1, T2, T3, T4)

**Validation:**
- Start Komorebi → Verify 2+ servers auto-connect
- Check logs for "Loaded MCP server: filesystem (connected)"
- GET `/api/v1/mcp/tools` → Should return 5+ tools

**Deliverables:**
- 3 new backend modules
- 1 new config file
- 15+ new unit tests
- Git commit: `feat: MCP configuration system with auto-connect on startup`

### Phase 3: Tool Result Capture (v0.3.0+build3)
**Goal:** Close the "MCP → Chunk" data pipeline  
**Duration:** 2 days  
**Version:** v0.3.0+build3

**Tasks:**
1. ✅ Implement "Tool Result → Chunk" in `api/mcp.py` (B7)
2. ✅ Add `disconnect_all()` to registry (B8)
3. ✅ Write integration tests (T5)

**Validation:**
- Call tool with `capture=True` → Verify chunk appears in database
- Call tool with `capture=False` → No chunk created
- SSE event `chunk.created` fires with `source: "mcp:tool_name"`

**Deliverables:**
- Updated `backend/app/api/mcp.py`
- 5+ integration tests
- Git commit: `feat: Auto-capture MCP tool results as chunks`

### Phase 4: Frontend MCP Panel (v0.3.0+build4)
**Goal:** User-facing MCP management UI  
**Duration:** 3-4 days  
**Version:** v0.3.0+build4

**Tasks:**
1. ✅ Add MCP types to store (F1)
2. ✅ Add MCP signals actions (F2)
3. ✅ Update SSE handler (F3)
4. ✅ Create `MCPPanel.tsx` component (F4)
5. ✅ Add MCP tab to `App.tsx` (F5)
6. ✅ Write E2E tests (T6)

**Validation:**
- Navigate to "MCP" tab → See server list with status badges
- Click "Connect" → Status changes to "Connected" in real-time
- Click "Tools" → Tool browser opens, search works
- Call tool → Result appears in modal, chunk appears in Inbox

**Deliverables:**
- 1 new React component (~200 lines)
- Updated store with 5 new actions
- 5+ E2E tests
- Git commit: `feat: Frontend MCP Panel with tool browser and real-time status`

### Phase 5: Reliability & Performance (v0.3.0+build5)
**Goal:** Production-ready MCP subsystem  
**Duration:** 2 days  
**Version:** v0.3.0 (release)

**Tasks:**
1. ✅ Add reconnection logic (B9)
2. ✅ Write load tests (T7)
3. ✅ Fix remaining low-priority bugs (BUG-4)
4. ✅ Update all documentation

**Validation:**
- Kill MCP subprocess → Verify auto-reconnect within 10s
- Run Hammer test: 100 tool calls/sec for 60s → No crashes
- All 52+ tests pass (27 existing + 25 new MCP tests)

**Deliverables:**
- Updated `backend/app/mcp/client.py` with reconnection
- `scripts/hammer_gen.py` MCP load test
- Git commit: `feat: MCP auto-reconnection + load testing (release v0.3.0)`
- **Git tag:** `v0.3.0`
- **Publish:** PyPI + NPM version bump

---

## Test Plan (25+ New Tests)

### Unit Tests (15+ tests)

#### `backend/tests/test_mcp_client.py` (7 tests)
```python
@pytest.mark.asyncio
async def test_env_merging_preserves_path():
    """Verify BUG-1 fix: subprocess inherits PATH from parent"""
    config = MCPServerConfig(
        id="test",
        name="Test",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        env={"CUSTOM_VAR": "value"}
    )
    client = MCPClient(config)
    
    # Mock subprocess to capture env dict
    with patch('asyncio.create_subprocess_exec') as mock_exec:
        await client.connect()
        call_kwargs = mock_exec.call_args.kwargs
        assert 'PATH' in call_kwargs['env']  # Must preserve PATH
        assert call_kwargs['env']['CUSTOM_VAR'] == 'value'  # Must include custom vars

@pytest.mark.asyncio
async def test_protocol_version():
    """Verify protocol version is 2025-11-25"""
    client = MCPClient(sample_config)
    with patch.object(client, '_request') as mock_request:
        await client._initialize()
        mock_request.assert_called_once()
        init_params = mock_request.call_args[0][1]
        assert init_params['protocolVersion'] == '2025-11-25'

@pytest.mark.asyncio
async def test_auto_reconnect():
    """Verify reconnection on subprocess crash"""
    client = MCPClient(sample_config)
    await client.connect()
    
    # Simulate crash
    client._process.kill()
    await asyncio.sleep(3)  # Wait for reconnection
    
    assert client._status == MCPServerStatus.CONNECTED
    assert client._reconnect_attempts >= 1
```

#### `backend/tests/test_mcp_registry.py` (4 tests)
```python
@pytest.mark.asyncio
async def test_parallel_connect():
    """Verify connect_all uses asyncio.gather"""
    registry = MCPRegistry()
    for i in range(3):
        registry.register(MCPServerConfig(
            id=f"server{i}",
            name=f"Server {i}",
            command="python",
            args=["-m", "http.server", str(8000 + i)]
        ))
    
    start_time = time.time()
    await registry.connect_all()
    duration = time.time() - start_time
    
    # Parallel connection should be <2s (sequential would be 6s+)
    assert duration < 2, "connect_all should parallelize connections"
```

#### `backend/tests/test_mcp_auth.py` (2 tests)
```python
def test_resolve_env_keys_success():
    """Resolve env_keys to actual env var values"""
    os.environ['TEST_KEY'] = 'secret_value'
    config = MCPServerConfig(
        id="test",
        name="Test",
        command="npx",
        args=[],
        env_keys=["TEST_KEY", "HOME"]
    )
    
    resolved = resolve_env_keys(config)
    assert resolved['TEST_KEY'] == 'secret_value'
    assert 'HOME' in resolved

def test_validate_command_rejects_injection():
    """Reject commands with shell operators"""
    with pytest.raises(ValueError, match="Command injection detected"):
        validate_command("npx; rm -rf /", [])
    
    with pytest.raises(ValueError, match="Command injection detected"):
        validate_command("npx", ["-y", "tool", "&&", "malicious"])
```

#### `backend/tests/test_config_loader.py` (2 tests)
```python
def test_load_valid_config(tmp_path):
    """Load and parse config/mcp_servers.json"""
    config_file = tmp_path / "mcp_servers.json"
    config_file.write_text(json.dumps({
        "version": "1.0",
        "servers": [{
            "id": "test",
            "name": "Test Server",
            "command": "npx",
            "args": ["-y", "tool"],
            "env_keys": ["API_KEY"]
        }]
    }))
    
    configs = load_mcp_config(config_file)
    assert len(configs) == 1
    assert configs[0].id == "test"

def test_load_invalid_json_raises(tmp_path):
    """Handle malformed JSON gracefully"""
    config_file = tmp_path / "mcp_servers.json"
    config_file.write_text("{invalid json")
    
    with pytest.raises(JSONDecodeError):
        load_mcp_config(config_file)
```

### Integration Tests (5+ tests)

#### `backend/tests/test_api.py` (extend existing file)
```python
@pytest.mark.asyncio
async def test_tool_call_auto_capture(client: AsyncClient, db_session: AsyncSession):
    """Verify tool result is captured as chunk when capture=True"""
    # Setup: Register and connect MCP server
    response = await client.post("/api/v1/mcp/servers", json={
        "id": "test",
        "name": "Test",
        "command": "python",
        "args": ["-m", "tests.fixtures.mock_mcp_server"]
    })
    assert response.status_code == 201
    
    await client.post("/api/v1/mcp/servers/test/connect")
    
    # Call tool with capture=True
    response = await client.post(
        "/api/v1/mcp/tools/mock.echo/call?capture=true",
        json={"arguments": {"message": "Hello MCP"}}
    )
    assert response.status_code == 200
    data = response.json()
    assert "chunk_id" in data
    
    # Verify chunk exists in database
    chunk_repo = ChunkRepository(db_session)
    chunk = await chunk_repo.get_by_id(data["chunk_id"])
    assert chunk is not None
    assert chunk.source == "mcp:mock.echo"
    assert "Hello MCP" in chunk.content
```

### E2E Tests (5+ tests)

#### `frontend/e2e/mcp.spec.ts` (NEW)
```typescript
import { test, expect } from '@playwright/test';

test('MCP tab displays servers and tools', async ({ page }) => {
  await page.goto('http://localhost:3000');
  
  // Navigate to MCP tab
  await page.click('text=MCP');
  
  // Verify server list
  await expect(page.locator('[data-testid="mcp-server-list"]')).toBeVisible();
  await expect(page.locator('text=Filesystem Tools')).toBeVisible();
  
  // Verify tool browser
  await page.click('button:has-text("Tools")');
  await expect(page.locator('[data-testid="tool-browser"]')).toBeVisible();
});

test('call tool and capture as chunk', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await page.click('text=MCP');
  
  // Call tool with capture enabled
  await page.click('button:has-text("Call Tool")');
  await page.fill('[name="tool_name"]', 'filesystem.read_file');
  await page.fill('[name="arguments"]', '{"path": "/tmp/test.txt"}');
  await page.check('[name="capture"]');
  await page.click('button:has-text("Execute")');
  
  // Verify chunk appears in Inbox
  await page.click('text=Inbox');
  await expect(page.locator('text=mcp:filesystem.read_file')).toBeVisible();
});
```

---

## Acceptance Criteria (20 items)

### Functional Requirements (10 items)

#### AC-1: Configuration Loading ✅
- **Given:** `config/mcp_servers.json` exists with 2+ servers
- **When:** Komorebi starts
- **Then:** All servers auto-connect within 10 seconds
- **Verify:** GET `/api/v1/mcp/servers` returns `"status": "connected"` for all

#### AC-2: Environment Variable Security ✅
- **Given:** Config uses `"env_keys": ["GITHUB_TOKEN"]`
- **When:** Server connects
- **Then:** `auth.resolve_env_keys()` reads from environment (not config)
- **Verify:** Config file contains NO secret values (only key references)

#### AC-3: Subprocess Environment Merging ✅
- **Given:** MCP server requires `npx` command
- **When:** Server connects with custom env vars
- **Then:** Subprocess inherits `PATH`, `HOME`, and custom vars
- **Verify:** `npx` command executes successfully (BUG-1 fixed)

#### AC-4: Tool Discovery ✅
- **Given:** 2 MCP servers connected (filesystem + github)
- **When:** GET `/api/v1/mcp/tools`
- **Then:** Returns aggregated list of 5+ tools from both servers
- **Verify:** Response includes `server_id`, `name`, `description` for each tool

#### AC-5: Tool Calling ✅
- **Given:** Tool `filesystem.read_file` exists
- **When:** POST `/api/v1/mcp/tools/filesystem.read_file/call` with `{"path": "/tmp/test.txt"}`
- **Then:** Returns file contents in `{"result": "..."}`
- **Verify:** Tool executes successfully without errors

#### AC-6: Auto-Capture Pipeline ✅
- **Given:** Tool call with `?capture=true&project_id=1`
- **When:** Tool execution completes
- **Then:** New chunk created with `source="mcp:tool_name"`, `status=INBOX`, `project_id=1`
- **Verify:** GET `/api/v1/chunks` includes new chunk with tool result in content

#### AC-7: SSE Events for MCP ✅
- **Given:** Frontend connected to `/api/v1/sse/events`
- **When:** MCP server status changes
- **Then:** SSE event `{"type": "mcp.status_changed", "data": {...}}` fires
- **Verify:** Frontend MCP Panel updates status badge in real-time

#### AC-8: Frontend MCP Panel ✅
- **Given:** User navigates to "MCP" tab
- **When:** Page loads
- **Then:** Displays table of servers with status, tool count, connect/disconnect buttons
- **Verify:** Visual inspection + E2E test `mcp.spec.ts`

#### AC-9: Tool Browser UI ✅
- **Given:** User clicks "Tools" button in MCP Panel
- **When:** Tool browser opens
- **Then:** Displays searchable list of all tools across servers
- **Verify:** Search "read" → Only shows tools with "read" in name

#### AC-10: Graceful Shutdown ✅
- **Given:** Komorebi is running with 2 MCP servers connected
- **When:** Komorebi receives SIGTERM
- **Then:** `mcp_registry.disconnect_all()` called, all subprocesses terminated within 10s
- **Verify:** No zombie processes remain after shutdown

### Quality Requirements (7 items)

#### QA-1: Test Coverage ✅
- All 27 existing tests pass
- 15+ new MCP unit tests pass
- 5+ new MCP integration tests pass
- 5+ new MCP E2E tests pass
- **Total:** 52+ tests passing

#### QA-2: No Dead Code ✅
- Zero `# TODO` comments in production code
- Zero `NotImplementedError` stubs
- Zero unused imports or dataclasses
- **Verify:** `ruff check .` passes with no warnings

#### QA-3: Bug Resolution ✅
- BUG-1 (env merging): Fixed and tested
- BUG-2 (protocol version): Updated to "2025-11-25"
- BUG-3 (compact_project): entity_repo parameter added
- BUG-4 (private member access): Public method added
- BUG-5 (dead code): Removed
- BUG-6 (deprecated asyncio): Updated to `asyncio.create_task()`

#### QA-4: Documentation ✅
- `docs/MODULE_3_MCP_AGGREGATOR.md` (this document) published
- `docs/CHANGELOG.md` updated with v0.3.0 entry
- `docs/API_REFERENCE.md` updated with 10 MCP endpoints
- `docs/CURRENT_STATUS.md` updated to mark Module 3 complete

#### QA-5: Version Consistency ✅
- `VERSION` file = `0.3.0`
- `pyproject.toml` = `0.3.0`
- `frontend/package.json` = `0.3.0`
- **Verify:** `python scripts/check_version.py` exits with code 0

#### QA-6: CHANGELOG Compliance ✅
- `docs/CHANGELOG.md` has `## [0.3.0] - 2026-02-0X` section
- Lists all new features (config loading, auto-capture, frontend panel)
- Lists all bug fixes (BUG-1 through BUG-6)
- Lists breaking changes (none for this release)
- **Verify:** `python scripts/validate_changelog.py` passes

#### QA-7: TypeScript Build ✅
- `npm run build` succeeds without errors
- No type errors in `MCPPanel.tsx` or store updates
- **Verify:** CI passes on GitHub Actions

### Security Requirements (3 items)

#### SEC-1: No Secrets in Config ✅
- `config/mcp_servers.json` contains zero API keys or tokens
- Only `env_keys` references allowed (e.g., `["GITHUB_TOKEN"]`)
- **Verify:** `grep -r "ghp_\|sk_live\|Bearer" config/` returns no matches

#### SEC-2: Command Whitelist ✅
- Only `["npx", "node", "python", "python3", "uvx"]` allowed
- Shell operators (`;`, `|`, `&&`, `>`, `<`) rejected
- **Verify:** `test_validate_command_rejects_injection` passes

#### SEC-3: Subprocess Isolation ✅
- No use of `shell=True` in subprocess calls
- All commands use `asyncio.create_subprocess_exec` with explicit args
- **Verify:** Code review of `backend/app/mcp/client.py`

---

## File Manifest

### New Files (8 files)

1. **`backend/app/mcp/auth.py`** (~60 lines)
   - `resolve_env_keys(config: MCPServerConfig) -> dict[str, str]`
   - `validate_command(command: str, args: list[str])`

2. **`backend/app/mcp/config_loader.py`** (~80 lines)
   - `load_mcp_config(path: Path) -> list[MCPServerConfig]`
   - `validate_config_schema(data: dict) -> bool`
   - `load_and_register_servers(registry: MCPRegistry, path: Path)`

3. **`config/mcp_servers.json`** (~30 lines)
   - JSON config with 2 example servers (filesystem, github)

4. **`backend/tests/test_mcp_client.py`** (~150 lines)
   - 7 unit tests for MCPClient

5. **`backend/tests/test_mcp_registry.py`** (~100 lines)
   - 4 unit tests for MCPRegistry

6. **`backend/tests/test_mcp_auth.py`** (~60 lines)
   - 2 unit tests for auth module

7. **`backend/tests/test_config_loader.py`** (~80 lines)
   - 2 unit tests for config loading

8. **`frontend/src/components/MCPPanel.tsx`** (~200 lines)
   - React component with server table, tool browser, call modal

### Modified Files (17 files)

1. **`backend/app/mcp/client.py`**
   - Fix env merging (line ~75)
   - Update protocol version (line ~85)
   - Add reconnection logic (new method `_monitor_process`)
   - Remove dead code (MCPMessage, uuid4 import)

2. **`backend/app/mcp/registry.py`**
   - Parallelize `connect_all()` with `asyncio.gather()`
   - Add `disconnect_all()` method
   - Add `list_servers()` public method

3. **`backend/app/api/mcp.py`**
   - Update `list_servers()` to use new public method
   - Add `capture` parameter to `call_tool` endpoint
   - Implement "Tool Result → Chunk" pipeline

4. **`backend/app/api/projects.py`**
   - Fix `compact_project` endpoint (add entity_repo parameter)

5. **`backend/app/main.py`**
   - Add `lifespan` context manager
   - Call `load_and_register_servers()` on startup
   - Call `disconnect_all()` on shutdown

6. **`frontend/src/store/index.ts`**
   - Add MCPServer, MCPTool types
   - Add mcpServers, mcpTools signals
   - Add fetchMCPServers, connectServer, fetchMCPTools, callTool actions
   - Update handleSSEEvent to process mcp.status_changed

7. **`frontend/src/App.tsx`**
   - Add 'mcp' to TabType union
   - Add `{activeTab === 'mcp' && <MCPPanel />}`

8. **`backend/tests/test_api.py`**
   - Add 5 new integration tests for MCP endpoints

9. **`frontend/e2e/mcp.spec.ts`** (NEW)
   - Add 5 E2E tests for MCP Panel

10. **`scripts/hammer_gen.py`**
    - Add `generate_mcp_tool_calls()` function

11. **`docs/MODULE_3_MCP_AGGREGATOR.md`** (THIS FILE)

12. **`docs/CHANGELOG.md`**
    - Add `## [0.3.0] - 2026-02-0X` section

13. **`docs/API_REFERENCE.md`**
    - Document 10 MCP endpoints with examples

14. **`docs/CURRENT_STATUS.md`**
    - Update Module 3 status to ✅ Complete

15. **`pyproject.toml`**
    - Bump version to `0.3.0`

16. **`frontend/package.json`**
    - Bump version to `0.3.0`

17. **`VERSION`**
    - Update to `0.3.0`

### Do Not Touch (5 files)

1. **`backend/app/core/ollama_client.py`** - Module 1 complete, no changes needed
2. **`backend/app/core/compactor.py`** - Module 2 complete, no changes needed
3. **`backend/app/models/chunk.py`** - Core models stable
4. **`backend/app/models/project.py`** - Core models stable
5. **`backend/app/models/entity.py`** - Entity system complete (v0.2.1)

---

## Versioning & Release Protocol

### Semantic Versioning Rules
- **v0.3.0+build1** → Phase 1 complete (critical bug fixes)
- **v0.3.0+build2** → Phase 2 complete (configuration system)
- **v0.3.0+build3** → Phase 3 complete (tool capture pipeline)
- **v0.3.0+build4** → Phase 4 complete (frontend MCP panel)
- **v0.3.0+build5** → Phase 5 complete (reliability)
- **v0.3.0** → Final release (all acceptance criteria met)

### Pre-Release Checklist
Before tagging `v0.3.0`:
- [ ] All 52+ tests pass (`pytest backend/tests`)
- [ ] All E2E tests pass (`npm run test:e2e`)
- [ ] Frontend builds without errors (`npm run build`)
- [ ] Linting passes (`ruff check .`)
- [ ] Version consistency validated (`python scripts/check_version.py`)
- [ ] CHANGELOG entry complete (`python scripts/validate_changelog.py`)
- [ ] Manual smoke test: Start Komorebi → Connect 2 MCP servers → Call tool → Verify chunk in Inbox
- [ ] Documentation updated (CURRENT_STATUS.md, API_REFERENCE.md)

### Release Commands
```bash
# 1. Update VERSION file
echo "0.3.0" > VERSION

# 2. Sync all version files
python scripts/sync_version.py

# 3. Commit and tag
git add -A
git commit -m "release: v0.3.0 - MCP Aggregator Integration"
python scripts/check_version.py  # Validate commit message
git tag -a v0.3.0 -m "Module 3: MCP Aggregator with auto-config and tool capture"

# 4. Push to remote
git push origin develop
git push origin v0.3.0

# 5. Merge to main (after review)
git checkout main
git merge develop
git push origin main
```

---

## Environment Setup for Agents

### Prerequisites
- Python 3.11+
- Node.js 18+
- Poetry (`pip install poetry`)
- NPM (`brew install node` on macOS)

### Backend Setup
```bash
cd /Users/earchibald/work/github/earchibald/komorebi

# Install dependencies
poetry install

# Activate virtualenv
poetry shell

# Run backend
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# Run tests
pytest backend/tests -v

# Lint
ruff check .
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev  # http://localhost:3000

# Run E2E tests
npm run test:e2e

# Build production
npm run build
```

### MCP Server Testing
```bash
# Test filesystem server (requires npx)
npx -y @modelcontextprotocol/server-filesystem /tmp

# Test in Python
python -c "
from backend.app.models.mcp import MCPServerConfig
from backend.app.mcp.client import MCPClient
import asyncio

async def test():
    config = MCPServerConfig(
        id='fs',
        name='Filesystem',
        command='npx',
        args=['-y', '@modelcontextprotocol/server-filesystem', '/tmp']
    )
    client = MCPClient(config)
    await client.connect()
    tools = await client.list_tools()
    print(f'Tools: {[t.name for t in tools]}')
    await client.disconnect()

asyncio.run(test())
"
```

---

## Risk Assessment

### Critical Risks

#### R1: Subprocess Stability
**Risk:** MCP servers may crash due to unhandled exceptions or resource limits  
**Mitigation:**
- Implement `_monitor_process()` with auto-reconnect
- Add exponential backoff (2s, 4s, 8s, ... max 60s)
- Log stderr output for debugging
- Test with `scripts/hammer_gen.py` (100 calls/sec for 60s)

#### R2: Security - Command Injection
**Risk:** Malicious config could execute arbitrary commands  
**Mitigation:**
- Whitelist commands: `["npx", "node", "python", "python3", "uvx"]`
- Reject args with shell operators: `;`, `|`, `&&`, `>`, `<`
- Never use `shell=True` in subprocess calls
- Use `env=merged_env` to avoid shell execution

#### R3: Secret Leakage
**Risk:** API keys exposed in config files or logs  
**Mitigation:**
- Config uses `env_keys` (references) not `env` (values)
- Secrets read from environment at runtime
- Add `.gitignore` entry for `config/mcp_servers.local.json`
- Mask secrets in stderr logs

### Medium Risks

#### R4: Protocol Version Incompatibility
**Risk:** MCP servers reject old protocol version  
**Mitigation:**
- Update to "2025-11-25" immediately (Phase 1)
- Add protocol version negotiation in future (v0.4.0)

#### R5: Performance - Sequential Connections
**Risk:** 10+ servers take 30s+ to connect sequentially  
**Mitigation:**
- Parallelize `connect_all()` with `asyncio.gather()` (Phase 2)
- Add connection timeout (default 10s)

#### R6: Frontend State Staleness
**Risk:** MCP status changes not reflected in UI  
**Mitigation:**
- Use SSE for real-time updates
- Implement `mcp.status_changed` event handler
- Add "Refresh" button as fallback

---

## Appendix: Code References

### A1: Existing MCP Models (backend/app/models/mcp.py)
```python
from enum import Enum
from pydantic import BaseModel
from typing import Any

class MCPServerStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

class MCPServerConfig(BaseModel):
    id: str
    name: str
    command: str
    args: list[str]
    env: dict[str, str] | None = None
    env_keys: list[str] | None = None  # NEW: For security
    description: str | None = None

class MCPTool(BaseModel):
    name: str
    description: str
    server_id: str
    input_schema: dict[str, Any]
```

### A2: MCPClient Key Methods (backend/app/mcp/client.py)
```python
class MCPClient:
    async def connect(self) -> MCPServerStatus:
        """Start subprocess and initialize MCP protocol"""
        self._status = MCPServerStatus.CONNECTING
        
        # BUG-1 FIX: Merge env instead of replace
        env = os.environ.copy()
        if self.config.env:
            env.update(self.config.env)
        
        self._process = await asyncio.create_subprocess_exec(
            self.config.command, *self.config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env  # Fixed
        )
        
        asyncio.create_task(self._read_responses())  # BUG-6 fix
        asyncio.create_task(self._monitor_process())  # NEW: Auto-reconnect
        
        await self._initialize()
        self._status = MCPServerStatus.CONNECTED
        return self._status
    
    async def _initialize(self):
        """Send initialize request"""
        response = await self._request("initialize", {
            "protocolVersion": "2025-11-25",  # BUG-2 fix
            "capabilities": {}
        })
        
        # Wait for initialized notification
        await self._wait_for_notification("initialized")
```

### A3: CompactorService Constructor (backend/app/core/compactor.py)
```python
class CompactorService:
    def __init__(
        self,
        chunk_repository: ChunkRepository,
        project_repository: ProjectRepository,
        entity_repository: EntityRepository,  # REQUIRED (BUG-3)
        llm: KomorebiLLM | None = None
    ):
        self.chunk_repo = chunk_repository
        self.project_repo = project_repository
        self.entity_repo = entity_repository
        self.llm = llm or KomorebiLLM()
```

### A4: Event Bus Usage (backend/app/core/events.py)
```python
# Publish MCP status change
from backend.app.core.events import event_bus, Event, EventType

event_bus.publish(Event(
    type=EventType.MCP_STATUS_CHANGED,
    data={
        "server_id": "filesystem",
        "status": "connected",
        "tool_count": 5
    }
))
```

### A5: Frontend SSE Handler (frontend/src/store/index.ts)
```typescript
function handleSSEEvent(event: MessageEvent) {
  const data = JSON.parse(event.data);
  
  // Existing chunk handlers
  if (data.type === 'chunk.created') {
    chunks.value = [...chunks.value, data.data];
  }
  
  // NEW: MCP handler
  if (data.type === 'mcp.status_changed') {
    const server = data.data as MCPServer;
    mcpServers.value = mcpServers.value.map(s => 
      s.id === server.id ? { ...s, status: server.status } : s
    );
  }
}
```

---

## Summary for External Agent

**Mission:** Implement Module 3 (MCP Aggregator Integration) for Komorebi v0.3.0

**Context:**
- Komorebi is a "Capture Now, Refine Later" cognitive infrastructure system
- Current version: v0.2.1+build1 (Modules 1 & 2 complete, entity system operational)
- Target version: v0.3.0 (MCP Aggregator complete)
- MCP backend is 70% coded but has 6 critical bugs preventing operation

**Scope:**
- Fix 6 bugs in existing MCP code (env merging, protocol version, dead code)
- Implement configuration system (`config/mcp_servers.json` + auto-connect)
- Build "Tool Result → Chunk" auto-capture pipeline
- Create frontend MCP Panel with real-time status display
- Write 25+ new tests (unit + integration + E2E)
- Update all documentation and version files

**Phases:**
1. **Phase 1 (v0.3.0+build1):** Fix critical bugs (BUG-1, BUG-2, BUG-3) - 1-2 days
2. **Phase 2 (v0.3.0+build2):** Implement config system + auto-connect - 2-3 days
3. **Phase 3 (v0.3.0+build3):** Add tool→chunk capture pipeline - 2 days
4. **Phase 4 (v0.3.0+build4):** Build frontend MCP Panel - 3-4 days
5. **Phase 5 (v0.3.0+build5):** Add reconnection + load testing - 2 days

**Deliverables:**
- 8 new files (auth.py, config_loader.py, MCPPanel.tsx, 4 test files, config JSON)
- 17 modified files (client.py, registry.py, api/mcp.py, store/index.ts, etc.)
- 25+ new tests passing (52+ total)
- All 20 acceptance criteria met (10 functional, 7 quality, 3 security)

**Critical Files:**
- `backend/app/mcp/client.py` (line ~75: env merging bug, line ~85: protocol version)
- `backend/app/api/projects.py` (line ~114: missing entity_repo parameter)
- `frontend/src/store/index.ts` (add MCP signals and SSE handler)
- `frontend/src/components/MCPPanel.tsx` (new component, ~200 lines)

**Testing Strategy:**
- Unit tests for MCPClient, MCPRegistry, auth.py (15+ tests)
- Integration tests for API endpoints (5+ tests)
- E2E tests for frontend MCP Panel (5+ tests)
- Load test: 100 tool calls/sec for 60s (Hammer)

**Success Criteria:**
- All servers auto-connect on startup
- Tool calls work via REST API
- Tool results auto-captured as chunks when `capture=True`
- Frontend displays real-time MCP status via SSE
- All 52+ tests pass, no TODOs, version consistency validated

**Reference:** This document (`docs/MODULE_3_MCP_AGGREGATOR.md`) is the authoritative specification. Report blockers to `ELICITATIONS.md`.

---

**End of Specification - Ready for Implementation**
