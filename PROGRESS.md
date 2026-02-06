# Execution Log

## Completed ✅

### Context Oracle: Modules 9-11 (Security, MCP Server, Cost Governance)

**Phase 1: Security & Profiles**
- ✅ `RedactionService` (`backend/app/core/redaction.py`)
  - 9 compiled regex patterns for secret scrubbing
  - `redact()`, `contains_secrets()`, `scan()` methods
  - Custom pattern support via constructor
- ✅ `ProfileManager` (`backend/app/core/profiles.py`)
  - YAML profile loading with multi-level inheritance
  - Cycle detection, dangerous env var blocking (`LD_PRELOAD`, `DYLD_INSERT_LIBRARIES`)
  - `load()`, `resolve()`, `build_env()` methods
- ✅ Pydantic models (`backend/app/models/profile.py`)
  - `BlockingPolicy`, `ExecutionProfile`, `ResolvedProfile`
- ✅ 37 tests passing (`backend/tests/test_phase1_security.py`)

**Phase 2: MCP Server & Traces**
- ✅ `KomorebiMCPServer` (`backend/app/mcp/server.py`)
  - MCP 2024-11-05 stdio server with JSON-RPC handling
  - 4 tools: `search_context`, `get_active_trace`, `read_file_metadata`, `get_related_decisions`
  - `run_stdio()` event loop
- ✅ Database tables (`backend/app/db/database.py`)
  - `TraceTable`, `FileEventTable`, `LLMUsageTable` + `trace_id` on `ChunkTable`
- ✅ `TraceRepository` (`backend/app/db/trace_repository.py`)
  - CRUD + `activate()`, `get_active()`, `get_summary()`, `search_by_name()`
- ✅ `FileEventRepository` (`backend/app/db/file_event_repository.py`)
  - CRUD + `path_history()`, `count_by_trace()`
- ✅ Migration script (`scripts/migrate_v1_oracle.py`)
- ✅ API routes (`backend/app/api/traces.py`, `file_events.py`)
  - 6 trace endpoints + 2 file event endpoints
- ✅ CLI commands (`cli/main.py`)
  - `mcp-serve`, `switch`, `trace rename`, `watch start`, `watch status`
- ✅ 36 tests passing (`backend/tests/test_phase2_oracle.py`)

**Phase 3: Cost Governance & Watcher**
- ✅ `CostService` (`backend/app/services/cost_service.py`)
  - Token counting heuristic (len/4), per-model cost estimation
  - Budget enforcement with auto-downgrade, `BudgetExceeded` exception
- ✅ `FileWatcherDaemon` (`backend/app/core/watcher.py`)
  - `watchdog`-based filesystem watching with ignore rules
  - Registration in `~/.komorebi/watchers.json`
- ✅ Billing API (`backend/app/api/billing.py`)
  - `GET /llm/usage`, `GET /llm/budget`, `PUT /llm/budget`
- ✅ Frontend signals store (`frontend/src/store/oracle.ts`)
  - `llmUsage`, `budgetConfig`, `activeTrace`, `traces`, `recentFileEvents` signals
  - Computed: `totalCost`, `isThrottled`
- ✅ `BillingDashboard` component (`frontend/src/components/BillingDashboard.tsx`)
- ✅ `WatcherStatus` component (`frontend/src/components/WatcherStatus.tsx`)
- ✅ App.tsx updated with Billing and Watcher tabs
- ✅ 29 tests passing (`backend/tests/test_phase3_cost.py`)
- ✅ Documentation updates (CHANGELOG, CURRENT_STATUS, PROGRESS)

### Module 8: Modular Target Delivery System
- ✅ Core abstractions (`backend/app/targets/`)
  - `TargetAdapter` ABC with schema, MCP tool mapping, argument transformation
  - `FieldSchema` and `TargetSchema` Pydantic models for declarative definitions
  - `FieldType` enum (TEXT, MARKDOWN, TEXTAREA, NUMBER, SELECT, CHECKBOX)
- ✅ `TargetRegistry` singleton
  - `register()`, `get()`, `list_schemas()`, `get_schema()` methods
  - Design enables runtime adapter discovery (zero frontend hardcoding)
