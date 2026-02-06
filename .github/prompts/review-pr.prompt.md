---
name: review-pr
description: Comprehensive pull request review covering security, conventions, tests, and documentation. Use for code review before merging.
agent: agent
model: Claude Sonnet 4
tools: ['search/codebase', 'githubRepo']
---

# Review Pull Request

## Governance (MUST Follow)

### Pre-1.0.0 Documentation Rule
**CRITICAL:** Verify documentation is synchronized with code changes.

- ✅ Check `CURRENT_STATUS.md` is updated (if version change)
- ✅ Check `CHANGELOG.md` has entry for user-facing changes
- ✅ Check `CONVENTIONS.md` is updated (if new pattern introduced)
- ✅ Check `PROGRESS.md` reflects milestone status

### Prime Directives Review
1. **Capture-First:** Ingestion endpoints use `202 Accepted` and background tasks?
2. **State Isolation:** Changes target correct branch (feature → develop → main)?
3. **Agentic Autonomy:** No trivial blockers left as TODOs?

---

## Task Context

You are performing a comprehensive code review for a Komorebi pull request. Review covers:
1. **Security:** No secrets, SQL injection, XSS vulnerabilities
2. **Conventions:** Code follows CONVENTIONS.md patterns
3. **Testing:** Adequate test coverage, tests pass
4. **Documentation:** Docs synchronized with changes
5. **Performance:** No obvious performance issues
6. **Breaking Changes:** Identified and documented

---

## Review Checklist

### 1. Security Review (CRITICAL)

#### Secret Detection
Scan for hardcoded secrets. REJECT if found:
```regex
# API Keys
ghp_[a-zA-Z0-9]{36}           # GitHub Personal Access Token
sk_live_[a-zA-Z0-9]+          # Stripe Live Key
sk-[a-zA-Z0-9]{48}            # OpenAI API Key
ANTHROPIC_API_KEY=\w+         # Anthropic Key

# AWS
AKIA[A-Z0-9]{16}              # AWS Access Key
aws_secret_access_key=\w+     # AWS Secret Key

# Database
password\s*=\s*["'][^"']+["'] # Hardcoded passwords
postgresql://.*:.*@           # Connection strings with credentials
```

**Verdict Options:**
- 🚨 **BLOCK:** Secret found - MUST be removed
- ✅ **PASS:** No secrets detected

#### SQL Injection
Check for unsafe SQL patterns:
```python
# ❌ VULNERABLE
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(f"DELETE FROM table WHERE id = {id}")

# ✅ SAFE
query = "SELECT * FROM users WHERE id = :id"
await session.execute(select(User).where(User.id == user_id))
```

**Verdict Options:**
- 🚨 **BLOCK:** Raw SQL with user input
- ⚠️ **WARN:** Raw SQL without parameterization
- ✅ **PASS:** Uses ORM or parameterized queries

#### XSS Prevention
Check for unsafe HTML rendering:
```typescript
// ❌ VULNERABLE
dangerouslySetInnerHTML={{ __html: userInput }}

// ✅ SAFE
{sanitizedContent}
```

**Verdict Options:**
- 🚨 **BLOCK:** Unsanitized user input in HTML
- ✅ **PASS:** Proper sanitization or no raw HTML

### 2. Convention Compliance

#### Backend (Python/FastAPI)

**Async/Await:**
```python
# ✅ CORRECT
@router.get("/items/{item_id}")
async def get_item(item_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await session.execute(query)  # await on I/O
    return result

# ❌ WRONG
@router.get("/items/{item_id}")
def get_item(item_id: UUID):  # Missing async
    result = session.execute(query)  # Missing await
```

**Pydantic Schemas:**
```python
# ✅ CORRECT (Separate Create/Update/Read)
class ItemCreate(BaseModel): ...
class ItemUpdate(BaseModel): ...
class Item(BaseModel): ...

# ❌ WRONG (Single schema for everything)
class Item(BaseModel): ...
```

**Response Format:**
```python
# ✅ CORRECT (Direct return)
return item

# ❌ WRONG (Wrapped response)
return {"data": item}
```

**Type Hints:**
```python
# ✅ CORRECT
async def get_item(item_id: UUID) -> Item: ...

# ❌ WRONG
async def get_item(item_id): ...  # Missing type hints
```

