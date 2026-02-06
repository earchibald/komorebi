"""Tests for Module 6: Enhanced Dashboard Stats.

Tests the enhanced stats endpoint with weekly trends,
insights, and per-project breakdowns.
"""

import pytest_asyncio

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.app.db.database import Base
from backend.app.main import app
from backend.app.db import get_db


# --- Fixtures ---

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a fresh test engine per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine):
    """Create a test session."""
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
def client(test_engine):
    """Create a test client with a clean database."""
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- Enhanced Stats Tests ---

class TestEnhancedStats:
    """Test the enhanced GET /api/v1/chunks/stats endpoint."""

    def test_stats_returns_basic_counters(self, client: TestClient):
        """Stats include inbox, processed, compacted, archived, total."""
        response = client.get("/api/v1/chunks/stats")
        assert response.status_code == 200
        data = response.json()
        assert "inbox" in data
        assert "processed" in data
        assert "compacted" in data
        assert "archived" in data
        assert "total" in data

    def test_stats_returns_weekly_trends(self, client: TestClient):
        """Stats include by_week array with week_start and count."""
        response = client.get("/api/v1/chunks/stats")
        assert response.status_code == 200
        data = response.json()
        assert "by_week" in data
        assert isinstance(data["by_week"], list)
        # Should have up to 8 weeks of data
        assert len(data["by_week"]) <= 8

    def test_stats_returns_insights(self, client: TestClient):
        """Stats include oldest_inbox_age_days, most_active_project, entity_count."""
        response = client.get("/api/v1/chunks/stats")
        assert response.status_code == 200
        data = response.json()
        assert "oldest_inbox_age_days" in data
        assert "most_active_project" in data
        assert "most_active_project_count" in data
        assert "entity_count" in data

    def test_stats_returns_per_project_breakdown(self, client: TestClient):
        """Stats include by_project array."""
        response = client.get("/api/v1/chunks/stats")
        assert response.status_code == 200
        data = response.json()
        assert "by_project" in data
        assert isinstance(data["by_project"], list)

    def test_stats_with_data(self, client: TestClient):
        """Stats reflect actual chunk data."""
        # Create some chunks
        for i in range(3):
            client.post("/api/v1/chunks", json={
                "content": f"Test chunk {i}",
                "tags": ["test"],
                "source": "test",
            })

        response = client.get("/api/v1/chunks/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["inbox"] == 3
        assert data["total"] == 3
        # Week data should include current week
        assert len(data["by_week"]) >= 1
        current_week = data["by_week"][-1]
        assert current_week["count"] >= 3

    def test_stats_oldest_inbox_age(self, client: TestClient):
        """oldest_inbox_age_days reflects the oldest inbox chunk."""
        # Create a chunk — it's immediately in inbox
        client.post("/api/v1/chunks", json={
            "content": "Old inbox chunk",
            "source": "test",
        })

        response = client.get("/api/v1/chunks/stats")
        data = response.json()
        # Chunk just created, age should be 0
        assert data["oldest_inbox_age_days"] == 0

    def test_stats_no_inbox_returns_null_age(self, client: TestClient):
        """oldest_inbox_age_days is null when inbox is empty."""
        response = client.get("/api/v1/chunks/stats")
        data = response.json()
        assert data["oldest_inbox_age_days"] is None

    def test_stats_most_active_project(self, client: TestClient):
        """most_active_project reflects the project with most chunks."""
        # Create a project
        proj_response = client.post("/api/v1/projects", json={
            "name": "Active Project",
        })
        project_id = proj_response.json()["id"]

        # Create chunks in the project
        for i in range(3):
            client.post("/api/v1/chunks", json={
                "content": f"Project chunk {i}",
                "project_id": project_id,
                "source": "test",
            })

        response = client.get("/api/v1/chunks/stats")
        data = response.json()
        assert data["most_active_project"] == "Active Project"
        assert data["most_active_project_count"] == 3

    def test_stats_entity_count(self, client: TestClient):
        """entity_count reflects total entities extracted."""
        response = client.get("/api/v1/chunks/stats")
        data = response.json()
        assert data["entity_count"] == 0  # No entities yet
