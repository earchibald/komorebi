"""Tests for API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.db import init_db


@pytest.fixture
async def client():
    """Create an async test client."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test the root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Komorebi"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test the health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_create_chunk(client: AsyncClient):
    """Test creating a chunk."""
    response = await client.post(
        "/api/v1/chunks",
        json={"content": "Test chunk content", "source": "test"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Test chunk content"
    assert data["status"] == "inbox"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_chunks(client: AsyncClient):
    """Test listing chunks."""
    # Create a chunk first
    await client.post(
        "/api/v1/chunks",
        json={"content": "Test chunk for listing"},
    )
    
    response = await client.get("/api/v1/chunks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_chunk_stats(client: AsyncClient):
    """Test getting chunk stats."""
    response = await client.get("/api/v1/chunks/stats")
    assert response.status_code == 200
    data = response.json()
    assert "inbox" in data
    assert "processed" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    """Test creating a project."""
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Test Project", "description": "A test project"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["description"] == "A test project"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient):
    """Test listing projects."""
    response = await client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_mcp_servers(client: AsyncClient):
    """Test listing MCP servers."""
    response = await client.get("/api/v1/mcp/servers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_sse_status(client: AsyncClient):
    """Test SSE status endpoint."""
    response = await client.get("/api/v1/sse/status")
    assert response.status_code == 200
    data = response.json()
    assert "subscribers" in data
    assert "status" in data
