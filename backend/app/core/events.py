"""Event bus for SSE (Server-Sent Events) broadcasting.

Enables real-time updates to connected clients using
an async event pattern.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Optional
from uuid import UUID
import json
from sse_starlette.sse import ServerSentEvent


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
        """Format as SSE-compatible dictionary."""
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
    
    async def subscribe(self):
        """Subscribe to events and yield SSE-formatted messages."""
        queue = asyncio.Queue()
        
        # 1. PROTECT THE ADDITION
        try:
            async with self._lock:
                self._subscribers.append(queue)
                logging.info(f"Subscriber added. Total: {len(self._subscribers)}")
        except Exception as e:
            logging.error(f"Failed to add subscriber: {e}")
            return  # Exit if we can't subscribe

        try:
            # 2. YIELD INITIAL EVENT (Use ServerSentEvent class)
            yield ServerSentEvent(
                event="connected",
                data=json.dumps({"message": "SSE connection established"})
            )
            logging.info("Sent connection message")
            
            # 3. SIMPLIFIED LOOP (Let EventSourceResponse handle pings)
            while True:
                # Wait for data. If the client disconnects, sse-starlette 
                # will stop iterating this generator automatically.
                event = await queue.get()
                
                if isinstance(event, ChunkEvent):
                    # Use the class! No manual dict formatting.
                    yield ServerSentEvent(
                        event=event.event_type.value,
                        data=json.dumps({
                            "type": event.event_type.value,
                            "chunk_id": str(event.chunk_id),
                            "data": event.data,
                            "timestamp": event.timestamp.isoformat(),
                        })
                    )
                else:
                    yield ServerSentEvent(data=json.dumps(event))

        except asyncio.CancelledError:
            logging.info("Subscriber disconnected (Cancelled)")
            raise  # Re-raise to let sse-starlette clean up
            
        except Exception as e:
            logging.error(f"SSE Generator Error: {e}")
            # Do not re-raise generic errors, just log and exit
            
        finally:
            # 4. ROBUST REMOVAL
            async with self._lock:
                if queue in self._subscribers:
                    self._subscribers.remove(queue)
                    logging.info(f"Subscriber removed. Total: {len(self._subscribers)}")
    
    async def publish(self, event: ChunkEvent | dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        async with self._lock:
            logging.info(f"Publishing event to {len(self._subscribers)} subscriber(s)")
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                    logging.info("Event queued successfully")
                except asyncio.QueueFull:
                    # Skip slow subscribers
                    logging.warning("Queue full, skipping subscriber")
                    pass
    
    @property
    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return len(self._subscribers)


# Global event bus instance
event_bus = EventBus()
