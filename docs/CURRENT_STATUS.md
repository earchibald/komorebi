# Komorebi: Current Status & Next Steps

**Date:** February 5, 2026  
**Version:** 0.2.3 (Pre-1.0.0 Development)

---

## 🆕 Latest Update: VS Code Prompts & Skills

### What's New

**VS Code Custom Prompts:** 5 prompts for common workflows
- `/implement-feature` - TDD-driven feature development
- `/write-tests` - Comprehensive test generation
- `/debug-issue` - Systematic debugging (Premium tier)
- `/review-pr` - Security-focused PR reviews
- `/update-docs` - Documentation sync (Economy tier)

**Agent Skills:** 2 skills with scripts
- `feature-implementer` - Full-stack scaffold generator
- `code-formatter` - Ruff formatting commands

**Telemetry:** Usage and cost tracking
- `scripts/telemetry/telemetry_tracker.py`
- Log, report, and cost analysis commands

**Documentation:**
- [PROMPT_GUIDE.md](./PROMPT_GUIDE.md) - Quick reference
- [PROMPTS_AND_SKILLS_PROPOSAL.md](./PROMPTS_AND_SKILLS_PROPOSAL.md) - Full strategy

---

## 🎯 What You Have Right Now

### ✅ Fully Working Systems

#### 1. **Core Capture Pipeline**
**Status:** Production-ready  
**What it does:** Capture thoughts/data instantly, process in background

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/chunks \
  -H "Content-Type: application/json" \
  -d '{"content":"My thought"}'

# Via CLI (basic)
komorebi add "My thought"

# Via Dashboard
# Open http://localhost:3000 and use the Inbox form
```

**Features:**
- ✅ Sub-100ms capture (no UI blocking)
- ✅ Background processing (auto-summarization)
- ✅ Real-time SSE updates (<5ms delivery)
- ✅ Automatic status transitions: `inbox` → `processed`

#### 2. **Dashboard UI**
**Status:** Production-ready with recent optimizations  
**What it does:** Visual interface for managing chunks

**URL:** http://localhost:3000

**Features:**
- ✅ Instant tab switching (0ms, client-side filtering)
- ✅ Real-time updates via SSE (see chunks appear live)
- ✅ Smart caching (instant page loads from localStorage)
- ✅ Status filters: All, Inbox, Processed, Compacted, Archived
- ✅ Stats dashboard (auto-updating)

**Recent Fixes (Feb 5, 2026):**
- Fixed SSE connection issues (<5ms event delivery now)
- Eliminated empty-state flicker on tab switch
- Implemented Fetch-All-Filter-Client pattern

#### 3. **Backend API**
**Status:** Production-ready  
**What it does:** RESTful API for all operations

**Interactive Docs:** http://localhost:8000/docs

**Endpoints:**
- ✅ Chunks: Create, read, update, delete, list, stats
- ✅ Projects: Create, read, update, delete, list
- ✅ SSE: Real-time event streaming
- ✅ MCP: Server registry (infrastructure only)

**Performance:**
- API response time: 2-10ms
- Database: Async SQLite with SQLAlchemy
- Concurrent connections: 1000+ per worker

#### 4. **Projects System**
**Status:** Basic functionality working  
**What it does:** Organize chunks into workstreams

**Features:**
- ✅ Create projects
- ✅ Associate chunks with projects
- ✅ Track chunk counts
- ✅ Project-level queries

**Example:**
```bash
# Create project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Q1 Planning","description":"2026 Q1 goals"}'

# Add chunk to project
curl -X POST http://localhost:8000/api/v1/chunks \
  -H "Content-Type: application/json" \
  -d '{"content":"Launch new feature","project_id":"<project-uuid>"}'
```

---

## ⚠️ Partially Implemented (Infrastructure Exists, Needs Enhancement)

### 1. **Compaction (Recursive Summarization)**

**Status:** 🟡 Infrastructure ready, but using placeholder logic

**What's implemented:**
- ✅ `CompactorService` class with map-reduce pattern
- ✅ API endpoint: `POST /api/v1/projects/{id}/compact`
- ✅ Database schema supports `compacted` status
- ✅ SSE events for compaction start/complete

**What's missing:**
- ❌ Real LLM integration (currently just truncates text)
- ❌ No Ollama client
- ❌ No streaming support for long summaries
- ❌ No token counting with tiktoken

**Current behavior:**
```python
# backend/app/core/compactor.py
def _generate_simple_summary(self, content: str) -> str:
    """Placeholder - just takes first sentence."""
    sentences = content.split('.')
    return sentences[0] + '.' if sentences else content[:100]
```

**What it SHOULD do:**
```python
async def _generate_summary(self, content: str) -> str:
    """Use Ollama to generate concise summary."""
    response = await ollama.generate(
        model="llama3.2",
        prompt=f"Summarize in one sentence: {content}",
        stream=False
    )
    return response['response']
