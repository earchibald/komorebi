# Feature Architecture: Modular Target Delivery System

**Date:** 2026-02-05  
**Author:** Architecture Agent  
**Status:** Architecture Phase Complete  
**Next Phase:** Implementation via `/implement-feature`

---

## Overview

A schema-driven adapter system that decouples Komorebi's internal data model from external tool APIs (GitHub, Jira, Slack, etc.). The Staging Area dynamically generates UI forms based on Target schemas, and Adapters translate generic data into tool-specific arguments before MCP dispatch.

---

## Phase 1: Requirements Analysis

### User Stories

**US-1: As a user**, I want to send a bug report to GitHub Issues without manually filling GitHub-specific fields, so that I can leverage auto-populated context from Komorebi chunks.

**US-2: As a user**, I want to add Jira as a delivery target without needing frontend code changes, so that I can integrate with my team's workflow tool of choice.

**US-3: As a developer**, I want to add new targets by implementing a Python adapter only, so that I avoid maintaining parallel frontend/backend logic for each tool.

**US-4: As a user**, I want the Staging Area to show only relevant fields (e.g., no "assignees" for Slack), so that the form is not cluttered with inapplicable options.

**US-5: As an LLM agent**, I want to receive the target schema in my prompt, so that I can refine chunk content into the exact format required by the destination tool.

### Success Criteria

- [x] Adding a new target (e.g., Jira) requires ONLY creating a Python adapter—no React changes
- [x] Frontend form fields dynamically render based on backend-supplied `TargetSchema`
- [x] Adapters are pure functions (`data -> mapped_data`) with 100% unit test coverage
- [x] LLM prompts include the target schema, improving refinement accuracy
- [x] Dispatch endpoint routes to correct MCP tool via adapter's `mcp_tool_name` property
- [x] System handles 50 concurrent dispatches without race conditions (Hammer test)

### Constraints

**Tech Stack:**
- **Must use:** Python 3.11+, Pydantic v2, FastAPI (existing)
- **Cannot use:** Frontend-specific validation logic (must be schema-driven)
- **Timeline:** 8-12 hours total (Backend 6h, Frontend 3h, Testing 3h)

**Compatibility:**
- Must work with existing MCP Aggregator (`backend/app/mcp/client.py`)
- Must not break existing Staging Area UX patterns
- Must support both sync and async MCP tool calls

### Edge Cases

1. **What if a target requires OAuth but MCP server is not connected?**
   - Adapter `map_arguments` should validate server availability via MCPService
   - Return 503 with actionable error message (e.g., "GitHub MCP server offline")

2. **What if a field is required by the tool but optional in Komorebi?**
   - Adapter `validation_rules` defines required fields per target
   - Frontend enforces these at form submission time
   - Backend validates again before dispatch (defense in depth)

3. **What if user switches target mid-form (data loss)?**
   - Frontend stores draft state in localStorage under `staging_draft_{target_name}`
   - Switching targets prompts "Discard draft or Cancel?"

4. **What if adapter mapping fails (e.g., missing field)?**
   - Adapter raises `TargetMappingError` with human-readable message
   - Backend returns 400 with `{"error": "title field required for GitHub Issues"}`

5. **What if MCP tool schema changes (e.g., GitHub adds new required field)?**
   - Adapter version field (`schema_version: "1.0"`) allows backward compatibility checks
   - Migration guide in `ELICITATIONS.md` when MCP tools upgrade

---

## Phase 2: System Design

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │ StagingArea  │─────▶│ DynamicForm  │                    │
│  │  Component   │      │  Component   │                    │
│  └──────────────┘      └──────────────┘                    │
│         │ GET /api/v1/targets/schemas   │                  │
│         ▼                                ▼                  │
└─────────────────────────────────────────────────────────────┘
         │                                │
         │ POST /api/v1/dispatch          │
         ▼                                ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend                               │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   Dispatch   │─────▶│   Target     │                    │
