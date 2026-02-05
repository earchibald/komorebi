"""Chunk API endpoints.

Provides fast capture and management of chunks - the
fundamental unit of information in Komorebi.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db, ChunkRepository, ProjectRepository, EntityRepository
from ..models import Chunk, ChunkCreate, ChunkUpdate, ChunkStatus
from ..core import CompactorService
from ..core.events import event_bus, ChunkEvent, EventType

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


@router.get("/stats")
async def get_stats(
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
) -> dict:
    """Get chunk statistics."""
    inbox_count = await chunk_repo.count(ChunkStatus.INBOX)
    processed_count = await chunk_repo.count(ChunkStatus.PROCESSED)
    compacted_count = await chunk_repo.count(ChunkStatus.COMPACTED)
    archived_count = await chunk_repo.count(ChunkStatus.ARCHIVED)
    
    return {
        "inbox": inbox_count,
        "processed": processed_count,
        "compacted": compacted_count,
        "archived": archived_count,
        "total": inbox_count + processed_count + compacted_count + archived_count,
    }


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
