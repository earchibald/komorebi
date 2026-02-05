"""MCP (Model Context Protocol) server configuration models.

Komorebi acts as an MCP host aggregator, connecting to multiple
external MCP servers (GitHub, Jira, etc.) through a unified interface.
"""

from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, SecretStr


class MCPServerStatus(str, Enum):
    """Connection status of an MCP server."""
    
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class MCPServerConfig(BaseModel):
    """Configuration for an external MCP server connection.
    
    MCP servers expose tools and resources that Komorebi can
    aggregate into its unified agentic interface.
    """
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    server_type: str = Field(..., description="Type of MCP server (e.g., 'github', 'jira', 'custom')")
    command: str = Field(..., description="Command to start the MCP server")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    enabled: bool = Field(default=True, description="Whether this server should be connected")
    status: MCPServerStatus = Field(default=MCPServerStatus.DISCONNECTED, description="Current status")
    last_error: Optional[str] = Field(None, description="Last error message if status is ERROR")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "GitHub MCP",
                    "server_type": "github",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "enabled": True,
                }
            ]
        }
    }


class MCPTool(BaseModel):
    """A tool exposed by an MCP server."""
    
    name: str = Field(..., description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    server_id: UUID = Field(..., description="ID of the MCP server providing this tool")
    input_schema: dict = Field(default_factory=dict, description="JSON Schema for tool input")
