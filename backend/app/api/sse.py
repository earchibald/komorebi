"""SSE (Server-Sent Events) endpoint for real-time updates.

Provides a streaming endpoint for clients to receive
live updates about chunks, projects, and system events.
"""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from ..core.events import event_bus

router = APIRouter(prefix="/sse", tags=["sse"])


@router.get("/events")
async def stream_events():
    """Stream real-time events to connected clients.
    
    Events include:
    - chunk.created: New chunk captured
    - chunk.updated: Chunk processed or modified
    - chunk.deleted: Chunk removed
    - project.updated: Project context changed
    - compaction.started: Compaction process began
    - compaction.completed: Compaction finished
    - mcp.status_changed: MCP server connection status changed
    """
    return EventSourceResponse(
        event_bus.subscribe(),
        ping=15,  # Sends a comment line ": ping" every 15 seconds
        media_type="text/event-stream"
    )


@router.get("/status")
async def get_sse_status():
    """Get SSE connection status."""
    return {
        "subscribers": event_bus.subscriber_count,
        "status": "active",
    }
