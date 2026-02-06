"""Models for Target Delivery System dispatch operations.

This module defines the request/response models for dispatching
data to external targets via the MCP aggregator.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class DispatchRequest(BaseModel):
    """Request model for dispatching data to a target.
    
    Attributes:
        target_name: Name of the target adapter (e.g., "github_issue")
        data: Dictionary of form field values (keys match field names)
        context: Dictionary of contextual data (repo, workspace, etc.)
    
    Example:
        {
            "target_name": "github_issue",
            "data": {
                "title": "Bug Report",
                "body": "Description",
                "labels": "bug,urgent"
            },
            "context": {
                "repo_owner": "myorg",
                "repo_name": "myrepo"
            }
        }
    """
    target_name: str = Field(..., description="Name of the target adapter")
    data: Dict[str, Any] = Field(..., description="Form field values")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual data (repo, workspace, etc.)"
    )


class DispatchResponse(BaseModel):
    """Response model for dispatch operations.
    
    Attributes:
        success: Whether the dispatch succeeded
        target_name: Name of the target adapter used
        mcp_tool: Name of the MCP tool called
        result: Result data from the MCP tool call
        error: Error message if dispatch failed
    
    Example Success:
        {
            "success": true,
            "target_name": "github_issue",
            "mcp_tool": "github.create_issue",
            "result": {
                "html_url": "https://github.com/owner/repo/issues/123",
                "number": 123
            }
        }
    
    Example Error:
        {
            "success": false,
            "target_name": "github_issue",
            "mcp_tool": "github.create_issue",
            "error": "MCP connection failed"
        }
    """
    success: bool = Field(..., description="Whether dispatch succeeded")
    target_name: str = Field(..., description="Target adapter name")
    mcp_tool: str = Field(..., description="MCP tool name called")
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Result data from MCP tool"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if dispatch failed"
    )