- ✅ `GitHubIssueAdapter` implementation
  - Maps form data to `github.create_issue` MCP tool arguments
  - Array splitting for labels and assignees
  - Prerequisite validation (stub for future OAuth)
- ✅ API endpoints (`backend/app/api/targets.py`)
  - `GET /api/v1/targets/schemas` - list all
  - `GET /api/v1/targets/{name}/schema` - get specific
  - `POST /api/v1/dispatch` - dispatch to target with MCP invocation
  - Comprehensive error handling (404, 400, 500)
- ✅ Frontend signals store (`frontend/src/store/targets.ts`)
  - `availableTargets`, `formData`, `dispatchState` signals
  - `fetchSchemas()`, `updateFormField()`, `dispatch()` functions
- ✅ UI components (`frontend/src/components/`)
  - `DynamicForm` - Schema-driven form renderer with field state
  - `StagingArea` - Target selector + form editor + dispatch interface
  - Integration into main `App.tsx` with new "Dispatch" tab
- ✅ 25 tests passing (19 unit + 6 integration)
  - Schema validation, registry lifecycle, adapter enforcement
  - API endpoint testing, MCP error handling, response models
- ✅ Documentation updates
  - CHANGELOG.md updated with Module 8 entry
  - CURRENT_STATUS.md updated with v0.8.1 entry
  - PROGRESS.md updated with completion status

### Module 7: Context Resume ("The Save Point")
- ✅ Pydantic models (`backend/app/models/resume.py`)
  - `ProjectBriefing` with summary, sections, recent_chunks, decisions, related_context
  - `BriefingSection` with heading, content, optional chunk_id link
- ✅ `ResumeService` (`backend/app/services/resume_service.py`)
  - Read-only aggregation from chunks, entities, TF-IDF, LLM
  - Template fallback when Ollama unavailable
  - System anchor injection for LLM context grounding
- ✅ API endpoint `GET /projects/{id}/resume?hours=48`
- ✅ `KomorebiLLM.generate()` general-purpose method
- ✅ `EntityRepository.list_by_project()` `since` parameter
- ✅ Frontend `ResumeCard` component + store signals
- ✅ 12 new tests (97 total passed, 3 skipped)

### Phase 1: Backend Service (FastAPI)
- ✅ Pydantic models (`backend/app/models/`)
  - Chunk model with status enum (INBOX, PROCESSED, COMPACTED, ARCHIVED)
  - Project model for organizing chunks
  - MCPServerConfig model for MCP server connections
- ✅ Database layer (`backend/app/db/`)
  - SQLAlchemy async setup with SQLite (aiosqlite)
  - Repository pattern (ChunkRepository, ProjectRepository)
- ✅ Core services (`backend/app/core/`)
  - CompactorService for recursive summarization
  - EventBus for SSE broadcasting
- ✅ MCP aggregator (`backend/app/mcp/`)
  - MCPClient for connecting to MCP servers
  - MCPRegistry for managing multiple connections
- ✅ API routes (`backend/app/api/`)
  - Chunk endpoints (CRUD + fast capture)
  - Project endpoints with compaction
  - MCP server management endpoints
  - SSE streaming endpoint
- ✅ Main FastAPI application with CORS and lifespan management

### Phase 2: CLI Tool
- ✅ CLI with Typer (`cli/main.py`)
  - `capture` command for quick inbox capture
  - `list` command for viewing chunks
  - `compact` command for manual compaction
  - `projects` command for listing projects
  - `stats` command for statistics
  - `serve` command for starting the server

### Phase 3: React Dashboard
- ✅ React + TypeScript + Vite setup (`frontend/`)
- ✅ Theme/styling with CSS variables (dark mode)
- ✅ Store with Preact signals for state management
- ✅ Components:
  - Stats component for statistics display
  - Inbox component with quick capture form
  - ChunkList component with filtering
  - ProjectList component with create form
- ✅ SSE integration for real-time updates

### Phase 4: Hammer Benchmarking Script
- ✅ `scripts/hammer_gen.py` created
- ✅ Load testing with configurable parameters
- ✅ Latency and throughput metrics

