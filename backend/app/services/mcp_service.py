"""MCP Aggregator Service – the "Capture Pipeline".

Wraps the MCPRegistry and adds automatic chunk capture:
    Tool Call  →  Execute  →  Capture Result as Chunk  →  Inbox

This closes the loop so every tool interaction becomes
part of Komorebi's persistent memory.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from ..db.repository import ChunkRepository
from ..models.chunk import ChunkCreate
from ..mcp.registry import MCPRegistry

logger = logging.getLogger(__name__)


class MCPService:
    """High-level MCP operations with auto-capture."""

    def __init__(self, registry: MCPRegistry, chunk_repo: ChunkRepository | None = None):
        self.registry = registry
        self.chunk_repo = chunk_repo

    # ------------------------------------------------------------------
    # Delegation helpers
    # ------------------------------------------------------------------

    def list_servers(self):
        return self.registry.list_servers()

    def list_tools(self):
        return self.registry.list_tools()

    def get_server(self, server_id: UUID):
        return self.registry.get_server(server_id)

    async def connect(self, server_id: UUID) -> bool:
        return await self.registry.connect(server_id)

    async def disconnect(self, server_id: UUID):
        return await self.registry.disconnect(server_id)

    async def connect_all(self):
        return await self.registry.connect_all()

    async def disconnect_all(self):
        return await self.registry.disconnect_all()

    # ------------------------------------------------------------------
    # The Capture Pipeline
    # ------------------------------------------------------------------

    async def call_tool(
        self,
        server_name: str | None,
        tool_name: str,
        arguments: dict[str, Any],
        project_id: Optional[UUID] = None,
        capture: bool = False,
    ) -> dict[str, Any]:
        """Execute a tool and optionally capture the result as a Chunk.

        Parameters
        ----------
        server_name
            If provided, route directly to this server.
            Otherwise, the registry performs name-based lookup.
        tool_name
            The name of the MCP tool to invoke.
        arguments
            JSON-serialisable arguments for the tool.
        project_id
            When provided *and* capture is True, the resulting chunk is
            associated with this project.
        capture
            If True, persist the tool result as an INBOX chunk.

        Returns
        -------
        dict with "result" and optionally "chunk_id".
        """
        # 1. Execute the tool via the registry
        result = await self.registry.call_tool(tool_name, arguments)

        # 2. Extract text content from MCP response
        text_content = self._extract_text(result)

        # 3. Auto-capture if requested
        chunk_id: UUID | None = None
        if capture and text_content and self.chunk_repo:
            chunk_id = await self._capture_as_chunk(
                server_name=server_name or "unknown",
                tool_name=tool_name,
                arguments=arguments,
                text_content=text_content,
                project_id=project_id,
            )

        response: dict[str, Any] = {
            "tool": tool_name,
            "result": result,
        }
        if chunk_id is not None:
            response["chunk_id"] = str(chunk_id)
        return response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(result: Any) -> str:
        """Pull text content out of the MCP tool response.

        MCP tool results are typically a list of content blocks.
        We concatenate all text blocks.
        """
        if isinstance(result, list):
            parts: list[str] = []
            for item in result:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif hasattr(item, "type") and item.type == "text":
                    parts.append(getattr(item, "text", ""))
            return "\n".join(parts)

        if isinstance(result, dict):
            # Fallback: wrap as JSON string
            return json.dumps(result, indent=2)

        return str(result) if result else ""

    async def _capture_as_chunk(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
        text_content: str,
        project_id: UUID | None,
    ) -> UUID:
        """Persist a tool result as an INBOX chunk."""
        log_entry = (
            f"🛠️ **Tool Execution: {server_name}:{tool_name}**\n"
            f"```json\n{json.dumps(arguments, indent=2)}\n```\n"
            f"**Output:**\n{text_content}"
        )

        chunk = await self.chunk_repo.create(
            ChunkCreate(
                content=log_entry,
                project_id=project_id,
                tags=["tool_result", f"mcp:{server_name}", tool_name],
                source=f"mcp:{server_name}:{tool_name}",
            )
        )
        logger.info(
            f"Captured tool result as chunk {chunk.id} "
            f"(tool={server_name}:{tool_name})"
        )
        return chunk.id
