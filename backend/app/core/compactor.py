"""Compactor service for recursive summarization.

Implements the "Recursive Compactor" pattern:
- Treats memory as a pyramid
- Instead of forgetting, we summarize
- Map-reduce summarization for large context
"""

import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

from ..models import Chunk, ChunkStatus, ChunkUpdate, ProjectUpdate
from ..models import EntityCreate, EntityType
from ..db.repository import ChunkRepository, ProjectRepository, EntityRepository
from .ollama_client import KomorebiLLM


MAX_CONTEXT_WINDOW = 12000
RECURSIVE_BATCH_SIZE = 5
INTERMEDIATE_MAX_WORDS = 200
FINAL_MAX_WORDS = 500


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
        entity_repo: Optional[EntityRepository] = None,
    ):
        self.chunk_repo = chunk_repo
        self.project_repo = project_repo
        self.entity_repo = entity_repo
        self.llm = KomorebiLLM()
    
    async def process_chunk(self, chunk_id: UUID) -> Optional[Chunk]:
        """Process a single chunk from INBOX to PROCESSED status.
        
        This is the Map step of the Map-Reduce pipeline:
        1. Tokenize the content
        2. Generate a summary using LLM
        3. Extract tags and entities
        4. Update token count
        
        If Ollama is unavailable, falls back to simple summarization.
        """
        chunk = await self.chunk_repo.get(chunk_id)
        if not chunk or chunk.status != ChunkStatus.INBOX:
            return None
        
        # 1. Safety Check: Verify Ollama is available
        llm_available = await self.llm.is_available()
        if not llm_available:
            print(f"⚠️  Ollama unavailable. Using fallback summarization for chunk {chunk_id}.")
            # Fallback to simple summarization
            summary = self._generate_simple_summary(chunk.content)
        else:
            try:
                # 2. Generate Summary using LLM
                summary = await self.llm.summarize(chunk.content, max_words=100)
            except Exception as e:
                print(f"❌ Inference failed for chunk {chunk_id}: {e}")
                summary = self._generate_simple_summary(chunk.content)
        
        # 3. Calculate Token Efficiency (Heuristic: 4 chars ~= 1 token)
        token_count = len(chunk.content) // 4
        
        # 4. Update chunk status and metadata
        update = ChunkUpdate(
            status=ChunkStatus.PROCESSED,
            summary=summary,
            token_count=token_count,
        )
        
        updated = await self.chunk_repo.update(chunk_id, update)
        
        # 5. Entity Extraction (non-blocking to summary update)
        if updated and llm_available and self.entity_repo and updated.project_id:
            try:
                entities_json = await self.llm.extract_entities(updated.content)
                await self._save_extracted_entities(
                    updated.id,
                    updated.project_id,
                    entities_json,
                )
            except Exception as e:
                print(f"⚠️ Entity extraction failed: {e}")
        
        return updated
    
    async def compact_project(self, project_id: UUID) -> Optional[str]:
        """Compact all processed chunks in a project into a context summary.
        
        This is the Reduce step of the Map-Reduce pipeline:
        1. Fetch all PROCESSED chunks for the project
        2. Map: Collect existing summaries (created by process_chunk)
        3. Reduce: Combine summaries into a high-level project context
        4. Archive compacted chunks (mark as COMPACTED)
        
        If combined text exceeds ~30,000 chars, recursive summarization would trigger.
        For MVP, we send all summaries to the LLM in a single pass.
        """
        project = await self.project_repo.get(project_id)
        if not project:
            return None
        
        # 1. Fetch Candidates: Get all PROCESSED chunks for this project
        chunks = await self.chunk_repo.list(
            status=ChunkStatus.PROCESSED,
            project_id=project_id,
        )
        
        if not chunks:
            return project.context_summary
        
        # 2. Map: Extract existing atomic summaries (created in process_chunk)
        summaries = [c.summary for c in chunks if c.summary]
        if not summaries:
            return project.context_summary
        
        combined_text = "\n---\n".join(summaries)
        
        # 3. Reduce: Create the "Global Context" using LLM
        llm_available = await self.llm.is_available()
        if not llm_available:
            print(f"⚠️  Ollama unavailable. Using fallback compaction for project {project_id}.")
            context_summary = self._reduce_summaries(summaries)
            compaction_depth = max(project.compaction_depth, 1)
        else:
            try:
                if len(combined_text) > MAX_CONTEXT_WINDOW:
                    context_summary = await self.recursive_reduce(summaries, depth=1)
                    compaction_depth = max(project.compaction_depth, 2)
                else:
                    context_summary = await self.llm.summarize(
                        combined_text,
                        max_words=FINAL_MAX_WORDS,
                        system_anchor="Create a high-level project status report based on these logs.",
                    )
                    compaction_depth = max(project.compaction_depth, 1)
            except Exception as e:
                print(f"❌ Project compaction failed for {project_id}: {e}")
                context_summary = self._reduce_summaries(summaries)
                compaction_depth = max(project.compaction_depth, 1)
        
        # 4. Update Project with the compacted summary
        await self.project_repo.update(
            project_id,
            ProjectUpdate(
                context_summary=context_summary,
                compaction_depth=compaction_depth,
                last_compaction_at=datetime.utcnow(),
            )
        )
        
        # Mark chunks as COMPACTED (removed from active context)
        for chunk in chunks:
            await self.chunk_repo.update(
                chunk.id,
                ChunkUpdate(status=ChunkStatus.COMPACTED)
            )
        
        return context_summary

    async def recursive_reduce(self, texts: list[str], depth: int = 1) -> str:
        """Recursively compact texts until they fit a single context window."""
        combined = "\n---\n".join(texts)
        
        if len(combined) < MAX_CONTEXT_WINDOW:
            return await self.llm.summarize(
                combined,
                max_words=FINAL_MAX_WORDS,
                system_anchor=f"Consolidating layer {depth} logs.",
            )
        
        batch_size = RECURSIVE_BATCH_SIZE
        intermediate_summaries = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_text = "\n".join(batch)
            summary = await self.llm.summarize(
                batch_text,
                max_words=INTERMEDIATE_MAX_WORDS,
                system_anchor=f"Consolidating layer {depth} logs.",
            )
            intermediate_summaries.append(summary)
        
        return await self.recursive_reduce(intermediate_summaries, depth + 1)

    async def _save_extracted_entities(
        self,
        chunk_id: UUID,
        project_id: UUID,
        entities_json: dict,
    ) -> None:
        """Validate and persist extracted entities."""
        if not self.entity_repo or not isinstance(entities_json, dict):
            return
        
        key_map = {
            "error": EntityType.ERROR,
            "url": EntityType.URL,
            "tool_id": EntityType.TOOL_ID,
            "decision": EntityType.DECISION,
            "code_ref": EntityType.CODE_REF,
        }
        
        entities: list[EntityCreate] = []
        for key, entity_type in key_map.items():
            values = entities_json.get(key, [])
            if not isinstance(values, list):
                continue
            for value in values:
                if isinstance(value, str) and value.strip():
                    entities.append(
                        EntityCreate(
                            chunk_id=chunk_id,
                            project_id=project_id,
                            entity_type=entity_type,
                            value=value.strip(),
                            confidence=1.0,
                            context_snippet=None,
                        )
                    )
        
        await self.entity_repo.create_many(entities)
    
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