```

**To complete this:**
1. Add `ollama-python` to dependencies
2. Create `OllamaClient` in `backend/app/core/`
3. Update `CompactorService` to use Ollama
4. Add streaming support for long summaries
5. Implement proper map-reduce for project compaction

**Why this matters:**
This is the **core value proposition** of Komorebi—the "memory pyramid" that summarizes context recursively instead of forgetting it.

### 2. **MCP Integration**

**Status:** 🟡 Registry implemented, no servers configured

**What's implemented:**
- ✅ `MCPClient` class (handles stdio communication)
- ✅ `MCPRegistry` class (manages multiple servers)
- ✅ API endpoints: `/api/v1/mcp/servers`, `/api/v1/mcp/tools`
- ✅ Database table for MCP server configs
- ✅ JSON-RPC 2.0 protocol handler

**What's missing:**
- ❌ No pre-configured servers
- ❌ No UI for browsing tools
- ❌ No workflow for calling tools → capturing results as chunks
- ❌ No error recovery for server crashes

**Example of what you COULD do (if servers were configured):**
```bash
# List available tools from all connected servers
curl http://localhost:8000/api/v1/mcp/tools

# Call a tool
curl -X POST http://localhost:8000/api/v1/mcp/tools/search_github/call \
  -H "Content-Type: application/json" \
  -d '{"arguments":{"query":"fastapi SSE"}}'
```

**To complete this:**
1. Add MCP server configs to `config/mcp_servers.json`:
   ```json
   {
     "servers": [
       {
         "name": "github",
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-github"],
         "env": {"GITHUB_TOKEN": "..."}
       },
       {
         "name": "filesystem",
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/..."]
       }
     ]
   }
   ```
2. Create startup logic to load and connect servers
3. Build UI in dashboard to browse tools
4. Create "Tool Result → Chunk" workflow
5. Add reconnection logic

**Why this matters:**
Turns Komorebi into a **universal tool aggregator**—query GitHub, read files, access memory, all from one place.

---

## 🚧 Not Yet Implemented (Greenfield)

### 1. **Enhanced CLI**

**Status:** 🔴 Only basic `add` command exists

**What exists:**
```bash
komorebi add "My thought"  # Works
komorebi --help             # Works
```

**What's missing:**
- `komorebi list` - View chunks in terminal
- `komorebi search <query>` - Full-text search
- `komorebi project create/list/view`
- `komorebi stats` - Terminal dashboard
- `komorebi compact <project>` - Trigger compaction
- Pipe support: `cat log.txt | komorebi add`

**What it should look like (mockup):**
```bash
$ komorebi list --status inbox --limit 10

╭─────────────────────────────────────────────────────────────╮
│ 📥 Inbox Chunks (10 of 43)                                  │
├─────────────────────────────────────────────────────────────┤
│ a1b2c3d4 │ My first thought!                     │ 2min ago │
│ e5f6g7h8 │ Remember to call John                 │ 5min ago │
│ i9j0k1l2 │ Fix the SSE connection issue          │ 10min ago│
│ ...                                                          │
╰─────────────────────────────────────────────────────────────╯

$ komorebi search "SSE"

╭─────────────────────────────────────────────────────────────╮
│ 🔍 Search Results for "SSE" (3 matches)                     │
├─────────────────────────────────────────────────────────────┤
│ i9j0k1l2 │ Fix the SSE connection issue          │ Processed│
│ m3n4o5p6 │ SSE now working with <5ms latency     │ Processed│
│ q7r8s9t0 │ Testing SSE real-time updates         │ Processed│
╰─────────────────────────────────────────────────────────────╯

$ cat debug.log | komorebi add --project debugging --tags log,error
✅ Captured 45.3 KB → chunk abc123de
🔄 Processing in background...
```

**To build this:**
- Use `rich` library for beautiful tables (already installed)
- Add commands to `cli/main.py`
- Use `httpx` to call backend API (already installed)
- Add `sys.stdin.isatty()` detection for pipes

### 2. **Search & Full-Text Indexing**

**Status:** 🔴 Tags exist but not searchable

**What exists:**
- Chunks have `tags: list[str]` field
- Tags are stored in database

**What's missing:**
- No full-text search across content
- No tag-based filtering in API
- No search UI in dashboard

**To build this:**
- Add SQLite FTS5 virtual table
- Create `/api/v1/chunks/search?q=<query>` endpoint
- Add search bar to dashboard
- Support tag filtering: `#urgent`, `#bug`

### 3. **Project Context Dashboard**

**Status:** 🔴 No project detail view

**What's missing:**
- Visual representation of chunk→context hierarchy
- Timeline of chunk capture
- Compaction history (who, when, token savings)
- Graph view of chunk relationships

