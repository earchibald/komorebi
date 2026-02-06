# Architect Brief: v0.7.0 — User Data API & Contextual Query Features

**Date:** February 7, 2026  
**Phase:** strategic planning for MODULE 6  
**Status:** Kickoff (architect-feature prompt required)  
**Primary Goal:** Make Komorebi *usable* by real people doing real work

---

## Strategic Context

We built a powerful flexible engine (Module 1-5: capture, projects, entities, MCP, search, deployment, bulk ops). **Now comes the hard question: What do I actually *do* with this as a PERSON?**

Current state:
- ✅ Data ingestion works (chunk capture)
- ✅ Organization exists (projects + entities)
- ✅ Search indexes chunks by text
- ❌ **Cannot do contextual queries** (answer questions about "my" data)
- ❌ **Cannot explore relationships** (entity connections, temporal patterns)
- ⚠️ **Search has usability bugs** (cannot type in fields, UI not responsive)
- ❌ **No way to get answers from my data** (no RAG, no synthesis, no insights)

The MVP vision was: *"Cognitive infrastructure for operations"* — yet we haven't connected the cognition part to user workflows.

---

## Part 1: Critical Bugs (Blocking User Adoption)

### Bug 1: Search Input Fields Not Accepting Text

**Impact:** HIGH - Users cannot perform any search operations
**Description:** When user clicks "All Chunks" search box (or filter fields), characters don't register. No text appears in input fields. Affects:
- Text search box in SearchBar component
- Status filter in FilterPanel
- Date range inputs
- Project selection dropdown

**Suspected Cause:** Likely input event binding issue in React/Preact signals or event handler not wired correctly

**Acceptance Criteria for Fix:**
- [ ] User can type text into search box and see characters appear
- [ ] List selector dropdowns respond to clicks
- [ ] Date picker fields accept input
- [ ] All filter fields in FilterPanel are interactive
- [ ] Hammer test: 100 rapid search keystroke sequences complete without errors

---

### Bug 2: (Potentially) Search Filter State Not Persisting

**Impact:** MEDIUM - User workflow broken
**Description:** After apply filters, unclear if state persists. May be related to above or separate signal/state issue.

**Acceptance Criteria:**
- [ ] Apply filter → results update
- [ ] Close filter panel → re-open → filters still there
- [ ] Clear filters → state clears, all chunks show
- [ ] Refresh page → filters lost (expected for MVP)

---

## Part 2: Module 6 — User Data API

### 2.1 Vision

Komorebi should be **a queryable knowledge base for your work**. Users ask questions about their captured data and get answers. Three layers:

1. **Data API Layer** (v0.7.0) — Filtered queries, aggregations, timeline views
2. **Intelligence Layer** (v0.8.0+) — Ollama synthesis over chunks, LLM-generated insights
3. **Exploration UI** (v0.8.0+) — Visual graph of entities, timeline scrubber, entity explorer

**This phase (v0.7.0):** Focus on *usability* — making data exploration intuitive without AI. Lay groundwork for synthesis later.

### 2.2 Core User Personas & Use Cases

#### Persona 1: The Researcher
*"I captured 200 articles about AI safety. How do I find all of them? Can I see related entities? What time period do they cover?"*

**Needs:**
- Filter by date range (when I was researching this topic)
- See all chunks in a project + their relationships
- View entity graph (what topics are mentioned together?)
- Export timeline of my research activity

**Endpoints Required:**
- `GET /projects/{id}/chunks` (filter, sort, paginate)
- `GET /projects/{id}/timeline` (chunks grouped by date)
- `GET /entities/{id}/related` (connected entities)
- `GET /entities/graph` (all entities + connections)

#### Persona 2: The Manager
*"My team captured tickets from 3 different sources. Show me a unified dashboard: how many new items this week? Which projects are growing? What's the oldest inbox item?"*

**Needs:**
- Dashboard stats (total chunks, by status, by project, by week)
- Inbox cleanup (show me the 50 oldest items, let me bulk action them)
- Project health (item velocity, status distribution)

**Endpoints Required:**
- `GET /stats/dashboard` (enhanced with timeline)
- `GET /chunks?status=inbox&sort=created_at&limit=50`
- `GET /projects/{id}/stats` (chunk count by status, by week)

#### Persona 3: The Knowledge Worker
*"I have thousands of notes/snippets. Help me discover: What did I learn about X? What are my frequent topics? Show me my thinking over time."*

**Needs:**
- Topic/entity frequency over time (word clouds, bar charts)
- "Related chunks" — if I'm reading chunk A, show similar chunks
- Search history (what have I searched before?)
- Smart collections (auto-group chunks by topic)

**Endpoints Required:**
- `GET /chunks/related/{id}` (cosine similarity-based, TF-IDF)
- `GET /stats/entities/frequency` (with time bucketing)
- `GET /chunks/similar?query=...` (semantic, if Ollama available)

