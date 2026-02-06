"""File-event API endpoints.

Read-only endpoints for querying filesystem change events
recorded by `k watch`.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..db.file_event_repository import FileEventRepository
from ..models.file_event import FileEvent, FileEventHistory

router = APIRouter(prefix="/file-events", tags=["file-events"])


async def _event_repo(db: AsyncSession = Depends(get_db)) -> FileEventRepository:
    return FileEventRepository(db)


@router.get("", response_model=list[FileEvent])
async def list_file_events(
    trace_id: Optional[UUID] = Query(None, description="Filter by trace ID"),
    path: Optional[str] = Query(None, description="Filter by file path (partial match)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: FileEventRepository = Depends(_event_repo),
) -> list[FileEvent]:
    """List file events with optional filters."""
    return await repo.list(trace_id=trace_id, path=path, limit=limit, offset=offset)


@router.get("/history/{path:path}", response_model=FileEventHistory)
async def file_history(
    path: str,
    repo: FileEventRepository = Depends(_event_repo),
) -> FileEventHistory:
    """Get the full CRUD history for a specific file path."""
    return await repo.path_history(path)
