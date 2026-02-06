# Komorebi API Reference

*Complete REST API documentation for the Komorebi backend service.*

**Base URL:** `http://localhost:8000/api/v1`

**Interactive Docs:** `http://localhost:8000/docs` (Swagger UI)

**Alternative Docs:** `http://localhost:8000/redoc` (ReDoc)

---

## Quick Reference

### Health & Info

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service information |
| `GET` | `/health` | Health check |

### Chunks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/chunks` | Create chunk |
| `GET` | `/api/v1/chunks` | List chunks |
| `GET` | `/api/v1/chunks/inbox` | List inbox only |
| `GET` | `/api/v1/chunks/stats` | Get statistics |
| `GET` | `/api/v1/chunks/{id}` | Get chunk |
| `PATCH` | `/api/v1/chunks/{id}` | Update chunk |
| `DELETE` | `/api/v1/chunks/{id}` | Delete chunk |
| `POST` | `/api/v1/chunks/process-inbox` | Process inbox |

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/projects` | Create project |
| `GET` | `/api/v1/projects` | List projects |
| `GET` | `/api/v1/projects/{id}` | Get project |
| `PATCH` | `/api/v1/projects/{id}` | Update project |
| `DELETE` | `/api/v1/projects/{id}` | Delete project |
| `POST` | `/api/v1/projects/{id}/compact` | Compact project |
| `GET` | `/api/v1/projects/{id}/context` | Get context |

### MCP Servers

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/mcp/servers` | List servers |
| `POST` | `/api/v1/mcp/servers` | Register server |
| `GET` | `/api/v1/mcp/servers/{id}` | Get server |
| `DELETE` | `/api/v1/mcp/servers/{id}` | Unregister server |
| `POST` | `/api/v1/mcp/servers/{id}/connect` | Connect |
| `POST` | `/api/v1/mcp/servers/{id}/disconnect` | Disconnect |
| `GET` | `/api/v1/mcp/tools` | List tools |
| `POST` | `/api/v1/mcp/tools/{name}/call` | Call tool |
| `POST` | `/api/v1/mcp/connect-all` | Connect all |
| `POST` | `/api/v1/mcp/disconnect-all` | Disconnect all |

### SSE

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/sse/events` | Event stream |
| `GET` | `/api/v1/sse/status` | Connection status |

---

## Table of Contents

1. [Overview](#overview)
2. [Health Endpoints](#health-endpoints)
3. [Authentication](#authentication)
4. [Error Handling](#error-handling)
5. [Chunks API](#chunks-api)
6. [Projects API](#projects-api)
7. [MCP API](#mcp-api)
8. [SSE API](#sse-api)
9. [Data Models](#data-models)
10. [SDK Examples](#sdk-examples)

---

## Overview

The Komorebi API is a RESTful service built with FastAPI. It provides:

- **Chunks API** - Capture and manage information fragments
- **Projects API** - Organize chunks into workstreams
- **MCP API** - Integrate external tool servers
- **SSE API** - Real-time event streaming

### Response Format

All responses are JSON. Successful responses return the requested data directly. Error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `204` | No Content (successful deletion) |
| `400` | Bad Request - Invalid input |
| `404` | Not Found |
| `422` | Validation Error |
| `500` | Internal Server Error |

---

## Health Endpoints

### Root

Get service information.

```
GET /
```

**Example Request:**

```bash
curl http://localhost:8000/
```

**Example Response (200 OK):**

```json
{
  "name": "Komorebi",
  "version": "0.1.0",
  "description": "Cognitive infrastructure service",
  "docs": "/docs"
}
```

### Health Check

Verify the service is running.

```
GET /health
```

**Example Request:**

```bash
curl http://localhost:8000/health
```

**Example Response (200 OK):**

```json
{
  "status": "healthy"
}
```

**Usage:** Use this endpoint for load balancer health checks and monitoring systems.

---

## Authentication

**Current Status:** No authentication required.

> ⚠️ **Note:** Authentication is not implemented in v0.1.0. For production deployments, implement authentication middleware before exposing the API publicly.

---

## Error Handling

### Validation Errors (422)

When request validation fails, the API returns detailed error information:

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "content"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {"min_length": 1}
    }
  ]
}
```

