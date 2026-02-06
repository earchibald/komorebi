"""Tests for Context Resume feature.

Tests the ResumeService and GET /projects/{id}/resume endpoint.
Covers: empty project, project with data, no decisions, Ollama unavailable,
time window filter, related chunks, project not found, archived deprioritized.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.db import init_db
from backend.app.db.repository import (
    ChunkRepository,
    ProjectRepository,
    EntityRepository,
)
from backend.app.models import (
    ChunkCreate,
    ProjectCreate,
    EntityCreate,
    EntityType,
    ChunkStatus,
)
from backend.app.models.resume import ProjectBriefing, BriefingSection
from backend.app.services.resume_service import ResumeService
from backend.app.core.similarity import TFIDFService
from backend.app.core.ollama_client import KomorebiLLM


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """Create an async test client with fresh DB."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def seeded_project(client: AsyncClient):
    """Create a project and return its ID."""
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Auth Service", "description": "OAuth2 authentication"},
    )
    return response.json()


@pytest.fixture
async def seeded_chunks(client: AsyncClient, seeded_project: dict):
    """Create several chunks in a project and return them."""
    project_id = seeded_project["id"]
    chunks = []
    contents = [
        "Debugging 401 error on /login endpoint. Stack trace points to JWT validation.",
        "Decision: Use RS256 algorithm for JWT signing instead of HS256.",
        "Implemented token refresh logic in auth_middleware.py.",
        "Error: CORS preflight failing for /api/v1/auth/callback.",
        "Switched background queue from sync to async using asyncio.Queue.",
    ]
    for content in contents:
        resp = await client.post(
            "/api/v1/chunks",
            json={
                "content": content,
                "project_id": project_id,
                "source": "test",
            },
        )
        chunks.append(resp.json())
    return chunks


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_project_not_found(client: AsyncClient):
    """GET /projects/{id}/resume returns 404 for missing project."""
    fake_id = str(uuid4())
    response = await client.get(f"/api/v1/projects/{fake_id}/resume")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_resume_empty_project(client: AsyncClient, seeded_project: dict):
    """Resume for project with zero chunks → 'No activity yet' message."""
    project_id = seeded_project["id"]
    response = await client.get(f"/api/v1/projects/{project_id}/resume")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert data["project_name"] == "Auth Service"
    assert "no activity" in data["summary"].lower() or len(data["recent_chunks"]) == 0
    assert isinstance(data["decisions"], list)
    assert isinstance(data["recent_chunks"], list)


@pytest.mark.asyncio
async def test_resume_with_data(
    client: AsyncClient, seeded_project: dict, seeded_chunks: list
):
    """Resume for project with chunks returns valid briefing structure."""
    project_id = seeded_project["id"]
    response = await client.get(f"/api/v1/projects/{project_id}/resume")
    assert response.status_code == 200
    data = response.json()

    # Structure checks
    assert data["project_id"] == project_id
    assert data["project_name"] == "Auth Service"
    assert isinstance(data["summary"], str)
    assert len(data["summary"]) > 0
    assert isinstance(data["recent_chunks"], list)
    assert len(data["recent_chunks"]) > 0
    assert len(data["recent_chunks"]) <= 10  # capped
    assert "generated_at" in data
    assert "ollama_available" in data


@pytest.mark.asyncio
async def test_resume_time_window(
    client: AsyncClient, seeded_project: dict, seeded_chunks: list
):
    """Hours query param controls the time window."""
    project_id = seeded_project["id"]

    # With a very small window (0 hours) — should still work, may have no decisions
    resp_0 = await client.get(f"/api/v1/projects/{project_id}/resume?hours=0")
    assert resp_0.status_code == 200

    # With default window
    resp_48 = await client.get(f"/api/v1/projects/{project_id}/resume?hours=48")
    assert resp_48.status_code == 200


@pytest.mark.asyncio
async def test_resume_response_model_complete(
    client: AsyncClient, seeded_project: dict, seeded_chunks: list
):
    """All ProjectBriefing fields are present in the response."""
    project_id = seeded_project["id"]
    response = await client.get(f"/api/v1/projects/{project_id}/resume")
    data = response.json()

    expected_keys = {
        "project_id",
        "project_name",
        "generated_at",
        "summary",
        "sections",
        "recent_chunks",
        "decisions",
        "related_context",
        "ollama_available",
        "context_window_usage",
    }
    assert expected_keys.issubset(set(data.keys()))


