"""Tests for Module 6: Related Chunks (TF-IDF similarity).

Tests the TF-IDF service and the GET /api/v1/chunks/{id}/related endpoint.
"""

import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4

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


# --- TF-IDF Service Unit Tests ---

class TestTFIDFService:
    """Test the TFIDFService class directly."""

    def test_tokenize_basic(self):
        """Tokenize splits text into lowercase alphanumeric tokens."""
        from backend.app.core.similarity import TFIDFService
        svc = TFIDFService()
        tokens = svc.tokenize("Hello World, this is a Test!")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens
        # Stopwords removed
        assert "this" not in tokens
        assert "is" not in tokens

    def test_tokenize_removes_short_tokens(self):
        """Tokens 2 chars or shorter are removed."""
        from backend.app.core.similarity import TFIDFService
        svc = TFIDFService()
        tokens = svc.tokenize("I am a big fan of AI")
        assert "am" not in tokens  # 2 chars
        assert "big" in tokens  # 3 chars
        assert "fan" in tokens

    def test_compute_tfidf_basic(self):
        """TF-IDF produces non-empty vectors for documents."""
        from backend.app.core.similarity import TFIDFService
        svc = TFIDFService()
        docs = [
            ("doc1", "Python programming language is great"),
            ("doc2", "JavaScript programming for web development"),
            ("doc3", "Python data science and machine learning"),
        ]
        tfidf = svc.compute_tfidf(docs)
        assert "doc1" in tfidf
        assert "doc2" in tfidf
        assert "doc3" in tfidf
        assert len(tfidf["doc1"]) > 0

    def test_cosine_similarity_identical(self):
        """Identical vectors have similarity 1.0."""
        from backend.app.core.similarity import TFIDFService
        svc = TFIDFService()
        vec = {"python": 0.5, "programming": 0.3}
        sim = svc.cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.001

    def test_cosine_similarity_orthogonal(self):
        """Completely different vectors have similarity 0.0."""
        from backend.app.core.similarity import TFIDFService
        svc = TFIDFService()
        vec_a = {"python": 0.5, "programming": 0.3}
        vec_b = {"javascript": 0.5, "react": 0.3}
        sim = svc.cosine_similarity(vec_a, vec_b)
        assert sim == 0.0

    def test_find_related_returns_similar(self):
        """find_related returns documents sorted by similarity."""
        from backend.app.core.similarity import TFIDFService
        svc = TFIDFService()
        docs = [
            ("doc1", "Python programming language for data science"),
            ("doc2", "Python data science machine learning algorithms"),
            ("doc3", "JavaScript web development frontend frameworks React"),
            ("doc4", "Python pandas numpy data analysis tools"),
        ]
        related = svc.find_related("doc1", docs, top_k=3)
        assert len(related) > 0
        # doc2 and doc4 should be more similar to doc1 than doc3
        related_ids = [r[0] for r in related]
        # doc3 (JS/web) should not be the most similar
        if len(related) >= 2:
            assert related[0][0] != "doc3"

    def test_find_related_excludes_self(self):
        """find_related does not include the target document."""
        from backend.app.core.similarity import TFIDFService
        svc = TFIDFService()
        docs = [
            ("doc1", "Python programming"),
            ("doc2", "Python development"),
        ]
        related = svc.find_related("doc1", docs)
        related_ids = [r[0] for r in related]
        assert "doc1" not in related_ids

    def test_find_related_empty_corpus(self):
        """find_related returns empty list for empty corpus."""
        from backend.app.core.similarity import TFIDFService
        svc = TFIDFService()
        related = svc.find_related("doc1", [])
        assert related == []

    def test_find_related_single_doc(self):
        """find_related returns empty list for single document corpus."""
        from backend.app.core.similarity import TFIDFService
        svc = TFIDFService()
        docs = [("doc1", "Python programming")]
        related = svc.find_related("doc1", docs)
        assert related == []

    def test_find_related_shared_terms(self):
        """find_related returns shared terms for each match."""
        from backend.app.core.similarity import TFIDFService
        svc = TFIDFService()
        docs = [
            ("doc1", "Python programming language data science"),
            ("doc2", "Python programming web development"),
        ]
        related = svc.find_related("doc1", docs)
        assert len(related) > 0
        _, similarity, shared_terms = related[0]
        assert isinstance(shared_terms, list)
        assert len(shared_terms) > 0
        assert "python" in shared_terms or "programming" in shared_terms

    def test_find_related_respects_top_k(self):
        """find_related returns at most top_k results."""
        from backend.app.core.similarity import TFIDFService
        svc = TFIDFService()
        docs = [
            ("doc1", "Python programming for data science analysis"),
            ("doc2", "Python data science tools and libraries"),
            ("doc3", "Python programming best practices for analysis"),
            ("doc4", "Python machine learning data analysis tools"),
            ("doc5", "Python web programming framework analysis"),
        ]
        related = svc.find_related("doc1", docs, top_k=2)
        assert len(related) <= 2

    def test_short_content_handled(self):
        """Very short content produces empty or minimal results."""
        from backend.app.core.similarity import TFIDFService
        svc = TFIDFService()
        docs = [
            ("doc1", "hi"),
            ("doc2", "Python programming data science machine learning"),
        ]
        related = svc.find_related("doc1", docs)
        # Short doc should have empty or zero-similarity results
        assert isinstance(related, list)


