---
name: update-docs
description: Synchronize documentation with code changes following Pre-1.0.0 governance requirements. Use after implementing features or fixing bugs.
agent: agent
model: Claude 3.5 Haiku
tools: ['editFiles']
---

# Update Documentation

## Governance (MUST Follow)

### Pre-1.0.0 Documentation Rule
**CRITICAL:** This is the core governance requirement for pre-1.0.0 development.

Always keep `CURRENT_STATUS.md` up to date along with the entire documentation suite:
- ✅ Update `CURRENT_STATUS.md` version and date on every release
- ✅ Ensure all documentation in `docs/` reflects the current state of the system
- ✅ Document new features, fixes, and breaking changes immediately
- ✅ Keep `CHANGELOG.md`, `CONVENTIONS.md`, `BUILD.md`, and `PROGRESS.md` synchronized with actual implementation

---

## Task Context

You are updating Komorebi's documentation to reflect code changes. Documentation must stay synchronized with implementation to maintain project integrity during pre-1.0.0 development.

---

## Documentation Structure

```
docs/
├── CURRENT_STATUS.md      # Version, date, and high-level status
├── CHANGELOG.md           # User-facing changes by version
├── BUILD.md               # Build and deployment instructions
├── CONVENTIONS.md         # Code patterns and best practices
├── PROGRESS.md            # Development progress tracking
├── VERSIONING.md          # Semantic versioning rules
└── ELICITATIONS.md        # Design decisions and trade-offs

.github/
└── copilot-instructions.md   # Agent governance and directives
```

---

## Documentation Files

### 1. CURRENT_STATUS.md

**Purpose:** High-level project status snapshot  
**Update Frequency:** Every release (version bump)

**Required Fields:**
```markdown
# Komorebi Current Status

**Version:** [X.Y.Z]  
**Date:** [YYYY-MM-DD]  
**Status:** [Alpha / Beta / RC / Stable]

## System Status

- **Backend:** [Status description]
- **Frontend:** [Status description]
- **MCP Aggregator:** [Status description]
- **Testing:** [Coverage percentage]

## Recent Changes

- [Major change 1]
- [Major change 2]

## Known Issues

- [Issue 1]
- [Issue 2]

## Next Milestones

- [Milestone 1]
- [Milestone 2]
```

**When to Update:**
- Every version bump (major, minor, or patch)
- When system status changes (e.g., backend moves from Alpha to Beta)
- When new major features are completed
- When critical bugs are discovered or fixed

### 2. CHANGELOG.md

**Purpose:** User-facing changes by version  
**Update Frequency:** Every user-visible change

**Format (Keep-a-Changelog style):**
```markdown
# Changelog

All notable changes to Komorebi will be documented in this file.

## [Unreleased]

### Added
- New feature descriptions

### Changed
- Changes to existing features

### Fixed
- Bug fixes

### Deprecated
- Features being phased out

### Removed
- Removed features

### Security
- Security-related changes

## [X.Y.Z] - YYYY-MM-DD

### Added
- Feature A: Description of feature A
- Feature B: Description of feature B

### Fixed
- Bug #123: Fixed race condition in chunk processing
```

**When to Update:**
- After implementing a new feature
- After fixing a user-visible bug
- After making breaking changes
- After deprecating or removing features
- Before every release (move "Unreleased" to version)

**What to include:**
- ✅ User-facing changes (new features, UI changes, bug fixes)
- ✅ Breaking changes (API changes, removed features)
- ✅ Security fixes
- ❌ Internal refactorings (unless they improve performance)
- ❌ Test changes (unless they fix flaky tests)
- ❌ Documentation updates (unless major)

### 3. CONVENTIONS.md

**Purpose:** Code patterns and best practices  
**Update Frequency:** When introducing new patterns

**Structure:**
```markdown
# Komorebi Code Conventions

## 1. Pydantic Models (Backend)
[Pattern examples]

## 2. State Management (Frontend)
[Pattern examples]

## 3. Async Patterns (Backend)
[Pattern examples]

...
```

**When to Update:**
- After establishing a new code pattern
- After discovering a better approach to existing patterns
- After team decides on a convention change
- When adding new technology or library