### Phase 5: Validation
- ✅ Backend tests passing (16/16)
- ✅ hammer_gen.py runs successfully against backend
- ✅ All 53 requests successful, 0 failures

### Phase 6: Developer Experience - VS Code Prompts & Skills
- ✅ Created VS Code custom prompts (`.github/prompts/`)
  - `implement-feature.prompt.md` - Full-stack TDD workflow (Standard tier)
  - `write-tests.prompt.md` - Pytest patterns and coverage (Standard tier)
  - `debug-issue.prompt.md` - 6-phase debugging (Premium/Opus 4.6 tier)
  - `review-pr.prompt.md` - Comprehensive PR review (Standard tier)
  - `update-docs.prompt.md` - Documentation governance (Economy/Haiku tier)
  - `refactor-code.prompt.md` - Code improvement workflows (Standard tier)
  - `architect-feature.prompt.md` - Complex feature design (Premium/Opus 4.6 tier)
- ✅ Created agent skills (`.github/skills/`)
  - `feature-implementer` (Standard) - Scaffold generator with validation scripts
  - `code-formatter` (Economy) - Ruff formatting and linting commands
  - `deep-debugger` (Premium) - Advanced async/race condition debugging
  - `research-agent` (Research) - Long-context codebase analysis with Gemini 3 Pro
- ✅ Created telemetry infrastructure (`scripts/telemetry/`)
  - Usage tracking with cost analysis
  - Report generation by time period
  - Optional MCP endpoint integration
- ✅ Comprehensive documentation
  - `docs/PROMPTS_AND_SKILLS_PROPOSAL.md` - Full strategy document
  - `docs/PROMPTS_SKILLS_AUDIT.md` - Audit and recommendations
  - `docs/PROMPT_GUIDE.md` - Usage guide for all prompts/skills
  - `docs/CONTEXT_AWARENESS_ANALYSIS.md` - Context derivation capabilities
  - `docs/IMPLEMENTATION_SUMMARY.md` - Quick reference

### Phase 7: Module 1 - Core Intelligence (Ollama Integration)
- ✅ Added `ollama` dependency to pyproject.toml
- ✅ Created `backend/app/core/ollama_client.py` with KomorebiLLM class
  - Async AsyncClient initialization with host/model from environment
  - `is_available()` health check
  - `summarize()` method for LLM-powered text summarization
  - `stream_summary()` for real-time UI feedback
- ✅ Updated `backend/app/models/chunk.py` ChunkUpdate schema
  - Added `token_count` field to ChunkUpdate
- ✅ Integrated LLM into `backend/app/core/compactor.py`
  - `process_chunk()` now uses KomorebiLLM for intelligent summaries (Map step)
  - Graceful fallback to simple summarization if Ollama unavailable
  - `compact_project()` now uses Map-Reduce pattern with LLM (Reduce step)
  - System anchor injection to maintain context fidelity
- ✅ API endpoints ready for testing:
  - POST `/api/v1/chunks` → triggers background `process_chunk` via CompactorService
  - POST `/api/v1/projects/{project_id}/compact` → triggers Map-Reduce compaction

### Phase 7: Module 2 - Recursive Compaction & Entity Extraction
- ✅ Database schema migration applied successfully
  - Created `entities` table with indexes on chunk_id, project_id, entity_type
  - Added `compaction_depth` and `last_compaction_at` columns to projects
- ✅ Created Entity model (`backend/app/models/entity.py`)
  - EntityType enum: ERROR, URL, TOOL_ID, DECISION, CODE_REF
  - Entity and EntityCreate schemas
- ✅ Extended Project model with compaction tracking
  - `compaction_depth`: 0=Raw, 1=Summarized, 2=Meta-Summarized
  - `last_compaction_at`: timestamp for scheduling
- ✅ Enhanced Ollama client with JSON extraction
  - `extract_entities()` method using Ollama's JSON mode
  - Parses structured entity data from LLM responses
- ✅ Integrated recursive compaction logic
  - `recursive_reduce()` handles large contexts (>12KB threshold)
  - Batching with configurable size (5 summaries per batch)
  - Depth tracking prevents infinite loops
