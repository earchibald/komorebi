"""Core abstractions for Target Delivery System.

This module defines the adapter pattern for decoupling internal data
from external tool APIs. Each delivery target (GitHub, Jira, Slack, etc.)
implements a TargetAdapter that provides:
1. A schema describing the form fields needed
2. Argument mapping logic to transform form data into MCP tool args
3. Prerequisite validation (optional)

Architecture:
- TargetAdapter: Abstract base class defining the adapter interface
- TargetSchema: Pydantic model describing a target's form structure
- FieldSchema: Pydantic model describing a single form field
- FieldType: Enum of supported field types
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel


class FieldType(str, Enum):
    """Supported field types for dynamic forms."""
    TEXT = "text"
    TEXTAREA = "textarea"
    MARKDOWN = "markdown"
    TAGS = "tags"
    SELECT = "select"
    CHECKBOX = "checkbox"


class FieldSchema(BaseModel):
    """Schema for a single form field.
    
    Attributes:
        name: Field identifier (used as key in data dict)
        type: Field type (text, textarea, etc.)
        label: Human-readable label for UI
        placeholder: Optional placeholder text
        required: Whether field is required (default False)
        options: For SELECT type, list of options
        default: Default value for the field
        help_text: Optional help text displayed below field
    """
    name: str
    type: FieldType
    label: str
    placeholder: Optional[str] = None
    required: bool = False
    options: Optional[List[str]] = None
    default: Optional[Any] = None
    help_text: Optional[str] = None


class TargetSchema(BaseModel):
    """Schema describing a delivery target's form structure.
    
    This schema drives the dynamic form generation in the frontend.
    Adding a new target requires only implementing a Python adapter;
    the frontend automatically renders the appropriate form.
    
    Attributes:
        name: Unique identifier (e.g., "github_issue")
        display_name: Human-readable name (e.g., "GitHub Issue")
        description: Brief description of what this target does
        icon: Optional emoji or icon identifier
        fields: List of form fields
        schema_version: Version of schema format (default "1.0")
    """
    name: str
    display_name: str
    description: str
    icon: Optional[str] = None
    fields: List[FieldSchema]
    schema_version: str = "1.0"


class TargetAdapter(ABC):
    """Abstract base class for delivery target adapters.
    
    Each concrete adapter (GitHubIssueAdapter, JiraTicketAdapter, etc.)
    must implement:
    1. schema property: Returns TargetSchema describing the form
    2. mcp_tool_name property: Returns the MCP tool identifier
    3. map_arguments(): Transforms form data into MCP tool args
    4. validate_prerequisites(): Checks if target is usable (optional)
    
    Example:
        class GitHubIssueAdapter(TargetAdapter):
            @property
            def schema(self) -> TargetSchema:
                return TargetSchema(
                    name="github_issue",
                    display_name="GitHub Issue",
                    fields=[...]
                )
            
            @property
            def mcp_tool_name(self) -> str:
                return "github.create_issue"
            
            def map_arguments(self, data: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "owner": data.get("repo_owner"),
                    "repo": data.get("repo_name"),
                    "title": data["title"],
                    "body": data["body"]
                }
    """
    
    @property
    @abstractmethod
    def schema(self) -> TargetSchema:
        """Return the target's schema definition.
        
        This schema describes the form fields needed for this target.
        The frontend will automatically generate a form based on this schema.
        """
        pass
    
    @property
    @abstractmethod
    def mcp_tool_name(self) -> str:
        """Return the MCP tool name to call.
        
        Example: "github.create_issue", "jira.create_ticket"
        """
        pass
    
    @abstractmethod
    def map_arguments(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map form data to MCP tool arguments.
        
        Args:
            data: Dictionary of form field values (keys match field names)
        
        Returns:
            Dictionary of MCP tool arguments
        
        Example:
            Input:  {"title": "Bug", "labels": "bug,urgent"}
            Output: {"title": "Bug", "labels": ["bug", "urgent"]}
        """
        pass
    
    def validate_prerequisites(self) -> bool:
        """Validate that this target is usable.
        
        Override this to check for:
        - Required MCP server is running
        - Authentication is configured
        - Required context (repo, workspace) is available
        
        Returns:
            True if target is usable, False otherwise
        
        Note: Default implementation returns True (no validation)
        """
        return True
