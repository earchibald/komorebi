# Changelog

All notable changes to Komorebi will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Module 5: Implementation — Docker deployment, bulk operations feature
- Performance optimization baseline

---

## [0.7.0] - 2026-02-08

### Added
- **Module 6: User Data API & Search Fix** — Full-stack user-facing data exploration features
  - **Enhanced Dashboard Stats** — `GET /chunks/stats` now returns `DashboardStats` with weekly activity trends (`by_week`), actionable insights (oldest inbox age, most active project, entity count), and per-project breakdown (`by_project`)
  - **Timeline View** — New `GET /chunks/timeline` endpoint with day/week/month granularity, project filtering, and status breakdown per time bucket
  - **Related Chunks** — New `GET /chunks/{id}/related` endpoint using TF-IDF cosine similarity to discover semantically related chunks with similarity scores and shared terms
  - **TF-IDF Service** — Pure Python `TFIDFService` class (`backend/app/core/similarity.py`) with tokenization, stopword filtering, cosine similarity — zero external dependencies
  - **StatsDashboard component** — Weekly bar chart, insights panel, per-project breakdown (replaces simple Stats component)
  - **TimelineView component** — Granularity toggle, project filter, expandable time buckets with status-colored segments
  - **Inbox Enhancements** — Age indicators (🔴>7d, 🟡2-7d, 🟢<2d), sort toggle (Newest/Oldest), InboxHeader with count and oldest age
  - **Related Chunks in Drawer** — Similarity badges, shared terms display, click-to-navigate between related chunks
  - **Tab Restructure** — Expanded from 4 tabs to 6: Inbox, All Chunks, Dashboard, Timeline, Projects, MCP Tools

### Fixed
- **Search Input Bug** — Fixed `@preact/signals-react` v2 race condition with controlled inputs; signal `.value` access intercepted in JSX render path caused input lag/loss. Fix: local `useState` bridge pattern in `SearchBar.tsx` and `FilterPanel.tsx` (6 filter fields)
- **Search results never display** — Signal `.value` reads inside `useMemo` callbacks in `ChunkList.tsx` did not create proper subscriptions; component never re-rendered when `searchResults` signal changed. Fix: read all signal values in render body, pass as plain deps.
- **Clearing filters leaves no results** — Same root cause as above; `clearSearch()` correctly reset signals but `useMemo` never re-evaluated.
- **Status filter hides tab buttons** — `FilterPanel` status dropdown set `isSearchActive=true`, hiding ChunkList's 5 status tab buttons. Fix: removed duplicate status dropdown from FilterPanel; ChunkList tabs now always visible and apply client-side on top of search results.
- **Enter key does nothing in search** — Added `onKeyDown` handler and `triggerImmediateSearch()` store function for instant search on Enter (cancels debounce timer).
- **Signal auto-tracking never installed** — `@preact/signals-react` v2 requires `import '@preact/signals-react/auto'` in `main.tsx` to enable signal reactivity in React components. Without this one-line import, `.value` reads had no subscription effect and components never re-rendered when signals changed. This was the true root cause of all search/filter UI failures.

### Added (v0.7.0 continued)
- **CLI `search` command** — `komorebi search "query"` with text, status, entity, date range filters, verbose/JSON output. Diagnostic tool for verifying search end-to-end.
- **10 new backend search tests** — Covers distinct results, partial matching, pagination no-overlap, combined filters, date ranges, response shape validation.

### Technical
- 7 new Pydantic models: `DashboardStats`, `WeekBucket`, `TimelineGranularity`, `TimelineBucket`, `TimelineResponse`, `RelatedChunk`, `RelatedChunksResponse`
- 5 new repository methods: `count_by_week()`, `oldest_inbox()`, `timeline()`, `get_all_content()`, `EntityRepository.count_all()`
- 37 new tests (9 stats, 11 timeline, 17 related/TF-IDF) — all passing
- Full regression: 75 passed, 3 skipped, 0 failures
- Frontend build clean (tsc + vite)
- Ruff lint clean (16 auto-fixed unused imports)

---

## [0.6.0] - 2026-02-07

