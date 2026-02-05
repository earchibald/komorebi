# Komorebi Build Blueprint (v0.1.0-alpha)

## 0. MISSION DIRECTIVE FOR AGENT
You are an autonomous Senior Engineer. Implement the following architecture in a single, exhaustive execution. 
- **DO NOT** stop to ask questions.
- **DO NOT** leave "TODO" comments; implement logic based on the best industry standard for the context.
- **LOG** all assumptions or deferred non-critical issues in `ELICITATIONS.md`.
- **PRIORITIZE** a working end-to-end "Hammer" test.

## 1. Project Stack
- **Backend:** Python 3.12, FastAPI, SQLModel (SQLite), Pydantic v2, `prometheus-client`.
- **Frontend:** React 19, Vite, Tailwind CSS, `@preact/signals-react`, `lucide-react`.
- **CLI:** Click, `requests`, `rich`, `shtab`.

## 2. Core Architecture Requirements

### A. Context Compaction (Recursive Summarization)
- Implement `backend/app/core/compactor.py`. 
- Logic: If input > 10KB, trigger recursive summarization using a local LLM (Ollama default). 
- Preserve "ROOT_TASK" and "GOAL" roles in every pass.

### B. Modular Auth Provider
- Implement `backend/app/mcp/auth.py` using an Abstract Base Class.
- Default to `keyring` (System Keychain).
- Provide stubs for `1Password` and `SOPS`.

### C. The Hammer Benchmarking
- Implement a `/admin/hammer` endpoint to ingest high-volume synthetic logs.
- Benchmarking must track "Tokenization Efficiency" and "Time to First Token" (TTFT).

## 3. Directory Initialization
Initialize the standard structure defined in previous sessions. Ensure `XDG_BASE_DIR` logic is respected for all local storage.

## 4. Execution Order
1. Define Pydantic Models (`backend/app/models/`).
2. Implement SQLite/SQLModel Database Layer.
3. Build the FastAPI service with SSE (Server-Sent Events) support.
4. Implement the CLI with "Auto-Sense" pipe detection.
5. Scaffold the React dashboard with Signal-based state management.
