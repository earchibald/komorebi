"""Database layer for Komorebi.

Provides async SQLAlchemy setup with SQLite and repository pattern
for data access.
"""

from .database import get_db, init_db, engine, async_session
from .repository import ChunkRepository, ProjectRepository, EntityRepository
from .trace_repository import TraceRepository
from .file_event_repository import FileEventRepository

__all__ = [
    "get_db",
    "init_db", 
    "engine",
    "async_session",
    "ChunkRepository",
    "ProjectRepository",
    "EntityRepository",
    "TraceRepository",
    "FileEventRepository",
]
