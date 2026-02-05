# Module 2: Recursive Compaction & Entity Extraction

**Proposal Status:** Ready for Validation & Team Review  
**Date:** February 5, 2026  
**Author:** Cloud/Research Agent  
**Target Release:** Weeks 3-6 post-Module-1  

---

## Executive Summary

### What is Module 2?

Module 2 extends the Memory Pyramid by adding two capabilities:

1. **Recursive Compaction**: When a project's context summary grows beyond ~30KB (tunable), automatically trigger a second Map-Reduce pass. This creates a hierarchical compression: Items → Chunks → Project Summary → **Meta-Summary**. Prevents context window overflow while preserving information density.

2. **Entity Extraction**: After each chunk is summarized, invoke the LLM to identify and extract structured entities (errors, URLs, command IDs, tool names, decision points). Store these in a normalized database table for later retrieval, aggregation, and agentic routing.

### Why Now?

- **Module 1 is stable**: Ollama integration proven in production, all tests passing.
- **Context pressure**: Real users will accumulate 100+ chunks/project within weeks. Without hierarchical summarization, the "Global Context" in a Project will become noisy and expensive to re-summarize.
- **Entity extraction unlocks routing**: Once we catalog error types, tool calls, URLs, we can route relevant chunks to specialized MCP agents (e.g., "Debug Agent" for errors, "Infrastructure Agent" for cloud IDs).

### Success Criteria

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Compression ratio** | ≥ 5:1 (5 summaries → 1 meta-summary) | Proof of hierarchical reduction |
| **Entity extraction F1 score** | ≥ 0.75 | Balanced precision/recall; tuned via Hammer |
| **Recursion depth limit** | ≤ 3 | Prevents infinite loops; typical projects use ≤ 2 |
| **Zero lost data** | 100% | Archived chunks always recoverable |
| **Non-blocking** | All async | No impact on capture ingestion throughput |

---

## Technical Specifications

### New Pydantic Models

```python
# backend/app/models/entity.py

class EntityType(str, Enum):
    """Structured entity categories."""
    ERROR = "error"              # Exception, stacktrace, error code
    URL = "url"                  # HTTP URL, GitHub link, etc.
    TOOL_ID = "tool_id"          # Tool name: "docker", "kubectl", "grep", etc.
    DECISION = "decision"        # Decision point or architecture choice
    IDENTIFIER = "identifier"    # UUID, SHA, ticket ID, etc.
    CODE_SNIPPET = "code"        # Highlighted code block
    REFERENCE = "reference"      # Doc link, RFC, pattern name

class Entity(BaseModel):
    """Extracted entity from a chunk."""
    id: UUID = Field(default_factory=uuid4)
    chunk_id: UUID                           # Source chunk
    project_id: UUID                         # Project context
    entity_type: EntityType
    value: str                               # The actual entity (e.g., "docker:permission denied")
    confidence: float                        # 0.0-1.0; thresholded at 0.6
    context: Optional[str]                   # Surrounding snippet (max 200 chars)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CompactionLevel(BaseModel):
    """Metadata about a compaction hierarchy."""
    project_id: UUID
    level: int                               # 0 = chunks, 1 = first reduce, 2 = meta-summary, etc.
    summary: str
    source_count: int                        # Number of items summarized
    source_tokens_in: int
    summary_tokens_out: int
    compression_ratio: float                 # source_tokens / summary_tokens
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Project(BaseModel):  # UPDATED
    """Extend existing Project model."""
    # ...existing fields...
    compaction_depth: int = Field(default=0, description="Current recursion depth")
    meta_summary: Optional[str] = Field(None, description="Level 2+ summary (recursive)")
    entity_count: int = Field(default=0, description="Total extracted entities")
    last_compaction_at: Optional[datetime] = None
    next_compaction_at: Optional[datetime] = None  # For scheduled triggers
```

### Recursive Compaction Algorithm

**Trigger Logic:**
```
When: chunk.status = COMPACTED (i.e., end of reduce step)
Check: project.last_compaction_at
       if (now - last_compaction_at) > 24 hours OR
          project.context_summary length > 30,000 chars
       then: schedule_recursive_compaction(project_id)
```

**Recursion Depth:**
- **Level 0**: Individual chunks (raw captures)
- **Level 1**: First reduce (chunk summaries → project summary) [CURRENT - Module 1]
- **Level 2**: Meta-summary (summarize all existing summaries)
- **Level 3+**: Stop (diminishing returns; preserve Level 2)