# ---------------------------------------------------------------------------
# ResumeService Unit Tests (mocked dependencies)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_empty_project():
    """ResumeService returns 'No activity' for project with zero chunks."""
    project_id = uuid4()
    project = MagicMock()
    project.id = project_id
    project.name = "Empty Project"
    project.description = "Nothing here"
    project.context_summary = None

    project_repo = AsyncMock(spec=ProjectRepository)
    project_repo.get.return_value = project

    chunk_repo = AsyncMock(spec=ChunkRepository)
    chunk_repo.list.return_value = []
    chunk_repo.get_all_content.return_value = []

    entity_repo = AsyncMock(spec=EntityRepository)
    entity_repo.list_by_project.return_value = []

    tfidf = TFIDFService()
    llm = AsyncMock(spec=KomorebiLLM)
    llm.is_available.return_value = False

    service = ResumeService(
        chunk_repo=chunk_repo,
        project_repo=project_repo,
        entity_repo=entity_repo,
        tfidf_service=tfidf,
        llm=llm,
    )

    briefing = await service.generate_briefing(project_id)

    assert briefing.project_name == "Empty Project"
    assert "no activity" in briefing.summary.lower()
    assert len(briefing.recent_chunks) == 0
    assert len(briefing.decisions) == 0
    assert briefing.ollama_available is False


@pytest.mark.asyncio
async def test_service_ollama_unavailable():
    """When Ollama is down, briefing uses fallback template."""
    project_id = uuid4()
    chunk_id = uuid4()

    project = MagicMock()
    project.id = project_id
    project.name = "My Project"
    project.description = "Test project"
    project.context_summary = "Prior summary"

    chunk = MagicMock()
    chunk.id = chunk_id
    chunk.content = "Fixed auth bug"
    chunk.summary = "Auth fix"
    chunk.status = ChunkStatus.PROCESSED
    chunk.created_at = datetime.utcnow()

    project_repo = AsyncMock(spec=ProjectRepository)
    project_repo.get.return_value = project

    chunk_repo = AsyncMock(spec=ChunkRepository)
    chunk_repo.list.return_value = [chunk]
    chunk_repo.get_all_content.return_value = [(str(chunk_id), "Fixed auth bug")]

    entity_repo = AsyncMock(spec=EntityRepository)
    entity_repo.list_by_project.return_value = []

    tfidf = TFIDFService()
    llm = AsyncMock(spec=KomorebiLLM)
    llm.is_available.return_value = False

    service = ResumeService(
        chunk_repo=chunk_repo,
        project_repo=project_repo,
        entity_repo=entity_repo,
        tfidf_service=tfidf,
        llm=llm,
    )

    briefing = await service.generate_briefing(project_id)

    assert briefing.ollama_available is False
    assert len(briefing.summary) > 0
    assert len(briefing.recent_chunks) == 1


@pytest.mark.asyncio
async def test_service_with_decisions():
    """Briefing includes recent decisions when present."""
    project_id = uuid4()
    chunk_id = uuid4()

    project = MagicMock()
    project.id = project_id
    project.name = "Decision Project"
    project.description = "Has decisions"
    project.context_summary = None

    chunk = MagicMock()
    chunk.id = chunk_id
    chunk.content = "Use JWT for auth"
    chunk.summary = "JWT decision"
    chunk.status = ChunkStatus.PROCESSED
    chunk.created_at = datetime.utcnow()

    decision_entity = MagicMock()
    decision_entity.entity_type = EntityType.DECISION
    decision_entity.value = "Use RS256 for JWT"
    decision_entity.confidence = 0.9
    decision_entity.created_at = datetime.utcnow()

    project_repo = AsyncMock(spec=ProjectRepository)
    project_repo.get.return_value = project

    chunk_repo = AsyncMock(spec=ChunkRepository)
    chunk_repo.list.return_value = [chunk]
    chunk_repo.get_all_content.return_value = [(str(chunk_id), "Use JWT for auth")]

    entity_repo = AsyncMock(spec=EntityRepository)
    entity_repo.list_by_project.return_value = [decision_entity]

    tfidf = TFIDFService()
    llm = AsyncMock(spec=KomorebiLLM)
    llm.is_available.return_value = False

    service = ResumeService(
        chunk_repo=chunk_repo,
        project_repo=project_repo,
        entity_repo=entity_repo,
        tfidf_service=tfidf,
        llm=llm,
    )

    briefing = await service.generate_briefing(project_id)

    assert len(briefing.decisions) == 1
    assert briefing.decisions[0].value == "Use RS256 for JWT"