│  │   Endpoint   │      │   Registry   │                    │
│  └──────────────┘      └──────────────┘                    │
│         │                       │                           │
│         │ resolve adapter       │                           │
│         ▼                       ▼                           │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │GitHub Adapter│      │ Jira Adapter │ ... (extensible)  │
│  └──────────────┘      └──────────────┘                    │
│         │                       │                           │
│         │ map_arguments         │                           │
│         ▼                       ▼                           │
│  ┌────────────────────────────────────┐                    │
│  │       MCP Service (Aggregator)     │                    │
│  └────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
         │
         │ call_tool(tool_name, arguments)
         ▼
┌─────────────────────────────────────────────────────────────┐
│                     External Tools                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   GitHub     │  │     Jira     │  │    Slack     │     │
│  │   MCP Server │  │  MCP Server  │  │  MCP Server  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Data Model

#### 2.1 Base Schema (Abstract)

```python
# backend/app/targets/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum

class FieldType(str, Enum):
    """Supported form field types for dynamic rendering."""
    TEXT = "text"
    TEXTAREA = "textarea"
    MARKDOWN = "markdown"
    TAGS = "tags"          # Comma-separated labels
    SELECT = "select"      # Dropdown
    CHECKBOX = "checkbox"
    
class FieldSchema(BaseModel):
    """Schema for a single form field."""
    name: str
    type: FieldType
    label: str
    placeholder: Optional[str] = None
    required: bool = False
    options: Optional[List[str]] = None  # For SELECT type
    default: Optional[Any] = None
    
class TargetSchema(BaseModel):
    """Defines the UI form and validation for a delivery target."""
    name: str                          # Unique ID: "github_issue"
    display_name: str                  # UI Label: "GitHub Issue"
    description: str                   # Tooltip text
    icon: Optional[str] = None         # Icon class or emoji
    fields: List[FieldSchema]          # Dynamic form fields
    schema_version: str = "1.0"        # For migration tracking
    
class TargetAdapter(ABC):
    """Abstract base for all delivery target adapters."""
    
    @property
    @abstractmethod
    def schema(self) -> TargetSchema:
        """Returns the schema for the Staging Area UI."""
        pass
    
    @abstractmethod
    def map_arguments(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform generic Komorebi data into tool-specific args."""
        pass
    
    @property
    @abstractmethod
    def mcp_tool_name(self) -> str:
        """The MCP tool to call (e.g., 'github.create_issue')."""
        pass
    
    @abstractmethod
    def validate_prerequisites(self) -> bool:
        """Check if MCP server is connected and authenticated."""
        pass
```

#### 2.2 Concrete Adapter: GitHub

```python
# backend/app/targets/github.py
from .base import TargetAdapter, TargetSchema, FieldSchema, FieldType

class GitHubIssueAdapter(TargetAdapter):
    @property
    def schema(self) -> TargetSchema:
        return TargetSchema(
            name="github_issue",
            display_name="GitHub Issue",
            description="Create a GitHub Issue with labels and assignees",
            icon="🐙",
            fields=[
                FieldSchema(
                    name="title",
                    type=FieldType.TEXT,
                    label="Issue Title",
                    placeholder="Brief summary of the issue",
                    required=True
                ),
                FieldSchema(
                    name="body",
                    type=FieldType.MARKDOWN,
                    label="Description",
                    placeholder="Detailed description (Markdown supported)",
                    required=True
                ),
                FieldSchema(
                    name="labels",
                    type=FieldType.TAGS,
                    label="Labels",
                    placeholder="bug, enhancement, docs",
                    required=False
                ),
                FieldSchema(
                    name="assignees",
                    type=FieldType.TAGS,
                    label="Assignees",
                    placeholder="username1, username2",
                    required=False
                ),
            ]
        )
    
    @property
    def mcp_tool_name(self) -> str:
        return "github.create_issue"
    
    def map_arguments(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map generic data to GitHub Issue API format."""
        return {
            "owner": os.getenv("GITHUB_REPO_OWNER"),  # From config
            "repo": os.getenv("GITHUB_REPO_NAME"),
            "title": data["title"],
            "body": data["body"],
            "labels": data.get("labels", "").split(",") if "labels" in data else [],
            "assignees": data.get("assignees", "").split(",") if "assignees" in data else [],
        }
    
    def validate_prerequisites(self) -> bool:
        """Check GitHub MCP server is available."""
        # Check MCPService for active GitHub server
        return True  # Placeholder
```

