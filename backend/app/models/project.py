"""Project model - container for organizing chunks.

Projects group related chunks together and maintain
aggregate context for a particular work stream.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, description="Project description")


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated name")
    description: Optional[str] = Field(None, description="Updated description")
    context_summary: Optional[str] = Field(None, description="AI-generated context summary")


class Project(BaseModel):
    """A project groups related chunks and maintains context.
    
    The context_summary field contains a compacted summary of all
    chunks in this project, enabling efficient context retrieval.
    """
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    context_summary: Optional[str] = Field(None, description="Compacted context from all chunks")
    chunk_count: int = Field(default=0, description="Number of chunks in this project")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Komorebi Development",
                    "description": "Building the cognitive infrastructure system",
                    "chunk_count": 42,
                }
            ]
        }
    }
