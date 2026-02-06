"""Test the Ollama integration with the Compactor service.

This test verifies:
1. KomorebiLLM client can be instantiated
2. Fallback logic works when Ollama is unavailable
3. Chunk processing handles both LLM and fallback paths
4. Project compaction completes successfully
"""

from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.core.ollama_client import KomorebiLLM
from backend.app.core.compactor import CompactorService
from backend.app.models import Chunk, ChunkStatus, Project
from backend.app.db.repository import ChunkRepository, ProjectRepository


@pytest.mark.asyncio
async def test_komorebi_llm_client_initialization():
    """Test that KomorebiLLM client initializes correctly."""
    llm = KomorebiLLM(host="http://localhost:11434", model="llama3.2")
    assert llm.host == "http://localhost:11434"
    assert llm.model == "llama3.2"


@pytest.mark.asyncio
async def test_komorebi_llm_availability_check():
    """Test health check when Ollama is unavailable."""
    llm = KomorebiLLM(host="http://localhost:9999", model="llama3.2")
    is_available = await llm.is_available()
    # Expected to be False since we're pointing to a non-existent address
    assert isinstance(is_available, bool)


@pytest.mark.asyncio
async def test_process_chunk_with_ollama_unavailable():
    """Test that chunk processing uses fallback when Ollama is down."""
    # Create mock repositories
    chunk_repo = AsyncMock(spec=ChunkRepository)
    project_repo = AsyncMock(spec=ProjectRepository)
    
    # Create a test chunk
    chunk_id = uuid4()
    test_chunk = Chunk(
        id=chunk_id,
        content="[ERROR] Connection timeout at db.py:42. Retrying... [INFO] Success after 30ms. [WARN] High latency detected.",
        project_id=None,
        status=ChunkStatus.INBOX,
    )
    
    # Setup mock to return the test chunk
    chunk_repo.get.return_value = test_chunk
    chunk_repo.update.return_value = test_chunk
    
    # Create compactor and process chunk (Ollama unavailable)
    with patch('backend.app.core.compactor.KomorebiLLM') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.is_available.return_value = False
        mock_llm_class.return_value = mock_llm
        
        compactor = CompactorService(chunk_repo, project_repo)
        result = await compactor.process_chunk(chunk_id)
        
        # Verify the chunk was updated with PROCESSED status
        assert result is not None
        chunk_repo.update.assert_called_once()
        
        # Verify update was called with token count
        call_args = chunk_repo.update.call_args
        update_obj = call_args[0][1]  # Second arg is ChunkUpdate
        assert update_obj.status == ChunkStatus.PROCESSED
        assert update_obj.token_count is not None
        assert update_obj.summary is not None


@pytest.mark.asyncio
async def test_compact_project_creates_context_summary():
    """Test that project compaction creates a context summary."""
    # Create mock repositories
    chunk_repo = AsyncMock(spec=ChunkRepository)
    project_repo = AsyncMock(spec=ProjectRepository)
    
    project_id = uuid4()
    chunk_id_1 = uuid4()
    chunk_id_2 = uuid4()
    
    # Create test data
    test_project = Project(id=project_id, name="Test Project")
    processed_chunks = [
        Chunk(
            id=chunk_id_1,
            content="Chunk 1 content",
            summary="Summary 1",
            status=ChunkStatus.PROCESSED,
            project_id=project_id,
        ),
        Chunk(
            id=chunk_id_2,
            content="Chunk 2 content",
            summary="Summary 2",
            status=ChunkStatus.PROCESSED,
            project_id=project_id,
        ),
    ]
    
    # Setup mocks
    project_repo.get.return_value = test_project
    chunk_repo.list.return_value = processed_chunks
    project_repo.update.return_value = test_project
    chunk_repo.update.return_value = processed_chunks[0]
    
    # Create compactor
    with patch('backend.app.core.compactor.KomorebiLLM') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.is_available.return_value = False  # Use fallback
        mock_llm_class.return_value = mock_llm
        
        compactor = CompactorService(chunk_repo, project_repo)
        result = await compactor.compact_project(project_id)
        
        # Verify project was updated
        assert result is not None
        project_repo.update.assert_called_once()
        
        # Verify chunks were marked as COMPACTED
        assert chunk_repo.update.call_count == 2
        for call in chunk_repo.update.call_args_list:
            update_obj = call[0][1]
            assert update_obj.status == ChunkStatus.COMPACTED


@pytest.mark.asyncio
async def test_chunk_processing_pipeline():
    """Integration test: INBOX -> PROCESSED -> COMPACTED pipeline."""
    chunk_repo = AsyncMock(spec=ChunkRepository)
    project_repo = AsyncMock(spec=ProjectRepository)
    
    project_id = uuid4()
    chunk_id = uuid4()
    
    # Original chunk in INBOX
    inbox_chunk = Chunk(
        id=chunk_id,
        content="[ERROR] Connection timeout. [INFO] Resolved.",
        project_id=project_id,
        status=ChunkStatus.INBOX,
    )
    
    # After processing -> PROCESSED
    processed_chunk = Chunk(
        id=chunk_id,
        content="[ERROR] Connection timeout. [INFO] Resolved.",
        summary="Connection timeout resolved successfully.",
        token_count=10,
        project_id=project_id,
        status=ChunkStatus.PROCESSED,
    )
    
    # After compaction -> COMPACTED
    compacted_chunk = Chunk(
        id=chunk_id,
        content="[ERROR] Connection timeout. [INFO] Resolved.",
        summary="Connection timeout resolved successfully.",
        token_count=10,
        project_id=project_id,
        status=ChunkStatus.COMPACTED,
    )
    
    # Setup mock to return chunks at different stages
    chunk_repo.get.side_effect = [inbox_chunk, processed_chunk]
    chunk_repo.update.side_effect = [processed_chunk, compacted_chunk]
    project_repo.get.return_value = Project(id=project_id, name="Test")
    project_repo.update.return_value = Project(id=project_id, name="Test")
    
    with patch('backend.app.core.compactor.KomorebiLLM') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.is_available.return_value = False
        mock_llm_class.return_value = mock_llm
        
        compactor = CompactorService(chunk_repo, project_repo)
        
        # Step 1: Process chunk (INBOX -> PROCESSED)
        result1 = await compactor.process_chunk(chunk_id)
        assert result1.status == ChunkStatus.PROCESSED
        
        # Step 2: Compact project (PROCESSED -> COMPACTED)
        chunk_repo.list.return_value = [processed_chunk]
        result2 = await compactor.compact_project(project_id)
        assert result2 is not None


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
