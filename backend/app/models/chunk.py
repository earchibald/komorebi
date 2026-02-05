"""Chunk model - the fundamental unit of captured information.

A Chunk represents a piece of information captured during work:
- Raw thoughts, notes, or ideas
- Code snippets
- Links and references
- Task fragments

Chunks follow the "Capture Now, Refine Later" philosophy.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ChunkStatus(str, Enum):
    """Status of a chunk in the processing pipeline."""
    
    INBOX = "inbox"  # Raw, unprocessed capture
    PROCESSED = "processed"  # Analyzed and enriched
    COMPACTED = "compacted"  # Summarized into higher-level context
    ARCHIVED = "archived"  # No longer active but preserved


class ChunkCreate(BaseModel):
    """Schema for creating a new chunk (fast capture)."""
    
    content: str = Field(..., min_length=1, description="The raw content to capture")
    project_id: Optional[UUID] = Field(None, description="Optional project association")
    tags: list[str] = Field(default_factory=list, description="Optional tags for categorization")
    source: Optional[str] = Field(None, description="Where this chunk originated (e.g., 'cli', 'api', 'mcp')")


class ChunkUpdate(BaseModel):
    """Schema for updating an existing chunk."""
    
    content: Optional[str] = Field(None, min_length=1, description="Updated content")
    project_id: Optional[UUID] = Field(None, description="Updated project association")
    tags: Optional[list[str]] = Field(None, description="Updated tags")
    status: Optional[ChunkStatus] = Field(None, description="Updated status")
    summary: Optional[str] = Field(None, description="AI-generated summary")


class Chunk(BaseModel):
    """The fundamental unit of captured information in Komorebi.
    
    A Chunk starts in the INBOX status and can be:
    1. PROCESSED - when AI has analyzed and enriched it
    2. COMPACTED - when it's been summarized into context
    3. ARCHIVED - when no longer needed but preserved
    """
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    content: str = Field(..., description="The captured content")
    summary: Optional[str] = Field(None, description="AI-generated summary")
    project_id: Optional[UUID] = Field(None, description="Associated project")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    status: ChunkStatus = Field(default=ChunkStatus.INBOX, description="Processing status")
    source: Optional[str] = Field(None, description="Origin of the chunk")
    token_count: Optional[int] = Field(None, description="Estimated token count")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": "Need to implement the SSE endpoint for real-time updates",
                    "tags": ["backend", "streaming"],
                    "status": "inbox",
                    "source": "cli",
                }
            ]
        }
    }
