"""MCP API endpoints.

Provides management of MCP server connections and
unified access to aggregated tools.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db, ChunkRepository
from ..models.mcp import MCPServerConfig, MCPServerStatus, MCPTool
from ..mcp import mcp_registry
from ..services.mcp_service import MCPService
from ..core.events import event_bus, ChunkEvent, EventType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["mcp"])


def _get_service(db: AsyncSession = Depends(get_db)) -> MCPService:
    """DI: build MCPService with a chunk_repo for capture."""
    return MCPService(mcp_registry, ChunkRepository(db))


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
    
    client = mcp_registry._clients.get(server_id)
    tool_names = [t.name for t in client.tools] if client else []
    
    return {
        "server_id": str(server_id),
        "status": server.status.value,
        "tools": tool_names,
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


@router.post("/{server_name}/reconnect")
async def reconnect_server(server_name: str) -> dict:
    """Disconnect then reconnect a server by name."""
    # Find server by name
    for config in mcp_registry.list_servers():
        if config.name == server_name:
            await mcp_registry.disconnect(config.id)
            success = await mcp_registry.connect(config.id)
            await event_bus.publish(ChunkEvent(
                event_type=EventType.MCP_STATUS_CHANGED,
                chunk_id=config.id,
                data={
                    "server_id": str(config.id),
                    "status": config.status.value,
                    "connected": success,
                },
            ))
            return {
                "server_id": str(config.id),
                "name": server_name,
                "status": config.status.value,
                "connected": success,
            }
    raise HTTPException(status_code=404, detail=f"Server not found: {server_name}")


@router.get("/tools", response_model=list[MCPTool])
async def list_tools() -> list[MCPTool]:
    """List all available tools from connected MCP servers."""
    return mcp_registry.list_tools()


@router.post("/tools/{tool_name}/call")
async def call_tool(
    tool_name: str,
    arguments: dict[str, Any],
    capture: bool = Query(False, description="Auto-capture result as chunk"),
    project_id: Optional[UUID] = Query(None, description="Project to associate captured chunk with"),
    service: MCPService = Depends(_get_service),
) -> dict:
    """Call a tool by name with the provided arguments.
    
    With capture=true, the tool result is automatically saved as an
    INBOX chunk for compaction.
    """
    try:
        result = await service.call_tool(
            server_name=None,
            tool_name=tool_name,
            arguments=arguments,
            project_id=project_id,
            capture=capture,
        )

        # Publish SSE event if chunk was captured
        if "chunk_id" in result:
            await event_bus.publish(ChunkEvent(
                event_type=EventType.CHUNK_CREATED,
                chunk_id=UUID(result["chunk_id"]),
                data={"source": f"mcp:{tool_name}"},
            ))

        return result
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