### Not Found Errors (404)

```json
{
  "detail": "Chunk not found"
}
```

---

## Chunks API

Chunks are the fundamental unit of information in Komorebi.

### Create Chunk

Capture a new chunk into the inbox.

```
POST /api/v1/chunks
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | The content to capture (min 1 char) |
| `project_id` | UUID | No | Associate with a project |
| `tags` | string[] | No | Categorization tags |
| `source` | string | No | Origin identifier (e.g., "cli", "api") |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/chunks \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Implement SSE endpoint for real-time updates",
    "tags": ["backend", "streaming"],
    "source": "api"
  }'
```

**Example Response (201 Created):**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "content": "Implement SSE endpoint for real-time updates",
  "summary": null,
  "project_id": null,
  "tags": ["backend", "streaming"],
  "status": "inbox",
  "source": "api",
  "token_count": null,
  "created_at": "2024-01-15T10:30:00.000000",
  "updated_at": "2024-01-15T10:30:00.000000"
}
```

**Notes:**
- Background processing automatically enriches the chunk after creation
- An SSE event `chunk.created` is broadcast to connected clients

---

### List Chunks

Retrieve chunks with optional filtering.

```
GET /api/v1/chunks
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | - | Filter by status: `inbox`, `processed`, `compacted`, `archived` |
| `project_id` | UUID | - | Filter by project |
| `limit` | integer | 100 | Maximum results (1-1000) |
| `offset` | integer | 0 | Pagination offset |

**Example Request:**

```bash
curl "http://localhost:8000/api/v1/chunks?status=inbox&limit=10"
```

**Example Response (200 OK):**

```json
[
  {
    "id": "a1b2c3d4-...",
    "content": "First chunk",
    "status": "inbox",
    ...
  },
  {
    "id": "b2c3d4e5-...",
    "content": "Second chunk",
    "status": "inbox",
    ...
  }
]
```

---

### List Inbox

Convenience endpoint to list only inbox chunks.

```
GET /api/v1/chunks/inbox
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 100 | Maximum results |
| `offset` | integer | 0 | Pagination offset |

---

### Get Chunk Statistics

Get counts of chunks by status.

```
GET /api/v1/chunks/stats
```

**Example Response (200 OK):**

```json
{
  "inbox": 12,
  "processed": 45,
  "compacted": 8,
  "archived": 3,
  "total": 68
}
```

---

### Get Chunk

Retrieve a specific chunk by ID.

```
GET /api/v1/chunks/{chunk_id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `chunk_id` | UUID | The chunk's unique identifier |

**Example Request:**

```bash
curl http://localhost:8000/api/v1/chunks/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Error Responses:**

| Code | Condition |
|------|-----------|
| `404` | Chunk not found |

---

### Update Chunk

Partially update a chunk.

```
PATCH /api/v1/chunks/{chunk_id}
```

**Request Body (all fields optional):**

| Field | Type | Description |
|-------|------|-------------|
| `content` | string | Updated content |
| `project_id` | UUID | Updated project association |
| `tags` | string[] | Updated tags |
| `status` | string | Updated status |
| `summary` | string | AI-generated summary |

**Example Request:**

```bash
curl -X PATCH http://localhost:8000/api/v1/chunks/a1b2c3d4-... \
  -H "Content-Type: application/json" \
  -d '{
    "tags": ["urgent", "backend"],
    "status": "processed"
  }'
```

**Notes:**
- Only provided fields are updated
- An SSE event `chunk.updated` is broadcast

---

### Delete Chunk

Permanently delete a chunk.

```
DELETE /api/v1/chunks/{chunk_id}
```

**Example Request:**

```bash
curl -X DELETE http://localhost:8000/api/v1/chunks/a1b2c3d4-...
```

**Response:** `204 No Content`

**Notes:**
- An SSE event `chunk.deleted` is broadcast

---

### Process Inbox

Manually trigger processing of inbox chunks.

```
POST /api/v1/chunks/process-inbox
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `batch_size` | integer | 10 | Number of chunks to process |

