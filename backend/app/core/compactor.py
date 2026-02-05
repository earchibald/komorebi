"""Compactor service for recursive summarization.

Implements the "Recursive Compactor" pattern:
- Treats memory as a pyramid
- Instead of forgetting, we summarize
- Map-reduce summarization for large context
"""

import asyncio
from typing import Optional
from uuid import UUID

from ..models import Chunk, ChunkStatus, ChunkUpdate
from ..db.repository import ChunkRepository, ProjectRepository


class CompactorService:
    """Service for compacting chunks into summaries.
    
    The compactor processes chunks through several stages:
    1. INBOX -> PROCESSED: Initial analysis and enrichment
    2. PROCESSED -> COMPACTED: Summarization into higher-level context
    
    For now, this uses a simple text-based summarization.
    In production, this would integrate with Ollama or another LLM.
    """
    
    def __init__(
        self,
        chunk_repo: ChunkRepository,
        project_repo: ProjectRepository,
    ):
        self.chunk_repo = chunk_repo
        self.project_repo = project_repo
    
    async def process_chunk(self, chunk_id: UUID) -> Optional[Chunk]:
        """Process a single chunk from INBOX to PROCESSED status.
        
        In a full implementation, this would:
        1. Tokenize the content
        2. Generate a summary using LLM
        3. Extract tags and entities
        4. Update token count
        """
        chunk = await self.chunk_repo.get(chunk_id)
        if not chunk or chunk.status != ChunkStatus.INBOX:
            return None
        
        # Simple token count estimation (roughly 4 chars per token)
        token_count = len(chunk.content) // 4
        
        # Generate a simple summary (in production, use LLM)
        summary = self._generate_simple_summary(chunk.content)
        
        update = ChunkUpdate(
            status=ChunkStatus.PROCESSED,
            summary=summary,
            token_count=token_count,
        )
        
        return await self.chunk_repo.update(chunk_id, update)
    
    async def compact_project(self, project_id: UUID) -> Optional[str]:
        """Compact all processed chunks in a project into a context summary.
        
        Uses map-reduce pattern:
        1. Map: Summarize each chunk
        2. Reduce: Combine summaries into project context
        """
        project = await self.project_repo.get(project_id)
        if not project:
            return None
        
        # Get all processed chunks for this project
        chunks = await self.chunk_repo.list(
            status=ChunkStatus.PROCESSED,
            project_id=project_id,
        )
        
        if not chunks:
            return project.context_summary
        
        # Map: Collect all summaries
        summaries = [
            chunk.summary or chunk.content[:200]
            for chunk in chunks
        ]
        
        # Reduce: Combine into project context
        context_summary = self._reduce_summaries(summaries)
        
        # Update project
        from ..models import ProjectUpdate
        await self.project_repo.update(
            project_id,
            ProjectUpdate(context_summary=context_summary)
        )
        
        # Mark chunks as compacted
        for chunk in chunks:
            await self.chunk_repo.update(
                chunk.id,
                ChunkUpdate(status=ChunkStatus.COMPACTED)
            )
        
        return context_summary
    
    async def process_inbox(self, batch_size: int = 10) -> int:
        """Process a batch of inbox chunks.
        
        Returns the number of chunks processed.
        """
        inbox_chunks = await self.chunk_repo.list(
            status=ChunkStatus.INBOX,
            limit=batch_size,
        )
        
        processed = 0
        for chunk in inbox_chunks:
            result = await self.process_chunk(chunk.id)
            if result:
                processed += 1
        
        return processed
    
    def _generate_simple_summary(self, content: str, max_length: int = 200) -> str:
        """Generate a simple text summary.
        
        In production, this would call an LLM like Ollama.
        For now, use first sentences or truncation.
        """
        # Split into sentences
        sentences = content.replace('\n', ' ').split('. ')
        
        summary = []
        current_length = 0
        
        for sentence in sentences:
            if current_length + len(sentence) > max_length:
                break
            summary.append(sentence)
            current_length += len(sentence) + 2
        
        result = '. '.join(summary)
        if result and not result.endswith('.'):
            result += '.'
        
        return result or content[:max_length] + '...'
    
    def _reduce_summaries(self, summaries: list[str], max_length: int = 1000) -> str:
        """Reduce multiple summaries into a single context summary.
        
        In production, this would use recursive LLM calls.
        For now, concatenate and truncate.
        """
        combined = '\n'.join(f"- {s}" for s in summaries if s)
        
        if len(combined) <= max_length:
            return combined
        
        # Truncate if too long
        return combined[:max_length] + '\n...(truncated)'
