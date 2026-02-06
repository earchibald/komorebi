# Questions for Operator

## [2026-02-05] Chunk Detail Drawer + Entity Panel

**Context:** Entities are extracted during chunk processing but have no visibility in the dashboard UI. After adding 200-char truncation to chunk cards, users need a way to view full content.

**Decision:** Implemented as a right-side slide-out drawer (not a modal or new page) because:
1. Drawer preserves list context — user can see which card they clicked
2. No route change needed — keeps SPA navigation simple
3. Follows established dark-theme patterns with existing CSS variables
4. Entity grouping by type with confidence bars gives scannable overview

**Trade-offs:**
- Drawer uses 560px fixed width (not responsive below 560px) — acceptable for MVP desktop-first target
- Entities fetched on every drawer open (no caching) — keeps data fresh, acceptable for MVP volume
- No keyboard navigation between entities — can add in v1.0

---

## [2026-02-05] Fixed: Chunk card content overflow on dashboard

**Issue:** Chunk cards display extremely long content strings (e.g., repeated "x" padding from hammer_gen.py explosion mode) without any truncation or word-breaking, causing cards to overflow horizontally and vertically.

**Root Cause:** Two compounding issues:
1. `.chunk-content` CSS class had no `word-break` or overflow handling — long strings without whitespace overflowed the container
2. `ChunkList.tsx` rendered `chunk.content` directly without length truncation

**Fix (belt-and-suspenders):**
1. **CSS:** Added `word-break: break-all`, `overflow-wrap: break-word`, and `-webkit-line-clamp: 3` to `.chunk-content`
2. **Component:** Truncated display to 200 characters with ellipsis; full content available via `title` hover attribute

**Decision:** Used 200-char truncation (not 100 or 300) as a balance between showing enough context and keeping cards compact. Line-clamp set to 3 lines as a visual safety net. These values can be adjusted based on user feedback.

**Trade-offs:**
- ✅ Cards remain fixed-height and readable with any content length
- ✅ Full content accessible via hover tooltip
- ❌ Users must hover to see full content (acceptable for card view; detail view can show full content later)