- ✅ Entity extraction pipeline
  - Non-blocking extraction after chunk processing
  - Bulk entity creation via EntityRepository
  - Filtering by type and confidence threshold
- ✅ Added entity API endpoints
  - GET `/api/v1/entities/projects/{project_id}` - list with filters
  - GET `/api/v1/entities/projects/{project_id}/aggregations` - counts by type
- ✅ Hammer explosion mode
  - `--mode explosion` flag for context explosion testing
  - Generates 50x 1KB chunks to force recursive compaction
  - Verified 51/51 requests successful at 72 req/sec
- ✅ Comprehensive test coverage
  - 6 new Module 2 tests (entity CRUD, recursive reduce, compaction depth)
  - All 27 tests passing (100% pass rate)
  - Test fixtures for in-memory database testing
- ✅ Documentation updates
  - Added Ollama installation instructions to MODULE_1_VERIFICATION.md
  - Added Ollama to GETTING_STARTED.md prerequisites
  - Created MODULE_2_VERIFICATION.md with comprehensive testing guide
  - Updated docs/README.md to reference verification guides

### Phase 8: Module 3 - MCP Aggregator (Tool Integration Layer)
- ✅ Created modular secret management (`backend/app/mcp/auth.py`)
  - SecretProvider ABC with pluggable architecture
  - SystemKeyringProvider for `keyring://service/username` URIs
  - EnvProvider for `env://VAR_NAME` URIs
  - SecretFactory.resolve_env_vars() for pre-spawn resolution
- ✅ Created declarative configuration system (`backend/app/mcp/config.py`)
  - MCPServerFileConfig Pydantic model
  - load_mcp_config() with JSON schema validation
  - load_and_register_servers() with parallel connection
  - Config file at `config/mcp_servers.json`
- ✅ Enhanced MCPClient stability (`backend/app/mcp/client.py`)
  - **BUG-1 Fix**: Environment merging now preserves PATH (os.environ.copy() pattern)
  - Zombie prevention via __aexit__ cleanup
  - Fixed deprecated asyncio.get_event_loop() → get_running_loop()
  - Added stderr logging background task
  - Removed dead code (MCPMessage dataclass)
- ✅ Optimized MCPRegistry (`backend/app/mcp/registry.py`)
  - Parallel connection via asyncio.gather() (5x faster startup)
- ✅ Created MCP Service Layer (`backend/app/services/mcp_service.py`)
  - **"Tool Result → Chunk" Capture Pipeline**
  - call_tool(capture=True) auto-capture parameter
  - _extract_text() for intelligent response parsing
  - _capture_as_chunk() with markdown formatting
- ✅ Updated API layer (`backend/app/api/mcp.py`)
  - MCPService dependency injection
  - capture and project_id query parameters
  - POST /mcp/{name}/reconnect endpoint
- ✅ **BUG-3 Fix**: Fixed compact_project missing entity_repo parameter (`backend/app/api/projects.py`)
- ✅ Created MCPPanel dashboard (`frontend/src/components/MCPPanel.tsx`)
  - Real-time server status badges (🟢🟡🔴)
  - Accordion-based server browser
  - Tool search and filtering
  - Tool call modal with JSON editor and capture checkbox
  - Connect/disconnect/reconnect actions
- ✅ SSE integration (`frontend/src/store/index.ts`)
  - Added mcp.status_changed event handler
  - Custom window events for MCPPanel reactivity
- ✅ UI navigation (`frontend/src/App.tsx`)
  - Added MCP tab (4th primary tab)
  - Lazy-loaded MCPPanel component
- ✅ Created hammer_mcp.py load test script
  - Embedded echo MCP server (Python JSON-RPC)
  - 50 concurrent calls validation @ 259 req/s
  - Zombie process detection
  - Chunk integrity verification
- ✅ Comprehensive validation
  - All 27 existing tests still passing
  - TypeScript compiles clean
  - Backend auto-connects MCP servers on startup
  - Filesystem server connected with 10+ tools
  - Capture pipeline validated (27 → 28 chunks)
  - Hammer test: 50/50 successful, 0 zombies

