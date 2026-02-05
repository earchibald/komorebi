"""Event bus for SSE (Server-Sent Events) broadcasting.

Enables real-time updates to connected clients using
an async event pattern.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Optional
from uuid import UUID
import json


class EventType(str, Enum):
    """Types of events that can be broadcast."""
    
    CHUNK_CREATED = "chunk.created"
    CHUNK_UPDATED = "chunk.updated"
    CHUNK_DELETED = "chunk.deleted"
    PROJECT_UPDATED = "project.updated"
    COMPACTION_STARTED = "compaction.started"
    COMPACTION_COMPLETED = "compaction.completed"
    MCP_STATUS_CHANGED = "mcp.status_changed"


@dataclass
class ChunkEvent:
    """Event data for chunk-related events."""
    
    event_type: EventType
    chunk_id: UUID
    data: dict[str, Any]
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_sse_dict(self) -> dict:
        \"\"\"Format as SSE-compatible dictionary.\"\"\"
        payload = {
            "type": self.event_type.value,
            "chunk_id": str(self.chunk_id),
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }
        return {
            "event": self.event_type.value,
            "data": json.dumps(payload),
        }


class EventBus:
    """Async event bus for broadcasting events to SSE clients.
    
    Uses asyncio.Queue for each subscriber to enable
    non-blocking event distribution.
    """
    
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
    
    async def subscribe(self) -> AsyncGenerator[dict, None]:
        """Subscribe to events and yield SSE-formatted messages."""
        queue: asyncio.Queue = asyncio.Queue()
        
        async with self._lock:
            self._subscribers.append(queue)
        
        # Send initial connection message
        yield {"event": "connected", "data": json.dumps({"message": "SSE connection established"})}
        
        try:
            while True:
                try:
                    # Wait for event with timeout for keep-alive
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    if isinstance(event, ChunkEvent):
                        yield event.to_sse_dict()
                    else:
                        yield {"data": json.dumps(event)}
                except asyncio.TimeoutError:
                    # Send keep-alive ping
                    yield {"event": "ping", "data": json.dumps({"message": "keep-alive"})}
        finally:
            async with self._lock:
                self._subscribers.remove(queue)
    
    async def publish(self, event: ChunkEvent | dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        async with self._lock:
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Skip slow subscribers
                    pass
    
    @property
    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return len(self._subscribers)


# Global event bus instance
event_bus = EventBus()