**Example Response (200 OK):**

```json
{
  "processed": 5,
  "message": "Processed 5 chunks"
}
```

---

## Projects API

Projects organize chunks into logical workstreams.

### Create Project

```
POST /api/v1/projects
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Project name (1-255 chars) |
| `description` | string | No | Project description |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Komorebi Development",
    "description": "Building the cognitive infrastructure"
  }'
```

**Example Response (201 Created):**

```json
{
  "id": "p1234567-...",
  "name": "Komorebi Development",
  "description": "Building the cognitive infrastructure",
  "context_summary": null,
  "chunk_count": 0,
  "created_at": "2024-01-15T10:30:00.000000",
  "updated_at": "2024-01-15T10:30:00.000000"
}
```

---

### List Projects

```
GET /api/v1/projects
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 100 | Maximum results |
| `offset` | integer | 0 | Pagination offset |

---

### Get Project

```
GET /api/v1/projects/{project_id}
```

---

### Update Project

```
PATCH /api/v1/projects/{project_id}
```

**Request Body (all fields optional):**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Updated name |
| `description` | string | Updated description |
| `context_summary` | string | Updated context summary |

---

### Delete Project

```
DELETE /api/v1/projects/{project_id}
```

**Response:** `204 No Content`

---

### Compact Project

Trigger compaction of all processed chunks in a project.

```
POST /api/v1/projects/{project_id}/compact
```

**Example Response (200 OK):**

```json
{
  "project_id": "p1234567-...",
  "context_summary": "- Implement SSE endpoint\n- Add authentication\n- Refactor database layer",
  "message": "Compaction completed"
}
```

**Notes:**
- Compaction summarizes PROCESSED chunks into a context summary
- Chunks are marked as COMPACTED after processing
- SSE events `compaction.started` and `compaction.completed` are broadcast

---

### Get Project Context

Get the compacted context summary for a project.

```
GET /api/v1/projects/{project_id}/context
```

**Example Response (200 OK):**

```json
{
  "project_id": "p1234567-...",
  "project_name": "Komorebi Development",
  "context_summary": "- Implement SSE endpoint\n- Add authentication",
  "chunk_count": 42
}
```

---

## MCP API

Manage Model Context Protocol server connections.

### List Servers

```
GET /api/v1/mcp/servers
```

**Example Response (200 OK):**

```json
[
  {
    "id": "m1234567-...",
    "name": "GitHub MCP",
    "server_type": "github",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {},
    "enabled": true,
    "status": "disconnected",
    "last_error": null
  }
]
```

---

### Register Server

```
POST /api/v1/mcp/servers
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name |
| `server_type` | string | Yes | Type identifier (e.g., "github") |
| `command` | string | Yes | Command to start server |
| `args` | string[] | No | Command arguments |
| `env` | object | No | Environment variables |
| `enabled` | boolean | No | Enable auto-connect (default: true) |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/mcp/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GitHub MCP",
    "server_type": "github",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {"GITHUB_TOKEN": "ghp_..."}
  }'
