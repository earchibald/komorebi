# Archived: Context Oracle Feature Request

**Archived:** 2026-02-06
**Original Source:** User-provided feature request (inline, no standalone file)
**Generated Output:** [CONTEXT_ORACLE_ARCHITECTURE.md](../../CONTEXT_ORACLE_ARCHITECTURE.md)

---

## Original Feature Request

**Goal:** A secure, bidirectional context engine that monitors your shell, filesystem, and IDE, serving as the "Source of Truth" for both humans and AI agents.

### 1. Komorebi as "The Context Oracle" (MCP Server)
- Komorebi exposes an MCP endpoint (stdio or SSE)
- Coding agents connect and call tools: `get_active_trace()`, `search_context(query)`, `read_file_metadata(path)`, `get_related_decisions()`

### 2. Filesystem Awareness (`k watch`)
- `k watch ./config --recursive` starts a background daemon using watchdog
- Tracks path, size, hash (sha256 of first 8kb), mime_type, crud_op
- Inserts lightweight "FileEvent" chunks into the active Trace

### 3. Advanced Execution Profiles (profiles.yaml)
- YAML-defined profiles with inheritance, env vars, blocking policies, secret redaction
- `k exec --profile=production` runs commands with profile constraints

### 4. Trace Lifecycle & Renaming
- `k switch dns-issue` with interactive create/fuzzy-match/AI-suggestion
- `k trace rename "New Name"` for renaming active or specific traces

### 5. LLM Governance & Cost Dashboard
- Token counting and cost tracking per model
- Budget caps with auto-downgrade from cloud to local LLM
- Frontend billing dashboard at /settings/billing

### 6. Deep Security Evaluation
- RedactionService: regex scrubbers before data leaves to cloud LLMs
- Environment variable tracking on trace switch
- Profile env var blacklist (LD_PRELOAD, etc.)

### 7. Implementation Checklist (3 phases)
- Phase 1: Security & Profiles
- Phase 2: Context Oracle (MCP Server)
- Phase 3: Filesystem Watcher & Cost Governance