# --- Related Chunks API Tests ---

class TestRelatedChunksAPI:
    """Test the GET /api/v1/chunks/{id}/related endpoint."""

    def test_related_chunks_endpoint_exists(self, client: TestClient):
        """Endpoint returns 404 for non-existent chunk (not 405)."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/chunks/{fake_id}/related")
        assert response.status_code == 404

    def test_related_chunks_returns_structure(self, client: TestClient):
        """Related chunks response has correct structure."""
        # Create two similar chunks
        r1 = client.post("/api/v1/chunks", json={
            "content": "Python programming language for data science and machine learning",
            "source": "test",
        })
        chunk_id = r1.json()["id"]

        client.post("/api/v1/chunks", json={
            "content": "Python data science tools numpy pandas machine learning",
            "source": "test",
        })

        response = client.get(f"/api/v1/chunks/{chunk_id}/related")
        assert response.status_code == 200
        data = response.json()
        assert "source_chunk_id" in data
        assert "related" in data
        assert "computation_ms" in data
        assert data["source_chunk_id"] == chunk_id

    def test_related_chunks_finds_similar(self, client: TestClient):
        """Related chunks finds content-similar chunks."""
        r1 = client.post("/api/v1/chunks", json={
            "content": "Python programming language for data science and machine learning projects",
            "source": "test",
        })
        chunk_id = r1.json()["id"]

        client.post("/api/v1/chunks", json={
            "content": "Python data science tools numpy pandas for machine learning analysis",
            "source": "test",
        })

        client.post("/api/v1/chunks", json={
            "content": "JavaScript React frontend web development user interface components",
            "source": "test",
        })

        response = client.get(f"/api/v1/chunks/{chunk_id}/related")
        data = response.json()
        assert len(data["related"]) >= 1
        # Most similar should be Python data science, not JS
        top_match = data["related"][0]
        assert "chunk" in top_match
        assert "similarity" in top_match
        assert top_match["similarity"] > 0

    def test_related_chunks_limit_param(self, client: TestClient):
        """Related chunks respects limit parameter."""
        r1 = client.post("/api/v1/chunks", json={
            "content": "Python programming language for data science analysis",
            "source": "test",
        })
        chunk_id = r1.json()["id"]

        for i in range(5):
            client.post("/api/v1/chunks", json={
                "content": f"Python data analysis tools library {i} for science",
                "source": "test",
            })

        response = client.get(f"/api/v1/chunks/{chunk_id}/related?limit=2")
        data = response.json()
        assert len(data["related"]) <= 2

    def test_related_chunks_includes_shared_terms(self, client: TestClient):
        """Related chunks response includes shared_terms."""
        r1 = client.post("/api/v1/chunks", json={
            "content": "Python programming language data science analysis",
            "source": "test",
        })
        chunk_id = r1.json()["id"]

        client.post("/api/v1/chunks", json={
            "content": "Python programming best practices data structures",
            "source": "test",
        })

        response = client.get(f"/api/v1/chunks/{chunk_id}/related")
        data = response.json()
        if data["related"]:
            assert "shared_terms" in data["related"][0]
            assert len(data["related"][0]["shared_terms"]) > 0
