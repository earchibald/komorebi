# Module 2: Recursive Compaction & Entity Extraction - Proposal

**Date:** February 5, 2026  
**Status:** Pending Approval  
**Depends On:** Module 1 (Ollama Integration) ✅

---

## 1. Executive Summary

### What is Module 2?

Module 2 extends Module 1's Map-Reduce pipeline by introducing **two new capabilities**:

1. **Recursive Compaction**: When a project's accumulated PROCESSED chunks exceed ~30KB, trigger a second pass of Map-Reduce. This prevents context window explosion and maintains the "Memory Pyramid" structure where older data is progressively abstracted into higher-level summaries.

2. **Entity Extraction**: Use the LLM to identify and catalog structured entities from chunks:
   - **Error Patterns**: Bug types, stack traces, frequency
   - **URLs & References**: Links to external docs, tools, APIs
   - **Tool IDs & Calls**: Extracted commands, function invocations
   - **Semantic Tags**: LLM-enhanced categorization beyond user tags

These extracted entities become queryable indexes, enabling future retrieval ("Module 3: Semantic Search").

### Why Now?

- **Module 1 Success**: LLM integration is stable and tested (21/21 tests passing). Entity extraction is a natural next step.
- **Memory Pyramid Readiness**: The INBOX → PROCESSED → COMPACTED → ARCHIVED pipeline is operational. Module 2 completes the pyramid by handling recursive depth.
- **Context Window Pressure**: Without recursive compaction, a single project can accumulate many PROCESSED summaries, risking LLM input limits (~8K tokens).
- **Unblocks Module 3**: Entity extraction provides structured data for semantic search.

### Success Criteria

| Criterion | Metric |
|-----------|--------|
| **Recursive Compaction** | Multiple compaction passes triggered correctly; context window stays < 75% of limit |
| **Entity Extraction** | ≥3 entity types extracted per chunk; false positive rate < 15% |
| **API Coverage** | New endpoints: GET `/api/v1/entities/{project_id}`, POST `/api/v1/chunks/{chunk_id}/extract` |
| **Tests** | ≥8 new tests covering recursion depth, entity accuracy, edge cases |
| **Performance** | Compaction latency < 2s for typical project (1000 PROCESSED chunks) |
| **Hammer Benchmark** | Stress test with 500 chunks + recursive compaction, all succeed |

---

## 2. Technical Specifications

### 2.1 New Pydantic Models

#### Entity Model (backend/app/models/entity.py)

```python
class EntityType(str, Enum):
    """Categories of extractable entities."""
    ERROR_PATTERN = "error_pattern"
    URL = "url"
    TOOL_ID = "tool_id"
    SEMANTIC_TAG = "semantic_tag"
    SYSTEM_ANCHOR = "system_anchor"  # For tracking context drift

class Entity(BaseModel):
    """An extracted entity from a chunk."""
    id: UUID = Field(default_factory=uuid4)
    chunk_id: UUID
    project_id: UUID
    entity_type: EntityType
    value: str = Field(..., description="The extracted entity value")
    context: str = Field(..., description="Surrounding context (50 chars before/after)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="LLM confidence score")
    raw_extraction: Optional[str] = Field(None, description="Full LLM response for debugging")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class EntityCreate(BaseModel):
    """Schema for creating entities."""
    entity_type: EntityType
    value: str
    context: str
    confidence: float

class EntitySummary(BaseModel):
    """Aggregated entity summary for a project."""
    project_id: UUID
    entity_type: EntityType
    unique_count: int
    examples: list[str]  # Top 5 most common
    frequency: dict[str, int]  # value -> count
```

#### CompactionLevel Model (backend/app/models/project.py - extend)

```python
class CompactionLevel(BaseModel):
    """Tracks recursive compaction state."""
    level: int = Field(default=0, description="0=PROCESSED, 1=first compaction, 2+=recursive")
    summary: str = Field(..., description="Summary at this level")
    chunk_count: int = Field(..., description="# chunks summarized to create this level")
    token_estimate: int = Field(..., description="Estimated tokens in summary")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Project (extend):
    """Add to existing Project model."""
    compaction_levels: list[CompactionLevel] = Field(default_factory=list)
    entity_index: Optional[dict] = Field(None, description="Cached entity frequencies")
```