### Added
- **FEATURE_MODULE5_v0.6.0_DESIGN.md** — Comprehensive architecture for Production Deployment + Bulk Operations
  - Single-container Docker deployment (Uvicorn + StaticFiles)
  - Module 5: Bulk tag/archive/delete operations with audit log and undo (30-min window)
  - SQLite persistence on Docker volumes
  - Railway.app deployment target (PaaS recommended path)
- **BUILD.md** — Populated from empty blueprint, now includes quick start, project structure, module inventory, configuration reference
- **Documentation** — 5 trade-off analyses with reversibility assessments, implementation sprints (20-28 hours), quality gates

### Documentation
- Architecture design complete for v0.6.0 feature set (deployment + bulk ops)
- Implementation plan: 2 sprints with detailed task breakdown
- Known constraints documented (SQLite JSON limitations, concurrent writes, undo window per-action)
- Blockers identified (Railway persistent volume testing, Ollama connectivity from Docker, SSE reconnection)

---

## [0.5.0] - 2026-02-07

### Added
- **Module 4 Frontend: Search UI** — Complete search interface with SearchBar, FilterPanel, and ChunkList integration
- **SearchBar component** — Real-time text search with 300ms debouncing, result count display, and clear button
- **FilterPanel component** — Collapsible advanced filters panel with 6 filter fields (status, project, entity type/value, date range)
- **Search store** — Preact signals for search state management (searchQuery, searchFilters, searchResults, isSearchActive)
- **Debounced search** — Auto-triggers search 300ms after user stops typing to reduce API calls
- **Seamless integration** — ChunkList automatically switches between regular chunks and search results based on `isSearchActive`
- **Search result count** — Badge showing total results and query term when search is active
- **Filter count badge** — Visual indicator showing number of active filters on FilterPanel toggle
- **Search CSS styling** — Responsive dark-theme styles for search bar, filters, and status indicators

### Developer Experience
- **Prompt System Enhancements** — All custom prompts now have full tool access (agent, edit, execute, read, search, todo, vscode, web, fetch, githubRepo)
- **integrate-feature.prompt.md** — New prompt for feature integration workflow (validation, versioning, git commit, PR creation)
- **Handoff template** — implement-feature.prompt.md now includes IMPLEMENTATION_HANDOFF.md template for documentation
- **MCP Server Configuration** — Added GitKraken and Playwright MCP servers to config (disabled by default)
- **Git Commit Hygiene** — Added mandatory governance rules in copilot-instructions.md for frequent commits and clean tree enforcement

### Technical Improvements
- **Backend cleanup** — Removed 9 unused imports across backend codebase (linting fixes)
- **Documentation updates** — CONVENTIONS.md now includes MCP Tool Ecosystem section with security rules
- **Gitignore** — Added frontend/.vite/ cache directory

---

## [0.4.0] - 2026-02-05

### Added
- **Module 4: Search & Entity Filtering API** — Server-side search endpoint with text queries, entity filters, date ranges, and pagination
- **GET /api/v1/chunks/search** — Unified search endpoint with 7 query parameters (q, status, project_id, entity_type, entity_value, created_after, created_before)
- **SearchResult model** — Pydantic wrapper containing search results with pagination metadata (items, total, limit, offset, query)
- **ChunkRepository.search()** — Repository method using LIKE queries for text search and EXISTS subquery for entity filtering
- **Text Search** — Case-insensitive partial matching in chunk content using SQLite LIKE operator
- **Entity Filtering Infrastructure** — EXISTS subquery pattern ready for filtering by entity type/value (tests skipped pending manual entity creation)
- **Date Range Filters** — Support for `created_after` and `created_before` timestamp filtering
- **Search Test Suite** — 8 tests (5 active, 3 skipped) covering text search, pagination, response structure, and entity filtering

### Technical Improvements
- **Database cleanup fixture** — Search tests properly dispose engine connections before database file removal
- **Module-level test fixtures** — test_search.py uses local fixture for database isolation
- **Type hint fixes** — Python 3.11 compatibility using `Tuple[List[Chunk], int]` from typing module
- **Linting cleanup** — Fixed 22 unused import and variable issues

---

## [0.3.1] - 2026-02-05