**Compaction Decision Tree:**
```
project_id → fetch project.context_summary
           → measure length
           → if > 30KB: map & reduce (same as Level 1, but on summaries)
           → if ≤ 30KB: skip (no recursion needed)
           → store CompactionLevel record for audit trail
           → increment project.compaction_depth
           → update project.meta_summary
           → emit COMPACTION_LEVEL_COMPLETED event
           → mark old summaries as ARCHIVED status
```

### Entity Extraction Pipeline

**LLM Extraction Call:**
```python
prompt = f"""
Extract entities from this chunk:

{chunk.content}

Return a JSON array. Each entity has:
- type: one of [error, url, tool_id, decision, identifier, code, reference]
- value: the actual entity (short string)
- confidence: 0.0-1.0
- context: surrounding snippet

Example output:
[
  {{"type": "error", "value": "connection refused", "confidence": 0.95, "context": "[ERROR] Connection refused at port 5432"}},
  {{"type": "tool_id", "value": "psql", "confidence": 0.88, "context": "psql error output"}},
]

Return ONLY valid JSON. If no entities found, return [].
"""

entities_json = await llm.extract_entities(prompt, system_anchor="Extract actionable items for debugging.")
```

**Storage:**
```
FOR each entity IN entities_json:
  IF confidence >= 0.6:  # Threshold
    INSERT INTO entities (chunk_id, project_id, entity_type, value, confidence, context)
    VALUES (...)
  ENDIF
  INCREMENT project.entity_count
ENDFOR
```

### API Endpoints (New/Modified)

#### POST `/api/v1/projects/{project_id}/recursive-compact`
**Purpose:** Manually trigger a recursive compaction pass.

**Request:**
```json
{
  "force": false,
  "max_depth": 3
}
```

**Response:**
```json
{
  "project_id": "uuid",
  "level_completed": 2,
  "summary": "High-level meta-summary...",
  "compression_ratio": 5.2,
  "entity_count_new": 42,
  "message": "Recursion completed at level 2"
}
```

#### POST `/api/v1/chunks/{chunk_id}/extract-entities`
**Purpose:** Manually trigger entity extraction on a specific chunk.

**Request:**
```json
{
  "force_rerun": false
}
```

**Response:**
```json
{
  "chunk_id": "uuid",
  "entities_extracted": 8,
  "entities": [
    {
      "id": "uuid",
      "type": "error",
      "value": "ECONNREFUSED",
      "confidence": 0.92,
      "context": "[ERROR] Connection refused at 127.0.0.1:5432"
    }
  ]
}
```

#### GET `/api/v1/projects/{project_id}/entities`
**Purpose:** List extracted entities for a project (with filters).

**Query Params:**
- `type`: `error`, `url`, `tool_id`, etc. (optional)
- `confidence_min`: 0.0-1.0 (optional, default 0.6)
- `limit`: 100 (default)
- `offset`: 0 (default)

**Response:**
```json
{
  "project_id": "uuid",
  "entities": [ { /* Entity objects */ } ],
  "total": 142,
  "filtered_count": 42,
  "aggregations": {
    "by_type": {
      "error": 18,
      "url": 12,
      "tool_id": 8,
      "decision": 4
    }
  }
}
```

#### GET `/api/v1/projects/{project_id}/compaction-history`
**Purpose:** Audit trail of compaction levels.

**Response:**
```json
{
  "project_id": "uuid",
  "levels": [
    {
      "level": 1,
      "summary": "First reduce: 50 chunks → 1 summary",
      "source_count": 50,
      "compression_ratio": 6.2,
      "created_at": "2026-02-05T..."
    },
    {
      "level": 2,
      "summary": "Meta-summary: 1 level-1 summary → compressed meta",
      "source_count": 1,
      "compression_ratio": 2.1,
      "created_at": "2026-02-06T..."
    }
  ]
}
```

### Database Schema Changes

**New Table: `entities`**
```sql
CREATE TABLE entities (
  id VARCHAR(36) PRIMARY KEY,
  chunk_id VARCHAR(36) NOT NULL,
  project_id VARCHAR(36) NOT NULL,
  entity_type VARCHAR(32) NOT NULL,  -- error, url, tool_id, etc.
  value TEXT NOT NULL,
  confidence FLOAT NOT NULL,          -- 0.0-1.0
  context TEXT,                       -- Surrounding snippet
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (chunk_id) REFERENCES chunks(id),
  FOREIGN KEY (project_id) REFERENCES projects(id),
  INDEX idx_project_type (project_id, entity_type),
  INDEX idx_confidence (confidence)
);
```

