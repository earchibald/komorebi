"""Tests for Pydantic models."""

from uuid import UUID
from datetime import datetime

from backend.app.models import (
    Chunk, ChunkCreate, ChunkUpdate, ChunkStatus,
    Project, ProjectCreate, MCPServerConfig, MCPServerStatus,
)


class TestChunkModels:
    """Tests for Chunk models."""
    
    def test_chunk_create_minimal(self):
        """Test creating a chunk with minimal data."""
        chunk_create = ChunkCreate(content="Test content")
        assert chunk_create.content == "Test content"
        assert chunk_create.project_id is None
        assert chunk_create.tags == []
        assert chunk_create.source is None
    
    def test_chunk_create_full(self):
        """Test creating a chunk with all fields."""
        project_id = UUID("12345678-1234-1234-1234-123456789012")
        chunk_create = ChunkCreate(
            content="Test content",
            project_id=project_id,
            tags=["tag1", "tag2"],
            source="cli",
        )
        assert chunk_create.content == "Test content"
        assert chunk_create.project_id == project_id
        assert chunk_create.tags == ["tag1", "tag2"]
        assert chunk_create.source == "cli"
    
    def test_chunk_model(self):
        """Test the full Chunk model."""
        chunk = Chunk(content="Test content")
        
        assert isinstance(chunk.id, UUID)
        assert chunk.content == "Test content"
        assert chunk.status == ChunkStatus.INBOX
        assert chunk.summary is None
        assert chunk.tags == []
        assert isinstance(chunk.created_at, datetime)
        assert isinstance(chunk.updated_at, datetime)
    
    def test_chunk_update_partial(self):
        """Test partial chunk updates."""
        update = ChunkUpdate(status=ChunkStatus.PROCESSED)
        
        dumped = update.model_dump(exclude_unset=True)
        assert "status" in dumped
        assert "content" not in dumped
        assert "tags" not in dumped


class TestProjectModels:
    """Tests for Project models."""
    
    def test_project_create(self):
        """Test creating a project."""
        project_create = ProjectCreate(
            name="Test Project",
            description="A test project",
        )
        assert project_create.name == "Test Project"
        assert project_create.description == "A test project"
    
    def test_project_model(self):
        """Test the full Project model."""
        project = Project(name="Test Project")
        
        assert isinstance(project.id, UUID)
        assert project.name == "Test Project"
        assert project.chunk_count == 0
        assert project.context_summary is None


class TestMCPModels:
    """Tests for MCP models."""
    
    def test_mcp_server_config(self):
        """Test MCP server configuration."""
        config = MCPServerConfig(
            name="GitHub MCP",
            server_type="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
        )
        
        assert isinstance(config.id, UUID)
        assert config.name == "GitHub MCP"
        assert config.server_type == "github"
        assert config.command == "npx"
        assert config.args == ["-y", "@modelcontextprotocol/server-github"]
        assert config.enabled is True
        assert config.status == MCPServerStatus.DISCONNECTED
