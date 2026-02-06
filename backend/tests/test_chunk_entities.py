"""Tests for chunk-level entity endpoints and repository methods.

TDD Step 1 (Red): Tests for the Chunk Detail Drawer backend support.
- EntityRepository.list_by_chunk() - filter entities by chunk_id
- GET /entities/chunks/{chunk_id} - API endpoint
"""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.db import init_db
from backend.app.models import (
    Entity,
    EntityCreate,
    EntityType,
    ProjectCreate,
    ChunkCreate,
)
from backend.app.db.repository import EntityRepository, ChunkRepository, ProjectRepository


@pytest.fixture
async def client():
    """Create an async test client."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================================================
# Repository Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_by_chunk_returns_entities(test_db):
    """Test that list_by_chunk returns entities for a specific chunk."""
    entity_repo = EntityRepository(test_db)
    chunk_repo = ChunkRepository(test_db)
    project_repo = ProjectRepository(test_db)

    project = await project_repo.create(ProjectCreate(name="Test Project"))
    chunk = await chunk_repo.create(
        ChunkCreate(content="Test content with errors", project_id=project.id)
    )

    entities = [
        EntityCreate(
            chunk_id=chunk.id,
            project_id=project.id,
            entity_type=EntityType.ERROR,
            value="ConnectionError",
            confidence=0.95,
            context_snippet="ConnectionError: refused at port 5432",
        ),
        EntityCreate(
            chunk_id=chunk.id,
            project_id=project.id,
            entity_type=EntityType.URL,
            value="https://example.com",
            confidence=0.88,
        ),
    ]
    await entity_repo.create_many(entities)

    result = await entity_repo.list_by_chunk(chunk.id)
    assert len(result) == 2
    assert all(isinstance(e, Entity) for e in result)
    assert {e.entity_type for e in result} == {EntityType.ERROR, EntityType.URL}


@pytest.mark.asyncio
async def test_list_by_chunk_filters_by_type(test_db):
    """Test that list_by_chunk can filter by entity type."""
    entity_repo = EntityRepository(test_db)
    chunk_repo = ChunkRepository(test_db)
    project_repo = ProjectRepository(test_db)

    project = await project_repo.create(ProjectCreate(name="Test Project"))
    chunk = await chunk_repo.create(
        ChunkCreate(content="Test content", project_id=project.id)
    )

    entities = [
        EntityCreate(
            chunk_id=chunk.id,
            project_id=project.id,
            entity_type=EntityType.ERROR,
            value="Error 1",
            confidence=0.9,
        ),
        EntityCreate(
            chunk_id=chunk.id,
            project_id=project.id,
            entity_type=EntityType.URL,
            value="http://test.com",
            confidence=0.7,
        ),
        EntityCreate(
            chunk_id=chunk.id,
            project_id=project.id,
            entity_type=EntityType.ERROR,
            value="Error 2",
            confidence=0.5,
        ),
    ]
    await entity_repo.create_many(entities)

    errors = await entity_repo.list_by_chunk(chunk.id, entity_type=EntityType.ERROR)
    assert len(errors) == 2

    urls = await entity_repo.list_by_chunk(chunk.id, entity_type=EntityType.URL)
    assert len(urls) == 1


@pytest.mark.asyncio
async def test_list_by_chunk_empty_for_no_entities(test_db):
    """Test that list_by_chunk returns empty list when chunk has no entities."""
    entity_repo = EntityRepository(test_db)
    chunk_repo = ChunkRepository(test_db)
    project_repo = ProjectRepository(test_db)

    project = await project_repo.create(ProjectCreate(name="Test Project"))
    chunk = await chunk_repo.create(
        ChunkCreate(content="No entities here", project_id=project.id)
    )

    result = await entity_repo.list_by_chunk(chunk.id)
    assert result == []


@pytest.mark.asyncio
async def test_list_by_chunk_isolates_by_chunk(test_db):
    """Test that list_by_chunk only returns entities for the specified chunk."""
    entity_repo = EntityRepository(test_db)
    chunk_repo = ChunkRepository(test_db)
    project_repo = ProjectRepository(test_db)

    project = await project_repo.create(ProjectCreate(name="Test Project"))
    chunk_a = await chunk_repo.create(
        ChunkCreate(content="Chunk A", project_id=project.id)
    )
    chunk_b = await chunk_repo.create(
        ChunkCreate(content="Chunk B", project_id=project.id)
    )

    await entity_repo.create_many([
        EntityCreate(
            chunk_id=chunk_a.id,
            project_id=project.id,
            entity_type=EntityType.ERROR,
            value="Error in A",
            confidence=0.9,
        ),
        EntityCreate(
            chunk_id=chunk_b.id,
            project_id=project.id,
            entity_type=EntityType.URL,
            value="http://b.com",
            confidence=0.8,
        ),
    ])

    result_a = await entity_repo.list_by_chunk(chunk_a.id)
    assert len(result_a) == 1
    assert result_a[0].value == "Error in A"

    result_b = await entity_repo.list_by_chunk(chunk_b.id)
    assert len(result_b) == 1
    assert result_b[0].value == "http://b.com"


# ============================================================================
# API Endpoint Tests
# ============================================================================


@pytest.mark.asyncio
async def test_api_list_chunk_entities(client):
    """Test GET /entities/chunks/{chunk_id} returns entities."""
    # Create a project and chunk
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "API Test Project"},
    )
    project_id = project_resp.json()["id"]

    chunk_resp = await client.post(
        "/api/v1/chunks",
        json={"content": "Test content for entity API", "project_id": project_id},
    )
    chunk_id = chunk_resp.json()["id"]

    # Fetch entities (should be empty since no processing happened)
    response = await client.get(f"/api/v1/entities/chunks/{chunk_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_api_list_chunk_entities_with_type_filter(client):
    """Test GET /entities/chunks/{chunk_id}?entity_type=error filters correctly."""
    # Create project and chunk
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Filter Test"},
    )
    project_id = project_resp.json()["id"]

    chunk_resp = await client.post(
        "/api/v1/chunks",
        json={"content": "Filter test content", "project_id": project_id},
    )
    chunk_id = chunk_resp.json()["id"]

    response = await client.get(
        f"/api/v1/entities/chunks/{chunk_id}?entity_type=error"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