**Verdict Options:**
- 🚨 **BLOCK:** Missing async/await on I/O operations
- ⚠️ **WARN:** Missing type hints or schema separation
- ✅ **PASS:** Follows conventions

#### Frontend (React/TypeScript)

**State Management:**
```typescript
// ✅ CORRECT (Preact Signals for shared state)
export const items = signal<Item[]>([])

// ⚠️ WARN (useState for shared state)
const [items, setItems] = useState<Item[]>([])
```

**Data Fetching:**
```typescript
// ✅ CORRECT (useEffect on mount only)
useEffect(() => { fetchItems() }, [])

// ❌ WRONG (useEffect with dependencies causing loops)
useEffect(() => { fetchItems() }, [items])
```

**Verdict Options:**
- ⚠️ **WARN:** useState for shared state (should use signals)
- 🚨 **BLOCK:** useEffect loops
- ✅ **PASS:** Follows conventions

### 3. Test Coverage

#### Test File Exists
Check that new code has corresponding tests:
```
backend/app/api/items.py → backend/tests/test_items.py
frontend/src/components/ItemList.tsx → (manual testing for MVP)
```

#### Test Quality
Check test coverage:
- ✅ Happy path tests
- ✅ Error case tests (404, 422, 500)
- ✅ Edge case tests (empty data, pagination)
- ✅ Async tests use `@pytest.mark.asyncio`

#### Test Execution
```bash
# Run tests to verify they pass
pytest backend/tests/test_<module>.py -v
```

**Verdict Options:**
- 🚨 **BLOCK:** No tests for new API endpoints
- ⚠️ **WARN:** Tests exist but incomplete coverage
- ✅ **PASS:** Adequate test coverage

### 4. Documentation Sync

Check if documentation needs updating:

| Change Type | Required Doc Updates |
|-------------|---------------------|
| New feature | CHANGELOG.md, PROGRESS.md |
| Bug fix (user-facing) | CHANGELOG.md |
| New pattern | CONVENTIONS.md |
| Version bump | CURRENT_STATUS.md |
| Design decision | ELICITATIONS.md |

**Verdict Options:**
- ⚠️ **WARN:** Docs need updating
- ✅ **PASS:** Docs are synchronized

### 5. Performance Review

#### N+1 Queries
```python
# ❌ N+1 PROBLEM
for item in items:
    author = await get_author(item.author_id)  # Query per item

# ✅ OPTIMIZED
items_with_authors = await get_items_with_authors()  # Single query
```

#### Large Data Loading
```python
# ⚠️ POTENTIAL ISSUE
items = await repo.list()  # No limit

# ✅ BETTER
items = await repo.list(limit=100, offset=0)  # Paginated
```

#### Blocking Operations in Async
```python
# ❌ BLOCKING
result = requests.get(url)  # Blocks event loop

# ✅ NON-BLOCKING
async with httpx.AsyncClient() as client:
    result = await client.get(url)
```

**Verdict Options:**
- ⚠️ **WARN:** Potential performance issue
- ✅ **PASS:** No obvious performance concerns

### 6. Breaking Changes

Check for changes that could break existing functionality:

#### API Breaking Changes
- Changed endpoint paths
- Changed request/response schemas
- Changed HTTP methods
- Changed authentication requirements

#### Database Breaking Changes
- Removed columns
- Changed column types
- Changed constraints

**Verdict Options:**
- 🚨 **BLOCK:** Undocumented breaking change
- ⚠️ **WARN:** Breaking change (must be documented in CHANGELOG)
- ✅ **PASS:** No breaking changes

---

## Review Workflow

### Step 1: Initial Scan

1. Review the PR diff for obvious issues
2. Check file names match conventions
3. Identify scope (backend, frontend, both)

### Step 2: Security Review

1. Run secret detection patterns
2. Check for SQL injection vulnerabilities
3. Check for XSS vulnerabilities
4. **STOP if security issues found**

### Step 3: Convention Review

1. Verify async/await patterns (backend)
2. Verify Pydantic schema patterns (backend)
3. Verify signal/state patterns (frontend)
4. Check type hints and imports

### Step 4: Test Review