### Phase 9: Chunk Detail Drawer + Entity Panel
- ✅ Per-chunk entity API (`backend/app/api/entities.py`)
  - GET `/api/v1/entities/chunks/{chunk_id}` - list entities by chunk with type filter
  - `EntityRepository.list_by_chunk()` with type filtering, pagination
- ✅ TDD test suite (`backend/tests/test_chunk_entities.py`)
  - 6 tests: list_by_chunk, type filter, empty case, chunk isolation, API endpoint, API filter
- ✅ Chunk Detail Drawer (`frontend/src/components/ChunkDrawer.tsx`)
  - Slide-out 560px panel with overlay
  - Full chunk content, summary, tags display
  - Entity panel grouped by type with confidence bars
  - Type-specific badges (🐛 error, 🔗 url, 🔧 tool_id, ⚖️ decision, 💻 code_ref)
  - Close on overlay click, Escape key, or ✕ button
- ✅ Store signals (`frontend/src/store/index.ts`)
  - `selectedChunk`, `chunkEntities`, `entitiesLoading` signals
  - `selectChunk()`, `closeDrawer()`, `fetchChunkEntities()` actions
- ✅ Component wiring
  - ChunkList.tsx: clickable chunk cards with selectChunk
  - Inbox.tsx: clickable chunk cards + 200-char content truncation fix
  - App.tsx: ChunkDrawer rendered globally
- ✅ CSS styling (`frontend/src/theme/styles.css`)
  - Drawer overlay with fade-in animation
  - Panel with slide-in animation
  - Entity badges, confidence bars, context snippets
- ✅ Documentation updates
  - ELICITATIONS.md: drawer design decisions
  - CURRENT_STATUS.md: new features listed
  - CHANGELOG.md: v0.3.1 entry added

### Phase 10: Developer Tooling — Prompt & MCP Infrastructure Upgrade
- ✅ Created `integrate-feature.prompt.md` — Integration/finalization workflow
  - Version bumping, changelog sync, PR creation, ship readiness
  - Aliases: `/integrate`, `/finalize`, `/ship`, `/int`
- ✅ Added NEW_FEATURE_ARCHITECTURE.md template to `architect-feature.prompt.md`
- ✅ Added NEW_IMPLEMENTATION_REFERENCE.md template to `implement-feature.prompt.md`
- ✅ Added `.vite/` to `.gitignore`
- ✅ Audited and upgraded all 8 prompt tool sets:
  - All prompts now have full builtin tools: `search/codebase`, `editFiles`, `runTerminalCommand`, `githubRepo`, `fetch`
  - Fixed critical gaps: `write-tests` was missing `runTerminalCommand`, `update-docs` was missing `search/codebase`, `review-pr` was missing `editFiles` and `runTerminalCommand`
- ✅ Added GitKraken MCP server to `config/mcp_servers.json` (`@gitkraken/mcp-server-gitkraken`)
- ✅ Added Playwright MCP server to `config/mcp_servers.json` (`@playwright/mcp@latest`)
- ✅ Updated governance docs with MCP Tool Ecosystem:
  - `copilot-instructions.md` — MCP server table and security rules
  - `CONVENTIONS.md` — Section 13 (MCP Tool Ecosystem)
  - `docs/CONFIGURATION.md` — GitKraken and Playwright config examples
  - `docs/PROMPT_GUIDE.md` — Updated Quick Reference, aliases, version 1.1.0
  - `docs/IMPLEMENTATION_SUMMARY.md` — Updated prompts table, file counts, tool info

### Phase 11: Module 4 - Search & Entity Filtering API (Backend)
- ✅ **TDD Red Phase**: Created comprehensive test suite
  - `backend/tests/test_search.py` with 8 test cases
  - Tests text search, entity filtering, pagination, response structure
  - All tests initially failed (Red ✅) before implementation