**Example Update:**
```markdown
## New Section: GraphQL Resolvers

### Resolver Pattern
We use async resolvers with dependency injection:

\`\`\`python
@query.field("chunk")
async def resolve_chunk(
    obj,
    info,
    chunk_id: str,
    repo: ChunkRepository = Depends(get_chunk_repo)
) -> Chunk:
    return await repo.get(UUID(chunk_id))
\`\`\`

**Rules:**
- All resolvers must be async
- Use Depends() for repository injection
- Return Pydantic models, not ORM models
```

### 4. PROGRESS.md

**Purpose:** Development progress tracking  
**Update Frequency:** After major module completion

**Format:**
```markdown
# Development Progress

## Backend

- ✅ Database Models (Chunk, Project)
- ✅ API Endpoints (CRUD operations)
- ⏳ Compaction Service (in progress)
- ❌ MCP Aggregator (not started)

## Frontend

- ✅ Basic UI Shell
- ✅ Chunk List Component
- ⏳ Metrics Dashboard (blocked by backend)
- ❌ Settings Page (not started)

## Testing

- ✅ Unit Tests (backend)
- ⏳ Integration Tests (backend)
- ❌ E2E Tests (not started)
```

**Symbols:**
- ✅ Complete
- ⏳ In Progress
- ❌ Not Started
- 🚧 Blocked

**When to Update:**
- After completing a major module
- When starting work on a new module
- When a module becomes blocked
- Weekly progress reviews

### 5. BUILD.md

**Purpose:** Build and deployment instructions  
**Update Frequency:** When build process changes

**When to Update:**
- After adding new dependencies
- After changing build scripts
- After updating Docker configuration
- After modifying deployment process
- After adding new environment variables

**Example Update:**
```markdown
## New Environment Variable

### `MCP_TIMEOUT`
**Required:** No  
**Default:** `30`  
**Description:** Timeout in seconds for MCP tool queries

**Example:**
\`\`\`bash
export MCP_TIMEOUT=60
\`\`\`
```

### 6. ELICITATIONS.md

**Purpose:** Design decisions and trade-offs  
**Update Frequency:** When making non-obvious decisions

**Format:**
```markdown
# Elicitations (Design Decisions)

## [YYYY-MM-DD] Decision: Use asyncio.Queue over Celery for MVP

**Context:** Need background task processing for chunk ingestion.

**Options Considered:**
1. Celery + Redis (industry standard)
2. asyncio.Queue (simple, no extra dependencies)

**Decision:** asyncio.Queue for MVP simplicity.

**Rationale:**
- MVP doesn't need distributed task processing
- Reduces infrastructure complexity
- Can migrate to Celery in v2.0 if needed

**Trade-offs:**
- ❌ Not suitable for multi-worker deployments
- ❌ Tasks lost on server restart
- ✅ Zero configuration
- ✅ Simpler debugging
```

**When to Update:**
- After making a significant architectural decision
- When choosing between multiple valid approaches
- When making trade-offs (performance vs simplicity)
- When deviating from conventions

---

## Update Workflow

### Step 1: Identify Documentation Updates Needed

After making code changes, ask:
1. **Version change?** → Update `CURRENT_STATUS.md`
2. **User-facing change?** → Update `CHANGELOG.md`
3. **New pattern?** → Update `CONVENTIONS.md`
4. **Module completion?** → Update `PROGRESS.md`
5. **Build change?** → Update `BUILD.md`
6. **Design decision?** → Update `ELICITATIONS.md`

### Step 2: Update Documentation Files

**Order of updates:**
1. `CURRENT_STATUS.md` (if version changed)
2. `CHANGELOG.md` (if user-facing)
3. `CONVENTIONS.md` (if new pattern)
4. `PROGRESS.md` (if milestone reached)
5. `BUILD.md` (if build changed)
6. `ELICITATIONS.md` (if decision made)

### Step 3: Verify Consistency

Check that all docs are synchronized:
- [ ] Version numbers match across `CURRENT_STATUS.md`, `CHANGELOG.md`, `pyproject.toml`, `package.json`
- [ ] `CHANGELOG.md` has an entry for the current version
- [ ] Code examples in `CONVENTIONS.md` match actual code patterns
- [ ] `PROGRESS.md` reflects actual completion status
- [ ] `BUILD.md` instructions work on a fresh setup

### Step 4: Commit Documentation

```bash
# Documentation updates should be in the same commit as code changes
git add docs/CURRENT_STATUS.md docs/CHANGELOG.md
git commit -m "feat: v0.3.0+build5 - add chunk favoriting feature"
```

