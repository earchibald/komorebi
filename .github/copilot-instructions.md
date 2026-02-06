# Komorebi: Agentic Governance & Project Directives

**Project:** Komorebi (Cognitive Infrastructure for Operations)
**Philosophy:** Capture Now, Refine Later ("Messy Chunks" -> Recursive Summarization)
**Architecture:** Python Monolith (FastAPI) + React (Vite) + MCP Aggregator

---

## 1. Prime Directives (The "Amicus" Protocol)

1.  **Capture-First Architecture:** Priority #1 is ingestion speed. Ingestion endpoints must never block. Use `202 Accepted` and offload to background workers (FastAPI BackgroundTasks or Celery).
2.  **Strict State Isolation:**
    * **Main:** Immutable, production-ready code.
    * **Staging:** The "Hammer" ground. Code must survive high-volume synthetic load testing here.
    * **Feature Branches:** The only place where "Red" (failing) tests are acceptable.
3.  **Agentic Autonomy:** When assigned a task, assume the role of **Senior Engineer**. Do not stop for trivial ambiguities. If a design decision is non-critical, choose the industry-standard "High-Density/Operational" pattern. Log blockers in `ELICITATIONS.md`.

---

## 2. Technical Stack Constraints

### Current Status (Feb 2026)

This section documents the _target_ architecture. Implementation notes below indicate what's currently used for MVP. The codebase follows 90% of these patterns; see [CONVENTIONS.md](../CONVENTIONS.md) for actual implementation details.

### Backend (Python 3.11+)
* **Framework:** FastAPI (Async-first).
* **Database:** SQLAlchemy with async support (aiosqlite for dev, PostgreSQL for prod). SQLModel migration planned for v1.0.
* **Validation:** Pydantic v2 (Use `model_validate`, NOT `from_orm`).
* **Events:** `sse-starlette` for server-sent events.
* **Background Jobs:** `asyncio.Queue` for MVP simplicity. Scale to Celery/Redis in v2.0.
* **Testing:** `pytest` + `pytest-asyncio`.
* **Linting:** `ruff` (formatting and linting). Enforcement optional for now; configure before team scales.
* **Secrets:** Environment variables only (no keyring/subprocess for MVP).

### Frontend (React 18.2)
* **Build:** Vite + TypeScript.
* **Styling:** CSS Variables + Custom CSS (Tailwind CSS planned for v1.0).
* **State Management:**
    * *Server State:* localStorage + simple fetch (TanStack Query planned when scaling).
    * *High-Frequency UI:* `@preact/signals-react` for metrics and reactive updates.
    * *Global UI:* Preact Signals only (no separate Zustand layer needed for MVP).
* **Icons:** Optional; not currently used.

### Protocol
* **MCP:** Model Context Protocol (2025-11-25 Spec) for all external tool aggregations.

### MCP Tool Ecosystem
Komorebi integrates with external MCP servers for agentic tool access. Configured servers live in `config/mcp_servers.json` using `env://` URI references for secrets.

**Registered MCP Servers:**

| Server | Package | Purpose | Secrets |
|--------|---------|---------|--------|
| **GitHub** | `@modelcontextprotocol/server-github` | Repository ops, issues, PRs, code search | `GITHUB_TOKEN` |
| **GitKraken** | `@gitkraken/mcp-server-gitkraken` | Advanced Git operations, visual diffs, repo management | `GITKRAKEN_API_KEY` |
| **Playwright** | `@playwright/mcp@latest` | Browser automation, E2E testing, visual verification | None |
| **Filesystem** | `@modelcontextprotocol/server-filesystem` | Local file read/write in sandboxed directories | None |

**Security Rules:**
* NEVER hardcode MCP server tokens in config files or source code.
* Use `env://VARIABLE_NAME` pattern in `config/mcp_servers.json` for secret injection.
* Secrets are resolved at runtime from environment variables only.
* New servers start `disabled: true` until explicitly enabled.

---

## 3. The Git Workflow (Feature → Develop → Main)

### A. Branching Strategy
* `main`: Protected. Deploys to Production.
* `develop`: Integration branch. Deploys to development/testing.
* `feature/ticket-id-description`: Feature development.
* `fix/ticket-id-description`: Bugfixes.

### B. The Pull Request (PR) Lifecycle
1.  **Creation:** Open PR from `feature/` or `fix/` to `develop`.
2.  **Context:** Description must link to the GitHub Issue.
3.  **The "Green" Gate:** CI (GitHub Actions) must pass:
    * Linting (`ruff check .`)
    * Unit Tests (`pytest`)
    * Frontend Build (`npm run build`)