---

## Part 3: API Design (v0.7.0 Scope)

### 3.1 New Endpoints — Query & Analytics

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| `/api/v1/chunks?filter` | GET | Enhanced filtering (date range, multiple projects, status) | HIGH |
| `/api/v1/projects/{id}/timeline` | GET | Chunks grouped by date bucket (day/week/month) | HIGH |
| `/api/v1/chunks/related/{id}` | GET | Find similar chunks (TF-IDF cosine distance) | MEDIUM |
| `/api/v1/entities/{id}/related` | GET | Entity adjacency (co-occurrence in chunks) | MEDIUM |
| `/api/v1/stats/dashboard` | GET | Global stats (total, by status, by project, trend) | HIGH |
| `/api/v1/projects/{id}/stats` | GET | Project-specific stats (item count, status dist, velocity) | HIGH |
| `/api/v1/chunks/timeline` | GET | Global timeline (chunks by date bucket) | MEDIUM |
| `/api/v1/search/history` | GET | User's recent searches (localStorage-backed) | LOW |
| `/api/v1/chunks/bulk-export` | GET | Export chunks as JSON/CSV (filtered/selected) | LOW |

**Not in v0.7.0:** Synthesis, summarization, entity relationship recommendations (deferred to v0.8.0+ when more data available).

### 3.2 Enhanced Query Parameters

```
GET /api/v1/chunks
  ?status=inbox,processed
  &project_id=proj-123,proj-456          # Multi-select
  &created_after=2025-12-01
  &created_before=2026-02-01
  &entities=entity-123:type1,entity-456:type2  # Entity filter
  &search_query=ai_safety                # Text search
  &sort=created_at:desc                  # Sort order
  &limit=50&offset=0                     # Pagination
  &group_by=created_date                 # Grouping (date bucket)
  &include_stats=true                    # Return count/aggregate
```

### 3.3 Response Models

```python
# Enhanced Chunk response with context
class ChunkWithContext(BaseModel):
    chunk: Chunk
    related_count: int          # How many similar chunks?
    entity_mentions: list[str]  # Which entities appear?
    project_name: str
    days_ago: int

# Timeline bucket
class TimelineBucket(BaseModel):
    date_bucket: str            # "2026-02-07" or "2026-02-W06" or "2026-02"
    bucket_start: datetime
    bucket_end: datetime
    chunk_count: int
    chunks: list[Chunk]

# Dashboard stats
class DashboardStats(BaseModel):
    total_chunks: int
    by_status: dict[str, int]              # inbox, processed, etc.
    by_project: dict[str, int]
    by_week: list[tuple[str, int]]         # Past 8 weeks
    oldest_inbox_chunk: Chunk | None
    most_active_entity: str | None

# Entity relationship
class EntityRelationship(BaseModel):
    entity_id: str
    related_entities: list[tuple[str, int]]  # (entity_id, co_occurrence_count)
    chunks_mentioning: int
    first_seen: datetime
    last_seen: datetime
```

---

## Part 4: Database & Performance

### 4.1 Required Indices (SQLite)

```sql
-- Already exist:
CREATE INDEX idx_chunks_status ON chunks(status);
CREATE INDEX idx_chunks_project_id ON chunks(project_id);
CREATE INDEX idx_chunks_created_at ON chunks(created_at);

-- New (for performance):
CREATE INDEX idx_chunks_status_created ON chunks(status, created_at);
CREATE INDEX idx_chunk_entities_chunk_id ON chunk_entities(chunk_id);
CREATE INDEX idx_chunk_entities_entity_id ON chunk_entities(entity_id);
CREATE INDEX idx_entities_type ON entities(type);
```

### 4.2 Query Performance Targets

- `GET /chunks?filters` with 3 conditions: < 100ms for 10k records
- `GET /stats/dashboard`: < 200ms (counts + aggregates)
- `GET /chunks/related/{id}`: < 300ms (TF-IDF similarity for 10k chunks)
- `GET /projects/{id}/timeline`: < 150ms (50 day buckets)

### 4.3 Caching Strategy

For MVP (single-user):
- Dashboard stats: Cache for 5 minutes (user manually refresh if needed)
- Timeline: No cache (fast enough)
- Related chunks: Cache per search (clear on new chunk capture)

No Redis needed — in-memory cache in FastAPI service.

---

## Part 5: Frontend UX Changes

### 5.1 Inbox View Enhancements

**Current:** ChunkList showing all chunks
**Target:** Inbox tab showing only `status=inbox` chunks, sorted by age, with bulk actions

**New Components:**
- `InboxHeader` — "5 items | Oldest from 30 days ago"
- Enhanced `ChunkList` — Show created date, aging indicator (color: red if >7 days)
- Bulk delete modal — "Archive these 5 inbox items?" confirmation

### 5.2 Timeline View (New Tab)

**Purpose:** Show "when did I capture what?"

