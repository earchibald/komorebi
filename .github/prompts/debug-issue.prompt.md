---
name: debug-issue
description: Systematic debugging workflow for complex issues using hypothesis-driven approach
tier: premium
model: opus
version: 1.0.0
---

# Debug Issue

## Governance (MUST Follow)

### Pre-1.0.0 Documentation Rule
- ✅ Document the bug and fix in `ELICITATIONS.md` for future reference
- ✅ Update `CHANGELOG.md` if the fix affects user-facing behavior

### Prime Directives
1. **Reproduce First:** Never debug without a reliable reproduction
2. **Hypothesis-Driven:** Form explicit hypotheses before investigating
3. **Minimal Changes:** Fix the root cause with surgical precision
4. **Regression Protection:** Add tests to prevent reoccurrence

---

## Task Context

You are debugging an issue in the Komorebi project. Follow a systematic approach:
1. **Reproduce** the issue reliably
2. **Isolate** the failing component
3. **Hypothesize** potential causes
4. **Investigate** with targeted debugging
5. **Fix** with minimal changes
6. **Verify** the fix and prevent regression

---

## Debugging Workflow

### Phase 1: Reproduction

#### Step 1.1: Gather Information

Collect all available information about the issue:
- **Error messages:** Full stack traces, log output
- **Environment:** Python/Node version, OS, dependencies
- **Steps to reproduce:** Exact sequence of actions
- **Expected vs actual behavior:** Clear delta
- **Frequency:** Always, intermittent, or race condition?

**Template:**
```markdown
## Issue Report

**Summary:** [One-line description]

**Environment:**
- Python: [version]
- FastAPI: [version]
- OS: [macOS/Linux/Windows]
- Database: [aiosqlite/PostgreSQL]

**Steps to Reproduce:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected:** [What should happen]
**Actual:** [What actually happens]

**Error Message:**
```
[Full stack trace or error output]
```

**Frequency:** [Always / Intermittent / Race condition]
```

#### Step 1.2: Create Minimal Reproduction

Write the smallest possible script/test that triggers the issue:

```python
# reproduction_script.py
import asyncio
from backend.app.api.chunks import create_chunk
from backend.app.models.chunk import ChunkCreate

async def reproduce_issue():
    """Minimal script to reproduce the bug."""
    chunk_data = ChunkCreate(content="Test content")
    result = await create_chunk(chunk_data)
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(reproduce_issue())
```

Run: `python reproduction_script.py`

**Success Criteria:** Issue reproduces consistently (>90% of the time)

---

### Phase 2: Isolation

#### Step 2.1: Identify Failing Component

Use binary search to narrow down the failing component:

```python
# Add logging to isolate the failure point
import logging
logging.basicConfig(level=logging.DEBUG)

async def function_with_bug():
    logger.debug("Entering function_with_bug")
    
    # Step 1
    logger.debug("Before step 1")
    result1 = await step1()
    logger.debug(f"After step 1: {result1}")
    
    # Step 2
    logger.debug("Before step 2")
    result2 = await step2(result1)
    logger.debug(f"After step 2: {result2}")  # ← Bug might be here
    
    # Step 3
    logger.debug("Before step 3")
    result3 = await step3(result2)
    logger.debug(f"After step 3: {result3}")
    
    return result3
```

**Goal:** Identify the exact function/line where the issue occurs

#### Step 2.2: Check Async Pitfalls (Backend)

Common async issues in Komorebi:

1. **Missing `await`:**
   ```python
   # ❌ WRONG
   result = some_async_function()  # Returns coroutine, not result
   
   # ✅ CORRECT
   result = await some_async_function()
   ```

2. **Blocking operations in async context:**
   ```python
   # ❌ WRONG
   result = requests.get("http://api.com")  # Blocks event loop
   
   # ✅ CORRECT
   result = await http_client.get("http://api.com")  # Async
   ```

3. **Database session not awaited:**
   ```python
   # ❌ WRONG
   result = session.execute(query)  # Missing await
   
   # ✅ CORRECT
   result = await session.execute(query)
   ```

4. **Race condition in concurrent operations:**
   ```python
   # ❌ WRONG
   await asyncio.gather(update_chunk(1), update_chunk(1))  # Race!
   
   # ✅ CORRECT
   async with lock:
       await update_chunk(1)
   ```

#### Step 2.3: Check React/Signal Pitfalls (Frontend)

Common frontend issues in Komorebi:

1. **Signal mutation without `.value`:**
   ```typescript
   // ❌ WRONG
   chunks = newChunks  // Replaces signal, doesn't update it
   
   // ✅ CORRECT
   chunks.value = newChunks  // Updates signal value
   ```

2. **useEffect dependency loops:**
   ```typescript
   // ❌ WRONG
   useEffect(() => {
       fetchChunks()
   }, [chunks.value])  // Infinite loop!
   
   // ✅ CORRECT
   useEffect(() => {
       fetchChunks()
   }, [])  // Fetch once on mount
   ```

