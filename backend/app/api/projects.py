"""Project API endpoints.

Provides management of projects - containers for organizing
chunks and maintaining aggregate context.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db, ChunkRepository, ProjectRepository, EntityRepository
from ..models import Project, ProjectCreate, ProjectUpdate
from ..core import CompactorService
from ..core.events import event_bus, ChunkEvent, EventType

router = APIRouter(prefix="/projects", tags=["projects"])


async def get_project_repo(db: AsyncSession = Depends(get_db)) -> ProjectRepository:
    """Dependency to get project repository."""
    return ProjectRepository(db)


async def get_chunk_repo(db: AsyncSession = Depends(get_db)) -> ChunkRepository:
    """Dependency to get chunk repository."""
    return ChunkRepository(db)


async def get_entity_repo(db: AsyncSession = Depends(get_db)) -> EntityRepository:
    """Dependency to get entity repository."""
    return EntityRepository(db)


@router.post("", response_model=Project, status_code=201)
async def create_project(
    project_create: ProjectCreate,
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> Project:
    """Create a new project."""
    return await project_repo.create(project_create)


@router.get("", response_model=list[Project])
async def list_projects(
    limit: int = 100,
    offset: int = 0,
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> list[Project]:
    """List all projects."""
    return await project_repo.list(limit=limit, offset=offset)


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: UUID,
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> Project:
    """Get a specific project by ID."""
    project = await project_repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=Project)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> Project:
    """Update a project."""
    project = await project_repo.update(project_id, project_update)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await event_bus.publish(ChunkEvent(
        event_type=EventType.PROJECT_UPDATED,
        chunk_id=project_id,  # Using chunk_id field for project_id
        data=project.model_dump(mode="json"),
    ))
    
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> None:
    """Delete a project."""
    success = await project_repo.delete(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")


@router.post("/{project_id}/compact")
async def compact_project(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    project_repo: ProjectRepository = Depends(get_project_repo),
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
    entity_repo: EntityRepository = Depends(get_entity_repo),
) -> dict:
    """Compact all processed chunks in a project into a context summary."""
    project = await project_repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Publish compaction started event
    await event_bus.publish(ChunkEvent(
        event_type=EventType.COMPACTION_STARTED,
        chunk_id=project_id,
        data={"project_id": str(project_id)},
    ))
    
    compactor = CompactorService(chunk_repo, project_repo, entity_repo)
    context_summary = await compactor.compact_project(project_id)
    
    # Publish compaction completed event
    await event_bus.publish(ChunkEvent(
        event_type=EventType.COMPACTION_COMPLETED,
        chunk_id=project_id,
        data={
            "project_id": str(project_id),
            "context_summary": context_summary,
        },
    ))
    
    return {
        "project_id": str(project_id),
        "context_summary": context_summary,
        "message": "Compaction completed",
    }


@router.get("/{project_id}/context")
async def get_project_context(
    project_id: UUID,
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> dict:
    """Get the compacted context summary for a project."""
    project = await project_repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "project_id": str(project_id),
        "project_name": project.name,
        "context_summary": project.context_summary,
        "chunk_count": project.chunk_count,
    }