### 2.2 Recursive Compaction Algorithm

#### Trigger Logic

```python
async def should_trigger_recursive_compaction(
    project_id: UUID,
    context_window_limit: int = 8192,
    safe_threshold: float = 0.75,
) -> bool:
    """
    Determine if recursive compaction should trigger.
    
    Returns True if:
    1. Total tokens in PROCESSED summaries > 75% of context_window_limit
    2. OR more than 20 PROCESSED chunks remain uncompacted
    3. AND last compaction was > 5 minutes ago (cooldown)
    """
    project = await project_repo.get(project_id)
    processed_chunks = await chunk_repo.list(
        status=ChunkStatus.PROCESSED,
        project_id=project_id,
    )
    
    if not processed_chunks:
        return False
    
    # Estimate tokens: average 100 chars ~= 25 tokens
    total_tokens = sum(
        (c.token_count or len(c.summary or "") // 4)
        for c in processed_chunks
    )
    
    trigger_within_window = total_tokens > (context_window_limit * safe_threshold)
    trigger_chunk_count = len(processed_chunks) > 20
    
    last_compaction = max(
        (level.created_at for level in project.compaction_levels),
        default=None
    )
    within_cooldown = (
        last_compaction and
        datetime.utcnow() - last_compaction < timedelta(minutes=5)
    )
    
    return (trigger_within_window or trigger_chunk_count) and not within_cooldown
```

#### Compaction Depth Limits

```python
COMPACTION_STRATEGY = {
    "max_depth": 3,              # Never go deeper than 3 levels
    "min_chunks_per_level": 5,   # Don't compct if < 5 chunks
    "max_summary_tokens": 2000,  # Each level summary max
    "system_anchor": (
        "You are creating a hierarchical summary of a project's work. "
        "Preserve high-level goals and key decisions. Focus on: "
        "What is being built? What are the current blockers? What's completed?"
    ),
}
```

#### Compaction Pass Pseudocode

```pseudocode
async function compact_recursive(project_id, current_depth=0):
    IF current_depth >= max_depth:
        RETURN  # Stop recursion
    
    IF not should_trigger_recursive_compaction(project_id):
        RETURN
    
    # Get PROCESSED chunks at current level
    chunks = fetch_chunks(status=PROCESSED, project_id=project_id)
    
    IF chunks.count < min_chunks_per_level:
        RETURN
    
    # This is the "second pass" of Map-Reduce
    # Map: Collect summaries (already done in Module 1)
    summaries = [c.summary for c in chunks]
    
    # Reduce: Create higher-level summary
    combined = join(summaries, "\n---\n")
    
    recursive_summary = llm.summarize(
        combined,
        max_tokens=max_summary_tokens,
        system_anchor=SYSTEM_ANCHOR,
    )
    
    # Store this compaction level
    project.compaction_levels.append({
        level: current_depth + 1,
        summary: recursive_summary,
        chunk_count: chunks.count,
        token_estimate: token_count(recursive_summary),
    })
    
    # Mark all summarized chunks as COMPACTED (cleaned up from active context)
    for chunk in chunks:
        chunk.status = COMPACTED
    
    # Recursively attempt another pass with remaining PROCESSED chunks
    # (if new chunks were added to PROCESSED since last pass)
    compact_recursive(project_id, current_depth + 1)
```

### 2.3 Entity Extraction Pipeline

#### Extraction Prompt