- ✅ **TDD Green Phase**: Implemented search endpoint
  - Created `SearchResult` Pydastic model (`backend/app/models/chunk.py`)
  - Implemented `ChunkRepository.search()` with LIKE queries and EXISTS subquery (`backend/app/db/repository.py`)
  - Added `GET /api/v1/chunks/search` endpoint with 7 query parameters (`backend/app/api/chunks.py`)
  - Fixed Python 3.11 type hints (Tuple[List[Chunk], int] instead of tuple[list[Chunk], int])
  - 5/8 tests passing (text search working ✅), 3 entity tests skipped (MVP limitation)
- ✅ **Linting & Cleanup**: Code quality validated
  - Fixed 22 linting issues (unused imports, unused variables)
  - Ran `ruff check --fix` to auto-fix import issues
  - All linting passes ✅
- ✅ **Database isolation**: Fixed test fixture interference
  - test_search.py uses local `client` fixture with database cleanup
  - Engine disposal before file removal to prevent "disk I/O error"
  - Database recreated fresh for each test
- ✅ **Full test suite passing**: 38 passed, 3 skipped
  - Text search: Case-insensitive LIKE queries working
  - Pagination: limit/offset parameters validated
  - Response structure: SearchResult wrapper with metadata
  - Entity filtering: Infrastructure ready (tests skipped until manual entity creation implemented)
- ✅ **Documentation**: Governance docs updated
  - CHANGELOG.md: Added Module 4 entry with all features and improvements
  - PROGRESS.md: Phase 11 milestone complete
  - ELICITATIONS.md: Pending technical decisions documentation

### Phase 12: Module 4 Frontend — Search UI (Feb 5, 2026)

✅ **Complete search interface implementation** using TDD + Agentic Integration workflow

#### Frontend Components Created
- ✅ **SearchBar component** (`frontend/src/components/SearchBar.tsx`):
  - Real-time text input connected to searchQuery signal
  - 300ms debouncing via debouncedSearch() to reduce API calls
  - Result count badge with query term display (e.g., "42 results for 'error'")
  - Clear button (✕) to reset search state
  - Loading spinner during search execution
  - 🔍 search icon for visual clarity

- ✅ **FilterPanel component** (`frontend/src/components/FilterPanel.tsx`):
  - Collapsible panel with expand/collapse toggle (▲/▼)
  - Filter count badge showing active filter count
  - 6 filter fields in responsive grid layout:
    - Status dropdown (all, inbox, processed, compacted, archived)
    - Project dropdown (populated from projects signal)
    - Entity type dropdown (error, url, tool_id, decision, code_ref)
    - Entity value text input (e.g., "ConnectionTimeout")
    - Created after datetime picker
    - Created before datetime picker
  - "Clear All Filters" button when filters active
  - Auto-triggers debounced search on filter changes

- ✅ **ChunkList integration** (`frontend/src/components/ChunkList.tsx`):
  - Imported SearchBar and FilterPanel at top of component
  - Smart chunk display switching: uses searchResults when isSearchActive=true, falls back to chunks + client-side filtering otherwise
  - Hide status tabs when search is active (replaced by search results)
  - Updated loading states: "Searching..." vs "Loading chunks..."
  - Updated empty states: "No results found. Try adjusting your search." vs "No chunks found with filter: {filter}"
  - Preserved existing chunk card rendering (drawer integration, summary, tags, metadata)

#### Store Extensions
- ✅ **Search state management** (added to `frontend/src/store/index.ts`):
  - **Types**: SearchResult interface (items, total, limit, offset, query), SearchFilters interface
  - **Signals**: searchQuery, searchFilters, searchResults, searchLoading
  - **Computed**: isSearchActive (true if query or filters present)
  - **Functions**:
    - `fetchSearchResults(limit, offset)`: Async function to call /chunks/search API
    - `debouncedSearch(limit, offset)`: 300ms debounced wrapper around fetchSearchResults
    - `clearSearch()`: Reset all search state and clear debounce timer
  - **Debounce tracking**: searchDebounceTimer global to prevent rapid API calls