### Added
- **Chunk Detail Drawer** — Click any chunk card to open a slide-out panel showing full content, summary, tags, and extracted entities
- **Per-Chunk Entity API** — `GET /entities/chunks/{chunk_id}` endpoint for fetching entities by chunk
- **EntityRepository.list_by_chunk()** — Repository method with type filtering for chunk-level entity queries
- **Entity Panel** — Grouped entity display with type badges, confidence bars, and context snippets
- **Inbox content truncation** — Inbox chunk cards now truncate to 200 chars (parity with All Chunks tab)

---

## [0.3.0] - 2026-02-05

### Added

#### Module 3 - MCP Aggregator (Tool Integration Layer)
- **Modular Secret Management** - `backend/app/mcp/auth.py` with pluggable provider architecture
  - `SecretProvider` ABC for extensible secret resolution
  - `SystemKeyringProvider` - Secure OS keychain integration (`keyring://service/username`)
  - `EnvProvider` - Environment variable resolution (`env://VAR_NAME`)
  - `SecretFactory.resolve_env_vars()` - URI-based secret injection without storing credentials
- **Declarative Server Configuration** - `backend/app/mcp/config.py` with JSON schema validation
  - `MCPServerFileConfig` - Pydantic model for server definitions
  - `MCPConfig` - Root configuration with validation rules
  - `load_mcp_config()` - File-based config loader with error handling
  - `load_and_register_servers()` - Automatic startup registration and parallel connection
- **MCP Service Layer** - `backend/app/services/mcp_service.py` with auto-capture pipeline
  - **"Tool Result → Chunk" Capture Pipeline** - Automatic persistence of MCP tool outputs
  - `call_tool(capture=True)` - Single-parameter control for result capture
  - `_extract_text()` - Intelligent text extraction from MCP responses
  - `_capture_as_chunk()` - Markdown-formatted chunk creation with metadata
  - Background chunk creation (non-blocking UI)
- **MCP Panel Dashboard** - `frontend/src/components/MCPPanel.tsx` with real-time updates
  - Server status indicators (🟢 connected, 🟡 connecting, 🔴 disconnected)
  - Accordion-based server browser with tool catalogs
  - Tool search/filter with instant highlighting
  - Tool call modal with JSON arguments editor and capture checkbox
  - Connect/disconnect/reconnect controls per server
  - Real-time SSE updates for status changes
- **Load Testing Framework** - `scripts/hammer_mcp.py` with embedded echo server
  - Validates concurrent capture pipeline (50 calls @ 259 req/s)
  - Zombie process detection and cleanup verification
  - Chunk count validation and integrity checks

### Changed
- **MCP Client Stability** - `backend/app/mcp/client.py` critical fixes
  - **BUG-1 Fix**: Environment variable merging now preserves `PATH` and system env
  - Zombie process prevention via proper `__aexit__` cleanup
  - Replaced deprecated `asyncio.get_event_loop()` with `get_running_loop()`
  - Added stderr logging background task for MCP server debugging
  - Removed dead code (`MCPMessage` dataclass unused)
- **MCP Registry Performance** - `backend/app/mcp/registry.py` optimization
  - Parallel server connection via `asyncio.gather()` (replaces sequential)
  - Significant startup time reduction for multi-server configs
- **API Layer Integration** - `backend/app/api/mcp.py` enhanced endpoints
  - `MCPService` dependency injection (replaces direct registry access)
  - `capture` and `project_id` query parameters on `/tools/{name}/call`
  - `POST /mcp/{name}/reconnect` endpoint for recovery workflows
- **BUG-3 Fix**: `backend/app/api/projects.py` - Fixed `compact_project` missing `entity_repo` parameter
- **Startup Lifecycle** - `backend/app/main.py` auto-connects MCP servers on startup
  - Loads `config/mcp_servers.json` during lifespan initialization
  - Logs connection summary (connected/total servers)
- **SSE Event Handling** - `frontend/src/store/index.ts` MCP status events
  - Added `mcp.status_changed` case in `handleSSEEvent`
  - Dispatches custom window events for MCPPanel reactivity
