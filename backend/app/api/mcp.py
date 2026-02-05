"""MCP API endpoints.

Provides management of MCP server connections and
unified access to aggregated tools.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException

from ..models.mcp import MCPServerConfig, MCPServerStatus, MCPTool
from ..mcp import mcp_registry
from ..core.events import event_bus, ChunkEvent, EventType

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/servers", response_model=list[MCPServerConfig])
async def list_servers() -> list[MCPServerConfig]:
    """List all registered MCP servers."""
    return mcp_registry.list_servers()


@router.post("/servers", status_code=201)
async def register_server(config: MCPServerConfig) -> MCPServerConfig:
    """Register a new MCP server configuration."""
    mcp_registry.register(config)
    return config


@router.get("/servers/{server_id}", response_model=MCPServerConfig)
async def get_server(server_id: UUID) -> MCPServerConfig:
    """Get a specific MCP server configuration."""
    server = mcp_registry.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.delete("/servers/{server_id}", status_code=204)
async def unregister_server(server_id: UUID) -> None:
    """Unregister an MCP server."""
    server = mcp_registry.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    await mcp_registry.disconnect(server_id)
    mcp_registry.unregister(server_id)


@router.post("/servers/{server_id}/connect")
async def connect_server(server_id: UUID) -> dict:
    """Connect to a specific MCP server."""
    server = mcp_registry.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    success = await mcp_registry.connect(server_id)
    
    await event_bus.publish(ChunkEvent(
        event_type=EventType.MCP_STATUS_CHANGED,
        chunk_id=server_id,
        data={
            "server_id": str(server_id),
            "status": server.status.value,
            "connected": success,
        },
    ))
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect: {server.last_error}",
        )
    
    return {
        "server_id": str(server_id),
        "status": server.status.value,
        "tools": [t.name for t in mcp_registry._clients[server_id].tools],
    }


@router.post("/servers/{server_id}/disconnect")
async def disconnect_server(server_id: UUID) -> dict:
    """Disconnect from a specific MCP server."""
    server = mcp_registry.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    await mcp_registry.disconnect(server_id)
    
    await event_bus.publish(ChunkEvent(
        event_type=EventType.MCP_STATUS_CHANGED,
        chunk_id=server_id,
        data={
            "server_id": str(server_id),
            "status": MCPServerStatus.DISCONNECTED.value,
        },
    ))
    
    return {
        "server_id": str(server_id),
        "status": MCPServerStatus.DISCONNECTED.value,
    }


@router.get("/tools", response_model=list[MCPTool])
async def list_tools() -> list[MCPTool]:
    """List all available tools from connected MCP servers."""
    return mcp_registry.list_tools()


@router.post("/tools/{tool_name}/call")
async def call_tool(tool_name: str, arguments: dict[str, Any]) -> dict:
    """Call a tool by name with the provided arguments."""
    try:
        result = await mcp_registry.call_tool(tool_name, arguments)
        return {
            "tool": tool_name,
            "result": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect-all")
async def connect_all_servers() -> dict:
    """Connect to all enabled MCP servers."""
    results = await mcp_registry.connect_all()
    return {
        "results": {str(k): v for k, v in results.items()},
        "connected": sum(1 for v in results.values() if v),
        "failed": sum(1 for v in results.values() if not v),
    }


@router.post("/disconnect-all")
async def disconnect_all_servers() -> dict:
    """Disconnect from all MCP servers."""
    await mcp_registry.disconnect_all()
    return {"message": "All servers disconnected"}
