"""Async SQLAlchemy database setup.

Uses aiosqlite for async SQLite operations, suitable for
development and single-instance deployments.
"""

import os
from typing import AsyncGenerator

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, Float
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# Database URL - defaults to SQLite in config directory
DATABASE_URL = os.getenv("KOMOREBI_DATABASE_URL", "sqlite+aiosqlite:///./komorebi.db")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("KOMOREBI_DEBUG", "").lower() == "true",
    future=True,
)

# Async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for ORM models
Base = declarative_base()


class ChunkTable(Base):
    """SQLAlchemy model for chunks table."""
    
    __tablename__ = "chunks"
    
    id = Column(String(36), primary_key=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    project_id = Column(String(36), nullable=True, index=True)
    tags = Column(JSON, default=list)
    status = Column(String(20), default="inbox", index=True)
    source = Column(String(100), nullable=True)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ProjectTable(Base):
    """SQLAlchemy model for projects table."""
    
    __tablename__ = "projects"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    context_summary = Column(Text, nullable=True)
    compaction_depth = Column(Integer, default=0)
    last_compaction_at = Column(DateTime, nullable=True)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class EntityTable(Base):
    """SQLAlchemy model for entities table."""
    
    __tablename__ = "entities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    entity_type = Column(String(20), nullable=False, index=True)
    value = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    context_snippet = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)


class MCPServerTable(Base):
    """SQLAlchemy model for MCP server configurations."""
    
    __tablename__ = "mcp_servers"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    server_type = Column(String(100), nullable=False)
    command = Column(String(500), nullable=False)
    args = Column(JSON, default=list)
    env = Column(JSON, default=dict)
    enabled = Column(Boolean, default=True)
    status = Column(String(20), default="disconnected")
    last_error = Column(Text, nullable=True)


async def init_db() -> None:
    """Initialize the database, creating tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
