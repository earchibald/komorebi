"""Trace and MCP Oracle models.

Traces are named context sessions that group related chunks,
file events, and decisions. The MCP Server exposes these as tools
for external coding agents.
"""

from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TraceStatus(str, Enum):
    """Lifecycle status of a trace session."""

    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class TraceCreate(BaseModel):
    """Schema for creating a new trace."""

    name: str = Field(..., min_length=1, max_length=255, description="Trace display name")


class TraceUpdate(BaseModel):
    """Schema for updating an existing trace."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[TraceStatus] = None
    meta_summary: Optional[str] = None


class Trace(BaseModel):
    """A named context session grouping related chunks."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=255)
    status: TraceStatus = Field(default=TraceStatus.ACTIVE)
    meta_summary: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class TraceSummary(BaseModel):
    """Lightweight trace info returned by MCP tools."""

    id: UUID
    name: str
    status: TraceStatus
    meta_summary: Optional[str] = None
    chunk_count: int = 0
    last_activity: Optional[str] = None
