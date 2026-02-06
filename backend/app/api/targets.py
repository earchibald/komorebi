"""API endpoints for Target Delivery System.

This module provides REST endpoints for:
1. Listing available target schemas
2. Retrieving specific target schemas
3. Dispatching data to targets via MCP

Endpoints:
- GET /api/v1/targets/schemas - List all registered target schemas
- GET /api/v1/targets/{name}/schema - Get specific target schema
- POST /api/v1/dispatch - Dispatch data to a target
"""
from typing import Dict, List
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.targets.registry import TargetRegistry
from backend.app.targets.base import TargetSchema
from backend.app.models.dispatch import DispatchRequest, DispatchResponse
from backend.app.services.mcp_service import MCPService
from backend.app.mcp import mcp_registry
from backend.app.db import get_db, ChunkRepository

router = APIRouter(prefix="/api/v1", tags=["targets"])


def _get_mcp_service(db: AsyncSession = Depends(get_db)) -> MCPService:
    """DI: build MCPService with chunk_repo."""
    return MCPService(mcp_registry, ChunkRepository(db))


@router.get("/targets/schemas", response_model=Dict[str, List[TargetSchema]])
async def list_target_schemas():
    """List all registered target schemas.
    
    Returns all schemas from registered adapters. The frontend uses
    this to build the target selector dropdown.
    
    Returns:
        Dictionary with "schemas" key containing list of TargetSchema objects
    
    Example Response:
        {
            "schemas": [
                {
                    "name": "github_issue",
                    "display_name": "GitHub Issue",
                    "description": "Create a new issue in a GitHub repository",
                    "icon": "🐙",
                    "fields": [...],
                    "schema_version": "1.0"
                }
            ]
        }
    """
    schemas = TargetRegistry.list_schemas()
    return {"schemas": schemas}


@router.get("/targets/{name}/schema", response_model=TargetSchema)
async def get_target_schema(name: str):
    """Get schema for a specific target.
    
    Args:
        name: Target name (e.g., "github_issue")
    
    Returns:
        TargetSchema for the specified target
    
    Raises:
        404: If target is not registered
    
    Example Response:
        {
            "name": "github_issue",
            "display_name": "GitHub Issue",
            "description": "Create a new issue in a GitHub repository",
            "icon": "🐙",
            "fields": [
                {
                    "name": "title",
                    "type": "text",
                    "label": "Title",
                    "required": true,
                    ...
                },
                ...
            ],
            "schema_version": "1.0"
        }
    """
    try:
        schema = TargetRegistry.get_schema(name)
        return schema
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target '{name}' not found: {str(e)}"
        )


@router.post("/dispatch", response_model=DispatchResponse)
async def dispatch_to_target(
    request: DispatchRequest,
    mcp_service: MCPService = Depends(_get_mcp_service)
):
    """Dispatch data to a target via MCP.
    
    This endpoint:
    1. Retrieves the target adapter from the registry
    2. Merges form data with context
    3. Maps arguments using the adapter
    4. Calls the MCP tool via mcp_service
    5. Returns the result
    
    Args:
        request: DispatchRequest with target_name, data, and context
        mcp_service: Injected MCPService instance
    
    Returns:
        DispatchResponse with success status and result/error
    
    Raises:
        400: If target is not registered
        500: If MCP call fails
    
    Example Request:
        {
            "target_name": "github_issue",
            "data": {
                "title": "Bug Report",
                "body": "Description of the bug",
                "labels": "bug,urgent"
            },
            "context": {
                "repo_owner": "myorg",
                "repo_name": "myrepo"
            }
        }
    
    Example Response:
        {
            "success": true,
            "target_name": "github_issue",
            "mcp_tool": "github.create_issue",
            "result": {
                "html_url": "https://github.com/myorg/myrepo/issues/123",
                "number": 123
            }
        }
    """
    try:
        # Get the target adapter
        adapter = TargetRegistry.get(request.target_name)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target not registered: {str(e)}"
        )
    
    try:
        # Merge form data with context
        merged_data = {**request.data, **request.context}
        
        # Map arguments using the adapter
        mcp_args = adapter.map_arguments(merged_data)
        
        # Call the MCP tool (no capture, direct call)
        result = await mcp_service.call_tool(
            server_name=None,  # Let registry auto-route
            tool_name=adapter.mcp_tool_name,
            arguments=mcp_args,
            capture=False  # Don't auto-capture; handled separately if needed
        )
        
        # Extract the tool result (it's wrapped in {"tool": ..., "result": ...})
        tool_result = result.get("result", result)
        
        return DispatchResponse(
            success=True,
            target_name=request.target_name,
            mcp_tool=adapter.mcp_tool_name,
            result=tool_result
        )
    
    except Exception as e:
        # Log the error for debugging
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MCP call failed: {str(e)}"
        )
