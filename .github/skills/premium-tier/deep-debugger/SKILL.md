---
name: deep-debugger
description: Advanced debugging for multi-file race conditions, async bugs, and complex system interactions. Use for issues spanning multiple files or requiring deep system understanding.
---

# Deep Debugger

## About This Skill

This premium-tier skill provides advanced debugging capabilities for the most complex issues:
- Multi-file race conditions
- Async/await timing issues
- Memory leaks and resource exhaustion
- Performance bottlenecks
- Database transaction conflicts
- Event loop blocking

**Model Tier:** Premium (Claude Opus 4.6)  
**Cost Multiplier:** 60x baseline  
**When to Use:** Only after standard debugging (/debug-issue) fails

## Triggers

Invoke deep-debugger when:
- "The bug only appears under high load"
- "It's a heisenbug - changes when I add logging"
- "Multiple async operations interfering"
- "Database deadlock or transaction timeout"
- "Memory usage grows unbounded"
- "Performance degrades over time"

## Debugging Workflow

### Phase 1: System-Wide Analysis

1. **Map the execution flow across all files:**
   ```bash
   # Find all async functions
   grep -r "async def" backend/app/ --include="*.py"
   
   # Find all event emitters
   grep -r "event_bus.emit" backend/app/ --include="*.py"
   
   # Find all database transactions
   grep -r "db.begin\|db.commit\|db.rollback" backend/app/ --include="*.py"
   ```

2. **Identify shared state:**
   - Global variables
   - Singleton instances
   - Database locks
   - File handles
   - Network connections

3. **Map dependencies:**
   ```bash
   # Visualize call graph (if available)
   pyan3 backend/app/**/*.py --uses --no-defines --colored --grouped --annotated --dot > callgraph.dot
   dot -Tpng callgraph.dot -o callgraph.png
   ```

### Phase 2: Instrumentation Strategy

1. **Add structured logging:**
   ```python
   import structlog
   logger = structlog.get_logger()
   
   async def suspect_function():
       request_id = get_request_id()
       logger.info("function_entry", request_id=request_id, thread=threading.get_ident())
       try:
           result = await risky_operation()
           logger.info("function_success", request_id=request_id, result=result)
           return result
       except Exception as e:
           logger.error("function_error", request_id=request_id, error=str(e), stack=traceback.format_exc())
           raise
   ```

2. **Add timing probes:**
   ```python
   import time
   from contextlib import asynccontextmanager
   
   @asynccontextmanager
   async def timer(operation: str):
       start = time.perf_counter()
       try:
           yield
       finally:
           duration = time.perf_counter() - start
           logger.info("timing", operation=operation, duration_ms=duration * 1000)
   
   async def process():
       async with timer("database_query"):
           results = await db.execute(query)
       async with timer("llm_call"):
           summary = await ollama.generate(prompt)
   ```

3. **Add resource tracking:**
   ```python
   import psutil
   import asyncio
   
   async def log_resources():
       process = psutil.Process()
       while True:
           mem = process.memory_info().rss / 1024 / 1024  # MB
           cpu = process.cpu_percent()
           tasks = len(asyncio.all_tasks())
           logger.info("resources", mem_mb=mem, cpu_percent=cpu, active_tasks=tasks)
           await asyncio.sleep(5)
   ```

### Phase 3: Hypothesis Generation

For complex bugs, generate multiple competing hypotheses:

1. **Race Condition Hypothesis:**
   - "Two async tasks accessing shared state without locks"
   - Test: Add explicit locks and see if bug disappears

2. **Resource Leak Hypothesis:**
   - "Connections/files not being properly closed"
   - Test: Monitor open file descriptors with `lsof`

3. **Event Loop Blocking Hypothesis:**
   - "Blocking I/O in async context"
   - Test: Use `async-timeout` to detect long-running operations

4. **Database Locking Hypothesis:**
   - "Deadlock between concurrent transactions"
   - Test: Check PostgreSQL logs for deadlock detection

### Phase 4: Systematic Isolation

1. **Binary search the codebase:**
   ```python
   # Temporarily disable half the features
   FEATURE_FLAGS = {
       "compaction": False,  # Disable suspect feature
       "mcp_integration": True,
       "real_time_events": True,
   }
   ```

2. **Reduce concurrency:**
   ```python
   # Force single-threaded execution
   uvicorn.run(app, workers=1, limit_concurrency=1)
   ```

3. **Mock external dependencies:**
   ```python
   @pytest.fixture
   def mock_ollama():
       """Replace real Ollama with instant mock."""
       async def instant_summary(content: str) -> str:
           return "Mock summary"
       return instant_summary
   ```

