# Architecture Handoff: Module 6 — User Data API & Search Fix

**Date:** February 7, 2026  
**Version:** v0.6.0 → v0.7.0 (target)  
**Sprint Count:** 3 sprints (~25 hours)  
**Philosophy:** Infrastructure → Utility. "What can a PERSON do with this system?"

---

## Feature Overview

Fix the broken search UI (blocking bug), add contextual data exploration (timeline, enhanced stats, related chunks), and make Komorebi usable as a personal knowledge base — not just a data store.

## Architecture Summary

The search bug is caused by Preact Signals v2 intercepting React's controlled input `value` binding — the signal `.value` accessor on `searchQuery.value` in the JSX `value=` prop creates a reactive binding that prevents React's synthetic `onChange` from updating the DOM input. The fix is to read the signal outside JSX or use a local React state bridge. Beyond the bug fix, this module adds 6 new backend endpoints for timeline views, enhanced dashboard stats, and related chunk discovery (TF-IDF cosine similarity), plus 3 new frontend components (TimelineView, StatsDashboard, enhanced InboxView) organized under a redesigned tab structure.

---

## Part 1: Search Bug — Root Cause Analysis & Fix

### 1.1 Root Cause

**Bug:** Cannot type into SearchBar input, FilterPanel text fields, or date pickers. Characters don't appear.

**Root Cause:** `@preact/signals-react` v2 integration with React controlled inputs.

In [SearchBar.tsx](frontend/src/components/SearchBar.tsx), the input reads:
```tsx
<input
  value={searchQuery.value}     // ← Problem: signal .value in JSX
  onChange={handleInput}
/>
```

When `@preact/signals-react` v2 is installed, it patches React's rendering to auto-subscribe to signal `.value` accesses inside render functions. This creates a **reactive binding** where:

1. User types a character → `onChange` fires → `handleInput` sets `searchQuery.value = newValue`
2. Signal mutation triggers Preact's fine-grained re-render
3. Preact's re-render **races with** React's own synthetic event/state reconciliation
4. React's controlled input bailout sees the DOM value already matches its "expected" value (from the signal) and **skips the update**, or the signal update triggers a re-render that resets the input before React processes the keystroke

**The same issue affects all signal-backed input fields:**
- `SearchBar.tsx` → `searchQuery.value` in `value=` prop
- `FilterPanel.tsx` → `searchFilters.value.entityValue` in text input
- `FilterPanel.tsx` → `searchFilters.value.createdAfter` / `createdBefore` in datetime inputs
- `FilterPanel.tsx` → `searchFilters.value.status` / `projectId` / `entityType` in select elements

**Why Inbox works fine:** The `Inbox` component uses `useState` for its input:
```tsx
const [content, setContent] = useState('')  // ← React state, not a signal
```

### 1.2 Fix Strategy

**Option A: Local React state bridge (SELECTED)**
- Read signal values into local `useState` hooks
- Sync signal → local state on mount/changes via `useEffect`
- Write local state → signal on user input
- Pro: Works reliably with React's controlled input pattern
- Con: Slight code duplication

**Option B: Use `useSignal()` hook from `@preact/signals-react/runtime`**
- Pro: Keeps signal-first pattern
- Con: Requires runtime plugin, complex setup, version-sensitive

**Option C: Use uncontrolled inputs with `defaultValue` + `ref`**
- Pro: Avoids controlled input entirely
- Con: Loses React-managed form state, harder to clear programmatically

**Selected: Option A** — Most reliable, matches existing Inbox pattern that already works.

### 1.3 Fix Implementation