---

## Common Documentation Updates

### Adding a New Feature

**Files to update:**
1. `CHANGELOG.md`:
   ```markdown
   ### Added
   - Chunk favoriting: Users can now mark chunks as favorites via PATCH /chunks/{id}/favorite
   ```

2. `PROGRESS.md` (if completing a milestone):
   ```markdown
   - ✅ Chunk Management (CRUD + favoriting)
   ```

3. `CURRENT_STATUS.md` (if major feature):
   ```markdown
   ## Recent Changes
   - Added chunk favoriting feature
   ```

### Fixing a Bug

**Files to update:**
1. `CHANGELOG.md`:
   ```markdown
   ### Fixed
   - Fixed race condition in concurrent chunk updates (issue #42)
   ```

2. `ELICITATIONS.md` (if non-obvious fix):
   ```markdown
   ## [2026-02-05] Fixed: Race condition in chunk updates
   
   **Issue:** Concurrent updates to the same chunk caused data loss.
   **Fix:** Added asyncio.Lock around critical section.
   **Lesson:** Always protect shared mutable state in async code.
   ```

### Changing a Convention

**Files to update:**
1. `CONVENTIONS.md`:
   ```markdown
   ## State Management (Frontend)
   
   **Updated:** We now use Preact Signals for all state management (previously used useState).
   
   [New pattern examples]
   ```

2. `CHANGELOG.md`:
   ```markdown
   ### Changed
   - Migrated frontend state management to Preact Signals
   ```

### Releasing a Version

**Files to update:**
1. `CURRENT_STATUS.md`:
   ```markdown
   **Version:** 0.3.0  
   **Date:** 2026-02-05
   ```

2. `CHANGELOG.md`:
   ```markdown
   ## [0.3.0] - 2026-02-05
   
   [Move all "Unreleased" items here]
   
   ## [Unreleased]
   
   [Empty for now]
   ```

3. `pyproject.toml`:
   ```toml
   [tool.poetry]
   version = "0.3.0"
   ```

4. `frontend/package.json`:
   ```json
   {
     "version": "0.3.0"
   }
   ```

---

## Documentation Quality Checklist

Before committing documentation changes:
- [ ] All version numbers are synchronized
- [ ] CHANGELOG.md follows Keep-a-Changelog format
- [ ] Code examples are valid and tested
- [ ] Links are not broken
- [ ] Markdown renders correctly
- [ ] Dates are in YYYY-MM-DD format
- [ ] Grammar and spelling are correct

---

## Output Format

**Provide the following deliverables:**

1. **Updated Documentation Files:**
   - List of files changed
   - Specific sections updated

2. **Version Consistency Check:**
   - Confirm all version numbers match
   - Confirm CHANGELOG.md has entry for current version

3. **Summary:**
   - Brief description of documentation changes
   - Justification for each change

**Do NOT:**
- Update documentation without corresponding code changes
- Leave "TODO" or "TBD" markers in committed docs
- Break existing links
- Use inconsistent formatting

---

## Example: Complete Documentation Update

**Scenario:** Just implemented chunk favoriting feature

### 1. CHANGELOG.md

```markdown
## [Unreleased]

### Added
- Chunk favoriting: Users can mark chunks as favorites via PATCH /api/v1/chunks/{id}/favorite
```

### 2. CURRENT_STATUS.md

```markdown
**Version:** 0.3.0+build5  
**Date:** 2026-02-05

## Recent Changes

- Added chunk favoriting feature
- Improved async error handling in repositories
```

### 3. CONVENTIONS.md

```markdown
## API Response Format

### 7.1 PATCH Endpoints

\`\`\`python
@router.patch("/{chunk_id}/favorite", response_model=Chunk)
async def favorite_chunk(
    chunk_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Chunk:
    """Mark chunk as favorite."""
    chunk = await chunk_repo.get(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found")
    return await chunk_repo.update(chunk_id, {"is_favorite": True})
\`\`\`
```

### 4. PROGRESS.md

```markdown
## Backend

- ✅ Database Models (Chunk with favorite flag)
- ✅ API Endpoints (CRUD + favoriting)
```

**Done!** Documentation synchronized with code changes.

---

**Ready to update documentation!** Follow the workflow above to keep docs synchronized.
