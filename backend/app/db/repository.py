"""Repository pattern for data access.

Provides clean abstractions over database operations,
enabling easy testing and potential backend swaps.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Chunk, ChunkCreate, ChunkUpdate, ChunkStatus
from ..models import Project, ProjectCreate, ProjectUpdate
from ..models import Entity, EntityCreate, EntityType
from .database import ChunkTable, ProjectTable, EntityTable


class ChunkRepository:
    """Repository for Chunk operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, chunk_create: ChunkCreate) -> Chunk:
        """Create a new chunk from capture data."""
        chunk = Chunk(
            content=chunk_create.content,
            project_id=chunk_create.project_id,
            tags=chunk_create.tags,
            source=chunk_create.source,
            status=ChunkStatus.INBOX,
        )
        
        db_chunk = ChunkTable(
            id=str(chunk.id),
            content=chunk.content,
            summary=chunk.summary,
            project_id=str(chunk.project_id) if chunk.project_id else None,
            tags=chunk.tags,
            status=chunk.status.value,
            source=chunk.source,
            token_count=chunk.token_count,
            created_at=chunk.created_at,
            updated_at=chunk.updated_at,
        )
        
        self.session.add(db_chunk)
        await self.session.commit()
        await self.session.refresh(db_chunk)
        
        return chunk
    
    async def get(self, chunk_id: UUID) -> Optional[Chunk]:
        """Get a chunk by ID."""
        result = await self.session.execute(
            select(ChunkTable).where(ChunkTable.id == str(chunk_id))
        )
        db_chunk = result.scalar_one_or_none()
        
        if not db_chunk:
            return None
        
        return self._to_model(db_chunk)
    
    async def list(
        self,
        status: Optional[ChunkStatus] = None,
        project_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Chunk]:
        """List chunks with optional filters."""
        query = select(ChunkTable)
        
        if status:
            query = query.where(ChunkTable.status == status.value)
        if project_id:
            query = query.where(ChunkTable.project_id == str(project_id))
        
        query = query.order_by(ChunkTable.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return [self._to_model(row) for row in result.scalars().all()]
    
    async def update(self, chunk_id: UUID, chunk_update: ChunkUpdate) -> Optional[Chunk]:
        """Update a chunk."""
        result = await self.session.execute(
            select(ChunkTable).where(ChunkTable.id == str(chunk_id))
        )
        db_chunk = result.scalar_one_or_none()
        
        if not db_chunk:
            return None
        
        update_data = chunk_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "status" and value:
                setattr(db_chunk, field, value.value if hasattr(value, 'value') else value)
            elif field == "project_id" and value:
                setattr(db_chunk, field, str(value))
            else:
                setattr(db_chunk, field, value)
        
        db_chunk.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(db_chunk)
        
        return self._to_model(db_chunk)
    
    async def delete(self, chunk_id: UUID) -> bool:
        """Delete a chunk."""
        result = await self.session.execute(
            select(ChunkTable).where(ChunkTable.id == str(chunk_id))
        )
        db_chunk = result.scalar_one_or_none()
        
        if not db_chunk:
            return False
        
        await self.session.delete(db_chunk)
        await self.session.commit()
        return True
    
    async def count(self, status: Optional[ChunkStatus] = None) -> int:
        """Count chunks, optionally filtered by status."""
        query = select(func.count(ChunkTable.id))
        if status:
            query = query.where(ChunkTable.status == status.value)
        result = await self.session.execute(query)
        return result.scalar_one()
    
    def _to_model(self, db_chunk: ChunkTable) -> Chunk:
        """Convert database row to Pydantic model."""
        return Chunk(
            id=UUID(db_chunk.id),
            content=db_chunk.content,
            summary=db_chunk.summary,
            project_id=UUID(db_chunk.project_id) if db_chunk.project_id else None,
            tags=db_chunk.tags or [],
            status=ChunkStatus(db_chunk.status),
            source=db_chunk.source,
            token_count=db_chunk.token_count,
            created_at=db_chunk.created_at,
            updated_at=db_chunk.updated_at,
        )


class ProjectRepository:
    """Repository for Project operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, project_create: ProjectCreate) -> Project:
        """Create a new project."""
        project = Project(
            name=project_create.name,
            description=project_create.description,
        )
        
        db_project = ProjectTable(
            id=str(project.id),
            name=project.name,
            description=project.description,
            context_summary=project.context_summary,
            compaction_depth=project.compaction_depth,
            last_compaction_at=project.last_compaction_at,
            chunk_count=project.chunk_count,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
        
        self.session.add(db_project)
        await self.session.commit()
        await self.session.refresh(db_project)
        
        return project
    
    async def get(self, project_id: UUID) -> Optional[Project]:
        """Get a project by ID."""
        result = await self.session.execute(
            select(ProjectTable).where(ProjectTable.id == str(project_id))
        )
        db_project = result.scalar_one_or_none()
        
        if not db_project:
            return None
        
        return self._to_model(db_project)
    
    async def list(self, limit: int = 100, offset: int = 0) -> list[Project]:
        """List all projects."""
        query = select(ProjectTable).order_by(ProjectTable.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return [self._to_model(row) for row in result.scalars().all()]
    
    async def update(self, project_id: UUID, project_update: ProjectUpdate) -> Optional[Project]:
        """Update a project."""
        result = await self.session.execute(
            select(ProjectTable).where(ProjectTable.id == str(project_id))
        )
        db_project = result.scalar_one_or_none()
        
        if not db_project:
            return None
        
        update_data = project_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_project, field, value)
        
        db_project.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(db_project)
        
        return self._to_model(db_project)
    
    async def delete(self, project_id: UUID) -> bool:
        """Delete a project."""
        result = await self.session.execute(
            select(ProjectTable).where(ProjectTable.id == str(project_id))
        )
        db_project = result.scalar_one_or_none()
        
        if not db_project:
            return False
        
        await self.session.delete(db_project)
        await self.session.commit()
        return True
    
    async def update_chunk_count(self, project_id: UUID) -> None:
        """Update the chunk count for a project."""
        count_result = await self.session.execute(
            select(func.count(ChunkTable.id)).where(
                ChunkTable.project_id == str(project_id)
            )
        )
        count = count_result.scalar_one()
        
        result = await self.session.execute(
            select(ProjectTable).where(ProjectTable.id == str(project_id))
        )
        db_project = result.scalar_one_or_none()
        
        if db_project:
            db_project.chunk_count = count
            await self.session.commit()
    
    def _to_model(self, db_project: ProjectTable) -> Project:
        """Convert database row to Pydantic model."""
        return Project(
            id=UUID(db_project.id),
            name=db_project.name,
            description=db_project.description,
            context_summary=db_project.context_summary,
            compaction_depth=db_project.compaction_depth or 0,
            last_compaction_at=db_project.last_compaction_at or db_project.updated_at,
            chunk_count=db_project.chunk_count,
            created_at=db_project.created_at,
            updated_at=db_project.updated_at,
        )


class EntityRepository:
    """Repository for Entity operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_many(self, entities: list[EntityCreate]) -> list[Entity]:
        """Create multiple entities in a single transaction."""
        if not entities:
            return []
        
        db_entities = []
        for entity in entities:
            db_entity = EntityTable(
                chunk_id=str(entity.chunk_id),
                project_id=str(entity.project_id),
                entity_type=entity.entity_type.value,
                value=entity.value,
                confidence=entity.confidence,
                context_snippet=entity.context_snippet,
                created_at=datetime.utcnow(),
            )
            db_entities.append(db_entity)
            self.session.add(db_entity)
        
        await self.session.commit()
        for db_entity in db_entities:
            await self.session.refresh(db_entity)
        
        return [self._to_model(db_entity) for db_entity in db_entities]
    
    async def list_by_project(
        self,
        project_id: UUID,
        entity_type: Optional[EntityType] = None,
        min_confidence: float = 0.0,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Entity]:
        """List entities for a project with optional filters."""
        query = select(EntityTable).where(EntityTable.project_id == str(project_id))
        
        if entity_type:
            query = query.where(EntityTable.entity_type == entity_type.value)
        if min_confidence > 0.0:
            query = query.where(EntityTable.confidence >= min_confidence)
        
        query = query.order_by(EntityTable.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return [self._to_model(row) for row in result.scalars().all()]

    async def list_by_chunk(
        self,
        chunk_id: UUID,
        entity_type: Optional[EntityType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Entity]:
        """List entities extracted from a specific chunk."""
        query = select(EntityTable).where(EntityTable.chunk_id == str(chunk_id))

        if entity_type:
            query = query.where(EntityTable.entity_type == entity_type.value)

        query = query.order_by(EntityTable.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return [self._to_model(row) for row in result.scalars().all()]
    
    def _to_model(self, db_entity: EntityTable) -> Entity:
        """Convert database row to Pydantic model."""
        return Entity(
            id=db_entity.id,
            chunk_id=UUID(db_entity.chunk_id),
            project_id=UUID(db_entity.project_id),
            entity_type=EntityType(db_entity.entity_type),
            value=db_entity.value,
            confidence=db_entity.confidence,
            context_snippet=db_entity.context_snippet,
            created_at=db_entity.created_at,
        )