#### 2.3 Target Registry

```python
# backend/app/targets/registry.py
from typing import Dict, List
from .base import TargetAdapter, TargetSchema

class TargetRegistry:
    """Global registry for all delivery target adapters."""
    _targets: Dict[str, TargetAdapter] = {}
    
    @classmethod
    def register(cls, adapter: TargetAdapter):
        """Register an adapter at startup."""
        cls._targets[adapter.schema.name] = adapter
    
    @classmethod
    def get(cls, name: str) -> TargetAdapter:
        """Get adapter by name."""
        if name not in cls._targets:
            raise ValueError(f"Target '{name}' not registered")
        return cls._targets[name]
    
    @classmethod
    def list_schemas(cls) -> List[TargetSchema]:
        """List all available target schemas."""
        return [adapter.schema for adapter in cls._targets.values()]
    
    @classmethod
    def get_schema(cls, name: str) -> TargetSchema:
        """Get schema by name."""
        return cls.get(name).schema
```

#### 2.4 Dispatch Request/Response Models

```python
# backend/app/models/dispatch.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class DispatchRequest(BaseModel):
    """Request to dispatch data to a target."""
    target_name: str = Field(..., description="Name of the target adapter")
    payload: Dict[str, Any] = Field(..., description="Data to be dispatched")
    chunk_id: Optional[str] = Field(None, description="Associated chunk ID")
    
class DispatchResponse(BaseModel):
    """Response from dispatch operation."""
    success: bool
    target_name: str
    external_id: Optional[str] = Field(None, description="Remote ID (e.g., GitHub issue #123)")
    external_url: Optional[str] = Field(None, description="Link to created item")
    message: str
    dispatched_at: datetime
```

### API Design

| Method | Endpoint | Request | Response | Description |
|--------|----------|---------|----------|-------------|
| GET | `/api/v1/targets/schemas` | - | `list[TargetSchema]` | List all available targets with their schemas |
| GET | `/api/v1/targets/{name}/schema` | - | `TargetSchema` | Get schema for specific target |
| POST | `/api/v1/dispatch` | `DispatchRequest` | `DispatchResponse` | Dispatch data to target via MCP |
| GET | `/api/v1/dispatch/history` | `?limit=50` | `list[DispatchResponse]` | Dispatch history (future) |

### State Management

#### Frontend: Signals Store

```typescript
// frontend/src/store/targets.ts
import { signal, computed } from '@preact/signals-react';

export interface TargetSchema {
  name: string;
  display_name: string;
  description: string;
  icon?: string;
  fields: FieldSchema[];
}

export interface FieldSchema {
  name: string;
  type: string;
  label: string;
  placeholder?: string;
  required: boolean;
  options?: string[];
  default?: any;
}

export const availableTargets = signal<TargetSchema[]>([]);
export const selectedTarget = signal<string | null>(null);
export const formData = signal<Record<string, any>>({});
export const dispatchLoading = signal(false);
export const dispatchError = signal<string | null>(null);

export async function fetchTargets(): Promise<void> {
  const response = await fetch('/api/v1/targets/schemas');
  availableTargets.value = await response.json();
}

export async function dispatchToTarget(
  targetName: string,
  payload: Record<string, any>
): Promise<void> {
  dispatchLoading.value = true;
  dispatchError.value = null;
  try {
    const response = await fetch('/api/v1/dispatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_name: targetName, payload })
    });
    if (!response.ok) throw new Error(await response.text());
    return await response.json();
  } catch (e) {
    dispatchError.value = e.message;
    throw e;
  } finally {
    dispatchLoading.value = false;
  }
}
```