**Modified: `projects` Table**
```sql
ALTER TABLE projects ADD COLUMN compaction_depth INT DEFAULT 0;
ALTER TABLE projects ADD COLUMN meta_summary TEXT NULL;
ALTER TABLE projects ADD COLUMN entity_count INT DEFAULT 0;
ALTER TABLE projects ADD COLUMN last_compaction_at DATETIME NULL;
ALTER TABLE projects ADD COLUMN next_compaction_at DATETIME NULL;
```

**Modified: `chunks` Table (No changes required)**
- Existing `status` enum already supports `COMPACTED` and `ARCHIVED`.
- No schema changes; compaction metadata lives in `CompactionLevel` model (optional ORM table if audit needed).

---

## Data Flow

### Recursive Compaction Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Trigger: chunk.status = COMPACTED (end of Module 1 reduce)  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ Check: next_compaction_at  │
        │ Has 24h passed? Or > 30KB? │
        └────────┬───────────────────┘
                 │
         ┌───────┴────────┐
         │ YES   │  NO    │
         ▼       ▼        │
    Schedule  Return  ◄──┘
    Recursive
    Compact
         │
         ▼
    ┌─────────────────────────────────┐
    │ Fetch all PROCESSED chunks      │ (Level 1)
    │ Collect existing summaries      │
    └──────────────┬──────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────┐
    │ Combine summaries into          │
    │ "context aggregation string"    │
    │ (32KB combined)                 │
    └──────────────┬──────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────┐
    │ Call LLM.summarize()            │
    │ System anchor: "High-level..."  │
    │ (Produces: meta-summary)        │
    └──────────────┬──────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────┐
    │ Store CompactionLevel record:   │
    │ ├─ level: 2                     │
    │ ├─ summary: meta-summary        │
    │ ├─ source_count: 50 (chunks)    │
    │ ├─ compression_ratio: 32KB/4KB = 8:1
    │ └─ created_at: now              │
    └──────────────┬──────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────┐
    │ Update project:                 │
    │ ├─ meta_summary = result        │
    │ ├─ compaction_depth = 2         │
    │ └─ last_compaction_at = now     │
    └──────────────┬──────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────┐
    │ Emit SSE event:                 │
    │ COMPACTION_LEVEL_COMPLETED      │
    │ {level: 2, compression: 8.0}    │
    └─────────────────────────────────┘
```

### Entity Extraction Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Trigger: chunk.status = PROCESSED (end of Module 1 map)     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ Entry: background task     │
        │ extract_chunk_entities()   │
        └────────────────┬───────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │ Build LLM prompt with:             │
        │ ├─ chunk.content                   │
        │ ├─ Expected entity types: [...]    │
        │ └─ Confidence threshold: 0.6       │
        └────────────────┬───────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │ Call LLM.extract_entities()        │
        │ (Returns: JSON array of entities)  │
        └────────────────┬───────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │ FOR each extracted entity:         │
        │  ├─ Parse JSON                     │
        │  ├─ Validate schema                │
        │  └─ IF confidence >= 0.6:          │
        │     └─ INSERT into entities table  │
        │        └─ INCREMENT project.entity_count
        └────────────────┬───────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │ Emit SSE event:                    │
        │ ENTITIES_EXTRACTED                 │
        │ {chunk_id, count: 8, entities}     │
        └────────────────────────────────────┘
```

### State Transitions with Module 2

```
Original (Module 1):
  INBOX → PROCESSED → COMPACTED → ARCHIVED

With Module 2 (Entity Extraction):
  INBOX → PROCESSED (+ extract entities) → COMPACTED → ARCHIVED
           ↑                                     ↑
           └─ EntityType catalog grows ─────────┘

With Module 2 (Recursive Compaction):
  Project Level 0: [chunk₁, chunk₂, ..., chunk₅₀]
                            │
                            ▼ (Map-Reduce)
  Project Level 1: [summary₁ (from 50 chunks)]
                            │
                            ▼ (after 24h or > 30KB)
  Project Level 2: [meta-summary (from summary₁)]
                            │
                            ▼ (if needed)
  Project Level 3: [meta-meta-summary] ← STOP (max depth)
```