**SearchBar.tsx — Fixed pattern:**
```tsx
import { useState, useEffect } from 'react'
import { searchQuery, searchResults, searchLoading, isSearchActive } from '../store'
import { debouncedSearch, clearSearch } from '../store'

export function SearchBar() {
  const [localQuery, setLocalQuery] = useState(searchQuery.value)

  // Sync signal → local when signal changes externally (e.g., clearSearch)
  useEffect(() => {
    setLocalQuery(searchQuery.value)
  }, [searchQuery.value])

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setLocalQuery(val)
    searchQuery.value = val
    debouncedSearch()
  }

  const handleClear = () => {
    clearSearch()
    setLocalQuery('')
  }

  // Read signal values outside JSX to avoid reactive binding issues
  const isActive = isSearchActive.value
  const isLoading = searchLoading.value
  const results = searchResults.value

  return (
    <div className="search-bar">
      <div className="search-input-wrapper">
        <span className="search-icon">🔍</span>
        <input
          type="text"
          className="search-input"
          placeholder="Search chunks by content..."
          value={localQuery}
          onChange={handleInput}
          autoComplete="off"
        />
        {isActive && (
          <button className="search-clear" onClick={handleClear} aria-label="Clear search">
            ✕
          </button>
        )}
      </div>
      {isLoading && (
        <div className="search-status loading">
          <span className="spinner">⏳</span> Searching...
        </div>
      )}
      {results && !isLoading && (
        <div className="search-status results">
          <span className="result-count">
            {results.total} result{results.total !== 1 ? 's' : ''}
          </span>
          {results.query && (
            <span className="result-query">for "{results.query}"</span>
          )}
        </div>
      )}
    </div>
  )
}
```

**FilterPanel.tsx — Same pattern:**
All filter inputs need local state bridges. Each `select`/`input` should read `searchFilters.value` into local state, and `updateFilter` should set both local state and signal.

### 1.4 Acceptance Criteria

- [ ] User can type into search box and see characters appear immediately
- [ ] Status/Project/EntityType dropdown selects respond to clicks and show selected value
- [ ] EntityValue text input accepts typed text
- [ ] Date range inputs accept datetime-local values
- [ ] Clear search resets all fields to empty
- [ ] Debounced search fires 300ms after last keystroke
- [ ] Inbox Quick Capture input still works (regression check)
- [ ] FilterPanel state persists when panel is collapsed and reopened
- [ ] 100 rapid keystroke test completes without dropped characters

---

## Part 2: Enhanced Dashboard Stats

### 2.1 Requirements

**User Story:** As a user, I want to see at-a-glance health of my data — weekly trends, oldest items, most active project — so I can decide what to do next.

**Current state:** Stats component shows 5 number cards (inbox, processed, compacted, archived, total). No trends, no actionable insights.

### 2.2 API Design

**Enhanced Stats Endpoint (replaces existing):**

| Method | Endpoint | Response | Description |
|--------|----------|----------|-------------|
| GET | `/api/v1/chunks/stats` | `DashboardStats` | Enhanced stats with trends and insights |

**New Pydantic Model:**

```python
class WeekBucket(BaseModel):
    """A week's chunk activity."""
    week_start: str           # ISO date "2026-02-03"
    count: int                # Chunks created that week

class DashboardStats(BaseModel):
    """Enhanced dashboard statistics with trends and insights."""
    # Existing counters
    inbox: int
    processed: int
    compacted: int
    archived: int
    total: int
    
    # New: Trends
    by_week: list[WeekBucket]            # Past 8 weeks of activity
    
    # New: Insights
    oldest_inbox_age_days: int | None    # Days since oldest inbox chunk created
    most_active_project: str | None      # Name of project with most chunks
    most_active_project_count: int       # Chunk count for that project
    entity_count: int                    # Total entities extracted
    
    # New: Per-project breakdown
    by_project: list[dict]               # [{name, chunk_count, id}, ...]
```

**Repository additions needed:**

```python
class ChunkRepository:
    # Existing methods...
    
    async def count_by_week(self, weeks: int = 8) -> list[tuple[str, int]]:
        """Count chunks created per week for the past N weeks."""
        # SQL: SELECT strftime('%Y-%W', created_at) as week, COUNT(*) 
        #      FROM chunks 
        #      WHERE created_at >= date('now', '-N weeks')
        #      GROUP BY week ORDER BY week
        ...
    
    async def oldest_inbox(self) -> datetime | None:
        """Get creation date of oldest inbox chunk."""
        # SQL: SELECT MIN(created_at) FROM chunks WHERE status = 'inbox'
        ...
```

### 2.3 Frontend Changes

**StatsDashboard component (replaces Stats):**