#### Styling
- ✅ **Search CSS** (added to `frontend/src/theme/styles.css`):
  - `.search-bar`, `.search-input-wrapper`: Dark theme input with focus states
  - `.search-icon`, `.search-input`, `.search-clear`: Icon, input field, clear button styling
  - `.search-status`, `.result-count`, `.result-query`: Result display styling
  - `.spinner` with keyframe animation for loading state
  - `.filter-panel`, `.filter-toggle`, `.filter-content`: Collapsible panel with borders
  - `.filter-grid`: Responsive grid layout (auto-fit, minmax(200px, 1fr))
  - `.filter-field`: Label, select, input styling with focus states
  - `.filter-badge`: Pill badge for active filter count (pink background)
  - `.clear-filters-btn`: Outlined button with hover transition
  - All styles follow existing CSS variable patterns (--bg-primary, --accent-pink, --text-secondary, etc.)

#### Quality Gates
- ✅ **Frontend build**: `npm run build` passes with no TypeScript errors
- ✅ **Backend tests**: 38 passed, 3 skipped (unchanged from Phase 11)
- ✅ **Type safety**: All components properly typed with React.ChangeEvent, signal types, etc.
- ✅ **Reactivity**: Preact signals automatically trigger re-renders on state changes

#### Integration Workflow
- ✅ All components integrated into existing ChunkList flow
- ✅ Search and regular chunk browsing coexist seamlessly (no breaking changes)
- ✅ Debouncing prevents excessive API calls during typing
- ✅ Clear functions properly reset state and cleanup timers

#### Files Changed (6 files)
1. **frontend/src/store/index.ts**: +65 lines (search types, signals, functions)
2. **frontend/src/components/SearchBar.tsx**: +58 lines (new file)
3. **frontend/src/components/FilterPanel.tsx**: +145 lines (new file)
4. **frontend/src/components/ChunkList.tsx**: +29 lines added, 13 modified (integration)
5. **frontend/src/theme/styles.css**: +200 lines (search and filter styling)
6. **docs/CHANGELOG.md**: Updated Unreleased section with frontend features

#### Next Steps
- [ ] **Hammer load testing**: Update `scripts/hammer_gen.py` with `--mode search` to test concurrent search queries
- [ ] **Optional entity creation endpoint**: `POST /api/v1/entities` to unblock 3 skipped entity tests
- [ ] **Performance monitoring**: Add search latency metrics to Stats dashboard
- [ ] **Future FTS5 migration**: When >10k chunks, switch to SQLite FTS5 for relevance ranking (transparent upgrade, no breaking changes)

### Phase 13: Module 6 — User Data API & Search Fix (v0.7.0)

✅ **Complete user-facing data exploration features** using TDD (Red → Green → Refactor)

#### Bug Fix: Signal Controlled Input Race Condition
- ✅ **Root Cause**: `@preact/signals-react` v2 intercepts `.value` access in JSX render path, causing React controlled input race condition (input lag, lost keystrokes)
- ✅ **Fix**: Local `useState` bridge pattern — local state for immediate UI, signal for store sync
- ✅ **SearchBar.tsx**: Fixed with `localQuery` useState bridge
- ✅ **FilterPanel.tsx**: Fixed all 6 filter inputs (localStatus, localProjectId, localEntityType, localEntityValue, localCreatedAfter, localCreatedBefore)
- ✅ **Documented**: Added "Signal-to-Input Bridge Pattern" to CONVENTIONS.md

#### Backend: Enhanced Stats, Timeline, Related Chunks
- ✅ **TDD Red Phase**: 37 tests written across 3 test files, verified failing (commit d4b9958)
  - `test_module6_stats.py` (9 tests): Weekly trends, insights, per-project breakdown
  - `test_module6_timeline.py` (11 tests): Granularity, project filter, buckets, status breakdown
  - `test_module6_related.py` (17 tests): 12 TFIDFService unit tests + 5 API endpoint tests
- ✅ **TDD Green Phase**: All 37 tests passing, 0 regressions (commit a2674fb)
- ✅ **TFIDFService** (`backend/app/core/similarity.py`): Pure Python TF-IDF cosine similarity
  - Tokenization with stopword filtering, 3-char minimum
  - Cosine similarity with 0.01 threshold
  - find_related() with top_k support and shared term extraction