### SSE Events Emitted

```python
# When entity extraction completes
{
  "type": "entities_extracted",
  "chunk_id": "uuid",
  "project_id": "uuid",
  "entity_count": 8,
  "timestamp": "2026-02-05T..."
}

# When recursive compaction completes
{
  "type": "compaction_level_completed",
  "project_id": "uuid",
  "level": 2,
  "compression_ratio": 8.0,
  "summary_preview": "High-level summary...",
  "timestamp": "2026-02-05T..."
}

# When recursion is skipped (context not yet large enough)
{
  "type": "compaction_skipped",
  "project_id": "uuid",
  "reason": "context_size_below_threshold",
  "current_size_kb": 12.4,
  "threshold_kb": 30,
  "timestamp": "2026-02-05T..."
}
```

---

## Implementation Checklist

### Phase 1: Models & Database (Days 1-2)
- [ ] Create `backend/app/models/entity.py` with `Entity`, `EntityType`, `CompactionLevel`
- [ ] Update `backend/app/models/project.py` with `compaction_depth`, `meta_summary`, `entity_count`, timestamps
- [ ] Update `backend/app/db/database.py` with `EntityTable` ORM
- [ ] Write migration or raw SQL for `entities` table and `projects` alterations
- [ ] Update `ChunkStatus` enum to ensure `ARCHIVED` is available

**Tests (TDD):**
- [ ] `test_entity_creation_with_confidence_threshold`
- [ ] `test_compaction_level_model_compression_ratio`

### Phase 2: LLM Integration (Days 3-4)
- [ ] Extend `backend/app/core/ollama_client.py` with `extract_entities()` method
  - Prompting strategy
  - JSON parsing logic
  - Confidence thresholding
- [ ] Update `backend/app/core/compactor.py`:
  - Add `extract_entities_from_chunk()` function
  - Add `recursive_compact_project()` function with depth checks
  - Trigger logic for recursive compaction (24h timer + size threshold)

**Tests (TDD):**
- [ ] `test_extract_entities_valid_json`
- [ ] `test_extract_entities_malformed_json_fallback`
- [ ] `test_recursive_compact_with_depth_limit`
- [ ] `test_recursive_compact_skipped_when_small`

### Phase 3: Repository & Database Access (Days 5-6)
- [ ] Add `EntityRepository` class to `backend/app/db/repository.py`
  - `create_bulk(entities: list[Entity])`
  - `list_by_project(project_id, filters: {type, confidence_min})`
  - `count_by_type(project_id)`
- [ ] Update `ProjectRepository.get()`, `update()` to handle new fields
- [ ] Update `ChunkRepository.list()` to support filtering by `status=ARCHIVED`

**Tests (TDD):**
- [ ] `test_entity_repository_bulk_create`
- [ ] `test_entity_repository_filtering_by_type_and_confidence`

### Phase 4: API Endpoints (Days 7-8)
- [ ] Create `backend/app/api/entities.py` with:
  - `POST /api/v1/chunks/{chunk_id}/extract-entities` (manual trigger)
  - `GET /api/v1/projects/{project_id}/entities` (list with aggregations)
  - `GET /api/v1/projects/{project_id}/entities/aggregations` (by type/confidence)
- [ ] Update `backend/app/api/projects.py`:
  - `POST /api/v1/projects/{project_id}/recursive-compact` (manual trigger)
  - `GET /api/v1/projects/{project_id}/compaction-history`
  - Update `GET /{project_id}` response to include `meta_summary`, `entity_count`, `compaction_depth`

**Tests (TDD):**
- [ ] `test_manual_entity_extraction_endpoint`
- [ ] `test_manual_recursive_compact_endpoint`
- [ ] `test_entity_list_aggregations`
- [ ] `test_compaction_history_endpoint`

### Phase 5: Background Tasks & Scheduling (Days 9-10)
- [ ] Update `backend/app/api/chunks.py` background task:
  - After `process_chunk()` completes, add call to `extract_entities_from_chunk()`
- [ ] Create background job runner (`backend/app/core/scheduler.py` or extend `events.py`):
  - On timer (every 1 hour): check all projects for recursion eligibility
  - For each eligible project: schedule `recursive_compact_project()`
- [ ] Integrate into FastAPI lifespan (startup/shutdown)

**Tests (TDD):**
- [ ] `test_entity_extraction_triggered_after_chunk_processed`
- [ ] `test_recursive_compaction_scheduled_on_timer`
- [ ] `test_recursive_compaction_skipped_too_soon`