- **UI Navigation** - `frontend/src/App.tsx` added MCP tab
  - Fourth primary tab alongside Inbox, Projects, Stats
  - Lazy-loaded MCPPanel component

### Fixed
- Critical subprocess environment corruption (BUG-1) preventing npx-based MCP servers
- Missing entity repository injection causing compaction crashes (BUG-3)
- Asyncio deprecation warnings in MCP client
- Zombie MCP server processes accumulating over time

### Performance
- **Capture Pipeline**: 259 req/s sustained throughput (hammer test validation)
- **Parallel Connection**: 5x faster startup for multi-server configurations
- **Zero Zombie Processes**: Validated via load testing

### Security
- **Zero Secrets in Config Files**: All credentials via `keyring://` or `env://` URIs
- **Secrets Never Logged**: Auth module redacts environment variables in error messages
- **Subprocess Isolation**: MCP servers run with minimal environment variable exposure

---

## [0.2.2] - 2026-02-05

### Added
- **Documentation Governance Rule** - Pre-1.0.0 requirement to keep CURRENT_STATUS.md and entire documentation suite up to date
- Added documentation maintenance guidelines to .github/copilot-instructions.md

### Changed
- Updated governance to emphasize documentation synchronization with implementation

---

## [0.3.0] - 2026-02-06

### Added

#### VS Code Prompts & Skills System
- **7 Custom Prompts** - Workflow templates for common development tasks
  - `implement-feature` (Standard/Sonnet) - TDD-driven feature development
  - `write-tests` (Standard/Sonnet) - Comprehensive test generation
  - `debug-issue` (Premium/Opus 4.6) - Systematic debugging workflow
  - `review-pr` (Standard/Sonnet) - Security-focused PR reviews
  - `update-docs` (Economy/Haiku) - Documentation sync with governance
  - `refactor-code` (Standard/Sonnet) - Code improvement patterns
  - `architect-feature` (Premium/Opus 4.6) - Complex feature design
- **Prompt Aliases** - 15+ shortcuts for faster typing (`/impl`, `/test`, `/debug`, etc.)
- **4 Agent Skills** - Specialized workflows with progressive loading
  - `feature-implementer` (Standard) - Full-stack scaffold generator with scripts
  - `code-formatter` (Economy) - Ruff formatting and linting commands
  - `deep-debugger` (Premium) - Advanced async/race condition debugging
  - `research-agent` (Research) - Long-context analysis with Gemini 3 Pro (1M tokens)

#### Infrastructure
- **Scaffold Generator** - `generate_scaffold.py` creates complete feature boilerplate
  - Generates Pydantic schemas, repositories, API routes, tests, React components
  - Follows project conventions automatically
  - Configurable backend-only/frontend-only modes
- **Feature Validator** - `validate_feature.py` checks convention compliance
- **Telemetry System** - Usage and cost tracking with optional MCP integration
  - Local JSONL storage (`~/.komorebi/telemetry/usage.jsonl`)
  - MCP endpoint support via `KOMOREBI_MCP_TELEMETRY_ENDPOINT`
  - Report generation: usage patterns, cost analysis, time savings

#### Documentation
- **PROMPTS_AND_SKILLS_PROPOSAL.md** - 33KB comprehensive strategy document
  - Model tier analysis and cost-benefit calculations
  - Implementation roadmap and best practices
- **PROMPTS_SKILLS_AUDIT.md** - 22KB audit report with pros/cons
- **PROMPT_GUIDE.md** - Complete usage guide for all prompts and skills
- **CONTEXT_AWARENESS_ANALYSIS.md** - How skills derive information automatically
- **IMPLEMENTATION_SUMMARY.md** - Quick reference for the entire system

### Changed
- **Model Specifications** - Updated premium prompts to use Claude Opus 4.6
- **CURRENT_STATUS.md** - Version bumped to 0.3.0 with latest features
- **PROGRESS.md** - Added Phase 6: Developer Experience

### Technical Details
- All scripts use `#!/usr/bin/env python3` for proper venv support
- Prompts follow VS Code frontmatter format with correct model names
- Skills use progressive loading (metadata → SKILL.md → resources)
- F-string syntax corrected in scaffold generator
- MCP telemetry integration with graceful failure handling