```
┌─────────────────────────────────────────────────┐
│  📊 Dashboard                                   │
│                                                 │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │
│  │  12  │ │   8  │ │   3  │ │   5  │ │  28  │  │
│  │Inbox │ │Proc. │ │Comp. │ │Arch. │ │Total │  │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘  │
│                                                 │
│  Weekly Activity (past 8 weeks)                 │
│  ████████ 12                                    │
│  ████     6                                     │
│  ██████   9                                     │
│  ███      4                                     │
│  ████████████ 18                                │
│  ██████████   15                                │
│  ██       3                                     │
│  █████    7                                     │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │ 💡 Insights                             │    │
│  │ • Oldest inbox item: 14 days old        │    │
│  │ • Most active project: "AI Research"    │    │
│  │ • 45 entities extracted                 │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

**Signals:**
```typescript
export interface DashboardStats {
  inbox: number
  processed: number
  compacted: number
  archived: number
  total: number
  by_week: Array<{ week_start: string; count: number }>
  oldest_inbox_age_days: number | null
  most_active_project: string | null
  most_active_project_count: number
  entity_count: number
  by_project: Array<{ name: string; chunk_count: number; id: string }>
}

// Replace existing ChunkStats with DashboardStats
export const stats = signal<DashboardStats>({ ... })
```

The weekly activity bar chart is rendered with pure CSS (no charting library):
```tsx
{stats.value.by_week.map(week => (
  <div className="week-bar" key={week.week_start}>
    <div 
      className="week-bar-fill" 
      style={{ width: `${(week.count / maxWeekCount) * 100}%` }}
    />
    <span className="week-bar-label">{week.count}</span>
  </div>
))}
```

---

## Part 3: Timeline View

### 3.1 Requirements

**User Story:** As a researcher, I want to see when I captured data across time so I can understand my activity patterns and find chunks from a specific period.

### 3.2 API Design

| Method | Endpoint | Query Params | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/v1/chunks/timeline` | `granularity=week`, `weeks=8`, `project_id=<optional>` | `TimelineResponse` | Chunks grouped by time bucket |

**Pydantic Models:**

```python
class TimelineGranularity(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"

class TimelineBucket(BaseModel):
    """A time bucket with its chunks."""
    bucket_label: str              # "Feb 3-9" or "2026-02-07" or "February 2026"
    bucket_start: datetime
    chunk_count: int
    by_status: dict[str, int]      # {inbox: 3, processed: 5, ...}
    chunk_ids: list[str]           # IDs only — load details on demand

class TimelineResponse(BaseModel):
    """Timeline of chunks grouped by date bucket."""
    granularity: str
    buckets: list[TimelineBucket]
    total_chunks: int
```

**Repository method:**

```python
async def timeline(
    self,
    granularity: str = "week",
    weeks: int = 8,
    project_id: UUID | None = None,
) -> list[dict]:
    """Group chunks by time bucket.
    
    Uses SQLite strftime for date bucketing:
    - day:   strftime('%Y-%m-%d', created_at)
    - week:  strftime('%Y-%W', created_at)
    - month: strftime('%Y-%m', created_at)
    """
    ...
```

### 3.3 Frontend Component

**TimelineView.tsx:**
- Horizontal bar chart showing chunk count per week (CSS-only, no lib)
- Click a bar → expand to show chunk previews from that week
- Status color coding (inbox=amber, processed=green, archived=gray)
- Granularity toggle: Day | Week | Month
- Project filter dropdown (optional)

**New signal:**
```typescript
export const timeline = signal<TimelineResponse | null>(null)
export const timelineLoading = signal(false)
export const timelineGranularity = signal<'day' | 'week' | 'month'>('week')

export async function fetchTimeline(
  granularity?: string,
  weeks?: number,
  projectId?: string
): Promise<void> { ... }
```

---

## Part 4: Inbox Enhancements

### 4.1 Requirements

**User Story:** As a user, I want my inbox to show me what needs attention — the oldest items, how many there are, and let me clean up quickly.

### 4.2 Changes to Inbox Component

**Current Inbox:** Capture form + flat list of inbox chunks.