```

---

### Get Server

```
GET /api/v1/mcp/servers/{server_id}
```

---

### Unregister Server

```
DELETE /api/v1/mcp/servers/{server_id}
```

---

### Connect to Server

```
POST /api/v1/mcp/servers/{server_id}/connect
```

**Example Response (200 OK):**

```json
{
  "server_id": "m1234567-...",
  "status": "connected",
  "tools": ["search_repositories", "get_file_contents", "create_issue"]
}
```

---

### Disconnect from Server

```
POST /api/v1/mcp/servers/{server_id}/disconnect
```

---

### List Available Tools

List tools from all connected MCP servers.

```
GET /api/v1/mcp/tools
```

**Example Response (200 OK):**

```json
[
  {
    "name": "search_repositories",
    "description": "Search GitHub repositories",
    "server_id": "m1234567-...",
    "input_schema": {
      "type": "object",
      "properties": {
        "query": {"type": "string"}
      }
    }
  }
]
```

---

### Call Tool

Execute a tool from a connected MCP server.

```
POST /api/v1/mcp/tools/{tool_name}/call
```

**Request Body:**

```json
{
  "query": "komorebi"
}
```

**Example Response (200 OK):**

```json
{
  "tool": "search_repositories",
  "result": [
    {"name": "komorebi", "stars": 100}
  ]
}
```

---

### Connect All Servers

```
POST /api/v1/mcp/connect-all
```

---

### Disconnect All Servers

```
POST /api/v1/mcp/disconnect-all
```

---

## SSE API

Server-Sent Events for real-time updates using the EventSource API.

### Event Stream

Connect to receive real-time events.

```
GET /api/v1/sse/events
```

**Response:** `text/event-stream`

**Connection Behavior:**
- Initial connection sends `connected` event immediately
- Keep-alive comment lines sent every 15 seconds (`: ping\n\n`)
- Connection stays open indefinitely
- Auto-reconnects on disconnect (5s delay)

**Event Types:**

| Event | Description | Trigger |
|-------|-------------|----------|
| `connected` | Connection established | Initial connection |
| `chunk.created` | New chunk captured | POST /chunks |
| `chunk.updated` | Chunk modified | Background processing |
| `chunk.deleted` | Chunk removed | DELETE /chunks/{id} |
| `project.updated` | Project modified | PATCH /projects/{id} |
| `compaction.started` | Compaction began | POST /projects/{id}/compact |
| `compaction.completed` | Compaction finished | Compaction finishes |
| `mcp.status_changed` | MCP server status changed | MCP connect/disconnect |

**Event Format:**

```
event: chunk.created
data: {"type": "chunk.created", "chunk_id": "a1b2c3d4-...", "data": {...}, "timestamp": "2026-02-05T18:28:45.133293"}

```

**Example (JavaScript):**

```javascript
const eventSource = new EventSource('/api/v1/sse/events');

// Connection opened
eventSource.onopen = () => {
  console.log('SSE connected');
};

// Message received
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data);
};

// Specific event type
eventSource.addEventListener('chunk.created', (event) => {
  const data = JSON.parse(event.data);
  console.log('New chunk:', data.chunk_id);
});

// Error handling (auto-reconnects)
eventSource.onerror = (error) => {
  console.error('SSE error, will reconnect...', error);
};

// Cleanup
function disconnect() {
  eventSource.close();
}
```

**Example (curl):**

```bash
# Connect and stay open
curl -N http://localhost:8000/api/v1/sse/events

# Output:
event: connected
data: {"message": "SSE connection established"}

event: chunk.created
data: {"type": "chunk.created", ...}

# Keep-alive comments (ignored by browsers):
: ping

```

**Implementation Notes:**

- Uses `sse-starlette` library with `EventSourceResponse`
- Each client gets dedicated `asyncio.Queue` for event delivery
- Events serialized using `ServerSentEvent` class
- Automatic keep-alive prevents timeout
- Memory per client: ~1KB + queued events
- Expected capacity: 1000+ clients per worker

---

### SSE Status

Get SSE connection information.

```
GET /api/v1/sse/status
```

**Example Response (200 OK):**

```json
{
  "subscribers": 3,
  "status": "active"
}
```

---

## Data Models

### Chunk

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `content` | string | The captured content |
| `summary` | string? | AI-generated summary |
| `project_id` | UUID? | Associated project |
| `tags` | string[] | Categorization tags |
| `status` | ChunkStatus | Processing status |
| `source` | string? | Origin of the chunk |
| `token_count` | integer? | Estimated token count |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

### ChunkStatus

| Value | Description |
|-------|-------------|
| `inbox` | Raw, unprocessed capture |
| `processed` | Analyzed and enriched |
| `compacted` | Summarized into context |
| `archived` | No longer active |

### Project

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `name` | string | Project name |
| `description` | string? | Project description |
| `context_summary` | string? | Compacted context |
| `chunk_count` | integer | Number of chunks |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

### MCPServerConfig

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `name` | string | Display name |
| `server_type` | string | Type identifier |
| `command` | string | Start command |
| `args` | string[] | Command arguments |
| `env` | object | Environment variables |
| `enabled` | boolean | Auto-connect enabled |
| `status` | MCPServerStatus | Connection status |
| `last_error` | string? | Last error message |

### MCPServerStatus

| Value | Description |
|-------|-------------|
| `disconnected` | Not connected |
| `connecting` | Connection in progress |
| `connected` | Successfully connected |
| `error` | Connection failed |

---

## Rate Limiting

**Current Status:** No rate limiting implemented.

> ⚠️ **Note:** For production, implement rate limiting to prevent abuse.

---

## Versioning

The API is versioned via URL path (`/api/v1/`). Breaking changes will increment the version number.

---

## SDK Examples

### Python with httpx

```python
import httpx