```python
ENTITY_EXTRACTION_PROMPT = """
Extract structured entities from this chunk. Return a JSON object with this schema:
{
    "errors": [{"type": "str", "description": "str", "confidence": 0.0-1.0}],
    "urls": ["url1", "url2"],
    "tool_ids": ["command1", "function_call1"],
    "semantic_tags": [{"tag": "str", "rationale": "str", "confidence": 0.0-1.0}],
}

Confidence threshold: only include if > 0.6 confidence.
"""

async def extract_entities(chunk: Chunk) -> dict[EntityType, list[Entity]]:
    """
    Use LLM to extract entities from a chunk.
    
    Flow:
    1. Send chunk content + extraction prompt to LLM
    2. Parse JSON response (with fallback)
    3. Validate entities (confidence, value length)
    4. Store in database with confidence scores
    5. Publish event for indexing
    
    Returns:
        Dict mapping EntityType -> list of Entity objects
    """
    llm = KomorebiLLM()
    
    if not await llm.is_available():
        return {}  # Graceful degradation
    
    try:
        raw_response = await llm.extract_entities(
            chunk.content,
            system_anchor=ENTITY_EXTRACTION_PROMPT,
        )
        
        parsed = json.loads(raw_response)
        entities = {}
        
        # Process error patterns
        for error in parsed.get("errors", []):
            if error["confidence"] > 0.6:
                entities.setdefault(EntityType.ERROR_PATTERN, []).append(
                    Entity(
                        chunk_id=chunk.id,
                        entity_type=EntityType.ERROR_PATTERN,
                        value=error["type"],
                        context=error["description"],
                        confidence=error["confidence"],
                    )
                )
        
        # Process URLs
        for url in parsed.get("urls", []):
            if _is_valid_url(url):
                entities.setdefault(EntityType.URL, []).append(
                    Entity(
                        chunk_id=chunk.id,
                        entity_type=EntityType.URL,
                        value=url,
                        context="URL reference",
                        confidence=0.95,  # High confidence for explicit URLs
                    )
                )
        
        # ... similar for tool_ids and semantic_tags
        
        return entities
        
    except JSONDecodeError as e:
        # Fallback: simple keyword extraction
        return _extract_entities_fallback(chunk)
```

### 2.4 API Endpoints (New)

#### POST `/api/v1/chunks/{chunk_id}/extract`

Extract entities from a single chunk.

**Request:**
```json
{
  "entity_types": ["error_pattern", "url"],  // Optional filter
  "force_reextract": false
}
```

**Response (202 Accepted):**
```json
{
  "chunk_id": "uuid",
  "task_id": "uuid",
  "status": "queued",
  "message": "Extraction started in background"
}
```

#### GET `/api/v1/projects/{project_id}/entities`

Retrieve aggregated entity index for a project.

**Query Parameters:**
- `entity_type`: Filter by type (optional)
- `limit`: Max unique entities to return (default 100)
- `sort_by`: "frequency" or "recent" (default: frequency)

**Response:**
```json
{
  "project_id": "uuid",
  "total_entities": 42,
  "by_type": {
    "error_pattern": {
      "unique_count": 5,
      "examples": ["NullPointerException", "TimeoutError"],
      "frequency": { "NullPointerException": 7, "TimeoutError": 3 }
    },
    "url": {
      "unique_count": 12,
      "examples": ["https://docs.example.com/api", ...],
      "frequency": { ... }
    }
  }
}
```

#### POST `/api/v1/projects/{project_id}/compact-recursive`

Manually trigger recursive compaction (for testing/admin).

**Request:**
```json
{
  "max_depth": 3,
  "context_window_limit": 8192,
  "safe_threshold": 0.75
}
```

**Response (202 Accepted):**
```json
{
  "project_id": "uuid",
  "task_id": "uuid",
  "current_depth": 0,
  "expected_passes": 2,
  "estimated_tokens_saved": 1200
}
```

### 2.5 Database Schema Changes

#### New Table: `entities`

```sql
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    value TEXT NOT NULL,
    context TEXT,
    confidence FLOAT CHECK(confidence >= 0.0 AND confidence <= 1.0),
    raw_extraction TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_project_entity (project_id, entity_type),
    INDEX idx_chunk_entities (chunk_id)
);
```

#### Updated Table: `projects`

```sql
ALTER TABLE projects ADD COLUMN (
    compaction_levels JSON DEFAULT '[]',  -- Store as JSON array
    entity_index JSON DEFAULT NULL,       -- Cached frequency map
    last_recursive_compaction TIMESTAMP,
    recursive_depth INT DEFAULT 0
);
```

---

## 3. Data Flow

