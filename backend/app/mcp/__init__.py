"""MCP (Model Context Protocol) aggregator layer.

Komorebi acts as a "Host of Hosts", connecting to multiple
external MCP servers and aggregating their tools into a
unified interface.
"""

from .auth import SecretFactory, SecretProvider, EnvProvider
from .client import MCPClient
from .config import MCPConfig, MCPServerFileConfig, load_mcp_config, load_and_register_servers
from .registry import MCPRegistry, mcp_registry

__all__ = [
    "MCPClient",
    "MCPConfig",
    "MCPServerFileConfig",
    "MCPRegistry",
    "SecretFactory",
    "SecretProvider",
    "EnvProvider",
    "load_mcp_config",
    "load_and_register_servers",
    "mcp_registry",
]
