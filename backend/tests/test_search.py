"""Tests for Module 4: Search & Entity Filtering API."""

import os
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.db import init_db


@pytest.fixture
async def client():
    """Create an async test client with clean database."""
    # Remove existing database for test isolation
    if os.path.exists("komorebi.db"):
        # First, dispose any existing engine connections
        from backend.app.db.database import engine
        await engine.dispose()
        # Now remove the file
        os.remove("komorebi.db")
    
    # Initialize fresh database
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # Cleanup after test
    from backend.app.db.database import engine
    await engine.dispose()


# ============================================================================
# Text Search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_chunks_by_keyword(client: AsyncClient):
    """Test that GET /chunks/search?q=keyword returns matching chunks."""
    # Create test chunks with varied content
    await client.post("/api/v1/chunks", json={"content": "error in authentication service"})
    await client.post("/api/v1/chunks", json={"content": "successful database migration"})
    await client.post("/api/v1/chunks", json={"content": "ERROR: connection timeout"})
    
    # Search for "error"
    response = await client.get("/api/v1/chunks/search?q=error")
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) == 2  # Should match 2 chunks
    assert all("error" in chunk["content"].lower() for chunk in data["items"])


@pytest.mark.asyncio
async def test_search_case_insensitive(client: AsyncClient):
    """Test that search is case-insensitive."""
    await client.post("/api/v1/chunks", json={"content": "Production ERROR"})
    await client.post("/api/v1/chunks", json={"content": "Testing error handling"})
    
    # Search with lowercase
    response = await client.get("/api/v1/chunks/search?q=error")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_search_no_results(client: AsyncClient):
    """Test that search returns empty list when no matches found."""
    await client.post("/api/v1/chunks", json={"content": "normal log entry"})
    
    response = await client.get("/api/v1/chunks/search?q=nonexistent_keyword_xyz")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


# ============================================================================
# Entity Filtering Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.skip(reason="Entity creation endpoint not implemented in MVP - entities are auto-created during processing")
async def test_filter_by_entity_type(client: AsyncClient):
    """Test filtering chunks by entity type."""
    # Create project and chunk
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Entity Filter Test"}
    )
    project_id = project_resp.json()["id"]
    
    chunk_resp = await client.post(
        "/api/v1/chunks",
        json={"content": "Test chunk with entities", "project_id": project_id}
    )
    chunk_id = chunk_resp.json()["id"]
    
    # Create error entity
    await client.post(
        f"/api/v1/entities/chunks/{chunk_id}",
        json={
            "entity_type": "error",
            "value": "AuthenticationError",
            "context": "login failed"
        }
    )
    
    # Search filtering by entity type
    response = await client.get("/api/v1/chunks/search?entity_type=error")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] >= 1
    assert any(chunk["id"] == chunk_id for chunk in data["items"])


@pytest.mark.asyncio
@pytest.mark.skip(reason="Entity creation endpoint not implemented in MVP - entities are auto-created during processing")
async def test_filter_by_entity_value(client: AsyncClient):
    """Test filtering chunks by entity value."""
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Entity Value Test"}
    )
    project_id = project_resp.json()["id"]
    
    chunk1_resp = await client.post(
        "/api/v1/chunks",
        json={"content": "Chunk with DatabaseError", "project_id": project_id}
    )
    chunk1_id = chunk1_resp.json()["id"]
    
    await client.post(
        f"/api/v1/entities/chunks/{chunk1_id}",
        json={"entity_type": "error", "value": "DatabaseError", "context": ""}
    )
    
    # Filter by specific entity value
    response = await client.get("/api/v1/chunks/search?entity_value=DatabaseError")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] >= 1
    assert any(chunk["id"] == chunk1_id for chunk in data["items"])


# ============================================================================
# Combined Filter Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.skip(reason="Entity creation endpoint not implemented in MVP - entities are auto-created during processing")
async def test_search_with_entity_filter(client: AsyncClient):
    """Test combining text search with entity filtering."""
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Combined Search Test"}
    )
    project_id = project_resp.json()["id"]
    
    chunk_resp = await client.post(
        "/api/v1/chunks",
        json={"content": "authentication error in production", "project_id": project_id}
    )
    chunk_id = chunk_resp.json()["id"]
    
    await client.post(
        f"/api/v1/entities/chunks/{chunk_id}",
        json={"entity_type": "error", "value": "AuthError", "context": ""}
    )
    
    # Search with both text and entity filter
    response = await client.get(
        "/api/v1/chunks/search?q=authentication&entity_type=error"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_search_response_structure(client: AsyncClient):
    """Test that search response has correct structure."""
    await client.post("/api/v1/chunks", json={"content": "structure test"})
    
    response = await client.get("/api/v1/chunks/search?q=structure")
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)


@pytest.mark.asyncio
async def test_search_pagination(client: AsyncClient):
    """Test that search respects limit and offset."""
    # Create multiple chunks
    for i in range(10):
        await client.post(
            "/api/v1/chunks",
            json={"content": f"searchable content {i}"}
        )
    
    response = await client.get("/api/v1/chunks/search?q=searchable&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 5
    assert data["total"] >= 10
