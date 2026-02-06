"""Tests for Module 2: Entity Extraction and Recursive Compaction."""

import pytest

from backend.app.models import (
    EntityCreate,
    EntityType,
    ProjectCreate,
    ChunkCreate,
    ChunkStatus,
)
from backend.app.core.compactor import CompactorService
from backend.app.db.repository import EntityRepository, ChunkRepository, ProjectRepository


@pytest.mark.asyncio
async def test_entity_repository_create_many(test_db):
    """Test bulk entity creation."""
    entity_repo = EntityRepository(test_db)
    chunk_repo = ChunkRepository(test_db)
    project_repo = ProjectRepository(test_db)
    
    # Setup test data
    project = await project_repo.create(ProjectCreate(name="Test Project"))
    chunk = await chunk_repo.create(
        ChunkCreate(content="Test content", project_id=project.id)
    )
    
    entities = [
        EntityCreate(
            chunk_id=chunk.id,
            project_id=project.id,
            entity_type=EntityType.ERROR,
            value="ConnectionError",
            confidence=0.95,
        ),
        EntityCreate(
            chunk_id=chunk.id,
            project_id=project.id,
            entity_type=EntityType.URL,
            value="https://example.com",
            confidence=0.88,
        ),
    ]
    
    created = await entity_repo.create_many(entities)
    assert len(created) == 2
    assert created[0].entity_type == EntityType.ERROR
    assert created[1].entity_type == EntityType.URL


@pytest.mark.asyncio
async def test_entity_repository_list_by_project(test_db):
    """Test filtering entities by project and type."""
    entity_repo = EntityRepository(test_db)
    chunk_repo = ChunkRepository(test_db)
    project_repo = ProjectRepository(test_db)
    
    project = await project_repo.create(ProjectCreate(name="Test Project"))
    chunk = await chunk_repo.create(
        ChunkCreate(content="Test", project_id=project.id)
    )
    
    # Create mixed entities
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
    
    # Filter by type
    errors = await entity_repo.list_by_project(
        project.id, entity_type=EntityType.ERROR
    )
    assert len(errors) == 2
    
    urls = await entity_repo.list_by_project(
        project.id, entity_type=EntityType.URL
    )
    assert len(urls) == 1
    
    # Filter by confidence
    high_conf = await entity_repo.list_by_project(
        project.id, min_confidence=0.8
    )
    assert len(high_conf) == 1


@pytest.mark.asyncio
async def test_recursive_reduce_small_context(test_db):
    """Test recursive reduce with small context (no recursion needed)."""
    chunk_repo = ChunkRepository(test_db)
    project_repo = ProjectRepository(test_db)
    entity_repo = EntityRepository(test_db)
    
    compactor = CompactorService(chunk_repo, project_repo, entity_repo)
    
    # Small texts that fit in one pass
    texts = [
        "Short summary 1",
        "Short summary 2",
        "Short summary 3",
    ]
    
    # Mock LLM to avoid actual Ollama call
    from unittest.mock import AsyncMock, patch
    
    with patch.object(compactor.llm, 'summarize', new_callable=AsyncMock) as mock_summarize:
        mock_summarize.return_value = "Final combined summary"
        
        result = await compactor.recursive_reduce(texts, depth=1)
        
        # Should call summarize once (no recursion)
        assert mock_summarize.call_count == 1
        assert result == "Final combined summary"


@pytest.mark.asyncio
async def test_recursive_reduce_large_context(test_db):
    """Test recursive reduce with large context (triggers recursion)."""
    chunk_repo = ChunkRepository(test_db)
    project_repo = ProjectRepository(test_db)
    entity_repo = EntityRepository(test_db)
    
    compactor = CompactorService(chunk_repo, project_repo, entity_repo)
    
    # Create texts that exceed MAX_CONTEXT_WINDOW
    # Each text is 3KB, 10 texts = 30KB > 12KB threshold
    large_text = "x" * 3000
    texts = [f"Summary {i}: {large_text}" for i in range(10)]
    
    from unittest.mock import AsyncMock, patch
    
    with patch.object(compactor.llm, 'summarize', new_callable=AsyncMock) as mock_summarize:
        mock_summarize.return_value = "Batch summary"
        
        await compactor.recursive_reduce(texts, depth=1)
        
        # Should call summarize multiple times (batching + final reduce)
        # 10 texts / batch_size(5) = 2 batches + 1 final = 3 calls
        assert mock_summarize.call_count >= 2


@pytest.mark.asyncio
async def test_save_extracted_entities(test_db):
    """Test entity extraction parsing and storage."""
    chunk_repo = ChunkRepository(test_db)
    project_repo = ProjectRepository(test_db)
    entity_repo = EntityRepository(test_db)
    
    compactor = CompactorService(chunk_repo, project_repo, entity_repo)
    
    project = await project_repo.create(ProjectCreate(name="Test"))
    chunk = await chunk_repo.create(
        ChunkCreate(content="Test", project_id=project.id)
    )
    
    # Mock LLM JSON response
    entities_json = {
        "error": ["ConnectionRefused", "Timeout"],
        "url": ["https://docs.example.com"],
        "tool_id": ["docker", "kubectl"],
        "decision": [],
        "code_ref": ["main.py:42"],
    }
    
    await compactor._save_extracted_entities(
        chunk.id, project.id, entities_json
    )
    
    # Verify entities were saved
    saved = await entity_repo.list_by_project(project.id)
    assert len(saved) == 6  # 2 errors + 1 url + 2 tools + 1 code_ref = 6 total
    
    errors = [e for e in saved if e.entity_type == EntityType.ERROR]
    assert len(errors) == 2
    assert any(e.value == "ConnectionRefused" for e in errors)


@pytest.mark.asyncio
async def test_compaction_depth_tracking(test_db):
    """Test that compaction updates depth correctly."""
    chunk_repo = ChunkRepository(test_db)
    project_repo = ProjectRepository(test_db)
    entity_repo = EntityRepository(test_db)
    
    compactor = CompactorService(chunk_repo, project_repo, entity_repo)
    
    project = await project_repo.create(ProjectCreate(name="Depth Test"))
    
    # Create and process chunks
    for i in range(5):
        chunk = await chunk_repo.create(
            ChunkCreate(
                content=f"Content {i}",
                project_id=project.id,
            )
        )
        # Manually mark as PROCESSED with summary
        from backend.app.models import ChunkUpdate
        await chunk_repo.update(
            chunk.id,
            ChunkUpdate(status=ChunkStatus.PROCESSED, summary=f"Summary {i}"),
        )
    
    # Mock LLM
    from unittest.mock import AsyncMock, patch
    
    with patch.object(compactor.llm, 'is_available', new_callable=AsyncMock) as mock_available:
        with patch.object(compactor.llm, 'summarize', new_callable=AsyncMock) as mock_summarize:
            mock_available.return_value = True
            mock_summarize.return_value = "Project summary"
            
            await compactor.compact_project(project.id)
    
    # Check depth was updated
    updated_project = await project_repo.get(project.id)
    assert updated_project.compaction_depth >= 1
    assert updated_project.last_compaction_at is not None
    assert updated_project.context_summary == "Project summary"