### Integration Points

| System | Protocol | Purpose | Fallback |
|--------|----------|---------|----------|
| GitHub MCP | HTTP/stdio | Create issues, PRs | Error message "GitHub MCP offline" |
| Jira MCP | HTTP | Create tickets | Error message "Jira MCP offline" |
| Slack MCP | HTTP | Post messages | Error message "Slack MCP offline" |
| MCPService | Internal | Tool call aggregation | 503 Service Unavailable |
| ChunkRepository | Database | Link dispatched items to chunks | Optional (null chunk_id) |

---

## Phase 3: Trade-off Analysis

### Decision 1: Schema-Driven Forms vs. Hardcoded Components

**Options Considered:**

**Option A: Hardcoded React Components** (Traditional)
- Pro: Full control over UI/UX per target
- Pro: TypeScript type safety at compile time
- Con: Every new target requires frontend + backend changes
- Con: High maintenance burden (2x code surface area)

**Option B: Schema-Driven Dynamic Forms** (Selected)
- Pro: Zero frontend code for new targets
- Pro: Single source of truth (Python adapter)
- Pro: LLM can generate valid forms from schema
- Con: Less UI flexibility (constrained by field types)
- Con: Runtime validation only (no compile-time checks)

**Selected:** Option B (Schema-Driven)

**Rationale:**  
The project's "Messy Chunks" philosophy prioritizes **speed of ingestion** over UI polish. Adding a new target should take 30 minutes (1 adapter), not 3 hours (adapter + React component + CSS). The trade-off is acceptable because:
1. Target forms are utility-focused, not user-delight-focused
2. Field types cover 90% of real-world tool APIs
3. Custom validation can be expressed in `validation_rules` JSON

**Reversibility:** Medium. If a target requires complex UI (e.g., rich file picker), we can add a "custom_component" escape hatch where the adapter specifies a React component name. This preserves the schema-first approach while allowing exceptions.

---

### Decision 2: Registry Pattern vs. Plugin System

**Options Considered:**

**Option A: Manual Registration** (Selected)
```python
# backend/app/main.py startup
TargetRegistry.register(GitHubIssueAdapter())
TargetRegistry.register(JiraTicketAdapter())
```
- Pro: Explicit, no magic
- Pro: Startup order is deterministic
- Con: Requires modifying `main.py` for new targets

**Option B: Auto-Discovery via Entry Points**
```python
# pyproject.toml
[project.entry-points."komorebi.targets"]
github = "backend.app.targets.github:GitHubIssueAdapter"
```
- Pro: True plugin architecture (no core changes)
- Con: Opaque startup (harder to debug)
- Con: Overkill for MVP (10-20 targets max)

**Selected:** Option A (Manual Registration)

**Rationale:**  
For MVP simplicity, explicit registration in `main.py` is sufficient. Entry points shine when there are 50+ plugins or external contributors, but Komorebi's target universe is bounded (GitHub, Jira, Slack, Linear, etc.). We can migrate to Option B post-1.0 if needed.

**Reversibility:** Easy. Entry points can coexist with manual registration (one-line change per adapter).

---

### Decision 3: Sync vs. Async Tool Dispatch

**Options Considered:**

**Option A: Synchronous (HTTP Request/Response)**
- Pro: Simpler error handling
- Pro: Immediate feedback to user
- Con: Blocks UI for slow tools (5-10s for GitHub API)

**Option B: Async with Background Task** (Selected)
- Pro: Non-blocking UI
- Pro: Can batch retries on failure
- Con: Requires SSE or polling for status updates
- Con: More complex state management

**Selected:** Option B (Async with SSE)