---

## [0.2.2] - 2026-02-05

### Added
- **Documentation Governance Rule** - Pre-1.0.0 requirement to keep CURRENT_STATUS.md and entire documentation suite up to date
- Added documentation maintenance guidelines to .github/copilot-instructions.md

### Changed
- Updated governance to emphasize documentation synchronization with implementation

---

## [0.2.1] - 2026-02-05

### Fixed
- **Dashboard:** Chunk card content overflow — long strings (e.g., hammer explosion padding) now truncated to 200 chars with CSS word-break and 3-line clamp

---

## [0.2.0] - 2026-02-05

### Added

#### Module 1 - Ollama Integration
- **Complete Ollama LLM Integration** - Local LLM server with llama3.2 model
- **Async Ollama Client** - JSON mode support with graceful error handling
- **Entity Extraction** - LLM-powered extraction of tool_ids, decisions, code_refs
- **Cold-Start Prevention** - Model pre-warming to prevent concurrent loading failures
- **Cross-Platform Support** - Installation guides for macOS, Linux, Windows
- **MODULE_1_VERIFICATION.md** - Comprehensive installation and testing guide

#### Module 2 - Recursive Compaction & Entity Extraction  
- **Intelligent Project Compaction** - LLM-powered summarization preserving system context
- **Entity Detection** - Structured extraction from project chunks
- **Recursive Summarization** - Map-Reduce pattern with system anchor preservation
- **Background Processing** - FastAPI BackgroundTasks for non-blocking operations
- **Load Testing Framework** - explosion test achieving 67+ req/sec sustained
- **MODULE_2_VERIFICATION.md** - Performance benchmarks and validation procedures

#### Testing & Infrastructure
- **27-Test Suite** - Comprehensive tests covering all modules (100% passing)
- **Performance Validation** - Entity extraction: 16 entities from 10 chunks  
- **Load Testing Script** - test_explosion.sh with model pre-warming
- **Environment Consistency** - Virtual environment usage validation
- **Benchmark Metrics** - Sub-500ms LLM response times with pre-warming

#### Documentation & Governance
- **VERSIONING.md** - Semantic versioning governance with build tracking
- **Version Scripts** - check-version.sh, sync-versions.sh, validate-changelog.sh
- **Commit Standards** - Version tracking in commit messages
- **Release Process** - Formal procedures for development → staging → production

### Changed
- **Environment Management** - Migrated from system Python to consistent venv usage
- **test_explosion.sh** - Enhanced with model pre-warming and entity validation
- **Entity Extraction** - Improved JSON parsing with structured output validation
- **Error Handling** - Enhanced Ollama cold-start scenario management
- **Database Initialization** - Improved schema creation timing

### Fixed
- **Environment Mismatch** - Resolved system Python vs venv package conflicts
- **Ollama Cold-Start** - Fixed concurrent model loading failures via pre-warming
- **Port Conflicts** - Resolved stale uvicorn processes blocking development
- **Database Race Conditions** - Fixed schema initialization timing issues
- **LLM Response Parsing** - Improved error handling for malformed JSON

### Performance
- **Load Testing:** 67+ requests/second sustained performance
- **Entity Extraction:** 16 entities extracted from 10 chunks reliably
- **Model Latency:** Sub-500ms response times with pre-warming
- **Test Reliability:** 27/27 tests passing consistently
- **Throughput:** Background task processing without blocking ingestion

### Security
- **Environment Isolation** - Virtual environment for dependency management
- **API Key Management** - Environment variable isolation for sensitive data
- **Process Isolation** - Subprocess management for external tool integration

---

## [0.1.0] - 2024-01-15

### Added

#### Backend (FastAPI)
- **Chunk API** - Full CRUD operations for chunks
  - `POST /api/v1/chunks` - Fast capture endpoint
  - `GET /api/v1/chunks` - List with filtering
  - `GET /api/v1/chunks/inbox` - Inbox-only listing
  - `GET /api/v1/chunks/stats` - Statistics endpoint
  - `GET /api/v1/chunks/{id}` - Get single chunk
  - `PATCH /api/v1/chunks/{id}` - Update chunk
  - `DELETE /api/v1/chunks/{id}` - Delete chunk
  - `POST /api/v1/chunks/process-inbox` - Manual processing

