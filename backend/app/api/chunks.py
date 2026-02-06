"""Chunk API endpoints.

Provides fast capture and management of chunks - the
fundamental unit of information in Komorebi.
"""

import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db, ChunkRepository, ProjectRepository, EntityRepository
from ..models import (
    Chunk, ChunkCreate, ChunkUpdate, ChunkStatus, SearchResult,
    DashboardStats, WeekBucket,
    TimelineGranularity, TimelineBucket, TimelineResponse,
    RelatedChunk, RelatedChunksResponse,
)
from ..core import CompactorService
from ..core.events import event_bus, ChunkEvent, EventType
from ..core.similarity import TFIDFService

router = APIRouter(prefix="/chunks", tags=["chunks"])


async def get_chunk_repo(db: AsyncSession = Depends(get_db)) -> ChunkRepository:
    """Dependency to get chunk repository."""
    return ChunkRepository(db)


async def get_project_repo(db: AsyncSession = Depends(get_db)) -> ProjectRepository:
    """Dependency to get project repository."""
    return ProjectRepository(db)


async def get_entity_repo(db: AsyncSession = Depends(get_db)) -> EntityRepository:
    """Dependency to get entity repository."""
    return EntityRepository(db)


@router.post("", response_model=Chunk, status_code=201)
async def capture_chunk(
    chunk_create: ChunkCreate,
    background_tasks: BackgroundTasks,
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> Chunk:
    """Capture a new chunk into the inbox.
    
    This is the primary "fast capture" endpoint, designed for
    minimal friction. Processing happens in the background.
    """
    chunk = await chunk_repo.create(chunk_create)
    
    # Update project chunk count if associated
    if chunk.project_id:
        await project_repo.update_chunk_count(chunk.project_id)
    
    # Publish event
    await event_bus.publish(ChunkEvent(
        event_type=EventType.CHUNK_CREATED,
        chunk_id=chunk.id,
        data=chunk.model_dump(mode="json"),
    ))
    
    # Schedule background processing
    background_tasks.add_task(
        _process_chunk_background,
        chunk.id,
    )
    
    return chunk


async def _process_chunk_background(chunk_id: UUID) -> None:
    """Background task to process a newly captured chunk."""
    from ..db.database import async_session
    
    async with async_session() as session:
        chunk_repo = ChunkRepository(session)
        project_repo = ProjectRepository(session)
        entity_repo = EntityRepository(session)
        compactor = CompactorService(chunk_repo, project_repo, entity_repo)
        
        result = await compactor.process_chunk(chunk_id)
        
        if result:
            await event_bus.publish(ChunkEvent(
                event_type=EventType.CHUNK_UPDATED,
                chunk_id=chunk_id,
                data=result.model_dump(mode="json"),
            ))


@router.get("/search", response_model=SearchResult)
async def search_chunks(
    q: Optional[str] = Query(None, description="Text search query (case-insensitive)"),
    status: Optional[ChunkStatus] = Query(None, description="Filter by chunk status"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (error, url, tool_id, decision, code_ref)"),
    entity_value: Optional[str] = Query(None, description="Filter by entity value (partial match)"),
    created_after: Optional[datetime] = Query(None, description="Filter chunks created after this timestamp"),
    created_before: Optional[datetime] = Query(None, description="Filter chunks created before this timestamp"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
) -> SearchResult:
    """Search chunks with text, entity, and date filters.
    
    Supports:
    - Text search: Case-insensitive partial matching in content
    - Entity filtering: Find chunks with specific entity types/values
    - Date range: Filter by creation date
    - Status/Project: Standard filtering
    - Pagination: limit and offset parameters
    """
    chunks, total = await chunk_repo.search(
        search_query=q,
        status=status,
        project_id=project_id,
        entity_type=entity_type,
        entity_value=entity_value,
        created_after=created_after,
        created_before=created_before,
        limit=limit,
        offset=offset,
    )
    
    return SearchResult(
        items=chunks,
        total=total,
        limit=limit,
        offset=offset,
        query=q,
    )


@router.get("", response_model=list[Chunk])
async def list_chunks(
    status: Optional[ChunkStatus] = None,
    project_id: Optional[UUID] = None,
    limit: int = 100,
    offset: int = 0,
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
) -> list[Chunk]:
    """List chunks with optional filters."""
    return await chunk_repo.list(
        status=status,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )


@router.get("/inbox", response_model=list[Chunk])
async def list_inbox(
    limit: int = 100,
    offset: int = 0,
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
) -> list[Chunk]:
    """List only inbox chunks (unprocessed)."""
    return await chunk_repo.list(
        status=ChunkStatus.INBOX,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    entity_repo: EntityRepository = Depends(get_entity_repo),
) -> DashboardStats:
    """Get enhanced chunk statistics with trends and insights."""
    # Basic counters
    inbox_count = await chunk_repo.count(ChunkStatus.INBOX)
    processed_count = await chunk_repo.count(ChunkStatus.PROCESSED)
    compacted_count = await chunk_repo.count(ChunkStatus.COMPACTED)
    archived_count = await chunk_repo.count(ChunkStatus.ARCHIVED)
    
    # Weekly trends
    weekly_data = await chunk_repo.count_by_week(weeks=8)
    by_week = [
        WeekBucket(week_start=week_start, count=count)
        for week_start, count in weekly_data
    ]
    
    # Insights: oldest inbox
    oldest_created = await chunk_repo.oldest_inbox()
    oldest_age: Optional[int] = None
    if oldest_created:
        delta = datetime.utcnow() - oldest_created
        oldest_age = delta.days
    
    # Insights: most active project
    projects = await project_repo.list(limit=1000)
    most_active_name: Optional[str] = None
    most_active_count = 0
    by_project: list[dict] = []
    for proj in projects:
        if proj.chunk_count > 0:
            by_project.append({
                "name": proj.name,
                "chunk_count": proj.chunk_count,
                "id": str(proj.id),
            })
        if proj.chunk_count > most_active_count:
            most_active_count = proj.chunk_count
            most_active_name = proj.name
    
    # Entity count
    entity_count = await entity_repo.count_all()
    
    return DashboardStats(
        inbox=inbox_count,
        processed=processed_count,
        compacted=compacted_count,
        archived=archived_count,
        total=inbox_count + processed_count + compacted_count + archived_count,
        by_week=by_week,
        oldest_inbox_age_days=oldest_age,
        most_active_project=most_active_name,
        most_active_project_count=most_active_count,
        entity_count=entity_count,
        by_project=by_project,
    )


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    granularity: TimelineGranularity = Query(
        TimelineGranularity.WEEK, description="Time bucket granularity"
    ),
    weeks: int = Query(8, ge=1, le=52, description="Number of weeks to look back"),
    project_id: Optional[UUID] = Query(None, description="Optional project filter"),
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
) -> TimelineResponse:
    """Get chunks grouped by time bucket for timeline view."""
    raw_buckets = await chunk_repo.timeline(
        granularity=granularity.value,
        weeks=weeks,
        project_id=project_id,
    )
    
    buckets = [
        TimelineBucket(
            bucket_label=b["bucket_label"],
            bucket_start=b["bucket_start"],
            chunk_count=b["chunk_count"],
            by_status=b["by_status"],
            chunk_ids=b["chunk_ids"],
        )
        for b in raw_buckets
    ]
    
    total = sum(b.chunk_count for b in buckets)
    
    return TimelineResponse(
        granularity=granularity.value,
        buckets=buckets,
        total_chunks=total,
    )


@router.get("/{chunk_id}", response_model=Chunk)
async def get_chunk(
    chunk_id: UUID,
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
) -> Chunk:
    """Get a specific chunk by ID."""
    chunk = await chunk_repo.get(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk


@router.get("/{chunk_id}/related", response_model=RelatedChunksResponse)
async def get_related_chunks(
    chunk_id: UUID,
    limit: int = Query(5, ge=1, le=20, description="Max related chunks to return"),
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
) -> RelatedChunksResponse:
    """Find chunks similar to the given chunk using TF-IDF cosine similarity."""
    # Verify chunk exists
    target_chunk = await chunk_repo.get(chunk_id)
    if not target_chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    # Get all chunk content for TF-IDF
    start_time = time.monotonic()
    all_content = await chunk_repo.get_all_content()
    
    # Compute related chunks
    tfidf = TFIDFService()
    related_raw = tfidf.find_related(str(chunk_id), all_content, top_k=limit)
    
    computation_ms = int((time.monotonic() - start_time) * 1000)
    
    # Fetch full chunk objects for results
    related: list[RelatedChunk] = []
    for doc_id, similarity, shared_terms in related_raw:
        related_chunk = await chunk_repo.get(UUID(doc_id))
        if related_chunk:
            related.append(RelatedChunk(
                chunk=related_chunk,
                similarity=round(similarity, 4),
                shared_terms=shared_terms,
            ))
    
    return RelatedChunksResponse(
        source_chunk_id=str(chunk_id),
        related=related,
        computation_ms=computation_ms,
    )


@router.patch("/{chunk_id}", response_model=Chunk)
async def update_chunk(
    chunk_id: UUID,
    chunk_update: ChunkUpdate,
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
) -> Chunk:
    """Update a chunk."""
    chunk = await chunk_repo.update(chunk_id, chunk_update)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    await event_bus.publish(ChunkEvent(
        event_type=EventType.CHUNK_UPDATED,
        chunk_id=chunk_id,
        data=chunk.model_dump(mode="json"),
    ))
    
    return chunk


@router.delete("/{chunk_id}", status_code=204)
async def delete_chunk(
    chunk_id: UUID,
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
) -> None:
    """Delete a chunk."""
    success = await chunk_repo.delete(chunk_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    await event_bus.publish(ChunkEvent(
        event_type=EventType.CHUNK_DELETED,
        chunk_id=chunk_id,
        data={},
    ))


@router.post("/process-inbox")
async def process_inbox(
    batch_size: int = 10,
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    entity_repo: EntityRepository = Depends(get_entity_repo),
) -> dict:
    """Manually trigger processing of inbox chunks."""
    compactor = CompactorService(chunk_repo, project_repo, entity_repo)
    processed = await compactor.process_inbox(batch_size)
    
    return {
        "processed": processed,
        "message": f"Processed {processed} chunks",
    }