### 3.1 Recursive Compaction Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Background Job: Check Compaction Triggers Every 5 Minutes   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │ For Each Project with PROCESSED:   │
        │ 1. Count cumulative tokens         │
        │ 2. Check if > 75% of context_limit │
        │ 3. Check if > 20 chunks uncompacted│
        └────────────────────────┬───────────┘
                                 │
                    ┌────────────┴─────────────┐
                    │ No                       │ Yes
                    ▼                          ▼
                  EXIT              ┌──────────────────────────┐
                                    │ Should Trigger Recursion?│
                                    │ Check: not in cooldown   │
                                    │        depth < max       │
                                    └────────────┬─────────────┘
                                                 │
                                  ┌──────────────┴────────────┐
                                  │ No                        │ Yes
                                  ▼                           ▼
                                 EXIT           ┌──────────────────────────┐
                                                │ Compaction Level 1:      │
                                                │ Summaries → Reduce       │
                                                │ Chunks PROCESSED→COMPACT │
                                                │ Publish EVENT            │
                                                └────────────┬─────────────┘
                                                             │
                                                             ▼
                                                ┌──────────────────────────┐
                                                │ Check New PROCESSED Added│
                                                │ Since Last Pass?         │
                                                └────────────┬─────────────┘
                                                             │
                                            ┌────────────────┴──────────────┐
                                            │ No                            │ Yes
                                            ▼                              ▼
                                           DONE                  ┌──────────────────────────┐
                                                                 │ Recursion Level 2, etc.  │
                                                                 │ Repeat Reduce Pattern     │
                                                                 └──────────────────────────┘
```

### 3.2 Entity Extraction Flow

```
POST /api/v1/chunks/{chunk_id}/extract
       │
       ▼
    Queue Task
       │
       ├─ Background Worker ─────┐
       │                         │
       ▼                         ▼
   Load Chunk          Check if Already Extracted
       │                         │
       └────────────┬────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Send to LLM:         │
         │ - chunk.content      │
         │ - extraction_prompt  │
         │ - system_anchor      │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Parse JSON Response  │
         │ Validate entities    │
         │ Filter < 0.6 conf    │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Store Entities:      │
         │ INSERT INTO entities │
         │ UPDATE entity_index  │
         └──────────┬───────────┘
                    │
                    ▼
        Publish EVENT: ENTITIES_EXTRACTED
                    │
                    ▼
         Return 202 Accepted
```

### 3.3 State Transitions

```
Chunk Lifecycle (Extended from Module 1):

Old Module 1:
  INBOX ──(LLM process_chunk)──> PROCESSED ──(LLM compact)──> COMPACTED

New Module 2:
  INBOX ──(LLM process_chunk)──> PROCESSED ──(extract_entities)──> PROCESSED
                                    ▲                               │
                                    │                               │
                                    └───(trigger check)─────────────┘
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │ Trigger? Batch PROCESS
                                    │ Chunks → Reduce      │
                                    │ Level 1 Summary      │
                                    │ Move to COMPACTED    │
                                    └──────────────────────┘
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │ Check Recursion      │
                                    │ Trigger? Batch COMPACT
                                    │ Chunks (level 1)     │
                                    │ → Reduce (level 2)   │
                                    │ Move to ARCHIVED     │
                                    └──────────────────────┘
```

### 3.4 SSE Events Emitted

```python
# When chunk processed (Module 1 existing)
{
    "event_type": "CHUNK_UPDATED",
    "chunk_id": "...",
    "status": "processed",
    "summary": "...",
}

# NEW: When entities extracted
{
    "event_type": "ENTITIES_EXTRACTED",
    "chunk_id": "...",
    "entities_count": 7,
    "by_type": {
        "error_pattern": 2,
        "url": 3,
        "semantic_tag": 2,
    }
}

