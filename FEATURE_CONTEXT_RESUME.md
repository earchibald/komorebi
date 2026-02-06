# Architecture Handoff: Context Resume ("The Save Point")

**Date:** February 6, 2026  
**Status:** Ready for Implementation  
**Version Target:** 0.8.0  
**Dependencies:** Module 1 (Ollama ✅), Module 2 (Entities ✅), Module 5/TF-IDF (Similarity ✅)

---

## Feature Overview

Context Resume transforms Komorebi from a passive archive into an active partner. When a user returns to a project after time away, they press a single "Resume" button and receive an LLM-synthesized briefing: where they left off, recent decisions, open blockers, and a suggested next step. The system aggregates data from chunks, entities, and TF-IDF similarity to build a contextual "save point."

## Architecture Summary

A new `ResumeService` acts as a read-only "Rake" that gathers context from existing repositories (chunks, entities, projects) and the `TFIDFService`, then delegates to `KomorebiLLM` for synthesis. No new database tables are needed — this is a pure aggregation feature. The output is a `ProjectBriefing` Pydantic model returned from a single new endpoint `GET /projects/{id}/resume`. The frontend renders a `ResumeCard` component with structured sections, callable from the project detail view or a new "Resume" button on each project card.

---

## Requirements

### User Stories
- As a developer returning to a project, I want a concise briefing of where I left off so that I can resume work without re-reading all my notes.
- As a team lead, I want to see recent decisions logged in a project so that I can quickly understand project trajectory.
- As a user with many projects, I want a "Resume" button on each project card that jumps me directly into context.

### Success Criteria
- [ ] `GET /projects/{id}/resume` returns structured `ProjectBriefing` within 3 seconds
- [ ] Briefing includes 3 bullet points: "Where you left off", "Key context", "Suggested next step"
- [ ] Briefing includes list of recent decisions (entities with type `decision`) from last 48 hours
- [ ] When Ollama is unavailable, returns a structured fallback (no LLM summary, but still returns raw context)
- [ ] Frontend `ResumeCard` renders with skeleton loading state and fully populated state
- [ ] 6+ new backend tests covering: empty project, project with data, no decisions, Ollama unavailable, time window filter, related chunks inclusion

### Constraints
- Must use existing `KomorebiLLM` client (no new LLM dependencies)
- Must use existing repository pattern (no raw SQL in service)
- Must not add new database tables or columns (pure read aggregation)
- Frontend must follow Signal-to-Input bridge pattern where applicable
- Must degrade gracefully when Ollama is offline

### Edge Cases
1. What if the project has zero chunks? → Return briefing with "No activity yet" message
2. What if Ollama is unavailable? → Return raw context without LLM synthesis
3. What if there are no decisions? → Show "No recorded decisions" in that section
4. What if all chunks are archived? → Still surface them as historical context (but deprioritize)
5. What if TF-IDF corpus is empty? → Skip related chunks section
6. What if LLM hallucinates? → System anchor injection prevents context drift (existing pattern)

---

## System Design

### Component Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ ProjectList   │───▶│ ResumeCard   │    │ ProjectDetail (new) │  │
│  │ "▶ Resume"    │    │ (3-bullet    │    │ Full briefing view  │  │
│  │ button        │    │  synthesis)  │    │ + chunk jump points │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│         │                    │                      │               │
│         └────────────────────┴──────────────────────┘               │
│                              │                                      │
│         signals: briefing, briefingLoading, briefingError           │
└────────────────────────────────────────────────────────────────────┘
                               │  GET /projects/{id}/resume
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                       BACKEND (FastAPI)                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    ResumeService                              │  │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐    │  │
│  │  │ Chunk   │ │ Entity   │ │ Project  │ │ TFIDFService  │    │  │
│  │  │ Repo    │ │ Repo     │ │ Repo     │ │ (similarity)  │    │  │
│  │  │ .list() │ │ .list_by │ │ .get()   │ │ .find_related │    │  │
│  │  │         │ │ _project │ │          │ │ ()            │    │  │
│  │  └────┬────┘ └────┬─────┘ └────┬─────┘ └──────┬────────┘    │  │
│  │       │           │            │               │             │  │
│  │       └───────────┴────────────┴───────────────┘             │  │
│  │                         │                                     │  │
│  │                    Aggregate raw context                      │  │
│  │                         │                                     │  │
│  │                    ┌────▼─────────┐                           │  │
│  │                    │ KomorebiLLM  │                           │  │
│  │                    │ .generate()  │ ← NEW method              │  │
│  │                    └────┬─────────┘                           │  │
│  │                         │                                     │  │
│  │                    ProjectBriefing                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. User clicks "▶ Resume" on project card
2. Frontend calls GET /projects/{project_id}/resume
3. ResumeService.generate_briefing(project_id):
   a. project_repo.get(project_id)           → Project meta
   b. chunk_repo.list(project_id, limit=10)  → Recent chunks (newest first)
   c. entity_repo.list_by_project(            → Recent decisions
        project_id, entity_type="decision",
        since=48h)
   d. chunk_repo.get_all_content()            → TF-IDF corpus
   e. tfidf.find_related(last_chunk_id)       → Related context
   f. llm.generate(structured_prompt)         → 3-bullet synthesis