### Phase 5: Advanced Tools

1. **Async stack traces:**
   ```bash
   # Install aiodebug
   pip install aiodebug
   
   # Enable in app
   import aiodebug.log_slow_callbacks
   aiodebug.log_slow_callbacks.enable(0.05)  # Log callbacks > 50ms
   ```

2. **Memory profiler:**
   ```bash
   # Install memory profiler
   pip install memory_profiler
   
   # Profile function
   @profile
   async def suspect_function():
       ...
   
   # Run with profiling
   python -m memory_profiler backend/app/main.py
   ```

3. **Async tracing:**
   ```bash
   # Install aiomonitor
   pip install aiomonitor
   
   # Add to app
   from aiomonitor import start_monitor
   with start_monitor(loop=asyncio.get_event_loop()):
       uvicorn.run(app)
   
   # Connect in terminal
   telnet localhost 50101
   # Commands: ps, where <task_id>, cancel <task_id>
   ```

4. **Database query logging:**
   ```python
   # SQLAlchemy echo
   engine = create_async_engine(
       "sqlite+aiosqlite:///komorebi.db",
       echo=True,  # Log all queries
       echo_pool=True,  # Log connection pool
   )
   ```

### Phase 6: Reproduction Script

Create minimal reproduction:

```python
"""
Minimal reproduction of [bug description].

Run:
    python repro_bug.py
    
Expected: [expected behavior]
Actual: [actual behavior]
"""
import asyncio
from backend.app.core.compactor import CompactorService

async def reproduce():
    # Minimal setup
    compactor = CompactorService()
    
    # Trigger bug
    tasks = [compactor.process_chunk(i) for i in range(100)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check for failure
    errors = [r for r in results if isinstance(r, Exception)]
    print(f"Errors: {len(errors)} / 100")
    for e in errors[:5]:
        print(f"  - {e}")

if __name__ == "__main__":
    asyncio.run(reproduce())
```

## Common Patterns

### Pattern 1: Async Context Manager Resource Leak

**Symptom:** Memory grows over time  
**Cause:** `__aexit__` not called due to exception

**Fix:**
```python
# ❌ Leaky
async with lock:
    risky_operation()  # Exception here skips cleanup

# ✅ Safe
try:
    async with lock:
        risky_operation()
except Exception:
    logger.error("Operation failed")
    raise
```

### Pattern 2: Shared Mutable Default

**Symptom:** State persists across requests  
**Cause:** Mutable default argument

**Fix:**
```python
# ❌ Shared state
async def process(items: list = []):
    items.append(new_item)  # Modifies shared list!

# ✅ Fresh state
async def process(items: list | None = None):
    items = items or []
    items.append(new_item)
```

### Pattern 3: Blocking I/O in Async

**Symptom:** Event loop hangs  
**Cause:** Synchronous I/O in async function

**Fix:**
```python
# ❌ Blocks event loop
async def load_config():
    with open("config.json") as f:  # Blocks!
        return json.load(f)

# ✅ Async I/O
async def load_config():
    async with aiofiles.open("config.json") as f:
        content = await f.read()
        return json.loads(content)
```

### Pattern 4: Database Transaction Deadlock

**Symptom:** Random "deadlock detected" errors  
**Cause:** Transactions acquiring locks in different orders

**Fix:**
```python
# ❌ Inconsistent lock order
async def update_a_then_b():
    await db.execute("UPDATE a SET ...;")
    await db.execute("UPDATE b SET ...;")

async def update_b_then_a():
    await db.execute("UPDATE b SET ...;")  # Opposite order!
    await db.execute("UPDATE a SET ...;")

# ✅ Consistent lock order (alphabetical)
async def update_a_then_b():
    await db.execute("UPDATE a SET ...;")
    await db.execute("UPDATE b SET ...;")

async def update_b_then_a():
    await db.execute("UPDATE a SET ...;")  # Same order
    await db.execute("UPDATE b SET ...;")
```

## Output Format

Provide:
1. **System-wide execution map** - All files and interactions involved
2. **Instrumentation patches** - Logging/timing code to add
3. **Hypothesis matrix** - Ranked by probability with test plans
4. **Isolation strategy** - Binary search plan to narrow down
5. **Reproduction script** - Minimal code to trigger bug reliably
6. **Root cause analysis** - Once found, explain the mechanism
7. **Fix + regression test** - Permanent solution with test

## Telemetry

Log usage:
```bash
python scripts/telemetry/telemetry_tracker.py log deep-debugger premium --duration <seconds>
```