### Phase 6: Testing & Hammer Benchmarking (Days 11-13)
- [ ] Backend unit tests (~/25 tests)
- [ ] Integration tests (chunk → entity extraction → project compaction pipeline)
- [ ] Update `scripts/hammer_gen.py`:
  - Generate 500 chunks with varied content (errors, URLs, tool names)
  - Measure entity extraction latency per chunk
  - Measure compression ratios at each recursion level
  - Assert: recursion depth ≤ 3, compression ≥ 5:1
- [ ] Load test: 1000 chunks/project with recursive compaction

**Tests (TDD):**
- [ ] `test_e2e_chunk_capture_through_entity_extraction`
- [ ] `test_e2e_recursive_compaction_full_pipeline`
- [ ] (Hammer benchmark: see **Hammer Benchmarks** section below)

### Phase 7: Frontend Display (Days 14-16, Optional for MVP)
- [ ] React component: `EntityPanel.tsx` (read-only view of extracted entities)
- [ ] Update `ProjectList.tsx` to show entity count, compaction depth
- [ ] SSE subscription for `entities_extracted`, `compaction_level_completed` events
- [ ] (Defer advanced filtering/search to Module 3)

### Phase 8: Documentation (Days 17-18)
- [ ] Update `docs/ARCHITECTURE.md` with recursion diagram
- [ ] Create `docs/MODULE_2_IMPLEMENTATION.md` with execution journal
- [ ] Update API_REFERENCE.md with new endpoints
- [ ] Log any blockers/decisions in `ELICITATIONS.md`

---

## Dependencies & Risks

### Dependencies on Module 1
- **Ollama client** (`KomorebiLLM`): Required for entity extraction. Provides `extract_entities()` method.
- **Background task system** (FastAPI `BackgroundTasks`): Already in place; extended for entity extraction.
- **Compactor service** (`CompactorService`): Extended with recursive logic; original Map-Reduce logic preserved.
- **SSE event bus** (`event_bus`): Reused to emit entity/compaction events.
- **Project/Chunk models**: Extended, not replaced. Backward compatible.

### New Dependencies (Packages)
- **None**. Module 2 reuses:
  - `ollama` (async LLM)
  - `pydantic` (models)
  - `sqlalchemy` (ORM)
  - `asyncio` (scheduling)

### Integration Points
1. **With Module 1's `process_chunk()`**: Add entity extraction in background task after status→PROCESSED
2. **With Module 1's `compact_project()`**: Add recursion check after first reduce completes
3. **With FastAPI lifespan**: Initialize background scheduler on app startup
4. **With database**: Requires migration for `entities` table and `projects` alterations
5. **With SSE**: Two new event types (`entities_extracted`, `compaction_level_completed`)

### Potential Blockers & Mitigations

| Blocker | Impact | Mitigation |
|---------|--------|-----------|
| **LLM JSON parsing fails** | Entities not extracted; project continues | Wrap extraction in try-except; fallback to empty entity list; log error |
| **Infinite recursion (depth > 3)** | Performance degradation, context explosion | Explicit depth check: `if depth >= 3: return` |
| **Token estimation inaccuracy** | Recursive trigger fires too early/late | Start with conservative estimate (4 chars/token); tune via Hammer |
| **Database migration blockers** | Data loss or downtime | Test migration on staging first; provide rollback script |
| **Ollama timeout on large summaries** | Entity extraction hangs | Add timeout to LLM call: `timeout=30s`; fallback to no entities |
| **Scheduled recursion + high ingestion = thundering herd** | API overload | Use staggered scheduling (e.g., offset by project ID hash) |

### Fallback Strategies

1. **If Ollama unavailable during entity extraction:**
   - Return empty entity list (skip extraction)
   - Log warning; continue chunk processing
   - Retry extraction on next run (optional future feature)

2. **If recursion fails (bad LLM output):**
   - Skip recursion level; keep existing summary
   - Log error with stack trace
   - Emit `compaction_failed` event for monitoring

3. **If confidence threshold too strict (few entities extracted):**
   - Lower threshold from 0.6 → 0.5 (tunable config)
   - Hammer testing will validate optimal threshold

4. **If project context still growing unbounded:**
   - Implement hard size cap: truncate context_summary to 50KB max
   - Archive oldest chunks more aggressively
   - (Escalate to Module 3: vector-based semantic search)