**Enhanced Inbox:**
```
┌─────────────────────────────────────────────────┐
│  📥 Inbox                                       │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │ Quick Capture                             │  │
│  │ [________________________________________]│  │
│  │                              [📝 Capture] │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │ ℹ️  12 inbox items                        │  │
│  │    Oldest: 14 days ago                    │  │
│  │    [Archive All Read ▾] [Sort: Oldest ▾]  │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  🔴 chunk-abc123 (14 days old)                  │
│     "Need to review the auth module..."         │
│  🟡 chunk-def456 (3 days old)                   │
│     "Interesting pattern in the logs..."        │
│  🟢 chunk-ghi789 (today)                        │
│     "Quick thought about the API design..."     │
└─────────────────────────────────────────────────┘
```

**Aging indicators:**
- 🔴 Red dot — > 7 days old
- 🟡 Yellow dot — 2-7 days old
- 🟢 Green dot — < 2 days old

**New UI elements:**
- `InboxHeader` — Count + oldest item age + sort toggle
- Age color indicators per chunk item
- Sort options: Newest first (default), Oldest first

**No new API endpoint needed** — uses existing `GET /chunks?status=inbox` with client-side sorting and age calculation.

---

## Part 5: Related Chunks (TF-IDF)

### 5.1 Requirements

**User Story:** As a knowledge worker, I want to see chunks similar to one I'm reading so I can discover related ideas I captured earlier.

### 5.2 API Design

| Method | Endpoint | Response | Description |
|--------|----------|----------|-------------|
| GET | `/api/v1/chunks/{chunk_id}/related` | `RelatedChunksResponse` | Find similar chunks by content |

**Query Params:** `limit=5` (default)

**Pydantic Models:**

```python
class RelatedChunk(BaseModel):
    """A chunk with its similarity score."""
    chunk: Chunk
    similarity: float     # 0.0 - 1.0 cosine similarity
    shared_terms: list[str]  # Top 3 terms contributing to similarity

class RelatedChunksResponse(BaseModel):
    """Response from related chunks endpoint."""
    source_chunk_id: str
    related: list[RelatedChunk]
    computation_ms: int   # How long the TF-IDF computation took
```

### 5.3 Implementation: TF-IDF Service

```python
# backend/app/core/similarity.py

import math
from collections import Counter
from typing import Optional
from uuid import UUID

class TFIDFService:
    """Compute chunk similarity using Term Frequency-Inverse Document Frequency.
    
    No external dependencies — pure Python implementation suitable for
    corpus sizes up to ~10k documents with < 300ms computation time.
    """
    
    def __init__(self):
        self._stopwords = set([
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'shall',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'as', 'into', 'through', 'during', 'before', 'after', 'and',
            'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
            'neither', 'each', 'every', 'all', 'any', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'only', 'own',
            'same', 'than', 'too', 'very', 'just', 'because', 'about',
            'this', 'that', 'these', 'those', 'it', 'its', 'i', 'me',
            'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his',
            'she', 'her', 'they', 'them', 'their', 'what', 'which',
            'who', 'whom', 'when', 'where', 'why', 'how',
        ])
    
    def tokenize(self, text: str) -> list[str]:
        """Simple whitespace + alphanumeric tokenizer."""
        import re
        tokens = re.findall(r'[a-z0-9_]+', text.lower())
        return [t for t in tokens if len(t) > 2 and t not in self._stopwords]
    
    def compute_tfidf(
        self, documents: list[tuple[str, str]]  # [(id, content), ...]
    ) -> dict[str, dict[str, float]]:
        """Compute TF-IDF vectors for all documents.
        
        Returns: {doc_id: {term: tfidf_score, ...}, ...}
        """
        # Term frequency per document
        doc_tf: dict[str, Counter] = {}
        for doc_id, content in documents:
            tokens = self.tokenize(content)
            doc_tf[doc_id] = Counter(tokens)
        
        # Document frequency per term
        n_docs = len(documents)
        df: Counter = Counter()
        for tf in doc_tf.values():
            for term in tf:
                df[term] += 1
        
        # TF-IDF
        tfidf: dict[str, dict[str, float]] = {}
        for doc_id, tf in doc_tf.items():
            total_terms = sum(tf.values())
            if total_terms == 0:
                tfidf[doc_id] = {}
                continue
            tfidf[doc_id] = {
                term: (count / total_terms) * math.log(n_docs / (1 + df[term]))
                for term, count in tf.items()
            }
        
        return tfidf
    
    def cosine_similarity(
        self, vec_a: dict[str, float], vec_b: dict[str, float]
    ) -> float:
        """Compute cosine similarity between two TF-IDF vectors."""
        common_terms = set(vec_a) & set(vec_b)
        if not common_terms:
            return 0.0
        
        dot = sum(vec_a[t] * vec_b[t] for t in common_terms)
        mag_a = math.sqrt(sum(v**2 for v in vec_a.values()))
        mag_b = math.sqrt(sum(v**2 for v in vec_b.values()))
        
        if mag_a == 0 or mag_b == 0:
            return 0.0
        
        return dot / (mag_a * mag_b)
    
    def find_related(
        self,
        target_id: str,
        documents: list[tuple[str, str]],
        top_k: int = 5,
    ) -> list[tuple[str, float, list[str]]]:
        """Find top_k most similar documents to target.
        
        Returns: [(doc_id, similarity, shared_terms), ...]
        """
        tfidf = self.compute_tfidf(documents)
        target_vec = tfidf.get(target_id, {})
        
        if not target_vec:
            return []
        
        similarities: list[tuple[str, float, list[str]]] = []
        for doc_id, vec in tfidf.items():
            if doc_id == target_id:
                continue
            sim = self.cosine_similarity(target_vec, vec)
            if sim > 0.01:  # Minimum threshold
                common = sorted(
                    (set(target_vec) & set(vec)),
                    key=lambda t: target_vec[t] * vec[t],
                    reverse=True,
                )[:3]
                similarities.append((doc_id, sim, common))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
```