**UI:**
- Horizontal timeline scrubber (past 8 weeks)
- Bar chart: chunks per week
- Click week → show chunks from that week
- Hover → see quick stats (5 items that week)

**Component:** `TimelineView.tsx` using `GET /projects/{id}/timeline`

### 5.3 Stats Dashboard (New Tab)

**Purpose:** "How much data do I have? What's the health?"

**Widgets:**
- Total chunks (big number)
- By status (pie chart: red=inbox, green=processed, gray=archived)
- By project (bar chart or list)
- Trend line (past 8 weeks)
- Action buttons: "Clean up inbox", "View oldest items"

**Component:** `StatsDashboard.tsx` using `GET /stats/dashboard`

### 5.4 Entity Explorer (New Tab — Phase 2)

**Deferred to v0.8.0** (wait until we have more data + synthesis)

**Planned:**
- Force-directed graph of entities
- Click entity → see all chunks mentioning it
- See co-occurrence relationships (which entities always appear together?)

---

## Part 6: Search UI Fixes

**While implementing new query API, also:**
- [ ] Fix input field responsiveness (debug SearchBar event handlers)
- [ ] Add autocomplete to project/status dropdowns
- [ ] Add date range picker component (calendar widget)
- [ ] Test on mobile (responsive inputs)
- [ ] Add live result count (show "42 results" as user types)

---

## Part 7: Known Issues & Constraints

1. **Token limit awareness** — For Ollama synthesis later: chunks need to be pre-chunked (~500 tokens each) to fit context windows
2. **Entity co-occurrence sparsity** — With small datasets, "related entities" may be sparse; acceptable for MVP
3. **TF-IDF computation** — Must be computed on-demand (no pre-computed embeddings in v0.7.0). Keep corpus ≤ 10k chunks for < 300ms
4. **Timeline bucketing** — For 10k chunks, hour-level granularity too fine; stick to day/week/month
5. **Real-time search** — User search won't auto-update on other clients (single-user for now)

---

## Part 8: Implementation Estimates

| Component | Hours | Notes |
|-----------|-------|-------|
| Backend: Enhanced filtering + indices | 6 | Query builder, parameter validation |
| Backend: Stats aggregation | 4 | Count queries, group by |
| Backend: Related chunks (TF-IDF) | 5 | Term importance calc, cosine distance |
| Backend: Entity relationships | 3 | Co-occurrence counts |
| Backend: Timeline bucketing | 2 | Date group by logic |
| Backend: Tests (all above) | 5 | Integration + hammer |
| Frontend: Fix search input bug | 2 | Debug event handlers |
| Frontend: New tabs (Timeline, Stats) | 8 | Components + signals |
| Frontend: Bulk cleanup flow | 3 | Modal + integration |
| Testing: E2E scenarios | 3 | Playwright tests |
| **Total** | **~41 hours** | **~5 sprints, 1 dev** |

---

## Part 9: Success Criteria

By end of v0.7.0:

- [ ] User can explore data by status, date range, project (no typing bugs)
- [ ] Dashboard shows instant stats (oldest item, item count, weekly trend)
- [ ] Inbox tab shows actionable cleanup opportunities (oldest items, bulk archive)
- [ ] Timeline view shows when data was captured (weekly granularity)
- [ ] Related chunks feature works for power users (find similar items)
- [ ] All queries complete < 300ms on 10k-item dataset
- [ ] E2E Playwright tests for all new flows pass
- [ ] User feedback from alpha: "I can trust this to organize my data"

---

## Part 10: Blockers & Questions

1. **Search bug root cause** — Need to debug: Is it React event binding? Preact signal issue? Browser inspector needed
2. **Related chunks similarity metric** — TF-IDF or use Ollama embeddings? (TF-IDF for v0.7.0, embeddings for v0.8.0+)
3. **Real user data** — Need someone to use alpha and say "I want to do X with my data" to validate UI
4. **Timeline granularity** — Is week-level useful? Or should we offer day/month switching?
5. **Synthesis timing** — Can we defer entity relationship UI to v0.8.0 when we have more data + Ollama integration mature?

---

## Next Steps

1. **Architect-Feature Prompt:** Use this brief to generate detailed FEATURE_MODULE6_v0.7.0_DESIGN.md
   - Full API contract
   - Database schema updates
   - Frontend component architecture
   - Search bug root cause analysis + fix
   
2. **Bug Fix Sprint:** First 1-2 days should fix search input issue (HIGH priority blocker)

3. **Implementation Sprint:** Follow Module 5-6 implementation approach (Red → Green → Refactor)

4. **User Validation:** Deploy v0.7.0 alpha and gather feedback on "What can I do with my data?" question

---

## Philosophy

**We built infrastructure. Now we're building *utility*.**

The question driving this phase: *Not "what can the system do?" but "what can a PERSON do with the system?"*

This is where Komorebi becomes useful instead of just impressive.
