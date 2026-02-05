# Changelog

All notable changes to Komorebi will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Module 3: Advanced MCP aggregation
- Frontend dashboard enhancements  
- Production deployment configuration
- Advanced testing automation

---

## [0.2.2] - 2026-02-05

### Added
- **Documentation Governance Rule** - Pre-1.0.0 requirement to keep CURRENT_STATUS.md and entire documentation suite up to date
- Added documentation maintenance guidelines to .github/copilot-instructions.md

### Changed
- Updated governance to emphasize documentation synchronization with implementation

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