3. **Stale closure in callbacks:**
   ```typescript
   // ❌ WRONG
   const handleClick = () => {
       console.log(chunks.value)  // Stale value!
   }
   
   // ✅ CORRECT
   const handleClick = () => {
       console.log(chunks.peek())  // Fresh value
   }
   ```

---

### Phase 3: Hypothesis Formation

#### Step 3.1: List Potential Causes

Based on the isolated failure point, list hypotheses:

**Template:**
```markdown
## Hypotheses (ranked by likelihood)

1. **[Hypothesis 1]** (70% confidence)
   - Evidence: [Why you think this is the cause]
   - Test: [How to verify]

2. **[Hypothesis 2]** (20% confidence)
   - Evidence: [Why you think this is the cause]
   - Test: [How to verify]

3. **[Hypothesis 3]** (10% confidence)
   - Evidence: [Why you think this is the cause]
   - Test: [How to verify]
```

**Example:**
```markdown
## Hypotheses

1. **Missing await on database query** (70%)
   - Evidence: Error says "coroutine was never awaited"
   - Test: Add await before session.execute()

2. **Database connection closed prematurely** (20%)
   - Evidence: Error mentions "connection closed"
   - Test: Check session lifecycle with logging

3. **Race condition in concurrent requests** (10%)
   - Evidence: Only fails under load
   - Test: Add locks around critical section
```

#### Step 3.2: Rank by Probability

Order hypotheses by:
1. **Likelihood:** Does the evidence support this?
2. **Impact:** If true, would it fully explain the issue?
3. **Testability:** Can we quickly verify?

---

### Phase 4: Investigation

#### Step 4.1: Test Hypotheses Systematically

For each hypothesis (starting with highest probability):

1. **Predict:** What should we see if this hypothesis is correct?
2. **Test:** Run targeted investigation (logging, debugging, experiments)
3. **Observe:** What actually happened?
4. **Conclude:** Does this confirm or refute the hypothesis?

**Example:**
```python
# Hypothesis: Missing await on database query
# Prediction: Adding await will fix the issue

# Before (broken):
result = session.execute(query)  # ❌

# After (fixed):
result = await session.execute(query)  # ✅

# Test: Run reproduction script
# Observe: Issue no longer occurs
# Conclusion: Hypothesis confirmed ✅
```

#### Step 4.2: Use Debugging Tools

**Python Debugger (pdb):**
```python
import pdb

async def function_with_bug():
    result1 = await step1()
    pdb.set_trace()  # ← Breakpoint here
    result2 = await step2(result1)
    return result2
```

**Async Debugging:**
```python
import asyncio

# Print all running tasks
tasks = asyncio.all_tasks()
for task in tasks:
    print(f"Task: {task.get_name()}, State: {task}")

# Check for pending coroutines
pending = [task for task in tasks if not task.done()]
print(f"Pending tasks: {len(pending)}")
```

**Performance Profiling:**
```python
import cProfile
import pstats

# Profile a function
cProfile.run('asyncio.run(function_to_profile())', 'profile_stats')

# Analyze results
p = pstats.Stats('profile_stats')
p.sort_stats('cumulative').print_stats(20)
```

**Memory Profiling:**
```python
from memory_profiler import profile

@profile
async def function_with_memory_issue():
    # ... code that might leak memory
    pass
```

#### Step 4.3: Check Logs and Events

```bash
# Backend logs
tail -f backend/logs/app.log

# Frontend console (in browser DevTools)
# Look for errors, warnings, failed network requests

# Database logs (if using PostgreSQL)
tail -f /var/log/postgresql/postgresql.log
```

---

### Phase 5: Fix

#### Step 5.1: Implement Minimal Fix

**Principles:**
1. Fix the root cause, not symptoms
2. Minimize changes to reduce risk
3. Follow existing code patterns
4. Add defensive checks if needed

**Example:**
```python
# Root cause: Missing await on database query

# ❌ SYMPTOM FIX (doesn't solve root cause)
try:
    result = session.execute(query)  # Still broken
except Exception:
    result = None  # Hide the problem

# ✅ ROOT CAUSE FIX
result = await session.execute(query)  # Proper async/await
```

#### Step 5.2: Add Defensive Checks (if needed)

If the bug was caused by invalid input or missing validation:

```python
# Add validation to prevent future issues
async def process_chunk(chunk_id: UUID):
    if chunk_id is None:
        raise ValueError("chunk_id cannot be None")  # ← Defensive check
    
    chunk = await chunk_repo.get(chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    # ... process chunk
```

#### Step 5.3: Document the Fix

Add a comment explaining why the fix is necessary:

```python
async def function_that_was_buggy():
    # Fix: Added await to prevent "coroutine was never awaited" error
    # Root cause: Database queries in SQLAlchemy async must be awaited
    result = await session.execute(query)  # ← Comment explains fix
    return result
```

---

### Phase 6: Verification

#### Step 6.1: Verify the Fix

