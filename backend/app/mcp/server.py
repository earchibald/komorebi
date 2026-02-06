"""Komorebi MCP Server — exposes context as tools for coding agents.

Implements the Model Context Protocol (2024-11-05 spec) over stdio
transport. External agents (Claude Code, Cursor, Windsurf) spawn
``k mcp-serve`` and communicate via JSON-RPC over stdin/stdout.

Tools exposed:
  - search_context(query, limit)
  - get_active_trace()
  - read_file_metadata(path)
  - get_related_decisions(topic, limit)
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Optional

logger = logging.getLogger(__name__)

# MCP protocol version we implement
PROTOCOL_VERSION = "2024-11-05"

# Tool definitions per MCP spec
TOOLS = [
    {
        "name": "search_context",
        "description": "Search all captured chunks and entities in Komorebi for relevant context",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "limit": {"type": "integer", "default": 10, "description": "Max results"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_active_trace",
        "description": "Returns the currently active trace with summary and chunk count",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "read_file_metadata",
        "description": "Returns CRUD event history for a specific file path tracked by k watch",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "get_related_decisions",
        "description": "Returns Decision entities relevant to a topic from the active trace",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic or keyword to match decisions against"},
                "limit": {"type": "integer", "default": 5, "description": "Max results"},
            },
            "required": ["topic"],
        },
    },
]


def _jsonrpc_response(request_id: Any, result: Any) -> dict:
    """Build a JSON-RPC 2.0 success response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


class KomorebiMCPServer:
    """MCP Server that bridges external coding agents to Komorebi data.

    Lifecycle:
        1. Agent sends ``initialize`` → we respond with capabilities
        2. Agent sends ``tools/list`` → we return tool definitions
        3. Agent sends ``tools/call`` → we dispatch to handler, return results
        4. Agent sends ``shutdown`` or closes stdin → we exit

    Transport: stdin/stdout (line-delimited JSON-RPC).
    """

    def __init__(self, db_url: Optional[str] = None) -> None:
        self._db_url = db_url
        self._initialized = False

    # ── Protocol handlers ──────────────────────────────────────

    async def handle_message(self, msg: dict) -> Optional[dict]:
        """Route a single JSON-RPC message to the appropriate handler."""
        method = msg.get("method", "")
        request_id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize":
            return self._handle_initialize(request_id, params)
        elif method == "initialized":
            # Notification — no response required
            return None
        elif method == "tools/list":
            return self._handle_tools_list(request_id)
        elif method == "tools/call":
            return await self._handle_tools_call(request_id, params)
        elif method == "shutdown":
            return _jsonrpc_response(request_id, {})
        else:
            return _jsonrpc_error(request_id, -32601, f"Method not found: {method}")

    def _handle_initialize(self, request_id: Any, params: dict) -> dict:
        self._initialized = True
        return _jsonrpc_response(request_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
            },
            "serverInfo": {
                "name": "komorebi",
                "version": "1.0.0",
            },
        })

    def _handle_tools_list(self, request_id: Any) -> dict:
        return _jsonrpc_response(request_id, {"tools": TOOLS})

    async def _handle_tools_call(self, request_id: Any, params: dict) -> dict:
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        handler = {
            "search_context": self._tool_search_context,
            "get_active_trace": self._tool_get_active_trace,
            "read_file_metadata": self._tool_read_file_metadata,
            "get_related_decisions": self._tool_get_related_decisions,
        }.get(tool_name)

        if not handler:
            return _jsonrpc_error(request_id, -32602, f"Unknown tool: {tool_name}")

        try:
            result = await handler(arguments)
            return _jsonrpc_response(request_id, {
                "content": [{"type": "text", "text": json.dumps(result, default=str)}],
            })
        except Exception as exc:
            logger.exception("Tool call failed: %s", tool_name)
            return _jsonrpc_error(request_id, -32603, str(exc))

    # ── Tool implementations ───────────────────────────────────

    async def _get_session(self):
        """Lazy-create an async DB session."""
        from ..db.database import async_session
        return async_session()

    async def _tool_search_context(self, args: dict) -> list[dict]:
        query = args.get("query", "")
        limit = args.get("limit", 10)

        async with await self._get_session() as session:
            from ..db.repository import ChunkRepository
            repo = ChunkRepository(session)
            chunks, _total = await repo.search(search_query=query, limit=limit)
            return [
                {
                    "id": str(c.id),
                    "content": c.content[:500],
                    "summary": c.summary,
                    "status": c.status.value if hasattr(c.status, "value") else c.status,
                    "created_at": str(c.created_at),
                }
                for c in chunks
            ]

    async def _tool_get_active_trace(self, args: dict) -> Optional[dict]:
        async with await self._get_session() as session:
            from ..db.trace_repository import TraceRepository
            repo = TraceRepository(session)
            active = await repo.get_active()
            if not active:
                return None
            summary = await repo.get_summary(active.id)
            return summary.model_dump(mode="json") if summary else None

    async def _tool_read_file_metadata(self, args: dict) -> dict:
        path = args.get("path", "")
        async with await self._get_session() as session:
            from ..db.file_event_repository import FileEventRepository
            repo = FileEventRepository(session)
            history = await repo.path_history(path)
            return history.model_dump(mode="json")

    async def _tool_get_related_decisions(self, args: dict) -> list[dict]:
        topic = args.get("topic", "")
        limit = args.get("limit", 5)

        async with await self._get_session() as session:
            from sqlalchemy import select
            from ..db.database import EntityTable

            # Search for decision entities matching the topic
            result = await session.execute(
                select(EntityTable)
                .where(EntityTable.entity_type == "decision")
                .where(EntityTable.value.ilike(f"%{topic}%"))
                .order_by(EntityTable.created_at.desc())
                .limit(limit)
            )
            rows = result.scalars().all()
            return [
                {
                    "entity_type": row.entity_type,
                    "value": row.value,
                    "confidence": row.confidence,
                    "context_snippet": row.context_snippet,
                    "created_at": str(row.created_at),
                }
                for row in rows
            ]

    # ── stdio event loop ───────────────────────────────────────

    async def run_stdio(self) -> None:
        """Run the MCP server reading JSON-RPC from stdin, writing to stdout.

        Each message is a single JSON object per line. We read until
        stdin closes or a ``shutdown`` method is received.
        """
        import asyncio

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line = await reader.readline()
            if not line:
                break  # stdin closed

            try:
                msg = json.loads(line.decode("utf-8").strip())
            except json.JSONDecodeError:
                continue

            response = await self.handle_message(msg)
            if response is not None:
                out = json.dumps(response) + "\n"
                sys.stdout.write(out)
                sys.stdout.flush()

            if msg.get("method") == "shutdown":
                break