### 5.4 Frontend Integration

**ChunkDrawer enhancement:**
When a chunk is selected and the drawer opens, show a "Related Chunks" section at the bottom:

```tsx
// In ChunkDrawer.tsx, add after entities section
{relatedChunks.value.length > 0 && (
  <div className="related-chunks">
    <h4>🔗 Related Chunks</h4>
    {relatedChunks.value.map(rc => (
      <div key={rc.chunk.id} className="related-chunk-item" 
           onClick={() => selectChunk(rc.chunk)}>
        <span className="similarity-badge">
          {Math.round(rc.similarity * 100)}%
        </span>
        <span className="related-preview">
          {rc.chunk.content.slice(0, 80)}...
        </span>
      </div>
    ))}
  </div>
)}
```

**New signals:**
```typescript
export const relatedChunks = signal<RelatedChunk[]>([])
export const relatedLoading = signal(false)

export async function fetchRelatedChunks(chunkId: string): Promise<void> {
  relatedLoading.value = true
  try {
    const response = await fetch(`${API_URL}/chunks/${chunkId}/related?limit=5`)
    if (!response.ok) throw new Error('Failed to fetch related chunks')
    const data = await response.json()
    relatedChunks.value = data.related
  } catch (e) {
    relatedChunks.value = []
  } finally {
    relatedLoading.value = false
  }
}
```

---

## Part 6: Tab Restructure

### 6.1 Current Tab Structure

```
[📥 Inbox] [📋 All Chunks] [📁 Projects] [🔌 MCP]
```

### 6.2 New Tab Structure

```
[📥 Inbox] [📋 All Chunks] [📊 Dashboard] [📅 Timeline] [📁 Projects] [🔌 MCP]
```

**Changes:**
- **Stats** moves from always-visible header widget to its own **Dashboard** tab (with enhanced stats)
- **Timeline** is a new tab
- Existing header `Stats` component removed — replaced by inline stat badges in the header or moved entirely to Dashboard tab

**App.tsx changes:**
```tsx
type Tab = 'inbox' | 'all' | 'dashboard' | 'timeline' | 'projects' | 'mcp'
```

---

## Part 7: Trade-off Analysis

### Decision 1: Search Bug Fix — Local State Bridge vs. Signals Runtime

**Options:**
1. **Local `useState` bridge** — Mirror signal values into React state for inputs
   - Pro: Reliable, matches working Inbox pattern, no new dependencies
   - Con: Slight code duplication, two sources of truth for input values
   
2. **`@preact/signals-react/runtime`** — Use the official runtime integration
   - Pro: Signal-first, no duplication
   - Con: Requires babel plugin or SWC transform, version-sensitive, may break with React updates

**Selected:** Local `useState` bridge