# Create a client
client = httpx.Client(base_url="http://localhost:8000/api/v1")

# Capture a chunk
response = client.post("/chunks", json={
    "content": "Remember to implement caching",
    "tags": ["backend", "performance"],
    "source": "python-sdk"
})
chunk = response.json()
print(f"Captured: {chunk['id']}")

# List chunks
response = client.get("/chunks", params={"status": "inbox", "limit": 10})
chunks = response.json()
for c in chunks:
    print(f"- {c['content'][:50]}...")

# Get stats
stats = client.get("/chunks/stats").json()
print(f"Total chunks: {stats['total']}")

# Create a project
project = client.post("/projects", json={
    "name": "My Project",
    "description": "A test project"
}).json()

# Compact project
result = client.post(f"/projects/{project['id']}/compact").json()
print(f"Context: {result['context_summary']}")

client.close()
```

### Python with httpx (Async)

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1") as client:
        # Capture a chunk
        response = await client.post("/chunks", json={
            "content": "Async capture example",
            "source": "async-python"
        })
        print(response.json())

asyncio.run(main())
```

### JavaScript with fetch

```javascript
const API_URL = 'http://localhost:8000/api/v1';

// Capture a chunk
async function captureChunk(content, tags = []) {
  const response = await fetch(`${API_URL}/chunks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, tags, source: 'js-sdk' })
  });
  return response.json();
}

// List chunks
async function listChunks(status = null, limit = 20) {
  const params = new URLSearchParams({ limit });
  if (status) params.append('status', status);
  
  const response = await fetch(`${API_URL}/chunks?${params}`);
  return response.json();
}

// SSE subscription
function subscribeToEvents(onEvent) {
  const eventSource = new EventSource(`${API_URL}/sse/events`);
  
  eventSource.onmessage = (event) => {
    onEvent(JSON.parse(event.data));
  };
  
  eventSource.onerror = (error) => {
    console.error('SSE Error:', error);
  };
  
  return eventSource; // Call .close() to unsubscribe
}

// Usage
captureChunk('Hello from JavaScript!', ['test'])
  .then(chunk => console.log('Captured:', chunk.id));
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Capture a chunk
curl -X POST http://localhost:8000/api/v1/chunks \
  -H "Content-Type: application/json" \
  -d '{"content": "My thought", "tags": ["idea"]}'

# List inbox chunks
curl "http://localhost:8000/api/v1/chunks?status=inbox&limit=10"

# Get statistics
curl http://localhost:8000/api/v1/chunks/stats

# Create project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project"}'

# Update chunk
curl -X PATCH http://localhost:8000/api/v1/chunks/{chunk_id} \
  -H "Content-Type: application/json" \
  -d '{"status": "processed"}'

# Delete chunk
curl -X DELETE http://localhost:8000/api/v1/chunks/{chunk_id}

# Stream SSE events (runs continuously)
curl -N http://localhost:8000/api/v1/sse/events
```

---

*For more information, see the [Getting Started Guide](./GETTING_STARTED.md).*
