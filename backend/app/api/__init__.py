"""API routes for Komorebi.

Provides RESTful endpoints for:
- Chunks: CRUD operations and fast capture
- Projects: Organization and context management
- MCP: Server management and tool discovery
- SSE: Real-time event streaming
"""

from .chunks import router as chunks_router
from .projects import router as projects_router
from .mcp import router as mcp_router
from .sse import router as sse_router

__all__ = [
    "chunks_router",
    "projects_router", 
    "mcp_router",
    "sse_router",
]