1. Verify test files exist for new code
2. Review test quality and coverage
3. Run tests if possible: `pytest backend/tests/`

### Step 5: Documentation Review

1. Check if CHANGELOG.md needs entry
2. Check if CONVENTIONS.md needs update
3. Check if PROGRESS.md needs update
4. Check if ELICITATIONS.md has design decisions

### Step 6: Performance & Breaking Changes

1. Scan for N+1 queries
2. Check for blocking operations
3. Identify breaking changes
4. Verify breaking changes are documented

---

## Output Format

Provide a structured review report:

```markdown
# PR Review: [PR Title]

## Summary
[Brief summary of what the PR does]

## Security Review
- [ ] Secret Detection: [PASS/BLOCK]
- [ ] SQL Injection: [PASS/WARN/BLOCK]
- [ ] XSS Prevention: [PASS/WARN/BLOCK]

## Convention Compliance
- [ ] Async/Await: [PASS/WARN/BLOCK]
- [ ] Pydantic Schemas: [PASS/WARN]
- [ ] Response Format: [PASS/WARN]
- [ ] Type Hints: [PASS/WARN]
- [ ] Frontend State: [PASS/WARN]

## Test Coverage
- [ ] Test Files Exist: [PASS/WARN/BLOCK]
- [ ] Test Quality: [PASS/WARN]
- [ ] Tests Pass: [PASS/BLOCK]

## Documentation
- [ ] CHANGELOG.md: [PASS/WARN] (needs update: [yes/no])
- [ ] CONVENTIONS.md: [PASS/WARN] (needs update: [yes/no])
- [ ] PROGRESS.md: [PASS/WARN] (needs update: [yes/no])

## Performance
- [ ] N+1 Queries: [PASS/WARN]
- [ ] Blocking Operations: [PASS/WARN]

## Breaking Changes
- [ ] API Changes: [PASS/WARN/BLOCK]
- [ ] Database Changes: [PASS/WARN/BLOCK]

## Verdict: [APPROVE / REQUEST_CHANGES / BLOCK]

## Required Changes
1. [Change 1]
2. [Change 2]

## Suggestions (Non-blocking)
1. [Suggestion 1]
2. [Suggestion 2]
```

---

## Verdict Criteria

### ✅ APPROVE
- All security checks pass
- Convention compliance is good
- Tests exist and pass
- No blocking issues

### 🔄 REQUEST_CHANGES
- Minor issues that need fixing
- Documentation needs updating
- Tests need improvement
- Non-critical convention violations

### 🚨 BLOCK
- Security vulnerabilities found
- Critical convention violations (missing async/await)
- No tests for new endpoints
- Breaking changes not documented

---

## Common Review Comments

### Security Issues
```markdown
🚨 **Security: Hardcoded Secret Detected**
Line 42: Found potential API key. Remove and use environment variable:
\`\`\`python
# Before
API_KEY = "sk-abc123..."

# After
API_KEY = os.environ.get("API_KEY")
\`\`\`
```

### Convention Issues
```markdown
⚠️ **Convention: Missing await on async operation**
Line 28: Database query must be awaited:
\`\`\`python
# Before
result = session.execute(query)

# After
result = await session.execute(query)
\`\`\`
```

### Test Issues
```markdown
⚠️ **Testing: Missing error case tests**
Consider adding tests for:
- 404 Not Found when item doesn't exist
- 422 Validation Error for invalid input
- 409 Conflict for duplicate entries
```

### Documentation Issues
```markdown
⚠️ **Documentation: CHANGELOG.md needs update**
This PR adds a new feature. Please add an entry:
\`\`\`markdown
### Added
- [Feature description]
\`\`\`
```

---

## Quick Reference

| Severity | Symbol | Meaning |
|----------|--------|---------|
| BLOCK | 🚨 | Must fix before merge |
| WARN | ⚠️ | Should fix, not blocking |
| PASS | ✅ | No issues found |

| Priority | Items |
|----------|-------|
| Critical | Security, Missing async/await |
| High | Tests, Breaking changes |
| Medium | Conventions, Documentation |
| Low | Style, Suggestions |

---

**Ready to review pull requests comprehensively!** Follow the 6-step workflow above.
