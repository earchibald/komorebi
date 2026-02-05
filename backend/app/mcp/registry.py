"""MCP server registry for managing multiple server connections.

The registry maintains connections to multiple MCP servers
and provides a unified interface for discovering and calling tools.
"""

from typing import Any, Optional
from uuid import UUID

from ..models.mcp import MCPServerConfig, MCPServerStatus, MCPTool
from .client import MCPClient


class MCPRegistry:
    """Registry for managing MCP server connections.
    
    Provides:
    - Server lifecycle management (connect/disconnect)
    - Tool discovery across all connected servers
    - Unified tool calling interface
    """
    
    def __init__(self):
        self._clients: dict[UUID, MCPClient] = {}
        self._configs: dict[UUID, MCPServerConfig] = {}
    
    def register(self, config: MCPServerConfig) -> None:
        """Register an MCP server configuration."""
        self._configs[config.id] = config
        self._clients[config.id] = MCPClient(config)
    
    def unregister(self, server_id: UUID) -> None:
        """Unregister an MCP server."""
        self._clients.pop(server_id, None)
        self._configs.pop(server_id, None)
    
    async def connect(self, server_id: UUID) -> bool:
        """Connect to a specific MCP server."""
        client = self._clients.get(server_id)
        if not client:
            return False
        return await client.connect()
    
    async def disconnect(self, server_id: UUID) -> None:
        """Disconnect from a specific MCP server."""
        client = self._clients.get(server_id)
        if client:
            await client.disconnect()
    
    async def connect_all(self) -> dict[UUID, bool]:
        """Connect to all enabled MCP servers."""
        results = {}
        for server_id, config in self._configs.items():
            if config.enabled:
                results[server_id] = await self.connect(server_id)
        return results
    
    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for client in self._clients.values():
            await client.disconnect()
    
    def get_server(self, server_id: UUID) -> Optional[MCPServerConfig]:
        """Get server configuration by ID."""
        return self._configs.get(server_id)
    
    def list_servers(self) -> list[MCPServerConfig]:
        """List all registered server configurations."""
        return list(self._configs.values())
    
    def list_tools(self) -> list[MCPTool]:
        """List all available tools across connected servers."""
        tools = []
        for client in self._clients.values():
            if client.status == MCPServerStatus.CONNECTED:
                tools.extend(client.tools)
        return tools
    
    def find_tool(self, tool_name: str) -> Optional[tuple[MCPClient, MCPTool]]:
        """Find a tool by name and return the client and tool."""
        for client in self._clients.values():
            if client.status == MCPServerStatus.CONNECTED:
                for tool in client.tools:
                    if tool.name == tool_name:
                        return (client, tool)
        return None
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool by name, routing to the appropriate server."""
        result = self.find_tool(tool_name)
        if not result:
            raise ValueError(f"Tool not found: {tool_name}")
        
        client, tool = result
        return await client.call_tool(tool_name, arguments)


# Global registry instance
mcp_registry = MCPRegistry()
