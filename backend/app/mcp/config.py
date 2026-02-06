"""MCP server configuration loader.

Loads MCP server definitions from config/mcp_servers.json and
registers them with the MCPRegistry at startup.

Config format uses env-key URIs for secrets:
    {
        "mcpServers": {
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_TOKEN": "env://GITHUB_TOKEN"
                }
            }
        }
    }
"""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MCPServerFileConfig(BaseModel):
    """Config-file representation of a single MCP server.

    This is the *declarative* shape stored in mcp_servers.json.
    It is converted to the runtime MCPServerConfig on load.
    """
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    disabled: bool = False


class MCPConfig(BaseModel):
    """Root object of config/mcp_servers.json."""
    mcpServers: dict[str, MCPServerFileConfig] = Field(default_factory=dict)


def load_mcp_config(path: Path) -> MCPConfig:
    """Load and validate mcp_servers.json.

    Returns an MCPConfig with validated server entries.
    Raises FileNotFoundError or json.JSONDecodeError on bad input.
    """
    if not path.exists():
        logger.info(f"MCP config not found at {path} – no servers to load")
        return MCPConfig()

    raw = path.read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(raw)
    config = MCPConfig.model_validate(data)
    logger.info(f"Loaded {len(config.mcpServers)} MCP server(s) from {path}")
    return config


async def load_and_register_servers(
    registry: Any,  # MCPRegistry – avoid circular import
    config_path: Path | None = None,
) -> int:
    """Load servers from config and register + connect them.

    Returns the number of successfully connected servers.
    """
    from ..models.mcp import MCPServerConfig

    if config_path is None:
        config_path = Path("config/mcp_servers.json")

    config = load_mcp_config(config_path)
    connected = 0

    for name, srv in config.mcpServers.items():
        if srv.disabled:
            logger.info(f"Skipping disabled MCP server: {name}")
            continue

        runtime_config = MCPServerConfig(
            name=name,
            server_type="config",
            command=srv.command,
            args=srv.args,
            env=srv.env,        # URI values resolved later by auth.py
            enabled=True,
        )
        registry.register(runtime_config)
        logger.info(f"Registered MCP server: {name} ({srv.command})")

    # Connect all enabled servers in parallel
    results = await registry.connect_all()
    connected = sum(1 for v in results.values() if v)
    logger.info(f"Connected {connected}/{len(results)} MCP server(s)")
    return connected