**Rationale:** The Inbox component already works this way. We know it's reliable. The duplication is minimal (~5 lines per component) and eliminates the class of signal/React reconciliation bugs entirely. When we eventually migrate to Preact proper (if ever), we can remove the bridge.

**Reversibility:** Easy — swap back to direct signal access in JSX if signals-react is updated.

### Decision 2: Weekly Activity Chart — Pure CSS vs. Chart Library

**Options:**
1. **Pure CSS bars** — `<div>` with `width: X%` styling
   - Pro: Zero dependencies, tiny bundle, fast render
   - Con: Limited to bar charts, no interactivity beyond click handlers
   
2. **Lightweight chart lib** (Chart.js, uPlot, Recharts)
   - Pro: Multiple chart types, tooltips, animations
   - Con: 30-200KB bundle increase, new dependency to maintain

**Selected:** Pure CSS bars

**Rationale:** We only need a simple horizontal bar chart. Adding a charting library would increase the bundle from ~180KB to ~300KB+ for a single bar chart. CSS bars render in < 1ms and need zero JavaScript. If we need pie charts or line graphs later, we can add a library then.

**Reversibility:** Easy — CSS bars can be replaced with a React charting component one-for-one.

### Decision 3: TF-IDF — Pure Python vs. scikit-learn

**Options:**
1. **Pure Python** — Implement tokenizer + TF-IDF + cosine similarity from scratch
   - Pro: Zero new dependencies, fully understandable, ~150 lines
   - Con: Slower than optimized C extensions, no pre-built optimizations
   
2. **scikit-learn** — Use `TfidfVectorizer` + `cosine_similarity`
   - Pro: Battle-tested, fast (Cython internals), supports large corpora
   - Con: ~200MB dependency (numpy + scipy + sklearn), overkill for MVP

**Selected:** Pure Python

**Rationale:** Our target corpus is ≤ 10k chunks. Pure Python TF-IDF on 10k short documents takes ~100-200ms. Adding scikit-learn would increase the Docker image from ~200MB to ~400MB and adds 3 transitive dependencies to maintain. If we hit performance limits at >10k chunks, we migrate to sklearn or pre-computed embeddings (Ollama) in v0.8.0.

**Reversibility:** Easy — `TFIDFService` has a clean interface; swap internals to sklearn without changing API.

### Decision 4: Stats Endpoint — Enhance Existing vs. New Endpoint

**Options:**
1. **Enhance existing** `GET /chunks/stats` — Add fields to current response
   - Pro: No new endpoint, backwards-compatible if we add optional params
   - Con: Response gets larger, clients that only need counts still get trends
   
2. **New endpoint** `GET /stats/dashboard` — Separate from basic stats
   - Pro: Clean separation, basic stats stay fast
   - Con: Two stats endpoints to maintain, frontend needs to call both

**Selected:** Enhance existing endpoint

**Rationale:** There's only one frontend consumer. Adding a separate stats endpoint creates unnecessary API surface for a single-user app. The additional data (trends, insights) adds ~1KB to the response and ~50ms to computation — negligible.

**Reversibility:** Easy — extract into separate endpoint if needed.

### Decision 5: Timeline Granularity — Fixed Week vs. User-Selectable

**Options:**
1. **User-selectable** — Day/Week/Month toggle
   - Pro: Flexible, user can zoom in/out
   - Con: More UI complexity, 3 separate query variants
   
2. **Fixed week** — Always show weekly buckets
   - Pro: Simple, one query, easier to design
   - Con: Not useful for users with daily or monthly capture patterns

**Selected:** User-selectable (with week as default)

**Rationale:** The query is the same (just change `strftime` format string) — no additional backend complexity. The frontend toggle is 3 buttons. Users with different capture frequencies need different views. Default to week since it's the most universally useful.

**Reversibility:** Easy — remove day/month options if unused.

---

## Part 8: API Endpoints Summary

### New Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/chunks/timeline` | — | Chunks grouped by date bucket |
| GET | `/api/v1/chunks/{id}/related` | — | Find similar chunks (TF-IDF) |

### Modified Endpoints

| Method | Path | Change | Purpose |
|--------|------|--------|---------|
| GET | `/api/v1/chunks/stats` | Add `by_week`, `oldest_inbox_age_days`, `most_active_project`, `entity_count`, `by_project` | Enhanced dashboard stats |