---

## Alternate Approaches

### Alternate A: Vector Embeddings for Entity Storage

**Description:** Instead of normalized entity table, store vector embeddings (via Ollama or external API) and perform semantic search.

**Pros:**
- ✅ Enables "find similar errors across all projects"
- ✅ Natural language query interface ("Show me all database connection issues")
- ✅ Deduplication via embedding similarity

**Cons:**
- ❌ Requires external embedding API or GPU (latency)
- ❌ Increases complexity; vector DB not available in MVP SQLite
- ❌ Overkill for MVP; normalized table sufficient for now

**Verdict:** **Defer to Module 3**. Structured entities in MVP enable later semantic search. All entity data preserved for future vector ingestion.

---

### Alternate B: PostgreSQL JSON Columns for Recursion Metadata

**Description:** Store all compaction levels in a single JSON array on `projects.compaction_history` column instead of normalizing to `CompactionLevel` ORM.

**Pros:**
- ✅ Fewer database tables
- ✅ Simpler schema changes
- ✅ Native PostgreSQL JSONB indexing available in production

**Cons:**
- ❌ SQLite doesn't support efficient JSONB (App-side parsing needed)
- ❌ Harder to query/aggregate (e.g., "average compression ratio")
- ❌ Normalization principle violated

**Verdict:** **Use normalized `CompactionLevel` table**. Enables future aggregations (e.g., "show compression trends") and respects Komorebi's data architecture.

---

### Alternate C: Watermark-Based Recursion Triggers (Size-Only)

**Description:** Trigger recursion only when context_summary exceeds fixed size (30KB), with no time-based checks.

**Pros:**
- ✅ Simpler logic; no scheduler needed
- ✅ Recursion only when truly necessary

**Cons:**
- ❌ May trigger recursion immediately after first Reduce (if 50 chunks produce >30KB summary)
- ❌ Violates "Capture-First" philosophy (ingestion can be blocked during recursion)
- ❌ No control over recursion frequency

**Verdict:** **Use scheduled + watermark approach**. Scheduler ensures recursion doesn't block capture; watermark ensures we don't recurse too soon.

---

### Alternate D: Store Entities Inline in Chunk.summary (No Separate Table)

**Description:** Append extracted entities to chunk.summary as structured JSON suffix.

**Pros:**
- ✅ Zero schema changes
- ✅ Entities stay with chunk

**Cons:**
- ❌ Hard to query entities across chunks
- ❌ Bloats chunk.summary field
- ❌ Can't aggregate (e.g., "count errors by type across project")
- ❌ API for entity filtering becomes slow (full-text search on summary)

**Verdict:** **Use separate entities table**. Enables future analytics and agentic routing.

---

## Phase Breakdown

### MVP (Weeks 2-3 after Module 1 = Weeks 5-6 overall)

**Goal:** Recursive compaction + entity extraction infrastructure in place, validated via Hammer.

**Ships:**
- ✅ Recursive compaction (Map-Reduce level 2, with depth limit)
- ✅ Entity extraction (6 entity types, confidence threshold 0.6)
- ✅ Database schema (entities table, projects alterations)
- ✅ API endpoints (manual triggers for testing)
- ✅ Background task hooks
- ✅ 25+ unit & integration tests
- ✅ Hammer scenario for stress testing

**Does NOT ship:**
- ❌ Background scheduler (scheduled recursion); only manual/on-demand
- ❌ Frontend entity panel (API only)
- ❌ Advanced entity filtering (basic listing only)

**Rationale:** Recursion must be proven stable before automating. Manual triggers let us validate behavior in production.

---

### v1.0 (Weeks 4-6)

**Goal:** Production-ready Module 2 with scheduler and frontend.

**Adds:**
- ✅ Background scheduler for automatic recursive compation (24h timer)
- ✅ React entity panel (read-only, filterable by type/confidence)
- ✅ Entity aggregations endpoint
- ✅ Compaction history visualization
- ✅ Configuration for recursion depth & thresholds (env vars)
- ✅ Monitoring/alerting for failed recursion

**Does NOT ship:**
- ❌ Semantic search on entities (Module 3)
- ❌ Entity deduplication across projects (Module 3)
- ❌ MCP agent routing based on entities (Module 3)

---

### Post-v1.0 (Module 3+)

