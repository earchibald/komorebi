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
    token_count: Optional[int] = Field(None, description="Estimated token count")


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


class SearchResult(BaseModel):
    """Search result wrapper with pagination metadata."""
    
    items: list[Chunk] = Field(default_factory=list, description="Matching chunks")
    total: int = Field(..., description="Total number of matching chunks")
    limit: int = Field(..., description="Page size used")
    offset: int = Field(..., description="Page offset used")
    query: Optional[str] = Field(None, description="Search query used")


# --- Module 6: Enhanced Stats ---

class WeekBucket(BaseModel):
    """A week's chunk activity."""
    week_start: str = Field(..., description="ISO date e.g. '2026-02-03'")
    count: int = Field(..., description="Chunks created that week")


class DashboardStats(BaseModel):
    """Enhanced dashboard statistics with trends and insights."""
    
    # Existing counters
    inbox: int = Field(0, description="Inbox chunk count")
    processed: int = Field(0, description="Processed chunk count")
    compacted: int = Field(0, description="Compacted chunk count")
    archived: int = Field(0, description="Archived chunk count")
    total: int = Field(0, description="Total chunk count")
    
    # Trends
    by_week: list[WeekBucket] = Field(default_factory=list, description="Past 8 weeks of activity")
    
    # Insights
    oldest_inbox_age_days: Optional[int] = Field(None, description="Days since oldest inbox chunk")
    most_active_project: Optional[str] = Field(None, description="Name of project with most chunks")
    most_active_project_count: int = Field(0, description="Chunk count for most active project")
    entity_count: int = Field(0, description="Total entities extracted")
    
    # Per-project breakdown
    by_project: list[dict] = Field(default_factory=list, description="Per-project chunk counts")


# --- Module 6: Timeline ---

class TimelineGranularity(str, Enum):
    """Supported timeline granularity levels."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class TimelineBucket(BaseModel):
    """A time bucket with its chunks."""
    bucket_label: str = Field(..., description="Human-readable label e.g. 'Feb 3-9'")
    bucket_start: str = Field(..., description="ISO datetime of bucket start")
    chunk_count: int = Field(0, description="Number of chunks in this bucket")
    by_status: dict[str, int] = Field(default_factory=dict, description="Status breakdown")
    chunk_ids: list[str] = Field(default_factory=list, description="Chunk IDs in this bucket")


class TimelineResponse(BaseModel):
    """Timeline of chunks grouped by date bucket."""
    granularity: str = Field(..., description="Granularity used")
    buckets: list[TimelineBucket] = Field(default_factory=list, description="Time buckets")
    total_chunks: int = Field(0, description="Total chunks across all buckets")


# --- Module 6: Related Chunks ---

class RelatedChunk(BaseModel):
    """A chunk with its similarity score."""
    chunk: Chunk = Field(..., description="The related chunk")
    similarity: float = Field(..., description="Cosine similarity 0.0-1.0")
    shared_terms: list[str] = Field(default_factory=list, description="Top contributing terms")


class RelatedChunksResponse(BaseModel):
    """Response from related chunks endpoint."""
    source_chunk_id: str = Field(..., description="ID of the source chunk")
    related: list[RelatedChunk] = Field(default_factory=list, description="Related chunks")
    computation_ms: int = Field(0, description="Computation time in milliseconds")