4. Return ProjectBriefing to frontend
5. ResumeCard renders: summary + jump points + decisions
```

---

### Pydantic Models Required

#### `backend/app/models/resume.py` (NEW FILE)

```python
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from .chunk import Chunk
from .entity import Entity


class BriefingSection(BaseModel):
    """A single section of the resume briefing."""
    
    heading: str = Field(..., description="Section heading (e.g., 'Where You Left Off')")
    content: str = Field(..., description="Section content text")
    chunk_id: Optional[UUID] = Field(None, description="Optional linked chunk for jump-to")


class ProjectBriefing(BaseModel):
    """The synthesized 'save point' briefing for a project."""
    
    project_id: UUID = Field(..., description="Project this briefing is for")
    project_name: str = Field(..., description="Project display name")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When this briefing was generated")
    
    # LLM-synthesized summary (3 bullet points)
    summary: str = Field(..., description="LLM-generated 3-bullet briefing")
    
    # Structured sections for UI rendering
    sections: list[BriefingSection] = Field(
        default_factory=list,
        description="Parsed briefing sections with optional chunk links"
    )
    
    # Raw context used to generate the briefing
    recent_chunks: list[Chunk] = Field(
        default_factory=list,
        description="Last N chunks (jump-to points)"
    )
    decisions: list[Entity] = Field(
        default_factory=list,
        description="Recent decision entities"
    )
    related_context: list[str] = Field(
        default_factory=list,
        description="Content snippets from TF-IDF related chunks"
    )
    
    # Metadata
    ollama_available: bool = Field(True, description="Whether LLM was used for synthesis")
    context_window_usage: Optional[float] = Field(
        None, description="Fraction of context window used for synthesis (0.0-1.0)"
    )
```

**Design notes:**
- `BriefingSection` supports optional `chunk_id` linking — clicking "Where You Left Off" can jump to that exact chunk in the drawer.
- `ollama_available` flag tells the frontend whether the summary is LLM-generated or a raw fallback.
- `related_context` is a list of snippet strings (not full `RelatedChunk` objects) to keep the response lightweight.

---

### API Endpoints

| Method | Path | Request | Response | Description |
|--------|------|---------|----------|-------------|
| GET | `/api/v1/projects/{project_id}/resume` | `?hours=48` (optional time window) | `ProjectBriefing` | Generate context resume |

**Query Parameters:**
- `hours` (int, default=48): Look-back window for recent decisions. Controls how much history to include.

**Response Codes:**
- `200`: Briefing generated successfully
- `404`: Project not found
- `503`: Ollama unavailable AND no cached briefing (returns 200 with `ollama_available=false` and raw context)

**Note:** This endpoint does NOT persist anything. It's a pure read-aggregation endpoint. Caching can be added in v2 by storing the last briefing in `projects.context_summary`.

---

### Repository Changes Required

#### `EntityRepository` — Add `list_by_project` with `since` parameter

The existing `list_by_project()` method needs a `since: Optional[datetime]` parameter to filter entities created after a certain time. This is a backward-compatible addition.

```python
async def list_by_project(
    self,
    project_id: UUID,
    entity_type: Optional[EntityType] = None,
    min_confidence: float = 0.0,
    since: Optional[datetime] = None,  # NEW PARAMETER
    limit: int = 100,
    offset: int = 0,
) -> list[Entity]:
    query = select(EntityTable).where(EntityTable.project_id == str(project_id))
    
    if entity_type:
        query = query.where(EntityTable.entity_type == entity_type.value)
    if min_confidence > 0.0:
        query = query.where(EntityTable.confidence >= min_confidence)
    if since:  # NEW FILTER
        query = query.where(EntityTable.created_at >= since)
    
    query = query.order_by(EntityTable.created_at.desc())
    query = query.limit(limit).offset(offset)
    
    result = await self.session.execute(query)
    return [self._to_model(row) for row in result.scalars().all()]