# NEW: When compaction level completed
{
    "event_type": "COMPACTION_LEVEL_COMPLETE",
    "project_id": "...",
    "level": 1,
    "chunks_compacted": 15,
    "summary_preview": "...(first 100 chars)",
    "next_trigger_check": "2026-02-05T10:30:00Z",
}
```

---

## 4. Implementation Checklist

### Phase 1: Data Models & Database (Week 1)

- [ ] **backend/app/models/entity.py** (NEW)
  - `Entity`, `EntityCreate`, `EntityType` enum
  - `EntitySummary` for aggregation
  - ✓ Dependency: None (pure Pydantic)

- [ ] **backend/app/models/project.py** (MODIFY)
  - Add `compaction_levels: list[CompactionLevel]`
  - Add `entity_index: Optional[dict]`
  - Add `recursive_depth: int`
  - ✓ Dependency: None

- [ ] **backend/app/db/repository.py** (NEW METHODS)
  - `EntityRepository` class with CRUD
  - `entities_for_chunk()`, `entities_by_type()`, `aggregate_entity_index()`
  - ✓ Dependency: Database schema migration

- [ ] **Database Migration Script** (NEW)
  - Create `entities` table
  - Alter `projects` table
  - Run via Alembic or manual script
  - ✓ Dependency: SQLAlchemy models

### Phase 2: LLM & Extraction (Week 1-2)

- [ ] **backend/app/core/entity_extractor.py** (NEW)
  - `EntityExtractor` class
  - `extract_entities(chunk)` method
  - Parsing, validation, fallback logic
  - ✓ Dependency: `KomorebiLLM`

- [ ] **backend/app/core/ollama_client.py** (MODIFY)
  - Add `extract_entities(content, system_anchor)` method
  - Add `extract_with_json_fallback()` helper
  - ✓ Dependency: ollama package

- [ ] **backend/app/core/compactor.py** (MODIFY)
  - Add `compute_compaction_level()` method
  - Add `should_trigger_recursive_compaction()` logic
  - Add `compact_recursive(project_id, depth)` method
  - Integrate entity extraction into `process_chunk()`
  - ✓ Dependency: `EntityExtractor`

### Phase 3: API Endpoints (Week 2)

- [ ] **backend/app/api/chunks.py** (MODIFY)
  - POST `/{chunk_id}/extract` endpoint
  - Background task: `_extract_chunk_background()`
  - ✓ Dependency: `EntityExtractor`

- [ ] **backend/app/api/projects.py** (MODIFY)
  - GET `/{project_id}/entities` endpoint
  - POST `/{project_id}/compact-recursive` endpoint
  - ✓ Dependency: `CompactorService`

- [ ] **backend/app/api/entities.py** (NEW)
  - GET `/` list with filters
  - GET `/{entity_id}` detail
  - DELETE endpoints for admin cleanup
  - ✓ Dependency: `EntityRepository`

### Phase 4: Testing (Week 2-3)

- [ ] **backend/tests/test_entity_extraction.py** (NEW, 4 tests)
  - ✓ `test_extract_errors_from_chunk` (Red → Green)
  - ✓ `test_extract_urls_and_tool_ids` (Red → Green)
  - ✓ `test_entity_confidence_filtering` (Red → Green)
  - ✓ `test_entity_extraction_fallback_if_ollama_unavailable` (Red → Green)

- [ ] **backend/tests/test_recursive_compaction.py** (NEW, 4 tests)
  - ✓ `test_should_trigger_recursive_compaction_by_token_count` (Red → Green)
  - ✓ `test_should_trigger_recursive_compaction_by_chunk_count` (Red → Green)
  - ✓ `test_recursive_compaction_depth_limit` (Red → Green)
  - ✓ `test_compaction_level_state_transitions` (Red → Green)

- [ ] **backend/tests/test_api_entities.py** (NEW, 3 tests)
  - ✓ `test_list_entities_with_filters` (Red → Green)
  - ✓ `test_extract_chunk_endpoint_202_async` (Red → Green)
  - ✓ `test_project_entity_aggregation_endpoint` (Red → Green)

- [ ] **backend/tests/test_integration_module_2.py** (NEW, 2 tests)
  - ✓ `test_end_to_end_chunk_to_entities_to_compaction` (Red → Green)
  - ✓ `test_concurrent_extraction_and_compaction` (Red → Green)

### Phase 5: Hammer Benchmarking (Week 3)

- [ ] **scripts/hammer_gen.py** (MODIFY)
  - Add entity extraction requests
  - Add recursive compaction trigger
  - Stress test with 500+ chunks
  - Generate "dirty" chunks (errors, URLs, mixed formats)
  - ✓ Dependency: New API endpoints

### Phase 6: Documentation (Week 3)

- [ ] **docs/MODULE_2_VERIFICATION.md** (NEW)
  - Success criteria checklist
  - End-to-end walkthrough
  - Performance benchmarks

- [ ] **CONVENTIONS.md** (MODIFY)
  - Document entity extraction pattern
  - Document recursive compaction trigger logic

---

## 5. Dependencies & Risks

### 5.1 New Packages Required

| Package | Version | Purpose | Risk Level |
|---------|---------|---------|-----------|
| `ollama` | ≥0.1.0 | Already installed (Module 1) | ✅ None |
| `pydantic` | ≥2.0 | Already installed | ✅ None |
| `aiosqlite` / `asyncpg` | Existing | Already used | ✅ None |
| `python-json-schema` | ≥1.0 (optional) | JSON validation fallback | ⚠ Low |

**No new external dependencies required.**

### 5.2 Integration Points

```
Module 2 ←→ Module 1
├─ Uses: KomorebiLLM from ollama_client.py
├─ Uses: CompactorService base structure
├─ Extends: ChunkStatus enum (no changes, compatible)
└─ Publishes: New events to event_bus

