# Tab Loading Performance Investigation

**Date:** February 5, 2026  
**Status:** 🔍 **UNDER INVESTIGATION** - Tabs under 'All Chunks' empty for subjectively long time before populating  
**Impact:** Poor user experience when switching between chunk status tabs  
**Cache Status:** ✅ Successfully caching data via localStorage

---

## Problem Summary

When users navigate to the "All Chunks" tab and click on status filter tabs (Inbox, Processed, Compacted, Archived), the tabs remain empty for a noticeable duration before data appears. This creates a perception of slowness even though the data is being cached successfully.

### Observable Symptoms

1. **User Experience:**
   - Click "All Chunks" main tab → Shows loading state
   - Click "Processed" sub-tab → Empty for several seconds
   - Click "Inbox" sub-tab → Empty again for several seconds
   - Data eventually appears, but delay is jarring

2. **Browser Console (Expected):**
   ```
   📦 Loaded N chunks from cache
   🔌 Connecting to SSE...
   ✅ SSE connected
   ```

3. **Network Tab Observations:**
   - Initial page load: Fast (cache restored immediately)
   - Tab switch: API call to `/api/v1/chunks?status=X&limit=100`
   - API response time: 2-10ms (Very fast!)
   - So the backend is NOT the bottleneck

4. **Caching Behavior:**
   - localStorage successfully stores chunks
   - Cache is read on page load
   - Cache is written after each API fetch
   - But switching tabs still feels slow despite cache

---

## Current Implementation Analysis

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Action                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ChunkList Component                            │
│  useEffect(() => {                                               │
│    fetchChunks(filter === 'all' ? undefined : filter)           │
│  }, [filter])  ◄─── Triggers on every tab change                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Store: fetchChunks()                         │
│  1. Set loading.value = true                                     │
│  2. Build params with status filter                              │
│  3. Fetch from API: /api/v1/chunks?status=X&limit=100           │
│  4. Wait for response (2-10ms)                                   │
│  5. chunks.value = await response.json()  ◄─── REPLACES array   │
│  6. writeCache(chunks.value)                                     │
│  7. Set loading.value = false                                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ChunkList Component Render                      │
│  const filteredChunks = filter === 'all'                         │
│    ? chunks.value                                                │
│    : chunks.value.filter(c => c.status === filter)  ◄─── FILTER │
└─────────────────────────────────────────────────────────────────┘
```

### Key Problem: Data Replacement Pattern

**Issue:**
```typescript
// In fetchChunks():
const response = await fetch(`${API_URL}/chunks?${params}`)
chunks.value = await response.json()  // REPLACES entire array
```

**What happens:**
1. User on "All" tab → `chunks.value` = [all chunks]
2. User clicks "Processed" → Fetches only processed chunks
3. `chunks.value` = [only processed chunks]
4. Client-side filtering: `chunks.value.filter(c => c.status === 'processed')` (redundant!)
5. User clicks "Inbox" → **Previous data is GONE**
6. Must fetch again from API

**This creates:**
- Unnecessary API calls (data was already fetched)
- Empty states between tab switches
- "Flash of empty content"
- Perception of slowness

### Redundant Filtering

**Backend filtering:**
```typescript
// Server-side
fetch(`/api/v1/chunks?status=processed&limit=100`)  // Returns ONLY processed
```

**Client-side filtering:**
```typescript
// Client-side (ChunkList.tsx)
const filteredChunks = filter === 'all' 
  ? chunks.value 
  : chunks.value.filter(c => c.status === filter)  // Filters again!
```

This is a **double-filter antipattern**:
- Server filters → Returns 50 processed chunks
- Client filters same 50 chunks → Still 50 chunks
- Wastes CPU, adds latency

---

## Performance Measurements

### API Response Times

```bash
# Backend is FAST:
$ curl -w "Time: %{time_total}s\n" "http://localhost:8000/api/v1/chunks?status=inbox&limit=100"
Time: 0.009951s  # ~10ms

