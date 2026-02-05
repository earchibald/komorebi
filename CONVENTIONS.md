# Komorebi Development Conventions

## 1. Python & FastAPI Patterns
- **Pydantic v2 Only:** Use `model_validate` instead of `from_orm`.
- **Dependency Injection:** Use `Annotated[T, Depends(get_db)]` for all FastAPI dependencies.
- **Async-First:** All DB operations and LLM calls must be `async`.
- **Error Handling:** Use custom exceptions that map to specific FastAPI `HTTPException` codes.

## 2. React & State Patterns
- **Signals for Performance:** Use `@preact/signals-react` for high-frequency updates (metrics).
- **Functional Components:** No Class components. Use custom hooks for all logic.
- **Tailwind Strategy:** Use a "Glassmorphism" palette (e.g., `bg-white/10 backdrop-blur-md`).

## 3. Operations & Logging
- **Structured Logging:** Use `structlog` for JSON-formatted logs.
- **Trace IDs:** Every ingestion request must carry a `trace_id` for debugging.