**Future Capabilities (not in Module 2 scope):**
- 🔮 Vector embeddings for entity similarity
- 🔮 Cross-project entity aggregation (e.g., "all errors matching pattern X")
- 🔮 MCP agent routing (e.g., error entities → Debug Agent)
- 🔮 Custom entity types (user-defined via config)
- 🔮 Entity lifecycle management (TTL, archival)

---

## Hammer Benchmarks (Stress Testing Strategy)

### Test Scenario 1: Bulk Entity Extraction
**Setup:** 500 chunks with varied content (errors, URLs, tool names).

**Metric:**
```
Entity Extraction Latency: P50, P95, P99
Entity Count Distribution: histogram by type
Confidence Score Distribution: mean, std dev
```

**Pass Criteria:**
- P99 latency < 2s per chunk
- ≥ 80% of extracted entities have confidence > 0.7
- At least 1 entity per chunk (on average)

---

### Test Scenario 2: Recursive Compaction
**Setup:** 10 projects, each with 100 PROCESSED chunks (10KB summaries each = 1MB combined).

**Metric:**
```
Compression Ratio (Level 1 → Level 2): target ≥ 5:1
Recursion Depth: never > 3
Recursion Latency: P99 < 10s per project
Memory usage: stable (no memory leak)
```

**Pass Criteria:**
- Compression ratio ≥ 5:1 (1MB summary → 200KB meta-summary)
- Zero projects exceed depth 3
- P99 latency < 10s
- Stable memory (no growth over 100 iterations)

---

### Test Scenario 3: Mixed Workload (Capture + Extraction + Recursion)
**Setup:** Concurrent ingestion of 1000 chunks over 5 minutes, while recursion scheduled for 2 projects.

**Metric:**
```
Ingestion Throughput: requests/sec
Entity Extraction Overhead: % additional latency vs. Module 1
Recursion Impact on Ingestion: % latency increase during recursion
```

**Pass Criteria:**
- Ingestion throughput ≥ 30 req/s (same as Module 1)
- Entity extraction adds ≤ 10% latency
- Recursion causes ≤ 5% ingestion latency spike (async, non-blocking)

---

## Success Validation Checklist

### Before Shipping v1.0

- [ ] 30+ unit tests (models, extraction, recursion)
- [ ] 5+ integration tests (end-to-end pipelines)
- [ ] Hammer scenario 1 passes (entity extraction latency)
- [ ] Hammer scenario 2 passes (recursive compression)
- [ ] Hammer scenario 3 passes (mixed workload)
- [ ] Manual testing: Create project → ingest 50 chunks → trigger recursion → verify meta-summary exists
- [ ] Manual testing: Extract entities manually → verify JSON parsing robust
- [ ] Code review checklist:
  - [ ] All async operations non-blocking
  - [ ] Error handling comprehensive (try-except with fallback)
  - [ ] Depth limit enforced (max 3)
  - [ ] Confidence threshold respected
  - [ ] Database migrations tested on staging
  - [ ] No n+1 queries
- [ ] Documentation complete (ARCHITECTURE.md, MODULE_2_IMPLEMENTATION.md, API_REFERENCE.md)
- [ ] ELICITATIONS.md updated with decisions
- [ ] PROGRESS.md updated
- [ ] Frontend panel tested with real data

---

## Open Questions for Team

1. **Entity confidence threshold:** Start at 0.6? Or more conservative (0.7)? Tune via Hammer.
2. **Recursion frequency:** 24-hour timer? Or more frequent (1h, 6h)? Impact on Ollama load?
3. **Entity types coverage:** Are the 7 types (error, url, tool_id, decision, identifier, code, reference) sufficient? Or add more (e.g., `metric`, `endpoint`, `config_name`)?
4. **Frontend entity display:** Read-only in MVP? Or allow manual tagging/correction for supervised ML future?
5. **Vector DB timeline:** Should we allocate Phase 7 for embeddings/semantic search, or push to Phase 8+?

**→ Log decisions in `ELICITATIONS.md` once team consensus reached.**

---

## Summary

Module 2 activates the next layer of the Memory Pyramid through recursive compaction and structured entity extraction. No new packages required. Fully backward compatible with Module 1. Ready for TDD-driven implementation with clear milestones and Hammer validation strategy.

**Next Step:** Team review → approval → implementation in Weeks 5-6 (post-Module-1 release).

---

**Proposal Authored:** February 5, 2026  
**Status:** Ready for Validation & Implementation Planning  
**Owner(s):** TBD by team