1. **Run reproduction script:** Issue should no longer occur
2. **Run full test suite:** `pytest` (ensure no regressions)
3. **Test manually:** Follow original reproduction steps
4. **Test edge cases:** Try variations that might still fail

```bash
# Run reproduction script
python reproduction_script.py  # ✅ Should work now

# Run tests
pytest backend/tests/  # ✅ All tests pass

# Check for regressions
pytest backend/tests/test_chunks.py -v  # ✅ No failures
```

#### Step 6.2: Add Regression Test

Prevent the bug from reoccurring:

```python
# backend/tests/test_regression_issue_123.py
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_regression_missing_await_on_query():
    """
    Regression test for issue #123: Missing await on database query.
    
    Bug: Database query was not awaited, causing "coroutine never awaited" error.
    Fix: Added await to session.execute(query) in chunk_repo.get()
    """
    response = client.get("/api/v1/chunks/00000000-0000-0000-0000-000000000000")
    
    # Should return 404, not 500 (server error from unawaited coroutine)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
```

**Why this helps:**
- Documents the bug and fix in code
- Catches the issue if someone accidentally removes the `await` again
- Serves as a test case for similar issues

#### Step 6.3: Update Documentation

```markdown
# ELICITATIONS.md
## [2026-02-05] Fixed: Missing await on database query in chunk_repo.get()

**Issue:** 
- Error: "RuntimeWarning: coroutine 'AsyncSession.execute' was never awaited"
- Cause: Database query in `chunk_repo.get()` was missing `await`

**Root Cause:**
- SQLAlchemy async queries return coroutines that must be awaited
- Previous code: `result = session.execute(query)` ❌
- Fixed code: `result = await session.execute(query)` ✅

**Fix:**
- Added `await` to `session.execute()` call in `backend/app/repositories/chunk.py:42`
- Added regression test in `backend/tests/test_regression_issue_123.py`

**Lesson:** Always verify that async functions use `await` for I/O operations.
```

---

## Common Bug Categories

### 1. Async/Await Issues (Backend)

**Symptoms:**
- "coroutine was never awaited"
- "RuntimeWarning: coroutine 'func' was never awaited"
- Event loop errors

**Debugging:**
```python
# Check for missing awaits
import asyncio

# Get all tasks
tasks = asyncio.all_tasks()
for task in tasks:
    if not task.done():
        print(f"Pending task: {task.get_coro()}")
```

**Common Fixes:**
- Add `await` before async function calls
- Use `asyncio.gather()` for concurrent operations
- Check database session lifecycle

### 2. Race Conditions (Backend)

**Symptoms:**
- Only fails under load or concurrent requests
- Intermittent failures
- Data corruption

**Debugging:**
```python
# Add locks to critical sections
import asyncio

lock = asyncio.Lock()

async def update_chunk(chunk_id):
    async with lock:
        # Critical section - only one coroutine at a time
        chunk = await chunk_repo.get(chunk_id)
        chunk.counter += 1
        await chunk_repo.update(chunk)
```

### 3. Signal Issues (Frontend)

**Symptoms:**
- UI doesn't update when data changes
- Stale values in callbacks
- Infinite re-renders

**Debugging:**
```typescript
// Check signal updates
import { effect } from '@preact/signals-react'

effect(() => {
    console.log('Chunks changed:', chunks.value)
})

// Check for mutations
const oldValue = chunks.value
// ... some code ...
if (chunks.value === oldValue) {
    console.error('Signal value didn\'t change!')
}
```

### 4. Validation Errors (Backend)

**Symptoms:**
- 422 Unprocessable Entity
- Pydantic validation errors
- Missing required fields

**Debugging:**
```python
# Print validation errors
from pydantic import ValidationError

try:
    chunk = ChunkCreate(**data)
except ValidationError as e:
    print("Validation errors:")
    for error in e.errors():
        print(f"- {error['loc']}: {error['msg']}")
```

### 5. Database Issues (Backend)

**Symptoms:**
- "connection closed"
- "no such table"
- "UNIQUE constraint failed"

**Debugging:**
```python
# Check database state
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Available tables: {tables}")

# Check connection
async with engine.begin() as conn:
    result = await conn.execute("SELECT 1")
    print(f"Connection OK: {result.scalar()}")
```

---

## Output Format

**Provide the following deliverables:**

1. **Issue Analysis:**
   - Problem summary
   - Environment details
   - Reproduction steps
   - Root cause identified

2. **Fix Implementation:**
   - Minimal code changes to fix the root cause
   - Defensive checks added (if applicable)
   - Comments explaining why the fix works

3. **Regression Test:**
   - Test file: `backend/tests/test_regression_issue_<number>.py`
   - Documents the bug and fix
   - Catches reoccurrence

4. **Documentation:**
   - Entry in `ELICITATIONS.md` with bug details and fix
   - Update `CHANGELOG.md` if user-facing

**Do NOT:**
- Fix symptoms without addressing root cause
- Make large refactorings while debugging
- Skip regression tests
- Leave debug logging in production code

---

**Ready to debug systematically!** Follow the 6-phase workflow above.
