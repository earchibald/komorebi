"""Unit tests for Target Delivery System - Adapters and Registry."""
import pytest
from typing import Dict, Any

# Tests will fail until we implement the modules
# These imports will fail initially - expected for Red phase
try:
    from backend.app.targets.base import (
        TargetAdapter,
        TargetSchema,
        FieldSchema,
        FieldType,
    )
    from backend.app.targets.registry import TargetRegistry
    from backend.app.targets.github import GitHubIssueAdapter
except ImportError:
    pytest.skip("Target modules not yet implemented", allow_module_level=True)


# ─────────────────────────────────────────────────────────────
# Base Models Tests
# ─────────────────────────────────────────────────────────────

def test_field_type_enum():
    """Test FieldType enum has required values."""
    assert FieldType.TEXT == "text"
    assert FieldType.TEXTAREA == "textarea"
    assert FieldType.MARKDOWN == "markdown"
    assert FieldType.TAGS == "tags"
    assert FieldType.SELECT == "select"
    assert FieldType.CHECKBOX == "checkbox"


def test_field_schema_creation():
    """Test FieldSchema model validation."""
    field = FieldSchema(
        name="title",
        type=FieldType.TEXT,
        label="Title",
        placeholder="Enter title",
        required=True
    )
    assert field.name == "title"
    assert field.type == FieldType.TEXT
    assert field.required is True
    assert field.placeholder == "Enter title"


def test_field_schema_defaults():
    """Test FieldSchema uses default values."""
    field = FieldSchema(
        name="tags",
        type=FieldType.TAGS,
        label="Labels"
    )
    assert field.required is False
    assert field.placeholder is None
    assert field.options is None
    assert field.default is None


def test_target_schema_creation():
    """Test TargetSchema model validation."""
    schema = TargetSchema(
        name="test_target",
        display_name="Test Target",
        description="A test target",
        icon="🧪",
        fields=[
            FieldSchema(
                name="title",
                type=FieldType.TEXT,
                label="Title",
                required=True
            )
        ]
    )
    assert schema.name == "test_target"
    assert schema.display_name == "Test Target"
    assert len(schema.fields) == 1
    assert schema.schema_version == "1.0"


def test_target_schema_version_default():
    """Test TargetSchema has default version."""
    schema = TargetSchema(
        name="test",
        display_name="Test",
        description="Test",
        fields=[]
    )
    assert schema.schema_version == "1.0"


# ─────────────────────────────────────────────────────────────
# Registry Tests
# ─────────────────────────────────────────────────────────────

def test_registry_register_adapter():
    """Test registering an adapter."""
    # Clear registry first
    TargetRegistry._targets = {}
    
    adapter = GitHubIssueAdapter()
    TargetRegistry.register(adapter)
    
    assert "github_issue" in TargetRegistry._targets


def test_registry_get_adapter():
    """Test retrieving registered adapter."""
    TargetRegistry._targets = {}
    
    adapter = GitHubIssueAdapter()
    TargetRegistry.register(adapter)
    
    retrieved = TargetRegistry.get("github_issue")
    assert isinstance(retrieved, GitHubIssueAdapter)


def test_registry_get_nonexistent_adapter():
    """Test that getting nonexistent adapter raises ValueError."""
    TargetRegistry._targets = {}
    
    with pytest.raises(ValueError, match="not registered"):
        TargetRegistry.get("nonexistent_target")


def test_registry_list_schemas():
    """Test listing all registered schemas."""
    TargetRegistry._targets = {}
    
    adapter1 = GitHubIssueAdapter()
    TargetRegistry.register(adapter1)
    
    schemas = TargetRegistry.list_schemas()
    assert len(schemas) == 1
    assert schemas[0].name == "github_issue"


def test_registry_get_schema():
    """Test getting schema by name."""
    TargetRegistry._targets = {}
    
    adapter = GitHubIssueAdapter()
    TargetRegistry.register(adapter)
    
    schema = TargetRegistry.get_schema("github_issue")
    assert schema.name == "github_issue"
    assert schema.display_name == "GitHub Issue"


# ─────────────────────────────────────────────────────────────
# GitHub Adapter Tests
# ─────────────────────────────────────────────────────────────

def test_github_adapter_schema():
    """Test GitHub adapter returns valid schema."""
    adapter = GitHubIssueAdapter()
    schema = adapter.schema
    
    assert schema.name == "github_issue"
    assert schema.display_name == "GitHub Issue"
    assert schema.icon == "🐙"
    assert len(schema.fields) == 4
    
    # Check field names
    field_names = [f.name for f in schema.fields]
    assert "title" in field_names
    assert "body" in field_names
    assert "labels" in field_names
    assert "assignees" in field_names


def test_github_adapter_mcp_tool_name():
    """Test GitHub adapter returns correct MCP tool name."""
    adapter = GitHubIssueAdapter()
    assert adapter.mcp_tool_name == "github.create_issue"


def test_github_adapter_map_arguments_basic():
    """Test GitHub adapter maps basic arguments."""
    adapter = GitHubIssueAdapter()
    
    data = {
        "title": "Bug Report",
        "body": "Description of the bug",
    }
    
    result = adapter.map_arguments(data)
    
    assert result["title"] == "Bug Report"
    assert result["body"] == "Description of the bug"
    assert "owner" in result
    assert "repo" in result


def test_github_adapter_map_arguments_with_labels():
    """Test GitHub adapter splits labels correctly."""
    adapter = GitHubIssueAdapter()
    
    data = {
        "title": "Feature Request",
        "body": "New feature",
        "labels": "enhancement,priority"
    }
    
    result = adapter.map_arguments(data)
    
    assert result["labels"] == ["enhancement", "priority"]


def test_github_adapter_map_arguments_empty_labels():
    """Test GitHub adapter handles missing labels."""
    adapter = GitHubIssueAdapter()
    
    data = {
        "title": "Test",
        "body": "Content",
    }
    
    result = adapter.map_arguments(data)
    
    assert result["labels"] == []


def test_github_adapter_map_arguments_with_assignees():
    """Test GitHub adapter splits assignees correctly."""
    adapter = GitHubIssueAdapter()
    
    data = {
        "title": "Task",
        "body": "Content",
        "assignees": "user1,user2"
    }
    
    result = adapter.map_arguments(data)
    
    assert result["assignees"] == ["user1", "user2"]


def test_github_adapter_validate_prerequisites():
    """Test GitHub adapter prerequisite validation."""
    adapter = GitHubIssueAdapter()
    
    # Placeholder implementation always returns True
    result = adapter.validate_prerequisites()
    assert result is True


# ─────────────────────────────────────────────────────────────
# Abstract Adapter Tests
# ─────────────────────────────────────────────────────────────

def test_cannot_instantiate_abstract_adapter():
    """Test that TargetAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError):
        TargetAdapter()


def test_adapter_must_implement_schema():
    """Test that adapters must implement schema property."""
    class IncompleteAdapter(TargetAdapter):
        def map_arguments(self, data: Dict[str, Any]) -> Dict[str, Any]:
            return data
        
        @property
        def mcp_tool_name(self) -> str:
            return "test.tool"
        
        def validate_prerequisites(self) -> bool:
            return True
    
    with pytest.raises(TypeError):
        IncompleteAdapter()
