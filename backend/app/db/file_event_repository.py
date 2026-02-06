"""File-event repository for data access.

Provides CRUD and path-history queries for the file_events table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.file_event import FileEvent, FileEventCreate, FileEventHistory, CrudOp
from .database import FileEventTable


class FileEventRepository:
    """Repository for FileEvent operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: FileEventCreate) -> FileEvent:
        """Record a new file event."""
        now = datetime.utcnow()
        event_id = uuid4()

        db_event = FileEventTable(
            id=str(event_id),
            trace_id=str(data.trace_id),
            path=data.path,
            crud_op=data.crud_op.value,
            size_bytes=data.size_bytes,
            hash_prefix=data.hash_prefix,
            mime_type=data.mime_type,
            created_at=now,
        )
        self.session.add(db_event)
        await self.session.commit()
        await self.session.refresh(db_event)

        return FileEvent(
            id=event_id,
            trace_id=data.trace_id,
            path=data.path,
            crud_op=data.crud_op,
            size_bytes=data.size_bytes,
            hash_prefix=data.hash_prefix,
            mime_type=data.mime_type,
            created_at=now.isoformat(),
        )

    async def list(
        self,
        trace_id: Optional[UUID] = None,
        path: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FileEvent]:
        """List file events with optional filters."""
        query = select(FileEventTable)

        if trace_id:
            query = query.where(FileEventTable.trace_id == str(trace_id))
        if path:
            query = query.where(FileEventTable.path.ilike(f"%{path}%"))

        query = query.order_by(FileEventTable.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return [self._to_model(r) for r in result.scalars().all()]

    async def path_history(self, path: str) -> FileEventHistory:
        """Return the CRUD history for a specific file path."""
        result = await self.session.execute(
            select(FileEventTable)
            .where(FileEventTable.path == path)
            .order_by(FileEventTable.created_at.asc())
        )
        events = [self._to_model(r) for r in result.scalars().all()]

        current_hash = events[-1].hash_prefix if events else None
        last_modified = events[-1].created_at if events else None

        return FileEventHistory(
            path=path,
            events=events,
            current_hash=current_hash,
            last_modified=last_modified,
        )

    async def count_by_trace(self, trace_id: UUID) -> int:
        """Count file events for a trace."""
        result = await self.session.execute(
            select(func.count(FileEventTable.id)).where(
                FileEventTable.trace_id == str(trace_id)
            )
        )
        return result.scalar_one()

    def _to_model(self, row: FileEventTable) -> FileEvent:
        return FileEvent(
            id=UUID(row.id),
            trace_id=UUID(row.trace_id),
            path=row.path,
            crud_op=CrudOp(row.crud_op),
            size_bytes=row.size_bytes,
            hash_prefix=row.hash_prefix,
            mime_type=row.mime_type,
            created_at=str(row.created_at),
        )
