"""Phase 2 tests: Traces, File Events, API routes, MCP Server.

Covers:
- TraceRepository CRUD and activation logic
- FileEventRepository CRUD and path history
- Trace API routes via TestClient
- File-event API routes via TestClient
- KomorebiMCPServer protocol and tool dispatch
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app.db.trace_repository import TraceRepository
from backend.app.db.file_event_repository import FileEventRepository
from backend.app.models.oracle import TraceCreate, TraceUpdate, TraceStatus
from backend.app.models.file_event import FileEventCreate, CrudOp
from backend.app.mcp.server import KomorebiMCPServer, TOOLS


# ── Helper ──────────────────────────────────────────────────

@pytest_asyncio.fixture
async def trace_repo(test_db):
    return TraceRepository(test_db)


@pytest_asyncio.fixture
async def event_repo(test_db):
    return FileEventRepository(test_db)


# ══════════════════════════════════════════════════════════════
# Trace Repository Tests
# ══════════════════════════════════════════════════════════════

class TestTraceRepository:

    @pytest.mark.asyncio
    async def test_create_trace(self, trace_repo):
        trace = await trace_repo.create(TraceCreate(name="My Trace"))
        assert trace.name == "My Trace"
        assert trace.status == TraceStatus.ACTIVE
        assert trace.id is not None

    @pytest.mark.asyncio
    async def test_get_trace(self, trace_repo):
        created = await trace_repo.create(TraceCreate(name="Fetch Me"))
        fetched = await trace_repo.get(created.id)
        assert fetched is not None
        assert fetched.name == "Fetch Me"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, trace_repo):
        result = await trace_repo.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_traces(self, trace_repo):
        await trace_repo.create(TraceCreate(name="Trace A"))
        await trace_repo.create(TraceCreate(name="Trace B"))
        traces = await trace_repo.list()
        assert len(traces) >= 2

    @pytest.mark.asyncio
    async def test_list_traces_filter_status(self, trace_repo):
        await trace_repo.create(TraceCreate(name="Active One"))
        traces = await trace_repo.list(status=TraceStatus.ACTIVE)
        assert all(t.status == TraceStatus.ACTIVE for t in traces)

    @pytest.mark.asyncio
    async def test_update_trace(self, trace_repo):
        created = await trace_repo.create(TraceCreate(name="Original"))
        updated = await trace_repo.update(created.id, TraceUpdate(name="Renamed"))
        assert updated is not None
        assert updated.name == "Renamed"

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, trace_repo):
        result = await trace_repo.update(uuid4(), TraceUpdate(name="Nope"))
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status(self, trace_repo):
        created = await trace_repo.create(TraceCreate(name="Close Me"))
        updated = await trace_repo.update(
            created.id, TraceUpdate(status=TraceStatus.CLOSED)
        )
        assert updated.status == TraceStatus.CLOSED

    @pytest.mark.asyncio
    async def test_activate_deactivates_others(self, trace_repo):
        t1 = await trace_repo.create(TraceCreate(name="First"))
        t2 = await trace_repo.create(TraceCreate(name="Second"))

        # Both start active; activate t2 should pause t1
        await trace_repo.activate(t2.id)
        t1_after = await trace_repo.get(t1.id)
        t2_after = await trace_repo.get(t2.id)

        assert t2_after.status == TraceStatus.ACTIVE
        assert t1_after.status == TraceStatus.PAUSED

    @pytest.mark.asyncio
    async def test_activate_nonexistent(self, trace_repo):
        result = await trace_repo.activate(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_active(self, trace_repo):
        await trace_repo.create(TraceCreate(name="The Active One"))
        active = await trace_repo.get_active()
        assert active is not None
        assert active.name == "The Active One"

    @pytest.mark.asyncio
    async def test_get_active_none(self, trace_repo):
        # No traces at all
        active = await trace_repo.get_active()
        assert active is None

    @pytest.mark.asyncio
    async def test_get_summary(self, trace_repo):
        created = await trace_repo.create(TraceCreate(name="Summary Trace"))
        summary = await trace_repo.get_summary(created.id)
        assert summary is not None
        assert summary.name == "Summary Trace"
        assert summary.chunk_count == 0

    @pytest.mark.asyncio
    async def test_search_by_name(self, trace_repo):
        await trace_repo.create(TraceCreate(name="Auth Bug Investigation"))
        await trace_repo.create(TraceCreate(name="Deploy Script"))
        results = await trace_repo.search_by_name("auth")
        assert len(results) == 1
        assert results[0].name == "Auth Bug Investigation"


# ══════════════════════════════════════════════════════════════
# FileEvent Repository Tests
# ══════════════════════════════════════════════════════════════

class TestFileEventRepository:

    @pytest.mark.asyncio
    async def test_create_event(self, trace_repo, event_repo):
        trace = await trace_repo.create(TraceCreate(name="File Trace"))
        event = await event_repo.create(FileEventCreate(
            trace_id=trace.id,
            path="/tmp/test.py",
            crud_op=CrudOp.CREATED,
            size_bytes=1024,
            hash_prefix="abc123",
            mime_type="text/x-python",
        ))
        assert event.path == "/tmp/test.py"
        assert event.crud_op == CrudOp.CREATED
        assert event.size_bytes == 1024

    @pytest.mark.asyncio
    async def test_list_events(self, trace_repo, event_repo):
        trace = await trace_repo.create(TraceCreate(name="List Trace"))
        await event_repo.create(FileEventCreate(
            trace_id=trace.id, path="/a.py", crud_op=CrudOp.CREATED
        ))
        await event_repo.create(FileEventCreate(
            trace_id=trace.id, path="/b.py", crud_op=CrudOp.MODIFIED
        ))
        events = await event_repo.list(trace_id=trace.id)
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_path(self, trace_repo, event_repo):
        trace = await trace_repo.create(TraceCreate(name="Path Filter"))
        await event_repo.create(FileEventCreate(
            trace_id=trace.id, path="/src/app.py", crud_op=CrudOp.MODIFIED
        ))
        await event_repo.create(FileEventCreate(
            trace_id=trace.id, path="/tests/test.py", crud_op=CrudOp.CREATED
        ))
        events = await event_repo.list(path="src")
        assert len(events) == 1
        assert "src" in events[0].path

    @pytest.mark.asyncio
    async def test_path_history(self, trace_repo, event_repo):
        trace = await trace_repo.create(TraceCreate(name="History Trace"))
        await event_repo.create(FileEventCreate(
            trace_id=trace.id, path="/config.yaml", crud_op=CrudOp.CREATED, hash_prefix="aaa"
        ))
        await event_repo.create(FileEventCreate(
            trace_id=trace.id, path="/config.yaml", crud_op=CrudOp.MODIFIED, hash_prefix="bbb"
        ))
        history = await event_repo.path_history("/config.yaml")
        assert history.path == "/config.yaml"
        assert len(history.events) == 2
        assert history.current_hash == "bbb"

    @pytest.mark.asyncio
    async def test_path_history_empty(self, event_repo):
        history = await event_repo.path_history("/nonexistent.txt")
        assert len(history.events) == 0
        assert history.current_hash is None

    @pytest.mark.asyncio
    async def test_count_by_trace(self, trace_repo, event_repo):
        trace = await trace_repo.create(TraceCreate(name="Count Trace"))
        await event_repo.create(FileEventCreate(
            trace_id=trace.id, path="/x.py", crud_op=CrudOp.CREATED
        ))
        count = await event_repo.count_by_trace(trace.id)
        assert count == 1


# ══════════════════════════════════════════════════════════════
# MCP Server Protocol Tests
# ══════════════════════════════════════════════════════════════

class TestMCPServer:

    @pytest.fixture
    def server(self):
        return KomorebiMCPServer()

    @pytest.mark.asyncio
    async def test_initialize(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = await server.handle_message(msg)
        assert resp["id"] == 1
        result = resp["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert "tools" in result["capabilities"]
        assert result["serverInfo"]["name"] == "komorebi"

    @pytest.mark.asyncio
    async def test_initialized_notification(self, server):
        msg = {"jsonrpc": "2.0", "method": "initialized"}
        resp = await server.handle_message(msg)
        assert resp is None  # Notifications produce no response

    @pytest.mark.asyncio
    async def test_tools_list(self, server):
        msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = await server.handle_message(msg)
        tools = resp["result"]["tools"]
        names = {t["name"] for t in tools}
        assert "search_context" in names
        assert "get_active_trace" in names
        assert "read_file_metadata" in names
        assert "get_related_decisions" in names

    @pytest.mark.asyncio
    async def test_shutdown(self, server):
        msg = {"jsonrpc": "2.0", "id": 3, "method": "shutdown", "params": {}}
        resp = await server.handle_message(msg)
        assert resp["result"] == {}

    @pytest.mark.asyncio
    async def test_unknown_method(self, server):
        msg = {"jsonrpc": "2.0", "id": 4, "method": "nonexistent", "params": {}}
        resp = await server.handle_message(msg)
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_unknown_tool(self, server):
        msg = {
            "jsonrpc": "2.0", "id": 5,
            "method": "tools/call",
            "params": {"name": "bogus_tool", "arguments": {}},
        }
        resp = await server.handle_message(msg)
        assert "error" in resp
        assert resp["error"]["code"] == -32602

    def test_tool_definitions_schema(self):
        """Every tool must have name, description, and inputSchema."""
        for tool in TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"


# ══════════════════════════════════════════════════════════════
# API Route Tests (via HTTPX AsyncClient)
# ══════════════════════════════════════════════════════════════

@pytest_asyncio.fixture
async def api_client():
    """Create an async HTTP client wired to the FastAPI app with in-memory DB."""
    from backend.app.main import app
    from backend.app.db.database import Base, engine

    # Re-create tables in the real engine (overridden to in-memory for tests)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class TestTraceAPI:

    @pytest.mark.asyncio
    async def test_create_trace(self, api_client):
        resp = await api_client.post("/api/v1/traces", json={"name": "API Trace"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "API Trace"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_list_traces(self, api_client):
        await api_client.post("/api/v1/traces", json={"name": "T1"})
        await api_client.post("/api/v1/traces", json={"name": "T2"})
        resp = await api_client.get("/api/v1/traces")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    @pytest.mark.asyncio
    async def test_get_active_trace(self, api_client):
        await api_client.post("/api/v1/traces", json={"name": "Active Trace"})
        resp = await api_client.get("/api/v1/traces/active")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_trace_by_id(self, api_client):
        create_resp = await api_client.post("/api/v1/traces", json={"name": "By ID"})
        tid = create_resp.json()["id"]
        resp = await api_client.get(f"/api/v1/traces/{tid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "By ID"

    @pytest.mark.asyncio
    async def test_get_trace_not_found(self, api_client):
        resp = await api_client.get(f"/api/v1/traces/{uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_trace(self, api_client):
        create_resp = await api_client.post("/api/v1/traces", json={"name": "Old"})
        tid = create_resp.json()["id"]
        resp = await api_client.patch(f"/api/v1/traces/{tid}", json={"name": "New"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    @pytest.mark.asyncio
    async def test_activate_trace(self, api_client):
        await api_client.post("/api/v1/traces", json={"name": "Alpha"})
        r2 = await api_client.post("/api/v1/traces", json={"name": "Beta"})
        tid2 = r2.json()["id"]
        resp = await api_client.post(f"/api/v1/traces/{tid2}/activate")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"


class TestFileEventAPI:

    @pytest.mark.asyncio
    async def test_list_file_events(self, api_client):
        resp = await api_client.get("/api/v1/file-events")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_file_history(self, api_client):
        resp = await api_client.get("/api/v1/file-events/history/nonexistent.txt")
        assert resp.status_code == 200
        data = resp.json()
        assert data["path"] == "nonexistent.txt"
        assert data["events"] == []
