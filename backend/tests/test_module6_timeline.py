"""Tests for Module 6: Timeline endpoint.

Tests the GET /api/v1/chunks/timeline endpoint with
granularity options and project filtering.
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


# --- Timeline Tests ---

class TestTimeline:
    """Test the GET /api/v1/chunks/timeline endpoint."""

    def test_timeline_returns_200(self, client: TestClient):
        """Timeline endpoint returns 200 with correct structure."""
        response = client.get("/api/v1/chunks/timeline")
        assert response.status_code == 200
        data = response.json()
        assert "granularity" in data
        assert "buckets" in data
        assert "total_chunks" in data

    def test_timeline_default_granularity_is_week(self, client: TestClient):
        """Default granularity should be 'week'."""
        response = client.get("/api/v1/chunks/timeline")
        data = response.json()
        assert data["granularity"] == "week"

    def test_timeline_supports_day_granularity(self, client: TestClient):
        """Timeline accepts granularity=day."""
        response = client.get("/api/v1/chunks/timeline?granularity=day")
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "day"

    def test_timeline_supports_month_granularity(self, client: TestClient):
        """Timeline accepts granularity=month."""
        response = client.get("/api/v1/chunks/timeline?granularity=month")
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "month"

    def test_timeline_rejects_invalid_granularity(self, client: TestClient):
        """Timeline rejects invalid granularity values."""
        response = client.get("/api/v1/chunks/timeline?granularity=invalid")
        assert response.status_code == 422

    def test_timeline_empty_returns_empty_buckets(self, client: TestClient):
        """Empty database returns empty buckets list."""
        response = client.get("/api/v1/chunks/timeline")
        data = response.json()
        assert data["buckets"] == []
        assert data["total_chunks"] == 0

    def test_timeline_with_data(self, client: TestClient):
        """Timeline shows chunks grouped by time bucket."""
        # Create chunks
        for i in range(3):
            client.post("/api/v1/chunks", json={
                "content": f"Timeline test chunk {i}",
                "source": "test",
            })

        response = client.get("/api/v1/chunks/timeline")
        data = response.json()
        assert data["total_chunks"] == 3
        assert len(data["buckets"]) >= 1

        # All chunks in current week
        current_bucket = data["buckets"][-1]
        assert current_bucket["chunk_count"] >= 3
        assert "bucket_label" in current_bucket
        assert "by_status" in current_bucket

    def test_timeline_bucket_has_status_breakdown(self, client: TestClient):
        """Each bucket includes by_status breakdown."""
        client.post("/api/v1/chunks", json={
            "content": "Inbox chunk",
            "source": "test",
        })

        response = client.get("/api/v1/chunks/timeline")
        data = response.json()
        bucket = data["buckets"][-1]
        assert "inbox" in bucket["by_status"]

    def test_timeline_with_project_filter(self, client: TestClient):
        """Timeline filters by project_id when provided."""
        # Create project
        proj_response = client.post("/api/v1/projects", json={
            "name": "Timeline Project",
        })
        project_id = proj_response.json()["id"]

        # Create chunk in project
        client.post("/api/v1/chunks", json={
            "content": "Project chunk",
            "project_id": project_id,
            "source": "test",
        })

        # Create chunk without project
        client.post("/api/v1/chunks", json={
            "content": "No project chunk",
            "source": "test",
        })

        response = client.get(f"/api/v1/chunks/timeline?project_id={project_id}")
        data = response.json()
        assert data["total_chunks"] == 1

    def test_timeline_weeks_param(self, client: TestClient):
        """Timeline accepts weeks parameter."""
        response = client.get("/api/v1/chunks/timeline?weeks=4")
        assert response.status_code == 200

    def test_timeline_bucket_has_chunk_ids(self, client: TestClient):
        """Each bucket includes chunk_ids list."""
        client.post("/api/v1/chunks", json={
            "content": "Chunk with ID",
            "source": "test",
        })

        response = client.get("/api/v1/chunks/timeline")
        data = response.json()
        bucket = data["buckets"][-1]
        assert "chunk_ids" in bucket
        assert len(bucket["chunk_ids"]) >= 1