**Rationale:**  
GitHub Issues can take 3-7 seconds due to MCP subprocess overhead + network latency. Blocking the Staging Area for this duration violates the "Capture First" principle. SSE is already implemented for chunk events (`backend/app/api/sse.py`), so we can reuse this infrastructure for dispatch status updates.

**Reversibility:** Medium. Can add a "sync mode" flag to `DispatchRequest` for low-latency tools (e.g., Slack messages under 1s).

---

### Decision 4: Validation Location (Frontend vs. Backend)

**Options Considered:**

**Option A: Frontend-Only Validation**
- Pro: Instant feedback (no round trip)
- Con: Bypassable (client-side only)

**Option B: Backend-Only Validation**
- Pro: Secure (cannot be bypassed)
- Con: Slow feedback (requires API call)

**Option C: Both (Defense in Depth)** (Selected)
- Pro: Best UX (instant feedback) + Security
- Con: Duplicate validation logic

**Selected:** Option C (Both)

**Rationale:**  
The `TargetSchema.fields[].required` flag is consumed by both:
1. **Frontend:** React form disables submit button until required fields are filled
2. **Backend:** Adapter `map_arguments` raises `ValueError` if required fields missing

This ensures attackers cannot bypass frontend checks, while users get instant feedback.

**Reversibility:** N/A (this is a best practice, not a reversible decision).

---

## Phase 4: Implementation Plan

### Task Breakdown

#### Backend (6 hours)

**Task 1: Core Abstractions** (1.5h)
- [ ] Create `backend/app/targets/__init__.py`
- [ ] Implement `TargetAdapter` ABC in `backend/app/targets/base.py`
- [ ] Implement `TargetSchema`, `FieldSchema`, `FieldType` Pydantic models
- [ ] Write 5 unit tests for base models

**Task 2: Registry** (1h)
- [ ] Implement `TargetRegistry` in `backend/app/targets/registry.py`
- [ ] Add `register()`, `get()`, `list_schemas()` methods
- [ ] Write 3 unit tests (registration, lookup, list)

**Task 3: GitHub Adapter** (1.5h)
- [ ] Implement `GitHubIssueAdapter` in `backend/app/targets/github.py`
- [ ] Implement `schema` property with 4 fields (title, body, labels, assignees)
- [ ] Implement `map_arguments()` with config injection
- [ ] Write 8 unit tests (happy path, missing fields, validation)

**Task 4: API Endpoints** (1.5h)
- [ ] Create `backend/app/models/dispatch.py` (DispatchRequest, DispatchResponse)
- [ ] Add `GET /api/v1/targets/schemas` in `backend/app/api/targets.py`
- [ ] Add `POST /api/v1/dispatch` with MCP integration
- [ ] Wire up registry in `backend/app/main.py` startup
- [ ] Write 6 integration tests (list schemas, dispatch success, dispatch failure)

**Task 5: Testing & Documentation** (0.5h)
- [ ] Add `test_adapters.py` unit tests (12 tests total)
- [ ] Add `test_dispatch.py` integration tests (6 tests)
- [ ] Update `docs/API_REFERENCE.md` with new endpoints

---

#### Frontend (3 hours)

**Task 6: Signals Store** (0.5h)
- [ ] Create `frontend/src/store/targets.ts`
- [ ] Implement `fetchTargets()`, `dispatchToTarget()` functions
- [ ] Add signals: `availableTargets`, `selectedTarget`, `formData`

**Task 7: Dynamic Form Component** (1.5h)
- [ ] Create `frontend/src/components/DynamicForm.tsx`
- [ ] Implement field type mapping: TEXT → `<input>`, TEXTAREA → `<textarea>`, etc.
- [ ] Add validation logic (required fields, client-side checks)
- [ ] Add loading/error states

**Task 8: Staging Area Integration** (1h)
- [ ] Update `frontend/src/components/StagingArea.tsx`
- [ ] Add target selector dropdown (fetches schemas on mount)
- [ ] Render `<DynamicForm>` based on selected target
- [ ] Wire up submit button to `dispatchToTarget()`