```

No other repository changes needed. All data gathering uses existing `list()`, `get()`, and `get_all_content()` methods.

---

### KomorebiLLM — Add `generate()` method

The existing `KomorebiLLM` class has `summarize()` and `extract_entities()`, but no general-purpose `generate()`. We need one for the briefing synthesis prompt.

```python
async def generate(
    self,
    prompt: str,
    system: Optional[str] = None,
    max_tokens: int = 500,
) -> str:
    """General-purpose text generation.
    
    Args:
        prompt: The user prompt
        system: Optional system prompt for context anchoring
        max_tokens: Approximate max response length
        
    Returns:
        Generated text response
    """
    response = await self.client.generate(
        model=self.model,
        prompt=prompt,
        system=system or "You are a concise assistant.",
        stream=False,
    )
    return response['response'].strip()
```

**Why not reuse `summarize()`?** The briefing prompt is not a summarization task — it's a structured synthesis with specific section headings. A general `generate()` is more appropriate and reusable for future features.

---

### ResumeService — New Service

```
backend/app/services/resume_service.py (NEW FILE)
```

**Responsibilities:**
1. Aggregate raw context from 4 sources (project meta, recent chunks, decisions, TF-IDF related)
2. Build structured prompt with system anchor injection
3. Call LLM for synthesis (or return fallback)
4. Parse LLM response into `BriefingSection` objects
5. Return complete `ProjectBriefing`

**Key design decisions:**
- **Read-only**: No writes to database. No side effects.
- **Graceful degradation**: If Ollama is down, returns raw context with `ollama_available=false` and a template-based fallback summary.
- **System anchor injection**: Every prompt includes the project name and description to prevent LLM drift (existing CompactorService pattern).
- **Token estimation**: Calculates approximate context window usage for monitoring.

**Constructor dependencies (injected via FastAPI `Depends`):**
```python
class ResumeService:
    def __init__(
        self,
        chunk_repo: ChunkRepository,
        project_repo: ProjectRepository,
        entity_repo: EntityRepository,
        tfidf_service: TFIDFService,
        llm: KomorebiLLM,
    ):
```

---

### Frontend Components

#### `ResumeCard.tsx` (NEW COMPONENT)

A self-contained card that fetches and displays a project briefing.

**Props:**
- `projectId: string` — The project UUID

**Signals used:**
- `briefing: signal<ProjectBriefing | null>(null)` — The fetched briefing
- `briefingLoading: signal<boolean>(false)` — Loading state
- `briefingError: signal<string | null>(null)` — Error state

**UI structure (following dark theme conventions):**
```
┌─────────────────────────────────────────────┐
│ ✨ Context Resume              Feb 6 14:30  │
│─────────────────────────────────────────────│
│                                             │
│ [LLM Summary — 3 bullet markdown block]    │
│                                             │
│─────────────────────────────────────────────│
│ LAST ACTIVE ITEM           RECENT DECISIONS │
│ ┌─────────────────┐  ┌──────────────────┐  │
│ │ → Fixing auth   │  │ ⚖️ Use JWT       │  │
│ │   bug in login  │  │ ⚖️ Switch to     │  │
│ │   flow          │  │   async queue    │  │
│ └─────────────────┘  └──────────────────┘  │
│                                             │
│ [▶ Open last chunk]   [📋 View all N dec.] │
└─────────────────────────────────────────────┘
```

**Integration point:** The "Open last chunk" button calls existing `selectChunk()` from the store, opening the `ChunkDrawer`. No new navigation needed.

#### Where it's rendered:
- **Option A (recommended):** Add to `ProjectList.tsx` — each project card gets a small "▶ Resume" button that expands or opens the ResumeCard inline.
- **Option B:** Add a new top-level tab "Resume" — too heavyweight for MVP.
- **Option C:** Add to the ChunkDrawer as a secondary panel — confuses the mental model.

**Selected: Option A** — keeps the feature discoverable without cluttering the tab bar.

---

### State Management

```typescript
// Added to frontend/src/store/index.ts

