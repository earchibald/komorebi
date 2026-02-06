"""File event models for filesystem awareness.

FileEvents track filesystem changes detected by `k watch`,
recording lightweight metadata (path, hash, CRUD operation)
into the active trace.
"""

from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CrudOp(str, Enum):
    """Filesystem operation type."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


class FileEventCreate(BaseModel):
    """Schema for creating a file event."""

    trace_id: UUID = Field(..., description="Trace this event belongs to")
    path: str = Field(..., min_length=1, description="Absolute file path")
    crud_op: CrudOp = Field(..., description="Type of filesystem operation")
    size_bytes: Optional[int] = Field(None, ge=0, description="File size in bytes")
    hash_prefix: Optional[str] = Field(None, description="sha256 of first 8KB")
    mime_type: Optional[str] = Field(None, description="Detected MIME type")


class FileEvent(BaseModel):
    """A lightweight record of a filesystem change."""

    id: UUID = Field(default_factory=uuid4)
    trace_id: UUID = Field(..., description="Trace this event belongs to")
    path: str = Field(..., description="Absolute file path")
    crud_op: CrudOp
    size_bytes: Optional[int] = None
    hash_prefix: Optional[str] = None
    mime_type: Optional[str] = None
    created_at: str = ""


class FileEventHistory(BaseModel):
    """CRUD history of a single file path."""

    path: str
    events: list[FileEvent] = Field(default_factory=list)
    current_hash: Optional[str] = None
    last_modified: Optional[str] = None