### Unchanged Endpoints (30 existing)

All current chunk CRUD, project, entity, MCP, and SSE endpoints remain unchanged.

---

## Part 9: Frontend Components Summary

### New Components

| Component | Purpose | Signals Used |
|-----------|---------|-------------|
| `StatsDashboard.tsx` | Enhanced stats w/ weekly chart + insights | `stats` (enhanced) |
| `TimelineView.tsx` | Timeline of chunks over time | `timeline`, `timelineGranularity` |
| `InboxHeader.tsx` | Inbox count, age, sort controls | `chunks` (filtered), local state |

### Modified Components

| Component | Change | Signals Affected |
|-----------|--------|-----------------|
| `SearchBar.tsx` | Fix: local state bridge for input | `searchQuery` (read), local state (write) |
| `FilterPanel.tsx` | Fix: local state bridge for all inputs | `searchFilters` (read), local state (write) |
| `ChunkList.tsx` | Minor: remove search bug workarounds if any | — |
| `ChunkDrawer.tsx` | Add: Related chunks section | `relatedChunks`, `relatedLoading` |
| `Inbox.tsx` | Add: InboxHeader, age indicators, sort | local state for sort |
| `Stats.tsx` | Replace: → `StatsDashboard.tsx` | `stats` (enhanced model) |
| `App.tsx` | Add: Dashboard + Timeline tabs | `activeTab` local state |

### New Signals

```typescript
// Timeline
export const timeline = signal<TimelineResponse | null>(null)
export const timelineLoading = signal(false)
export const timelineGranularity = signal<'day' | 'week' | 'month'>('week')

// Related chunks (loaded per-chunk in drawer)
export const relatedChunks = signal<RelatedChunk[]>([])
export const relatedLoading = signal(false)
```

---

## Part 10: Database Schema

### No New Tables

Module 6 requires no schema changes. All new endpoints query existing tables with new aggregation patterns.

### New Indices (Performance)

```sql
-- Composite index for timeline bucketing + status breakdown
CREATE INDEX IF NOT EXISTS idx_chunks_created_status 
  ON chunks(created_at, status);

-- Entity type index (already exists per database.py, verify in migration)
-- CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
```

### Migration Script

```python
# scripts/migrate_module6.py
"""Migration: Add composite indices for Module 6 queries."""

async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_chunks_created_status "
            "ON chunks(created_at, status)"
        ))
```

---

## Part 11: Implementation Tasks

### Sprint 1: Search Bug Fix + Stats Enhancement (8 hours)

#### Bug Fix (3 hours)
- [ ] Fix `SearchBar.tsx` — local state bridge for input
- [ ] Fix `FilterPanel.tsx` — local state bridges for all 6 filter fields
- [ ] Test: type in search box → characters appear
- [ ] Test: select status dropdown → value changes
- [ ] Test: enter date range → values accept input
- [ ] Test: clear search → all fields reset
- [ ] Test: rapid typing → debounce fires correctly
- [ ] Test: Inbox capture still works (regression)

#### Stats Enhancement (5 hours)
- [ ] Add `DashboardStats`, `WeekBucket` Pydantic models to `models/chunk.py`
- [ ] Add `count_by_week()`, `oldest_inbox()` to `ChunkRepository`
- [ ] Enhance `GET /chunks/stats` to return `DashboardStats`
- [ ] Create `StatsDashboard.tsx` component (CSS bar chart + insights)
- [ ] Update `stats` signal type from `ChunkStats` to `DashboardStats`
- [ ] Replace `Stats.tsx` usage in `App.tsx` with `StatsDashboard` tab
- [ ] Add tab: Dashboard
- [ ] Tests: stats endpoint returns new fields
- [ ] Tests: weekly counts are correct

### Sprint 2: Timeline + Inbox + Tabs (10 hours)

#### Timeline (5 hours)
- [ ] Add `TimelineGranularity`, `TimelineBucket`, `TimelineResponse` models
- [ ] Add `timeline()` method to `ChunkRepository`
- [ ] Create `GET /chunks/timeline` endpoint with granularity param
- [ ] Create `TimelineView.tsx` component (CSS bar chart per week)
- [ ] Add granularity toggle (Day | Week | Month)
- [ ] Add timeline signals and fetch action to store
- [ ] Add tab: Timeline
- [ ] Tests: timeline endpoint groups correctly by week
- [ ] Tests: empty timeline returns empty buckets