// Briefing state (per-project, not global)
export const briefing = signal<ProjectBriefing | null>(null)
export const briefingLoading = signal(false)
export const briefingError = signal<string | null>(null)

export async function fetchBriefing(projectId: string, hours: number = 48) {
  briefingLoading.value = true
  briefingError.value = null
  
  try {
    const params = new URLSearchParams({ hours: String(hours) })
    const response = await fetch(`${API_URL}/projects/${projectId}/resume?${params}`)
    if (!response.ok) throw new Error('Failed to generate briefing')
    briefing.value = await response.json()
  } catch (e) {
    briefingError.value = e instanceof Error ? e.message : 'Briefing error'
    briefing.value = null
  } finally {
    briefingLoading.value = false
  }
}

export function clearBriefing() {
  briefing.value = null
  briefingError.value = null
}
```

**Note:** Signals are used here (not TanStack Query) because this is a single-fetch-on-demand action, not a continuously refreshed data stream. No caching layer needed for MVP.

---

## Trade-off Analysis

### Decision 1: Pure Aggregation vs Materialised View

**Options:**
1. **Pure aggregation (selected):** Compute briefing on every request from live data
   - Pro: Always fresh, no staleness, no schema changes
   - Con: Slower (multiple DB queries + LLM call per request)
   
2. **Materialised view:** Pre-compute and cache briefings in a new `project_briefings` table
   - Pro: Instant retrieval after first generation
   - Con: Stale data, new table, cache invalidation logic, more complexity

**Selected:** Pure aggregation.

**Rationale:** Komorebi MVP prioritizes data freshness over speed. A 2-3 second generation time is acceptable for an explicit user action ("Resume"). Caching can be added in v2 by storing `last_briefing` in the projects table — a non-breaking additive change.

**Reversibility:** Easy. Adding a cache layer later requires zero API changes — just store the result in `projects.context_summary` and add a TTL check.

---

### Decision 2: LLM Synthesis vs Template-Based Briefing

**Options:**
1. **LLM synthesis (selected):** Use Ollama to generate natural-language briefing from structured context
   - Pro: Natural reading experience, can infer connections between chunks
   - Con: Requires Ollama running, 1-2s latency, potential hallucination
   
2. **Template-based:** String interpolation with fixed structure ("Last item: X. Decisions: Y.")
   - Pro: Zero latency, zero dependency, deterministic
   - Con: Reads like a database dump, no contextual insight

**Selected:** LLM synthesis with template fallback.

**Rationale:** The core value of "Context Resume" is cognitive — helping the user *understand* where they were, not just listing data. The LLM can connect dots ("You were debugging auth, and you decided to use JWT — the next step might be implementing token refresh"). Template fallback ensures the feature works even without Ollama.

**Reversibility:** Easy. The fallback path already exists as the degraded mode.

---

### Decision 3: Time Window — Fixed 48h vs User-Configurable

**Options:**
1. **Fixed 48h:** Hardcoded look-back window
   - Pro: Simple, predictable behavior
   - Con: Doesn't work for users who leave for a week

2. **User-configurable via query param (selected):** `?hours=48` default, user can pass `?hours=168` for a week
   - Pro: Flexible, no UI complexity (power-user feature via query param)
   - Con: Slightly more complex endpoint signature

3. **Auto-detect from last activity:** Calculate window from `project.updated_at` to now
   - Pro: Magic — always right
   - Con: If user hasn't interacted, window could be months; need max cap anyway

**Selected:** User-configurable with 48h default.

**Rationale:** The query param adds trivial backend complexity but enables power users (CLI, API consumers) to tune the window. The frontend uses the default. Auto-detect is a v2 enhancement — the `hours` param is a superset that doesn't preclude adding auto-detect later.

**Reversibility:** Easy. Adding auto-detect later is additive.

---

### Decision 4: Frontend Placement — Project Card vs New Tab vs Drawer

**Options:**
1. **Project card inline (selected):** "▶ Resume" button on each project card in ProjectList
   - Pro: Discoverable, contextual, no new navigation
   - Con: Inline expansion can feel cramped

2. **New top-level tab:** "Resume" tab next to Dashboard/Timeline
   - Pro: Prominent placement
   - Con: Requires project selection UI; breaks 6-tab balance

3. **ChunkDrawer secondary panel:** Show briefing when a project is selected
   - Pro: Reuses existing UI pattern
   - Con: ChunkDrawer is chunk-centric, not project-centric; mental model clash

**Selected:** Project card inline.

**Rationale:** The "Resume" action is project-scoped. Placing it directly on the project card makes the feature contextually obvious. The expanded ResumeCard appears below the project card (or as an overlay) — similar to how FilterPanel expands inline in ChunkList.

**Reversibility:** Easy. Moving to a tab or separate route later requires no backend changes.

---

### Decision 5: Related Chunks in Briefing — TF-IDF vs Last-N Proximity

**Options:**
1. **TF-IDF from last chunk (selected):** Use existing `TFIDFService.find_related()` on the most recent chunk
   - Pro: Surfaces semantically relevant context the user may have forgotten
   - Con: O(N) computation, adds 100-200ms

2. **Last-N proximity:** Just show the 3 chunks before the most recent one chronologically
   - Pro: Fast, deterministic
   - Con: No semantic relevance; might show unrelated items created in the same session

3. **Skip related entirely:** Keep briefing simple
   - Pro: Faster, simpler
   - Con: Misses the "contextual clues" insight

**Selected:** TF-IDF from last chunk.

**Rationale:** The TF-IDF service is already production-tested and runs in <200ms for corpora up to 10k chunks. The semantic link is the differentiator — "You were working on X, and these related items might be relevant" is high-value context that proximity alone can't provide.

**Reversibility:** Easy. Swappable to any strategy behind the same interface.

---

## Implementation Plan

### Backend (5 hours)

- [ ] **Models** (30 min): Create `backend/app/models/resume.py` with `BriefingSection` and `ProjectBriefing`
- [ ] **Models registration** (5 min): Add exports to `backend/app/models/__init__.py`
- [ ] **Repository extension** (15 min): Add `since` parameter to `EntityRepository.list_by_project()`
- [ ] **LLM extension** (15 min): Add `generate()` method to `KomorebiLLM`
- [ ] **ResumeService** (2 hours): Create `backend/app/services/resume_service.py` with:
  - `generate_briefing()` — main orchestration method
  - `_build_context_prompt()` — structured prompt builder with system anchor
  - `_parse_sections()` — parse LLM output into `BriefingSection` objects
  - `_build_fallback_briefing()` — template-based fallback when Ollama is down
  - `_estimate_token_usage()` — context window usage calculation
- [ ] **API endpoint** (30 min): Add `GET /projects/{id}/resume` to `backend/app/api/projects.py`
- [ ] **Wire dependencies** (15 min): Create `get_resume_service()` dependency in `projects.py`
- [ ] **Tests** (1 hour): Create `backend/tests/test_resume.py` with 8+ test cases:
  - `test_resume_empty_project` — no chunks, returns "No activity yet"
  - `test_resume_with_data` — project with chunks + decisions returns valid briefing
  - `test_resume_no_decisions` — chunks but no decision entities
  - `test_resume_ollama_unavailable` — fallback briefing with `ollama_available=false`
  - `test_resume_time_window` — `hours` param filters decisions correctly
  - `test_resume_related_chunks` — TF-IDF related context included
  - `test_resume_project_not_found` — 404 response
  - `test_resume_archived_deprioritized` — archived chunks ranked lower

### Frontend (3 hours)

- [ ] **Store** (30 min): Add `briefing`, `briefingLoading`, `briefingError` signals + `fetchBriefing()` + `clearBriefing()` to store
- [ ] **ResumeCard component** (1.5 hours): Create `frontend/src/components/ResumeCard.tsx`:
  - Skeleton loading state (pulsing bars)
  - Summary section (markdown rendering via `dangerouslySetInnerHTML` or simple text)
  - "Last Active Item" panel (clickable → `selectChunk()`)
  - "Recent Decisions" panel (entity list)
  - "Open last chunk" button
  - Error state with retry button
- [ ] **CSS** (30 min): Add resume card styles to `frontend/src/theme/styles.css`
  - Dark theme gradient (indigo accent)
  - Section grid layout
  - Skeleton animation keyframes
- [ ] **Integration** (30 min): Add "▶ Resume" button to project cards in `ProjectList.tsx`
  - Click toggles ResumeCard inline below the project card
  - State managed via local `expandedProjectId` signal or useState

### Integration & QA (1.5 hours)

- [ ] **Manual E2E test** (30 min): Ingest test data → click Resume → verify briefing
- [ ] **Fallback test** (15 min): Stop Ollama → click Resume → verify template fallback
- [ ] **Documentation** (45 min): Update CHANGELOG.md, CURRENT_STATUS.md, PROGRESS.md, CONVENTIONS.md

### Total: 9.5 hours estimated

---

## External Integrations

| Service | Protocol | Purpose | Fallback |
|---------|----------|---------|----------|
| Ollama | HTTP (async) | LLM synthesis of briefing | Template-based summary from raw context |
| TFIDFService | In-process | Related chunk discovery | Skip section if corpus empty |

**No new external dependencies.** All integrations use existing, tested code paths.

---

## Database Schema

- **New tables:** None
- **New columns:** None
- **Migrations needed:** No
- **Index additions:** None (existing `entity_type` and `created_at` indexes on `entities` table are sufficient)

The only schema-adjacent change is adding the `since` parameter to `EntityRepository.list_by_project()`, which translates to a `WHERE created_at >= :since` clause on the already-indexed `entities` table.

---

## Key Trade-off Decisions Summary

| # | Decision | Choice | Alternative | Reversibility |
|---|----------|--------|-------------|---------------|
| 1 | Storage strategy | Pure aggregation (no cache) | Materialised view | Easy |
| 2 | Summary generation | LLM + template fallback | Template only | Easy |
| 3 | Time window | Configurable `?hours=48` | Fixed or auto-detect | Easy |
| 4 | Frontend placement | Project card inline | New tab or drawer | Easy |
| 5 | Related context | TF-IDF from last chunk | Chronological proximity | Easy |

---

## Known Constraints

- **Ollama dependency:** Feature degrades (but works) without Ollama running. Fallback is deterministic and fast.
- **TF-IDF corpus size:** The `get_all_content()` call loads all chunk content into memory. For >10k chunks, this should be scoped to `project_id` only. **Action item:** Add `project_id` filter to `get_all_content()` during implementation.
- **No streaming:** The briefing is generated in a single blocking call. Streaming via SSE is a v2 enhancement.
- **Single-user context:** No concept of "which user" last worked on this project. Multi-tenancy would need user tracking.
- **No briefing history:** Each resume is ephemeral. No comparison with previous briefings. Could add in v2.

---

## Blockers or Open Questions

- **None blocking.** All dependencies are met (Ollama client exists, TF-IDF service exists, entity repo exists).
- **Enhancement for v2:** Consider caching briefings in `projects.context_summary` with a 5-minute TTL to avoid re-generation on repeated clicks. Log in ELICITATIONS.md at implementation time.
- **Enhancement for v2:** SSE streaming of briefing generation for sub-second perceived latency. The existing `event_bus` infrastructure supports this pattern.

---

## Testing Strategy

### Unit Tests (backend/tests/test_resume.py)
```
Test ID                           What It Validates
───────────────────────────────────────────────────────────
test_resume_empty_project         Zero chunks → "No activity" message
test_resume_with_data             Chunks + decisions → valid ProjectBriefing
test_resume_no_decisions          Chunks only → decisions list empty
test_resume_ollama_unavailable    Fallback mode → ollama_available=false
test_resume_time_window           hours=1 vs hours=168 filters correctly
test_resume_related_chunks        TF-IDF related context populated
test_resume_project_not_found     Invalid UUID → 404
test_resume_archived_deprioritized Archived chunks not in recent_chunks
```

### Integration Tests
- Ingest 5 chunks ("Fixing auth bug", "Decision: Use JWT", "Error: 401 on /login", "Switched to async queue", "Added rate limiting")
- Call `GET /projects/{id}/resume`
- Assert: 3-bullet summary mentions "auth" or "JWT" or "login"
- Assert: `decisions` list contains "Use JWT"
- Assert: `recent_chunks` has 5 items ordered by recency

---

## Next Phase

Code is ready for implementation via `/implement-feature` prompt.

**Implementation order:**
1. Models (`resume.py`) — defines the contract
2. Repository extension (`since` param) — unlocks time-windowed queries
3. LLM extension (`generate()`) — enables synthesis
4. ResumeService — core business logic
5. API endpoint — exposes the feature
6. Tests — validates all paths
7. Frontend (store → component → integration)
8. Documentation sync

All design decisions documented above. No further architectural questions.
