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

### Backend (Python 3.12+)
* **Framework:** FastAPI (Async-first).
* **ORM:** SQLModel (SQLite for local, PostgreSQL for prod).
* **Validation:** Pydantic v2 (Use `model_validate`, NOT `from_orm`).
* **Events:** `sse-starlette` for server-sent events.
* **Testing:** `pytest` + `pytest-asyncio`.
* **Linting:** `ruff` (formatting and linting).
* **Secrets:** `keyring` (Local) / `subprocess` injection (MCP).

### Frontend (React 19)
* **Build:** Vite + TypeScript.
* **Styling:** Tailwind CSS (Glassmorphism palette: `bg-white/10`, `backdrop-blur-md`).
* **State:** * *Server State:* TanStack Query (React Query).
    * *High-Frequency UI:* `@preact/signals-react` (for metrics/latency graphs).
    * *Global UI:* Zustand.
* **Icons:** `lucide-react`.

### Protocol
* **MCP:** Model Context Protocol (2025-11-25 Spec) for all external tool aggregations.

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

### Recursive Summarization (The "Compactor")
* **Pattern:** Map-Reduce.
* **Constraint:** Every summary pass must inject the **"System Anchor"** (Project Goal) to prevent context drift.
* **Threshold:** Trigger recursion if context > 80% of window.

### MCP Aggregator (The "Muxer")
* **Security:** NEVER hardcode API keys.
* **Pattern:** Use `backend/app/mcp/auth.py`.
* **Injection:** Secrets are environment variables injected *only* into the `subprocess.Popen` `env` dict.

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

---

**End of Directives.**