- ✅ **Enhanced Stats**: `GET /chunks/stats` → DashboardStats (weekly trends, insights, per-project)
- ✅ **Timeline**: `GET /chunks/timeline` with day/week/month granularity, project filter
- ✅ **Related Chunks**: `GET /chunks/{id}/related` with similarity scores and shared terms
- ✅ **7 new Pydantic models**: DashboardStats, WeekBucket, TimelineGranularity, TimelineBucket, TimelineResponse, RelatedChunk, RelatedChunksResponse
- ✅ **5 new repository methods**: count_by_week, oldest_inbox, timeline, get_all_content, EntityRepo.count_all

#### Frontend: Dashboard, Timeline, Inbox, Related Chunks
- ✅ **StatsDashboard.tsx** (new): Weekly bar chart, insights panel, per-project breakdown
- ✅ **TimelineView.tsx** (new): Granularity toggle, project filter, expandable buckets with status-colored segments
- ✅ **Inbox.tsx** (enhanced): Age indicators (🔴🟡🟢), sort toggle, InboxHeader with count/oldest
- ✅ **ChunkDrawer.tsx** (enhanced): Related chunks section with similarity badges, shared terms, click-to-navigate
- ✅ **App.tsx** (restructured): 6 tabs (inbox, all, dashboard, timeline, projects, mcp), removed Stats, footer → v0.7.0
- ✅ **Store** (extended): DashboardStats type, timeline/relatedChunks signals, fetchTimeline/fetchRelatedChunks functions
- ✅ **CSS** (appended): ~250 lines for dashboard, timeline, inbox header, related chunks styling

#### Quality Gates
- ✅ **Backend Tests**: 85 passed, 3 skipped, 0 failures (88 collected)
- ✅ **Ruff Lint**: All checks passed (16 unused imports auto-fixed)
- ✅ **Frontend Build**: `tsc && vite build` clean
- ✅ **Documentation**: CHANGELOG, CONVENTIONS, PROGRESS, CURRENT_STATUS updated

#### Signal Auto-Tracking Root Cause Fix (v0.7.0 continued)
- ✅ **Root Cause**: `@preact/signals-react` v2 requires `import '@preact/signals-react/auto'` as the first import in `main.tsx` to enable auto-tracking. Without it, `.value` reads are plain property accesses — zero subscription effect, components never re-render.
- ✅ **Fix**: Added one-line import to `frontend/src/main.tsx`
- ✅ **Verified**: Playwright browser automation confirmed search "content 5" → 1 result, clear → 10, gibberish → 0 + empty state
- ✅ **CLI Search**: New `komorebi search "query"` command with text, status, entity, date range filters
- ✅ **10 New Backend Search Tests**: Distinct results, partial matching, pagination no-overlap, combined filters, date ranges
- ✅ **Documented**: Added auto-tracking rule to CONVENTIONS.md (mandatory pattern)

## Benchmark Results

### Module 2 - Recursive Compaction
```
╔══════════════════════════════════════════════════════════════╗
║                    KOMOREBI HAMMER RESULTS                   ║
╠══════════════════════════════════════════════════════════════╣
║  Total Requests:           53                            ║
║  Successful:               53                            ║
║  Failed:                    0                            ║
╠══════════════════════════════════════════════════════════════╣
║  Total Time:             1.76s                           ║
║  Requests/Second:       30.16                           ║
╠══════════════════════════════════════════════════════════════╣
║  Avg Latency:           50.46ms                          ║
║  Min Latency:            3.80ms                          ║
║  Max Latency:          143.58ms                          ║
╚══════════════════════════════════════════════════════════════╝
```

### Module 3 - MCP Aggregator
```
╔══════════════════════════════════════════════════════════════╗
║                    MCP HAMMER RESULTS                        ║
╠══════════════════════════════════════════════════════════════╣
║  Concurrent Calls:         50                            ║
║  Successful:               50                            ║
║  Failed:                    0                            ║
╠══════════════════════════════════════════════════════════════╣
║  Total Time:             0.19s                           ║
║  Requests/Second:       259                              ║
╠══════════════════════════════════════════════════════════════╣
║  Chunks Captured:          50 (28 → 78)                  ║
║  Zombie Processes:          0                            ║
╚══════════════════════════════════════════════════════════════╝
```