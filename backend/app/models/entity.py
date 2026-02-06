"""Entity model - structured data extracted from chunks.

Entities capture actionable signals (errors, URLs, decisions, code refs)
for indexing and future routing.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Supported entity categories."""

    ERROR = "error"
    URL = "url"
    TOOL_ID = "tool_id"
    DECISION = "decision"
    CODE_REF = "code_ref"


class EntityCreate(BaseModel):
    """Schema for creating an entity."""

    chunk_id: UUID = Field(..., description="Source chunk identifier")
    project_id: UUID = Field(..., description="Associated project identifier")
    entity_type: EntityType = Field(..., description="Entity category")
    value: str = Field(..., min_length=1, description="Extracted entity value")
    confidence: float = Field(default=1.0, description="Confidence score 0.0-1.0")
    context_snippet: Optional[str] = Field(
        None,
        description="Sentence or snippet containing the entity",
    )


class Entity(BaseModel):
    """Entity record returned from the API."""

    id: Optional[int] = Field(None, description="Primary key")
    chunk_id: UUID = Field(..., description="Source chunk identifier")
    project_id: UUID = Field(..., description="Associated project identifier")
    entity_type: EntityType = Field(..., description="Entity category")
    value: str = Field(..., description="Extracted entity value")
    confidence: float = Field(default=1.0, description="Confidence score 0.0-1.0")
    context_snippet: Optional[str] = Field(
        None,
        description="Sentence or snippet containing the entity",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
