# Changelog

All notable changes to Komorebi will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Comprehensive documentation suite
- Playwright UI testing framework
- Human testing procedures (HT-1 through HT-12)

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
