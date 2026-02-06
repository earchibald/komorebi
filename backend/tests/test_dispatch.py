"""Integration tests for dispatch endpoint."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

# Tests will fail until we implement the modules
try:
    from backend.app.main import app
    from backend.app.db import init_db
    from backend.app.targets.registry import TargetRegistry
    from backend.app.targets.github import GitHubIssueAdapter
except ImportError:
    pytest.skip("Dispatch modules not yet implemented", allow_module_level=True)


@pytest.fixture
async def client():
    """Create an async test client with initialized database."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def setup_registry():
    """Initialize registry before each test."""
    TargetRegistry._targets = {}
    adapter = GitHubIssueAdapter()
    TargetRegistry.register(adapter)
    yield
    TargetRegistry._targets = {}


@pytest.mark.asyncio
async def test_list_target_schemas(client: AsyncClient):
    """Test GET /api/v1/targets/schemas returns all schemas."""
    response = await client.get("/api/v1/targets/schemas")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "schemas" in data
    assert len(data["schemas"]) == 1
    assert data["schemas"][0]["name"] == "github_issue"


@pytest.mark.asyncio
async def test_get_target_schema_by_name(client: AsyncClient):
    """Test GET /api/v1/targets/{name}/schema returns specific schema."""
    response = await client.get("/api/v1/targets/github_issue/schema")
    
    assert response.status_code == 200
    schema = response.json()
    
    assert schema["name"] == "github_issue"
    assert schema["display_name"] == "GitHub Issue"
    assert "fields" in schema
    assert len(schema["fields"]) == 4


@pytest.mark.asyncio
async def test_get_nonexistent_schema(client: AsyncClient):
    """Test GET /api/v1/targets/{name}/schema returns 404 for unknown target."""
    response = await client.get("/api/v1/targets/nonexistent/schema")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_dispatch_to_github_issue(client: AsyncClient):
    """Test POST /api/v1/dispatch creates GitHub issue via MCP."""
    # Mock MCP service call_tool method
    mock_result = {
        "tool": "github.create_issue",
        "result": {
            "html_url": "https://github.com/owner/repo/issues/123",
            "number": 123
        }
    }
    
    with patch("backend.app.services.mcp_service.MCPService.call_tool", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_result
        
        response = await client.post(
            "/api/v1/dispatch",
            json={
                "target_name": "github_issue",
                "data": {
                    "title": "Test Issue",
                    "body": "Test description",
                    "labels": "bug,urgent"
                },
                "context": {
                    "repo_owner": "testorg",
                    "repo_name": "testrepo"
                }
            }
        )
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["success"] is True
    assert result["target_name"] == "github_issue"
    assert result["mcp_tool"] == "github.create_issue"
    assert "html_url" in result["result"]


@pytest.mark.asyncio
async def test_dispatch_with_invalid_target(client: AsyncClient):
    """Test POST /api/v1/dispatch returns 400 for invalid target."""
    response = await client.post(
        "/api/v1/dispatch",
        json={
            "target_name": "invalid_target",
            "data": {},
            "context": {}
        }
    )
    
    assert response.status_code == 400
    assert "not registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_dispatch_mcp_call_failure(client: AsyncClient):
    """Test POST /api/v1/dispatch handles MCP call failures."""
    with patch("backend.app.services.mcp_service.MCPService.call_tool", new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = Exception("MCP connection failed")
        
        response = await client.post(
            "/api/v1/dispatch",
            json={
                "target_name": "github_issue",
                "data": {
                    "title": "Test",
                    "body": "Content"
                },
                "context": {
                    "repo_owner": "test",
                    "repo_name": "repo"
                }
            }
        )
    
    assert response.status_code == 500
    assert "MCP call failed" in response.json()["detail"]
