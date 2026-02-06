# Implementation Handoff: Module 6 — User Data API & Search Fix (v0.7.0)

**Date:** February 8, 2026  
**Branch:** `copilot/implement-backend-service-cli-dashboard`  
**Architecture:** `docs/FEATURE_MODULE6_v0.7.0_DESIGN.md`

---

## Summary

Module 6 delivers user-facing data exploration features that transform Komorebi from a capture-only tool into one where users can explore, understand, and act on their data. Also fixes a critical search input bug.

## What Was Built

### 1. Search Bug Fix (Critical)
**Problem:** `@preact/signals-react` v2 intercepts `.value` access during JSX render, causing controlled input race conditions — users experience input lag and lost keystrokes.

**Fix:** Local `useState` bridge pattern. Each controlled input maintains local state for immediate UI response while syncing to the signal for store updates.

**Files:** `SearchBar.tsx`, `FilterPanel.tsx` (6 fields)

### 2. Enhanced Dashboard Stats
**Endpoint:** `GET /api/v1/chunks/stats` → `DashboardStats`
- Weekly activity trends (last 8 weeks with counts)
- Insights: oldest inbox age, most active project, entity count
- Per-project chunk breakdown
- Backward-compatible (extends existing ChunkStats counters)

**Component:** `StatsDashboard.tsx` — bar chart, insights, project breakdown

### 3. Timeline View
**Endpoint:** `GET /api/v1/chunks/timeline?granularity=week&weeks=8&project_id=...`
- Day/week/month granularity via strftime SQL bucketing
- Status breakdown per time bucket (inbox, processed, compacted, archived)
- Optional project filter

**Component:** `TimelineView.tsx` — granularity toggle, expandable buckets, status-colored bar segments

### 4. Related Chunks (TF-IDF)
**Endpoint:** `GET /api/v1/chunks/{id}/related?limit=5`
- Pure Python TF-IDF cosine similarity (zero dependencies)
- Returns top-k related chunks with similarity scores and shared terms
- Computation time included in response

**Service:** `backend/app/core/similarity.py` — `TFIDFService` class
**Component:** Related chunks section in `ChunkDrawer.tsx` with similarity badges

### 5. Inbox Enhancements
- Age indicators: 🔴 (>7d), 🟡 (2-7d), 🟢 (<2d)
- Sort toggle: Newest first / Oldest first
- InboxHeader: count + oldest chunk age

### 6. Tab Restructure
4 tabs → 6 tabs: `inbox | all | dashboard | timeline | projects | mcp`
Removed always-visible Stats from header.

## Files Changed

### Backend (New)
| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/core/similarity.py` | ~150 | TFIDFService — tokenize, TF-IDF, cosine similarity |
| `backend/tests/test_module6_stats.py` | ~120 | 9 tests for enhanced stats |
| `backend/tests/test_module6_timeline.py` | ~150 | 11 tests for timeline |
| `backend/tests/test_module6_related.py` | ~285 | 17 tests (12 unit + 5 API) |

### Backend (Modified)
| File | Change |
|------|--------|
| `backend/app/models/chunk.py` | +7 Pydantic models |
| `backend/app/models/__init__.py` | +7 exports |
| `backend/app/db/repository.py` | +5 methods, `from __future__ import annotations` |
| `backend/app/api/chunks.py` | Enhanced stats, +2 endpoints |
| `backend/app/core/__init__.py` | +TFIDFService export |

### Frontend (New)
| File | Lines | Purpose |
|------|-------|---------|
| `frontend/src/components/StatsDashboard.tsx` | ~85 | Dashboard with charts |
| `frontend/src/components/TimelineView.tsx` | ~110 | Timeline explorer |

### Frontend (Modified)
| File | Change |
|------|--------|
| `frontend/src/components/SearchBar.tsx` | useState bridge fix |
| `frontend/src/components/FilterPanel.tsx` | 6 local state bridges |
| `frontend/src/store/index.ts` | +types, +signals, +functions |
| `frontend/src/components/Inbox.tsx` | Age indicators, sort, InboxHeader |
| `frontend/src/components/ChunkDrawer.tsx` | Related chunks section |
| `frontend/src/App.tsx` | 6 tabs, footer v0.7.0 |
| `frontend/src/theme/styles.css` | +~250 lines for new components |

### Documentation
| File | Change |
|------|--------|
| `docs/CHANGELOG.md` | v0.7.0 entry |
| `docs/CURRENT_STATUS.md` | Updated to v0.7.0 |
| `CONVENTIONS.md` | Signal-to-Input Bridge Pattern |
| `PROGRESS.md` | Phase 13 milestone |
| `VERSION` | 0.6.0 → 0.7.0 |
| `pyproject.toml` | 0.6.0 → 0.7.0 |
| `frontend/package.json` | 0.6.0 → 0.7.0 |

## Test Results

```
75 passed, 3 skipped in 17.94s
```

Module 6 specific: 37/37 passing (9 stats + 11 timeline + 17 related)

## Known Limitations

1. **TF-IDF is O(N)** — loads all chunk content into memory. Suitable for ≤10k chunks. For larger corpora, consider pre-computed embeddings or SQLite FTS5.
2. **Timeline SQL uses strftime** — SQLite-specific. PostgreSQL migration will need `date_trunc()`.
3. **Stats.tsx is orphaned** — no longer imported but not deleted. Can be removed in cleanup.
4. **Hammer testing** — Not yet run against new endpoints. Recommend `hammer_gen.py` update with `--mode stats/timeline/related`.

## Rollback Plan
All changes are additive. Existing endpoints unchanged. To rollback:
1. Revert to commit before this branch merge
2. No database schema changes required