---

#### Testing & Integration (3 hours)

**Task 9: E2E Tests** (1.5h)
- [ ] Create `frontend/e2e/staging_dynamic_form.spec.ts`
- [ ] Test: GitHub target renders title, body, labels fields
- [ ] Test: Slack target renders different fields (no title)
- [ ] Test: Switching targets preserves draft in localStorage
- [ ] Test: Form validation prevents submission with missing required fields

**Task 10: Load Testing (Hammer)** (1h)
- [ ] Create `scripts/hammer_dispatch.py`
- [ ] Fire 50 concurrent dispatch requests
- [ ] Assert success rate ≥ 98% (allow 1 transient failure)
- [ ] Measure P50, P95, P99 latencies

**Task 11: Documentation & Handoff** (0.5h)
- [ ] Update `CONVENTIONS.md` with adapter pattern examples
- [ ] Create `docs/ADDING_NEW_TARGETS.md` tutorial
- [ ] Update `PROGRESS.md` with Module 8 completion

---

### Total Estimated Time: 12 hours
- Backend: 6h
- Frontend: 3h
- Testing: 3h

---

## Open Questions

### Q1: Should adapters handle authentication (OAuth)?
**Decision Needed:** If GitHub requires OAuth, should the adapter manage token refresh, or delegate to MCPService?

**Options:**
1. Adapter owns auth logic (pro: encapsulation, con: duplication across adapters)
2. MCPService owns auth (pro: centralized, con: leaky abstraction)

**Recommendation:** MCPService owns auth. Adapters call `validate_prerequisites()` to check if server is authenticated, but don't manage tokens.

**Blocker Status:** Not blocking MVP. Can decide during implementation.

---

### Q2: Should there be an "Undo Dispatch" feature?
**Decision Needed:** If a user sends a chunk to GitHub, then realizes it's wrong, can they "undo"?

**Trade-offs:**
- GitHub API supports issue deletion (requires delete permission)
- Jira API supports ticket deletion (requires admin permission)
- Slack API does NOT support message deletion after 30 days

**Recommendation:** No undo in MVP. Add "Edit on GitHub" link in UI instead (opens external tool).

**Blocker Status:** Not blocking. Log in `ELICITATIONS.md` for v1.1.

---

### Q3: How to handle tool-specific features (e.g., GitHub Projects)?
**Decision Needed:** GitHub Issues can be added to Projects. Should the adapter support this?

**Options:**
1. Add `project_id` field to GitHub adapter schema (specific)
2. Add generic "metadata" field to TargetSchema (flexible but untyped)
3. Skip for MVP, add later as "Advanced Mode"

**Recommendation:** Option 3 (MVP: no Projects support). Track in `ELICITATIONS.md`.

**Blocker Status:** Not blocking.

---

## Handoff to Implementation

### Prerequisites
- [x] Architecture reviewed and approved
- [x] Trade-offs documented
- [x] Testing strategy defined (Unit, Integration, E2E, Hammer)
- [x] Task breakdown with time estimates

### Next Steps
1. **Implementer:** Follow task breakdown above in order (Backend → Frontend → Tests)
2. **TDD Workflow:** Write tests first for each task (Red → Green → Refactor)
3. **Commit Strategy:** One commit per task (12 commits total)
4. **Documentation:** Update `CONVENTIONS.md` and `API_REFERENCE.md` as you go

### Success Metrics
- [ ] 100% unit test coverage for adapters
- [ ] All 6 integration tests passing
- [ ] E2E tests cover 3 scenarios (GitHub, Slack, draft preservation)
- [ ] Hammer test: ≥98% success rate at 50 req/s
- [ ] Zero frontend changes required to add Jira adapter (verify by implementing Jira as proof)

---

**Architecture Phase Complete. Ready for `/implement-feature`.**