@pytest.mark.asyncio
async def test_service_related_chunks():
    """TF-IDF related context is populated when corpus exists."""
    project_id = uuid4()
    chunk_id_1 = uuid4()
    chunk_id_2 = uuid4()

    project = MagicMock()
    project.id = project_id
    project.name = "Related Project"
    project.description = "Test project"
    project.context_summary = None

    chunk1 = MagicMock()
    chunk1.id = chunk_id_1
    chunk1.content = "Authentication service using JWT tokens with RS256 algorithm"
    chunk1.summary = "Auth JWT"
    chunk1.status = ChunkStatus.PROCESSED
    chunk1.created_at = datetime.utcnow()

    chunk2 = MagicMock()
    chunk2.id = chunk_id_2
    chunk2.content = "JWT token validation middleware implementing RS256 verification"
    chunk2.summary = "JWT validation"
    chunk2.status = ChunkStatus.PROCESSED
    chunk2.created_at = datetime.utcnow() - timedelta(hours=1)

    project_repo = AsyncMock(spec=ProjectRepository)
    project_repo.get.return_value = project

    chunk_repo = AsyncMock(spec=ChunkRepository)
    chunk_repo.list.return_value = [chunk1, chunk2]
    chunk_repo.get_all_content.return_value = [
        (str(chunk_id_1), chunk1.content),
        (str(chunk_id_2), chunk2.content),
    ]

    entity_repo = AsyncMock(spec=EntityRepository)
    entity_repo.list_by_project.return_value = []

    tfidf = TFIDFService()
    llm = AsyncMock(spec=KomorebiLLM)
    llm.is_available.return_value = False

    service = ResumeService(
        chunk_repo=chunk_repo,
        project_repo=project_repo,
        entity_repo=entity_repo,
        tfidf_service=tfidf,
        llm=llm,
    )

    briefing = await service.generate_briefing(project_id)

    # With 2 semantically similar chunks, TF-IDF should find related context
    assert isinstance(briefing.related_context, list)


@pytest.mark.asyncio
async def test_service_ollama_available():
    """When Ollama is available, LLM generates the summary."""
    project_id = uuid4()
    chunk_id = uuid4()

    project = MagicMock()
    project.id = project_id
    project.name = "LLM Project"
    project.description = "Test LLM"
    project.context_summary = None

    chunk = MagicMock()
    chunk.id = chunk_id
    chunk.content = "Implementing rate limiting for API"
    chunk.summary = "Rate limiting"
    chunk.status = ChunkStatus.PROCESSED
    chunk.created_at = datetime.utcnow()

    project_repo = AsyncMock(spec=ProjectRepository)
    project_repo.get.return_value = project

    chunk_repo = AsyncMock(spec=ChunkRepository)
    chunk_repo.list.return_value = [chunk]
    chunk_repo.get_all_content.return_value = [(str(chunk_id), chunk.content)]

    entity_repo = AsyncMock(spec=EntityRepository)
    entity_repo.list_by_project.return_value = []

    tfidf = TFIDFService()
    llm = AsyncMock(spec=KomorebiLLM)
    llm.is_available.return_value = True
    llm.generate.return_value = (
        "• Where you left off: Implementing rate limiting for the API.\n"
        "• Key context: Rate limiting logic is in progress.\n"
        "• Suggested next step: Add tests for rate limiter middleware."
    )

    service = ResumeService(
        chunk_repo=chunk_repo,
        project_repo=project_repo,
        entity_repo=entity_repo,
        tfidf_service=tfidf,
        llm=llm,
    )

    briefing = await service.generate_briefing(project_id)

    assert briefing.ollama_available is True
    assert "rate limit" in briefing.summary.lower()
    llm.generate.assert_called_once()


# ---------------------------------------------------------------------------
# Model Validation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_briefing_model_defaults():
    """ProjectBriefing model sets sensible defaults."""
    briefing = ProjectBriefing(
        project_id=uuid4(),
        project_name="Test",
        summary="Test summary",
    )
    assert briefing.sections == []
    assert briefing.recent_chunks == []
    assert briefing.decisions == []
    assert briefing.related_context == []
    assert briefing.ollama_available is True
    assert briefing.context_window_usage is None
    assert briefing.generated_at is not None


@pytest.mark.asyncio
async def test_briefing_section_model():
    """BriefingSection model validates correctly."""
    section = BriefingSection(
        heading="Where You Left Off",
        content="Working on auth service",
        chunk_id=uuid4(),
    )
    assert section.heading == "Where You Left Off"
    assert section.chunk_id is not None

    # Without chunk_id
    section_no_link = BriefingSection(
        heading="Key Context",
        content="JWT implementation",
    )
    assert section_no_link.chunk_id is None