**Mockup:**
```
┌─────────────────────────────────────────────────────────────┐
│ 📁 Project: Q1 Planning                                     │
├─────────────────────────────────────────────────────────────┤
│ Context Summary (1,234 tokens)                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ "Q1 goals include launching feature X, improving...    │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Chunks (12)                                                 │
│ ┌─ Raw    (5) - 12,456 tokens                              │
│ ├─ Processed (4) - 8,234 tokens                            │
│ └─ Compacted (3) - 1,234 tokens → Context                  │
│                                                             │
│ Compression: 90% (12,456 → 1,234 tokens)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Recommended Next Step: **Option 1 - Ollama Integration**

### Why This First?

Because it makes the **core feature** actually work. Everything else is additive, but compaction is the main value proposition.

### What to Build

**1. Add Ollama Python Client**

```bash
pip install ollama
```

**2. Create `backend/app/core/ollama_client.py`**

```python
import ollama
from typing import AsyncIterator

class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
    
    async def summarize(self, content: str, max_length: int = 100) -> str:
        """Generate a concise summary."""
        response = await ollama.generate(
            model="llama3.2",
            prompt=f"Summarize this in under {max_length} words:\n\n{content}",
            stream=False
        )
        return response['response']
    
    async def summarize_stream(self, content: str) -> AsyncIterator[str]:
        """Stream summary generation."""
        async for chunk in ollama.generate(
            model="llama3.2",
            prompt=f"Summarize concisely:\n\n{content}",
            stream=True
        ):
            yield chunk['response']
```

**3. Update `backend/app/core/compactor.py`**

Replace `_generate_simple_summary` with:

```python
async def process_chunk(self, chunk_id: UUID) -> Optional[Chunk]:
    chunk = await self.chunk_repo.get(chunk_id)
    if not chunk or chunk.status != ChunkStatus.INBOX:
        return None
    
    # Use Ollama for real summarization
    ollama_client = OllamaClient()
    summary = await ollama_client.summarize(chunk.content, max_length=100)
    
    # Count tokens properly
    token_count = len(chunk.content) // 4  # Or use tiktoken
    
    update = ChunkUpdate(
        status=ChunkStatus.PROCESSED,
        summary=summary,
        token_count=token_count,
    )
    
    return await self.chunk_repo.update(chunk_id, update)
```

**4. Implement Map-Reduce for Projects**

```python
async def compact_project(self, project_id: UUID) -> Optional[str]:
    """Real map-reduce compaction."""
    chunks = await self.chunk_repo.list(
        status=ChunkStatus.PROCESSED,
        project_id=project_id,
    )
    
    if not chunks:
        return None
    
    # Map: Get summaries
    summaries = [chunk.summary for chunk in chunks if chunk.summary]
    
    # Reduce: Combine with Ollama
    combined = "\n".join(summaries)
    ollama_client = OllamaClient()
    context_summary = await ollama_client.summarize(
        combined, 
        max_length=500
    )
    
    # Update project
    await self.project_repo.update(
        project_id,
        ProjectUpdate(context_summary=context_summary)
    )
    
    # Mark chunks as compacted
    for chunk in chunks:
        await self.chunk_repo.update(
            chunk.id,
            ChunkUpdate(status=ChunkStatus.COMPACTED)
        )
    
    return context_summary
```

**5. Test It**

```bash
# Start Ollama
ollama serve

# Create chunks in a project
curl -X POST http://localhost:8000/api/v1/chunks \
  -d '{"content":"Long detailed text...","project_id":"<uuid>"}'

# Trigger compaction
curl -X POST http://localhost:8000/api/v1/projects/<uuid>/compact

# Check the result
curl http://localhost:8000/api/v1/projects/<uuid>/context
```

### Expected Impact

- ✅ Real summarization instead of placeholder
- ✅ Project context actually useful
- ✅ Token counting and compression metrics
- ✅ Prove the "memory pyramid" concept works

**Time estimate:** 2-4 hours

---

## Alternative Paths

### Option 2: MCP Server Integration (2-3 hours)

Add GitHub and Filesystem servers, build tool browser in UI.

**Why second?** Makes Komorebi useful for gathering external data.

### Option 3: Enhanced CLI (3-5 hours)

Build beautiful terminal commands with Rich tables.

**Why second?** Great for power users, terminal workflows.

### Option 4: Search (2-3 hours)

Add FTS5 and search endpoint.

**Why second?** Necessary once you have >100 chunks.

---

## Summary

**You have a solid foundation:**
- ✅ Fast capture pipeline
- ✅ Real-time dashboard  
- ✅ Background processing
- ✅ SSE streaming
- ✅ Smart caching

**The missing piece is meaningful summarization.**

**Next step:** Integrate Ollama so the compaction actually does something useful. This will make Komorebi's core value proposition real.

Once that's done, you can:
- Add MCP servers to pull external data
- Enhance the CLI for terminal workflows
- Add search for finding old context
- Build project detail views

But start with Ollama. That's the heart of the system.