Module 2 ←→ Database
├─ Reads: chunks (status, summary, token_count)
├─ Reads: projects (compaction_levels history)
├─ Writes: entities table (NEW)
├─ Updates: projects (compaction_levels, entity_index)
└─ Risk: Schema migration must complete before deployment

Module 2 ←→ Frontend (Optional for MVP)
├─ SSE: New event types (ENTITIES_EXTRACTED, COMPACTION_LEVEL_COMPLETE)
├─ UI Component: EntityPanel (showing extracted errors, URLs)
└─ Deferred to post-MVP (Phase 7)
```

### 5.3 Potential Blockers

| Blocker | Severity | Mitigation |
|---------|----------|-----------|
| **JSON Parsing Failure** | Medium | Implement fallback keyword extraction; log raw response for debugging |
| **Recursive Infinity Loop** | High | Enforce `max_depth=3`; add exponential backoff cooldown |
| **Token Estimation Accuracy** | Low | Use conservative multiplier (chars/4 → tokens); monitor in Hammer test |
| **Ollama Unavailable During Extraction** | Medium | Gracefully degrade to empty entity list; queue for retry |
| **Database Migration Timing** | High | Test migration script on staging before production; include rollback plan |
| **High False Positives in Extraction** | Medium | Fine-tune confidence thresholds via Hammer; log examples to ELICITATIONS.md |

### 5.4 Fallback Strategies

#### Fallback 1: LLM Unavailable
```python
async def extract_entities_fallback(chunk: Chunk) -> dict:
    """If LLM unavailable, use rule-based extraction."""
    entities = {}
    
    # Rule: Any line with "error" or "Error"
    for line in chunk.content.split('\n'):
        if 'error' in line.lower():
            entities.setdefault(EntityType.ERROR_PATTERN, []).append(
                Entity(
                    chunk_id=chunk.id,
                    entity_type=EntityType.ERROR_PATTERN,
                    value="[DETECTED_ERROR]",
                    context=line[:100],
                    confidence=0.5,  # Lower confidence
                )
            )
    
    # Rule: Extract http/https URLs with regex
    urls = re.findall(r'https?://[^\s]+', chunk.content)
    for url in urls:
        entities.setdefault(EntityType.URL, []).append(...)
    
    return entities
```

#### Fallback 2: Recursive Compaction Fails
```python
async def compact_recursive_safe(...):
    """If recursion fails, keep current state and emit warning."""
    try:
        await compact_recursive(project_id, depth=0)
    except Exception as e:
        logger.warning(f"Recursive compaction failed: {e}")
        # PROCESSED chunks remain PROCESSED; can retry later
        # Project.recursive_depth not incremented
        await event_bus.publish(ChunkEvent(
            event_type=EventType.COMPACTION_FAILED,
            chunk_id=project_id,
            data={"error": str(e)},
        ))
