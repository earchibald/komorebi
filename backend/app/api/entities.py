"""Entity API endpoints.

Provides access to extracted entities from chunks:
- List entities by project
- Filter by type and confidence
- Aggregations by type
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db, EntityRepository
from ..models import Entity, EntityType

router = APIRouter(prefix="/entities", tags=["entities"])


async def get_entity_repo(db: AsyncSession = Depends(get_db)) -> EntityRepository:
    """Dependency to get entity repository."""
    return EntityRepository(db)


@router.get("/projects/{project_id}", response_model=list[Entity])
async def list_project_entities(
    project_id: UUID,
    entity_type: Optional[EntityType] = None,
    min_confidence: float = 0.0,
    limit: int = 100,
    offset: int = 0,
    entity_repo: EntityRepository = Depends(get_entity_repo),
) -> list[Entity]:
    """List entities extracted from a project's chunks.
    
    Filter by entity type (error, url, tool_id, decision, code_ref)
    and minimum confidence threshold.
    """
    return await entity_repo.list_by_project(
        project_id=project_id,
        entity_type=entity_type,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset,
    )


@router.get("/chunks/{chunk_id}", response_model=list[Entity])
async def list_chunk_entities(
    chunk_id: UUID,
    entity_type: Optional[EntityType] = None,
    limit: int = 100,
    offset: int = 0,
    entity_repo: EntityRepository = Depends(get_entity_repo),
) -> list[Entity]:
    """List entities extracted from a specific chunk.

    Filter by entity type (error, url, tool_id, decision, code_ref).
    """
    return await entity_repo.list_by_chunk(
        chunk_id=chunk_id,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )


@router.get("/projects/{project_id}/aggregations")
async def get_entity_aggregations(
    project_id: UUID,
    entity_repo: EntityRepository = Depends(get_entity_repo),
) -> dict:
    """Get entity counts aggregated by type for a project."""
    # Fetch all entities for the project
    all_entities = await entity_repo.list_by_project(
        project_id=project_id,
        limit=10000,  # High limit to get all
    )
    
    # Aggregate by type
    aggregations = {
        "error": 0,
        "url": 0,
        "tool_id": 0,
        "decision": 0,
        "code_ref": 0,
    }
    
    for entity in all_entities:
        aggregations[entity.entity_type.value] += 1
    
    return {
        "project_id": str(project_id),
        "total_entities": len(all_entities),
        "by_type": aggregations,
    }