$ curl -w "Time: %{time_total}s\n" "http://localhost:8000/api/v1/chunks?limit=100"
Time: 0.002615s  # ~3ms
```

**Conclusion:** Backend is NOT the bottleneck (2-10ms is excellent).

### Frontend Timing (Expected)

Using browser Performance API, we should measure:
1. **Time to API response:** 2-10ms (confirmed above)
2. **JSON parsing:** ~1-5ms for 100 chunks
3. **Signal update + React re-render:** ~5-20ms
4. **DOM update:** ~10-50ms depending on chunk count

**Total expected time:** 18-85ms (should feel instant)

**User perception:** "Several seconds" (indicating something else is wrong)

---

## Hypotheses

### Hypothesis 1: React StrictMode Double Render (Likely Culprit)

**Evidence:**
```tsx
// main.tsx
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>  // ◄── This causes double-mount in dev
    <App />
  </React.StrictMode>,
)
```

**Impact in Development:**
- Every `useEffect` runs TWICE
- `fetchChunks()` called twice per tab change
- Second call might see debounce promise and skip
- Creates timing confusion and extra renders

**Testing:**
1. Remove `<React.StrictMode>` temporarily
2. Check if tab switching feels faster
3. Check console for duplicate API calls

**Solution (if confirmed):**
- Keep StrictMode (it's good for finding bugs)
- But be aware of double-renders in dev
- Configure better loading states

### Hypothesis 2: Loading State Timing (UX Issue)

**Evidence:**
```typescript
// In fetchChunks():
loading.value = true  // Immediately hides content
// ... fetch happens (fast) ...
loading.value = false  // Shows content again
```

**Problem:**
```tsx
// In ChunkList.tsx:
{loading.value && filteredChunks.length === 0 ? (
  <div className="loading">Loading chunks...</div>
) : ...
```

**Scenario:**
1. User on "All" with 10 chunks visible
2. Clicks "Processed" tab
3. `loading.value = true` → **All chunks disappear instantly**
4. Fetch happens (10ms)
5. `loading.value = false` → New chunks appear

**User perception:** "Empty for a long time" (actually 10ms + render time)

**Why it feels slow:**
- Going from "content" → "empty" → "content" is jarring
- Human perception notices emptiness more than slight delays
- Animation/transition would help

**Solution:**
- Show skeleton UI instead of empty state
- Keep old data visible during fetch ("stale while revalidate")
- Add a minimum delay before showing loading (debounce loading state)

### Hypothesis 3: Cache Not Being Used Effectively

**Evidence from store code:**
```typescript
// Cache is loaded on page load:
const cachedChunks = readCache<Chunk[]>(STORAGE_KEYS.chunks)
if (cachedChunks) {
  chunks.value = cachedChunks  // ✅ Restored
}

// But when fetching with filter:
export async function fetchChunks(status?: string, limit = 100) {
  // ... OVERWRITES chunks.value with filtered subset ...
  chunks.value = await response.json()  // ❌ Throws away other data
}
```

**Problem:**
- Cache stores ALL chunks
- Fetching with filter REPLACES chunks.value with filtered subset
- Next filter switch must fetch again (previous data gone)
- Cache is only useful on page load, not during navigation

**Solution:**
- Always fetch ALL chunks and filter client-side, OR
- Store per-status chunks separately in cache

### Hypothesis 4: SSE Interfering with Loading

**Evidence:**
```typescript
// In Inbox.tsx:
useEffect(() => {
  fetchChunks('inbox')
  connectSSE()  // ◄── SSE connected on Inbox mount
  return () => disconnectSSE()
}, [])
```

**But ChunkList has no SSE control:**
```typescript
// In ChunkList.tsx:
useEffect(() => {
  fetchChunks(filter === 'all' ? undefined : filter)
  // No SSE setup here
}, [filter])
```

**Potential issue:**
- SSE is only connected when on Inbox tab
- Switching to "All Chunks" disconnects SSE
- Might cause re-fetches or state confusion

**Testing:**
- Check if SSE stays connected when switching tabs
- Check console for disconnect/reconnect messages

### Hypothesis 5: Network Waterfall (Cache + Fetch Race)

**Scenario:**
```
Page Load:
  1. JS executes → Reads cache (1ms)
  2. chunks.value = cachedChunks (instant)
  3. Component mounts
  4. useEffect runs
  5. fetchChunks() called → OVERWRITES cache data with fresh fetch
```

**If cache has 100 chunks but API returns 10 processed:**
- User sees: 100 → then suddenly 10
- Or: Empty → 10 (if timing is bad)

**Solution:**
- Don't fetch on mount if cache is fresh
- Add cache timestamp and TTL
- Show cached data immediately, fetch in background

### Hypothesis 6: Browser DevTools Slowing Down Execution

**Known Issue:**
- Chrome DevTools (especially with React DevTools) can slow down React significantly
- Signals might be affected by DevTools interception

**Testing:**
1. Close DevTools completely
2. Test tab switching
3. Check if it feels faster

**Solution:**
- Profile without DevTools open first
- Use Performance API for timing (not console.time)

---

## Proposed Solutions

### Solution 1: Fetch-All-Filter-Client Pattern (Recommended)

**Change ChunkList to always fetch ALL chunks, filter client-side:**

```typescript
// ChunkList.tsx
export function ChunkList() {
  const [filter, setFilter] = useState<StatusFilter>('all')

  useEffect(() => {
    // Fetch ALL chunks once
    fetchChunks(undefined, 100)  // No status filter
  }, [])  // Only on mount

  // Client-side filtering (data already in memory)
  const filteredChunks = filter === 'all' 
    ? chunks.value 
    : chunks.value.filter(c => c.status === filter)
  
  // ... rest of component
}
```

**Pros:**
- Single fetch per session
- Instant tab switching (pure client-side filter)
- Simpler architecture
- Cache always has complete dataset

**Cons:**
- Fetches all data even if user only wants one status
- Higher initial load time (but cached after)
- More memory (but 100 chunks is <100KB)

### Solution 2: Per-Status Cache with Intelligent Fetch

**Store chunks separately by status:**

```typescript
// New signals
export const allChunks = signal<Chunk[]>([])
export const inboxChunks = signal<Chunk[]>([])
export const processedChunks = signal<Chunk[]>([])
// ... etc

export async function fetchChunks(status?: string) {
  const cacheKey = `${STORAGE_PREFIX}:chunks:${status || 'all'}`
  
  // Check cache first
  const cached = readCache<Chunk[]>(cacheKey)
  if (cached) {
    updateSignalForStatus(status, cached)
    // Optionally fetch in background to update
  }
  
  // Fetch from API
  const response = await fetch(...)
  const chunks = await response.json()
  
  // Update appropriate signal
  updateSignalForStatus(status, chunks)
  writeCache(cacheKey, chunks)
}
```

**Pros:**
- Can cache each status separately
- Fetches only what's needed
- No data overwrites

**Cons:**
- More complex
- Cache management harder
- Duplicate chunks across caches

### Solution 3: Stale-While-Revalidate Pattern

**Show old data while fetching new data:**

```typescript
export async function fetchChunks(status?: string, limit = 100) {
  // Don't clear loading immediately
  const oldChunks = chunks.value
  
  // Fetch in background
  const response = await fetch(...)
  const newChunks = await response.json()
  
  // Update only when new data arrives
  chunks.value = newChunks
  writeCache(STORAGE_KEYS.chunks, newChunks)
}
```

**In component:**
```tsx
{loading.value && filteredChunks.length > 0 ? (
  // Show stale data with indicator
  <div className="chunk-list stale">
    <div className="loading-indicator">Updating...</div>
    {/* Render chunks */}
  </div>
) : ...}
```

**Pros:**
- No "flash of empty"
- Feels instant even with fetch
- Better UX

**Cons:**
- User might see stale data briefly
- Need visual indicator

### Solution 4: Skeleton UI During Load

**Replace empty state with skeleton:**

```tsx
{loading.value && filteredChunks.length === 0 ? (
  <div className="chunk-list">
    {[...Array(5)].map((_, i) => (
      <div key={i} className="chunk-item skeleton">
        <div className="skeleton-header" />
        <div className="skeleton-content" />
      </div>
    ))}
  </div>
) : ...}
```

```css
.skeleton {
  background: linear-gradient(90deg, #2a2a2a 25%, #333 50%, #2a2a2a 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}
```

**Pros:**
- Feels less "empty"
- Modern UX pattern
- Indicates loading without hiding layout

**Cons:**
- Doesn't fix underlying issue
- More CSS to maintain

---

## Recommended Investigation Steps

### Immediate (5 minutes)

1. **Measure actual timing with Performance API:**
   ```typescript
   export async function fetchChunks(status?: string, limit = 100) {
     const t0 = performance.now()
     
     // ... fetch logic ...
     
     const t1 = performance.now()
     console.log(`fetchChunks(${status}) took ${t1 - t0}ms`)
   }
   ```

2. **Test without StrictMode:**
   - Temporarily remove `<React.StrictMode>` wrapper
   - Check if tab switching feels faster
   - Count API calls in Network tab

3. **Add stale-while-revalidate:**
   - Don't set `loading.value = true` if data already exists
   - Show old data during refresh

### Short Term (30 minutes)

1. **Implement Solution 1 (Fetch All, Filter Client):**
   - Simplest fix
   - Best UX for small datasets (<1000 chunks)
   - Instant tab switching

2. **Add performance logging dashboard:**
   - Track: API time, parse time, render time
   - Use Performance Observer API
   - Log to console or send to analytics

3. **User testing:**
   - Ask someone else to try it
   - Get subjective feedback on "feels fast"
   - Compare before/after

### Medium Term (1-2 hours)

1. **Implement proper cache strategy:**
   - Add cache timestamps
   - Add TTL (time-to-live)
   - Background refresh when stale

2. **Optimize rendering:**
   - Add React.memo for ChunkItem
   - Virtualize long lists (react-window)
   - Lazy load images/data

3. **Add skeleton UI:**
   - Better than empty state
   - Feels more responsive

---

## Questions for Investigation

1. What is the actual measured time from tab click to content display?
2. Is React StrictMode causing double-fetches in development?
3. Does the app feel faster with StrictMode disabled?
4. What does the Performance profiler show during tab switch?
5. Is the "loading" state showing for the full duration, or is there a delay?
6. Does the Network tab show duplicate requests?
7. Is localStorage read/write time significant? (Use Performance API)
8. What's the total chunk count? (If >1000, need virtualization)
9. Are there any console errors or warnings during tab switch?
10. Does adding a 100ms debounce to tab clicks help or hurt?

---

## Success Metrics

**Current (Subjective):**
- Tab switch feels slow
- Empty state visible for "a long time"
- Data "coming and going"

**Target:**
- Tab switch feels instant (<100ms)
- No empty flash
- Smooth transitions
- Data feels "always there"

**Quantitative Targets:**
- API response: <50ms (currently 2-10ms ✅)
- Parse + render: <100ms
- Total perceived load: <150ms
- No more than 1 API call per tab switch

---

## Related Files

- `frontend/src/components/ChunkList.tsx` - Tab UI and filtering
- `frontend/src/store/index.ts` - Data fetching and caching
- `frontend/src/components/Inbox.tsx` - SSE setup
- `frontend/src/main.tsx` - React StrictMode configuration
- `backend/app/api/chunks.py` - Backend endpoint (fast, not the issue)

---

**End of Report**