```

#### Fallback 3: Entity Confidence Too Low
```python
# If LLM extraction returns < 50% avg confidence per chunk:
# → Skip entity indexing for that chunk
# → Log to ELICITATIONS.md: "Consider adjusting extraction prompts"
# → Continue processing without stalling
```

---

## 6. Alternate Approaches

### Alternate A: Vector Embedding + Semantic Search (Deferred)

**Description:** Use an embedding model (e.g., via Ollama's embedding endpoint or external service like OpenAI) to create dense vector representations of summaries. Store in a vector DB (Pinecone, Weaviate, Milvus) or PostgreSQL with pgvector extension.

**Pros:**
- Fuzzy semantic search: "Show me chunks about authentication failures"
- Similarity matching: "Find similar issues"
- Cross-project pattern detection: "Which projects have similar errors?"

**Cons:**
- Requires new infrastructure (vector DB)
- Higher latency (~500ms per query)
- Additional model calls (↑ cost, ↑ Ollama load)
- Complexity: storage, indexing, query optimization

**Recommendation:** **Defer to Module 3 (Phase 7)**. Module 2 focuses on structured extraction (error types, URLs). Semantic search can leverage these entities as starting point.

---

### Alternate B: Native PostgreSQL JSON Indexing (Lightweight)

**Description:** Skip the `entities` table entirely. Store extracted entities as a JSONB column on `chunks`, and use PostgreSQL's native JSONB operators (`@>`, `?`) for querying.

**Pros:**
- No schema migration complexity
- Single table write (faster)
- Native GIN index support on JSONB
- Lightweight, suitable for MVP

**Cons:**
- Query complexity for aggregation (entity_index on project)
- Harder to enforce consistency (no foreign key constraints)
- Bulk deletion of old entities requires JSON array manipulation
- Less structured for future aggregations

**Recommendation:** **Not selected for MVP.** Normalized `entities` table is more maintainable as we add features (confidence filtering, type-specific queries, global entity catalog).

---

### Alternate C: Watermark-Based Compaction (vs. Scheduled Triggers)

**Description:** Instead of background job checking every 5 min, compaction is triggered automatically when a chunk is marked PROCESSED (push model) and accumulated token count exceeds watermark.

**Pros:**
- Lower latency: compaction starts immediately (not waiting for next 5-min cycle)
- More reactive: prevents context bloat in real-time

**Cons:**
- Risk of thundering herd: many chunks processed → many concurrent compaction jobs
- Harder to throttle and control resources
- Violates "Capture-First" philosophy (fast capture should not block on compaction)

**Recommendation:** **Keep scheduled trigger model (current design).** Provides better resource control and aligns with "Capture Now, Refine Later."

---

## 7. Phase Breakdown

### MVP (Module 2a): Immediate – Recursive Compaction Only

**Timeline:** 2-3 weeks  
**Ships:** Core recursion logic without entity indexing

**Includes:**
- ✅ Recursive compaction with depth limits
- ✅ New compaction_levels field on Project
- ✅ Background job that checks triggers every 5 min
- ✅ POST `/api/v1/projects/{project_id}/compact-recursive` for manual testing
- ✅ Tests: 4 recursive compaction tests
- ✅ Hammer: Load test with 500 chunks, trigger recursion, verify all pass

**Does NOT Include:**
- ❌ Entity extraction (save for v1.0)
- ❌ Entity API endpoints
- ❌ Frontend entity panel
- ❌ Entity index caching

**Rationale:** Recursion is prerequisite for extraction (avoid extracting same error patterns from different compaction levels). Ship recursion first, stable; then layer extraction on top.

---

### v1.0 (Module 2b): Entity Extraction

**Timeline:** Weeks 4-6 (after MVP ships)  
**Depends On:** Module 2a MVP ✅

**Includes:**
- ✅ Entity extraction pipeline (all 4 entity types)
- ✅ Entity repository + database
- ✅ Confidence filtering (> 0.6)
- ✅ POST `/api/v1/chunks/{chunk_id}/extract` endpoint
- ✅ GET `/api/v1/projects/{project_id}/entities` aggregation endpoint
- ✅ Tests: 7 new tests covering extraction + API
- ✅ Update Hammer to include extraction requests
- ✅ Frontend: Read-only EntityPanel component (no mutations)

**Does NOT Include:**
- ❌ Vector embeddings
- ❌ Semantic search
- ❌ Manual entity editing/deletion
- ❌ Entity validation rules (future: e.g., enforce URL format)

---

### Post-v1.0 (Module 3+): Advanced Features

**Phase 7 (Semantic Search):**
- Vector embeddings for entities
- Fuzzy search: "Find chunks mentioning database errors"
- Cross-project pattern matching

**Phase 8 (Entity Catalog):**
- Global entity registry (not per-project)
- Track entity evolution over time
- Suggest common error patterns across all projects

**Phase 9 (Agentic Entity Management):**
- Smart merging of similar entities ("NullPointer" ← canonical)
- Auto-classification of new errors
- Anomaly detection (e.g., "Spike in TimeoutErrors")

---

## 8. Success Validation

### Test Coverage Checklist

- [ ] `test_recursive_compaction_triggers_by_token_count`
- [ ] `test_recursive_compaction_respects_depth_limit`
- [ ] `test_recursive_compaction_cooldown`
- [ ] `test_compaction_level_data_structure`
- [ ] `test_extract_entities_json_parse` (LLM response)
- [ ] `test_extract_entities_fallback` (no Ollama)
- [ ] `test_entity_confidence_filtering`
- [ ] `test_list_entities_endpoint_with_filters`
- [ ] `test_entity_aggregation_by_type`
- [ ] `test_end_to_end_chunk_to_compaction_levels`

### Hammer Benchmark

**Scenario:** 500 chunks, 5 projects, recursive compaction triggered

```
Expected Results:
- All 500 chunks move from INBOX → PROCESSED (Module 1)
- Compaction triggers when PROCESSED count > 20 per project
- Recursion reaches Level 1 and optionally Level 2
- All chunks eventually COMPACTED or ARCHIVED
- Latency: p95 < 500ms per compaction pass
- No errors logged; graceful Ollama unavailable handling
```

---

## 9. Risk Mitigation & Rollback Plan

### If Recursive Compaction Causes Context Loss

**Symptom:** High-level summaries missing critical details after Level 2 compaction.

**Mitigation:**
1. Lower `safe_threshold` from 0.75 to 0.5 (trigger earlier, smaller batches)
2. Increase `max_summary_tokens` per level
3. Add more specific system_anchor prompts per industry domain

**Rollback:** Keep compaction_levels as immutable history. Can re-run compaction at lower depth.

### If Entity Extraction False Positive Rate > 15%

**Symptom:** Entity index polluted with non-errors, invalid URLs.

**Mitigation:**
1. Increase confidence threshold from 0.6 to 0.7
2. Add post-extraction validation (e.g., URL must be valid HTTP)
3. Fine-tune extraction prompt with negative examples

**Rollback:** Clear entity_index; disable extraction temporarily; retry after prompt tuning.

---

## 10. Open Questions → ELICITATIONS.md

1. **Compaction Anchor Tuning:** Should system_anchor be parameterizable per project (domain-specific)?
   - *Provisional:* No for MVP. Add in v1.0 via project settings.

2. **Entity Deduplication:** How to handle similar entities across multiple chunks (e.g., "NullPointerException" vs. "Null Pointer Exception")?
   - *Provisional:* Exact-match deduplication for MVP. Fuzzy matching in Phase 8.

3. **Recursive Depth UI Feedback:** Should frontend display compaction level hierarchy?
   - *Provisional:* No for MVP. Display in admin panel (Phase 9). Hide from users until stable.

4. **Entity Cleanup Policy:** When should old entities be deleted?
   - *Provisional:* Never delete (immutable history for audit). Pagination in queries (Phase 8).

---

## Conclusion

Module 2 completes the "Memory Pyramid" by introducing recursive depth and structured entity extraction. It unblocks Module 3 (Semantic Search) while maintaining the "Capture-First" philosophy.

**Recommendation:** Approve for MVP phase (Recursive Compaction). Phase entity extraction (v1.0) after MVP validation.

---

**Next Steps:**
1. Operator review & feedback
2. Create GitHub issue: `[Module 2] Recursive Compaction & Entity Extraction`
3. Assign story points + sprint
4. Begin TDD cycle (Red → Green → Hammer)
