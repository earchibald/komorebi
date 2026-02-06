"""Resume models - Context Resume briefing data structures.

Provides the ProjectBriefing model returned by the resume endpoint,
and BriefingSection for structured UI rendering.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .chunk import Chunk
from .entity import Entity


class BriefingSection(BaseModel):
    """A single section of the resume briefing."""

    heading: str = Field(..., description="Section heading (e.g., 'Where You Left Off')")
    content: str = Field(..., description="Section content text")
    chunk_id: Optional[UUID] = Field(None, description="Optional linked chunk for jump-to")


class ProjectBriefing(BaseModel):
    """The synthesized 'save point' briefing for a project."""

    project_id: UUID = Field(..., description="Project this briefing is for")
    project_name: str = Field(..., description="Project display name")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this briefing was generated",
    )

    # LLM-synthesized summary (3 bullet points)
    summary: str = Field(..., description="LLM-generated 3-bullet briefing")

    # Structured sections for UI rendering
    sections: list[BriefingSection] = Field(
        default_factory=list,
        description="Parsed briefing sections with optional chunk links",
    )

    # Raw context used to generate the briefing
    recent_chunks: list[Chunk] = Field(
        default_factory=list,
        description="Last N chunks (jump-to points)",
    )
    decisions: list[Entity] = Field(
        default_factory=list,
        description="Recent decision entities",
    )
    related_context: list[str] = Field(
        default_factory=list,
        description="Content snippets from TF-IDF related chunks",
    )

    # Metadata
    ollama_available: bool = Field(True, description="Whether LLM was used for synthesis")
    context_window_usage: Optional[float] = Field(
        None, description="Fraction of context window used for synthesis (0.0-1.0)",
    )
