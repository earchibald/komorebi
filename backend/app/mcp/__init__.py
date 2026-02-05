"""MCP (Model Context Protocol) aggregator layer.

Komorebi acts as a "Host of Hosts", connecting to multiple
external MCP servers and aggregating their tools into a
unified interface.
"""

from .client import MCPClient
from .registry import MCPRegistry, mcp_registry

__all__ = [
    "MCPClient",
    "MCPRegistry",
    "mcp_registry",
]