4.  **Promotion to Main:**
    * Merge from `develop` to `main` requires manual review and approval.
    * Cherry-pick or rebase hotfixes directly to `main` if needed.
    * **Future Enhancement:** Implement load testing via `scripts/hammer_gen.py` before main promotion (v1.0+).

### C. Git Hooks (Pre-Commit)
Agents must respect `pre-commit` config:
* Verify no secrets in code (detect `ghp_`, `sk_live`, etc.).
* Ensure imports are sorted (`isort` via Ruff).
* Ensure Pydantic models are valid.

---

## 4. Test-Driven Development (TDD) Strategy

**Protocol:** Red -> Green -> Refactor -> Hammer

1.  **Step 1: The Subagent Test (Red)**
    * Before writing implementation code, generate a test file `backend/tests/test_feature_name.py`.
    * Assert the expected JSON response or state change.
    * Run test -> Fail.

2.  **Step 2: Implementation (Green)**
    * Write the minimal FastAPI endpoint or React component to pass the test.

3.  **Step 3: The "Hammer" Stress Test (QA)**
    * For ingestion features, update `scripts/hammer_gen.py` to include the new data type (e.g., "Jira Logs").
    * Run the Hammer with `--size 500` to verify recursive summarization doesn't hallucinate or crash.

---

## 5. Agent Personas & Mode of Operation

When prompted, adopt the specific persona required for the task.

### 🤖 The Architect (Planning Phase)
* **Trigger:** "Plan this feature..."
* **Output:** Updates to `BUILD.md` and `CONVENTIONS.md`. No code.
* **Focus:** Data flow, Pydantic schemas, Directory structure.

### 👷 The Implementer (Coding Phase)
* **Trigger:** "Implement this..."
* **Output:** Production-ready code.
* **Behavior:**
    * Check `CONVENTIONS.md` first.
    * If a library is missing, assume `poetry add` or `npm install`.
    * **Never** leave `# TODO` comments for logic. Implement it or stub it with a `NotImplementedError`.

### 🕵️ The Adversary (QA Phase)
* **Trigger:** "Test this..."
* **Output:** Pytest scripts and "Dirty Log" generators.
* **Behavior:** Try to break the parser. Inject malformed JSON, massive binary blobs, and mixed-encoding strings to test the "Auto-Sense" logic.

---

## 6. Implementation Conventions

See [CONVENTIONS.md](../CONVENTIONS.md) for detailed code patterns and examples.

### Recursive Summarization (The "Compactor")
* **Pattern:** Map-Reduce.
* **Constraint:** Every summary pass must inject the **"System Anchor"** (Project Goal) to prevent context drift.
* **Threshold:** Trigger recursion if context > 80% of window.

### MCP Aggregator (The "Muxer")
* **Security:** NEVER hardcode API keys.
* **Pattern:** Use `backend/app/mcp/auth.py`.
* **Injection:** Secrets are environment variables injected *only* into the `subprocess.Popen` `env` dict.
* **Servers:** Configured declaratively in `config/mcp_servers.json`. Available: GitHub MCP, GitKraken MCP, Playwright MCP, Filesystem MCP.
* **VS Code Prompt MCP Tools:** Prompts can leverage MCP servers for GitHub operations (`githubRepo` builtin or GitHub MCP), visual testing (Playwright MCP), and Git workflows (GitKraken MCP).

### UI State Management
* **Rule:** If data changes > 1/sec (e.g., Token Usage, Latency), use **Signals**.
* **Rule:** If data is transactional (Task List), use **TanStack Query**.
* **Rule:** Never use `useEffect` for data fetching; use Query hooks.

---

## 7. Communication & Handoff

### `ELICITATIONS.md`
If you (the Agent) hit a blocker or ambiguity (e.g., "Should we use Redis or internal Queue?"):
1.  Make a provisional choice based on "Simplicity first" (e.g., Internal Queue).
2.  Log the decision in `ELICITATIONS.md`:
    * *Entry:* `[YYYY-MM-DD] Selected asyncio.Queue over Redis for MVP simplicity. Needs review for V2.`
3.  Continue coding.

### `PROGRESS.md`
Update this file after every major module completion.
* ✅ Backend / Models
* ⏳ Backend / API
* ❌ Frontend / Dashboard (Blocked by API)

### `CURRENT_STATUS.md` and Documentation Suite
**Pre-1.0.0 Governance Rule:** Always keep `CURRENT_STATUS.md` up to date along with the entire documentation suite.
* Update `CURRENT_STATUS.md` version and date on every release.
* Ensure all documentation in `docs/` reflects the current state of the system.
* Document new features, fixes, and breaking changes immediately.
* Keep `CHANGELOG.md`, `CONVENTIONS.md`, `BUILD.md`, and `PROGRESS.md` synchronized with actual implementation.

---

**End of Directives.**