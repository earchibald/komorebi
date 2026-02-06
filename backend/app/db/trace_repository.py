"""Trace repository for data access.

Provides CRUD and active-trace management for the traces table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.oracle import Trace, TraceCreate, TraceUpdate, TraceStatus, TraceSummary
from .database import TraceTable, ChunkTable


class TraceRepository:
    """Repository for Trace operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: TraceCreate) -> Trace:
        """Create a new trace."""
        now = datetime.utcnow()
        trace = Trace(
            name=data.name,
            status=TraceStatus.ACTIVE,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
        )
        db_trace = TraceTable(
            id=str(trace.id),
            name=trace.name,
            status=trace.status.value,
            meta_summary=trace.meta_summary,
            created_at=now,
            updated_at=now,
        )
        self.session.add(db_trace)
        await self.session.commit()
        await self.session.refresh(db_trace)
        return trace

    async def get(self, trace_id: UUID) -> Optional[Trace]:
        """Get a trace by ID."""
        result = await self.session.execute(
            select(TraceTable).where(TraceTable.id == str(trace_id))
        )
        row = result.scalar_one_or_none()
        return self._to_model(row) if row else None

    async def get_active(self) -> Optional[Trace]:
        """Return the currently active trace, if any."""
        result = await self.session.execute(
            select(TraceTable)
            .where(TraceTable.status == TraceStatus.ACTIVE.value)
            .order_by(TraceTable.updated_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return self._to_model(row) if row else None

    async def list(
        self,
        status: Optional[TraceStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trace]:
        """List traces with optional status filter."""
        query = select(TraceTable)
        if status:
            query = query.where(TraceTable.status == status.value)
        query = query.order_by(TraceTable.updated_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return [self._to_model(r) for r in result.scalars().all()]

    async def update(self, trace_id: UUID, data: TraceUpdate) -> Optional[Trace]:
        """Update a trace."""
        result = await self.session.execute(
            select(TraceTable).where(TraceTable.id == str(trace_id))
        )
        db_trace = result.scalar_one_or_none()
        if not db_trace:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "status" and value:
                setattr(db_trace, field, value.value if hasattr(value, "value") else value)
            else:
                setattr(db_trace, field, value)

        db_trace.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(db_trace)
        return self._to_model(db_trace)

    async def activate(self, trace_id: UUID) -> Optional[Trace]:
        """Activate a trace, deactivating all others.

        Only ACTIVE traces are deactivated — PAUSED and CLOSED
        traces keep their status.
        """
        # Deactivate all currently-active traces
        await self.session.execute(
            update(TraceTable)
            .where(TraceTable.status == TraceStatus.ACTIVE.value)
            .values(status=TraceStatus.PAUSED.value, updated_at=datetime.utcnow())
        )
        # Activate the requested trace
        result = await self.session.execute(
            select(TraceTable).where(TraceTable.id == str(trace_id))
        )
        db_trace = result.scalar_one_or_none()
        if not db_trace:
            return None

        db_trace.status = TraceStatus.ACTIVE.value
        db_trace.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(db_trace)
        return self._to_model(db_trace)

    async def get_summary(self, trace_id: UUID) -> Optional[TraceSummary]:
        """Return a lightweight TraceSummary with chunk count."""
        result = await self.session.execute(
            select(TraceTable).where(TraceTable.id == str(trace_id))
        )
        db_trace = result.scalar_one_or_none()
        if not db_trace:
            return None

        count_result = await self.session.execute(
            select(func.count(ChunkTable.id)).where(
                ChunkTable.trace_id == str(trace_id)
            )
        )
        chunk_count = count_result.scalar_one()

        # Last activity: most recent chunk or the trace updated_at
        last_chunk_result = await self.session.execute(
            select(func.max(ChunkTable.created_at)).where(
                ChunkTable.trace_id == str(trace_id)
            )
        )
        last_chunk_at = last_chunk_result.scalar_one_or_none()

        return TraceSummary(
            id=UUID(db_trace.id),
            name=db_trace.name,
            status=TraceStatus(db_trace.status),
            meta_summary=db_trace.meta_summary,
            chunk_count=chunk_count,
            last_activity=str(last_chunk_at) if last_chunk_at else str(db_trace.updated_at),
        )

    async def search_by_name(self, query: str, limit: int = 10) -> list[Trace]:
        """Search traces by name (case-insensitive LIKE)."""
        result = await self.session.execute(
            select(TraceTable)
            .where(TraceTable.name.ilike(f"%{query}%"))
            .order_by(TraceTable.updated_at.desc())
            .limit(limit)
        )
        return [self._to_model(r) for r in result.scalars().all()]

    def _to_model(self, row: TraceTable) -> Trace:
        return Trace(
            id=UUID(row.id),
            name=row.name,
            status=TraceStatus(row.status),
            meta_summary=row.meta_summary,
            created_at=str(row.created_at),
            updated_at=str(row.updated_at),
        )