- **Project API** - Project management
  - `POST /api/v1/projects` - Create project
  - `GET /api/v1/projects` - List projects
  - `GET /api/v1/projects/{id}` - Get project
  - `PATCH /api/v1/projects/{id}` - Update project
  - `DELETE /api/v1/projects/{id}` - Delete project
  - `POST /api/v1/projects/{id}/compact` - Trigger compaction
  - `GET /api/v1/projects/{id}/context` - Get context summary

- **MCP API** - MCP server integration
  - `GET /api/v1/mcp/servers` - List registered servers
  - `POST /api/v1/mcp/servers` - Register server
  - `POST /api/v1/mcp/servers/{id}/connect` - Connect to server
  - `POST /api/v1/mcp/servers/{id}/disconnect` - Disconnect
  - `GET /api/v1/mcp/tools` - List available tools
  - `POST /api/v1/mcp/tools/{name}/call` - Call tool
  - `POST /api/v1/mcp/connect-all` - Connect all servers
  - `POST /api/v1/mcp/disconnect-all` - Disconnect all

- **SSE API** - Real-time streaming
  - `GET /api/v1/sse/events` - Event stream
  - `GET /api/v1/sse/status` - Connection status

- **Core Services**
  - `CompactorService` - Recursive summarization
  - `EventBus` - SSE event broadcasting

- **Database Layer**
  - SQLAlchemy async ORM
  - SQLite support (default)
  - PostgreSQL support
  - Repository pattern for data access

- **Models**
  - `Chunk` - Information fragment
  - `Project` - Chunk container
  - `MCPServerConfig` - Server configuration
  - Status enums: INBOX, PROCESSED, COMPACTED, ARCHIVED

#### CLI (Typer)
- `komorebi capture <content>` - Quick capture
- `komorebi list` - List chunks
- `komorebi stats` - Show statistics
- `komorebi compact <project_id>` - Compact project
- `komorebi projects` - List projects
- `komorebi serve` - Start backend server

#### Frontend (React + TypeScript)
- Dashboard layout with tabs
- Stats component with real-time updates
- Inbox component with capture form
- ChunkList component with filtering
- ProjectList component with creation
- Preact Signals for state management
- SSE integration for live updates
- Dark theme with CSS variables

#### Testing
- pytest test suite (16 tests)
- API endpoint tests
- Model validation tests
- Benchmark script (`hammer_gen.py`)

#### Documentation
- `GETTING_STARTED.md` - Installation and usage guide
- `TEST_MANIFEST.md` - Test documentation
- `DEVELOPMENT_WORKFLOWS.md` - AI agent collaboration
- `PEDAGOGY_PLAYWRIGHT.md` - UI testing patterns
- `API_REFERENCE.md` - Complete API documentation
- `CONFIGURATION.md` - Configuration guide
- `ARCHITECTURE.md` - Technical deep dive
- `DEPLOYMENT.md` - Deployment instructions
- `CONTRIBUTING.md` - Contributor guide
- `TROUBLESHOOTING.md` - FAQ and solutions
- `SECURITY.md` - Security considerations

### Changed
- Nothing (initial release)

### Deprecated
- Nothing (initial release)

### Removed
- Nothing (initial release)

### Fixed
- Nothing (initial release)

### Security
- Input validation via Pydantic
- SQL injection protection via ORM
- CORS configuration (open by default, restrict for production)

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 0.1.0 | 2024-01-15 | Initial release |

---

## Migration Guides

### Upgrading to 0.1.0

This is the initial release. No migration required.

### Future Migrations

Migration guides will be added here when breaking changes are introduced.

---

## Release Process

1. Update version in `pyproject.toml`
2. Update this CHANGELOG
3. Create git tag: `git tag v0.1.0`
4. Push tag: `git push --tags`
5. Create GitHub release

---

## Links

- [Repository](https://github.com/earchibald/komorebi)
- [Issues](https://github.com/earchibald/komorebi/issues)
- [Documentation](./docs/)

---

*For upgrade instructions, see the Migration Guides section above.*
