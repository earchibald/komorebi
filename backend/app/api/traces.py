"""Trace API endpoints.

CRUD and lifecycle management for traces — named context sessions
that group related chunks and file events.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..db.trace_repository import TraceRepository
from ..models.oracle import (
    Trace,
    TraceCreate,
    TraceStatus,
    TraceSummary,
    TraceUpdate,
)

router = APIRouter(prefix="/traces", tags=["traces"])


async def _trace_repo(db: AsyncSession = Depends(get_db)) -> TraceRepository:
    return TraceRepository(db)


@router.post("", response_model=Trace, status_code=201)
async def create_trace(
    data: TraceCreate,
    repo: TraceRepository = Depends(_trace_repo),
) -> Trace:
    """Create a new trace."""
    return await repo.create(data)


@router.get("", response_model=list[Trace])
async def list_traces(
    status: Optional[TraceStatus] = None,
    limit: int = 100,
    offset: int = 0,
    repo: TraceRepository = Depends(_trace_repo),
) -> list[Trace]:
    """List traces with optional status filter."""
    return await repo.list(status=status, limit=limit, offset=offset)


@router.get("/active", response_model=Optional[TraceSummary])
async def get_active_trace(
    repo: TraceRepository = Depends(_trace_repo),
) -> Optional[TraceSummary]:
    """Get the currently active trace with summary."""
    active = await repo.get_active()
    if not active:
        return None
    return await repo.get_summary(active.id)


@router.get("/{trace_id}", response_model=Trace)
async def get_trace(
    trace_id: UUID,
    repo: TraceRepository = Depends(_trace_repo),
) -> Trace:
    """Get a trace by ID."""
    trace = await repo.get(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.patch("/{trace_id}", response_model=Trace)
async def update_trace(
    trace_id: UUID,
    data: TraceUpdate,
    repo: TraceRepository = Depends(_trace_repo),
) -> Trace:
    """Update a trace (rename, change status, set summary)."""
    trace = await repo.update(trace_id, data)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.post("/{trace_id}/activate", response_model=Trace)
async def activate_trace(
    trace_id: UUID,
    repo: TraceRepository = Depends(_trace_repo),
) -> Trace:
    """Set a trace as active, pausing all other active traces."""
    trace = await repo.activate(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