#### Inbox Enhancement (3 hours)
- [ ] Create `InboxHeader.tsx` sub-component (count + oldest age)
- [ ] Add age indicators to chunk cards (🔴🟡🟢)
- [ ] Add sort toggle (Newest / Oldest first)
- [ ] Tests: age indicators render correctly
- [ ] Tests: sort order changes chunk display order

#### Tab Restructure (2 hours)
- [ ] Update `App.tsx` tab type and navigation
- [ ] Move Stats from header → Dashboard tab
- [ ] Verify all 6 tabs render correct components
- [ ] Update footer version from hardcoded "0.1.0" to read from config

### Sprint 3: Related Chunks + Polish (7 hours)

#### Related Chunks Backend (4 hours)
- [ ] Create `backend/app/core/similarity.py` — `TFIDFService` class
- [ ] Add `GET /chunks/{id}/related` endpoint
- [ ] Wire into existing `ChunkRepository` for document loading
- [ ] Tests: related chunks returns similar content
- [ ] Tests: empty corpus returns empty list
- [ ] Tests: performance < 300ms for 1000 chunks

#### Related Chunks Frontend (2 hours)
- [ ] Add `relatedChunks`, `relatedLoading` signals to store
- [ ] Add `fetchRelatedChunks()` action
- [ ] Enhance `ChunkDrawer.tsx` — add related chunks section
- [ ] Style related chunk cards with similarity percentage

#### Polish (1 hour)
- [ ] CSS cleanup: consistent spacing, dark theme
- [ ] Remove header Stats widget (now a tab)
- [ ] Update `docs/API_REFERENCE.md` with new endpoints
- [ ] Run full test suite (backend + e2e)
- [ ] Version bump → v0.7.0, changelog, commit

---

## Part 12: External Integrations

| Service | Protocol | Purpose | Fallback |
|---------|----------|---------|----------|
| SQLite | SQL | All queries | — (core dependency) |
| SSE EventBus | Server-sent events | Notify after stats change | Silent (next fetch refreshes) |
| Ollama | HTTP (future) | Semantic similarity in v0.8.0 | TF-IDF (this module) |

No new external dependencies. No new Python packages. No new npm packages.

---

## Part 13: Known Constraints

1. **Signals + React controlled inputs** — The root cause of the search bug. Our fix is defensive (local state bridge). If `@preact/signals-react` v3 fixes this, we can simplify.
2. **TF-IDF is on-demand** — No pre-computed index. Related chunks costs O(N) per request. Acceptable for ≤10k chunks (< 300ms). Beyond that, need embeddings or FTS5.
3. **SQLite `strftime`** — Timeline bucketing depends on SQLite's date functions. If we migrate to PostgreSQL, these become `date_trunc()` calls.
4. **No authentication** — Stats and timeline show all data for all users. Single-user for MVP.
5. **Weekly bar chart is CSS-only** — No hover tooltips, no smooth animations. If users want richer charts, add a library in v0.8.0.

---

## Part 14: Blockers or Open Questions

1. **Inbox "Archive All" button** — Should we batch-archive from inbox view? Depends on Module 5 (bulk ops) landing first. For v0.7.0, skip bulk actions in inbox; just show the insights.
2. **Footer version hardcoded to "0.1.0"** — Currently in `App.tsx`. Should read from `package.json` version or an env var injected at build time. Fix during tab restructure.
3. **Entity count in stats** — Requires a count query on entities table. If entities table is large, this may need an index. Add `idx_entities_chunk_id` if slow.
4. **Related chunks for short content** — Chunks with < 10 words produce poor TF-IDF vectors. Return empty `related` list for chunks under minimum token threshold.

---

## Next Phase

Code is ready for implementation via `/implement-feature` prompt.

**Implementation order:**
1. **Sprint 1:** Fix search bug FIRST (blocks all user testing), then enhance stats
2. **Sprint 2:** Timeline + Inbox + Tab restructure  
3. **Sprint 3:** Related chunks + polish + release

All design decisions documented above. No further architectural questions.
