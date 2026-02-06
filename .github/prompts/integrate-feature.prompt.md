---
name: integrate-feature
description: Finalize implemented features through testing, versioning, documentation, and commit workflow. Use for transitioning code from feature branch to develop/main.
agent: agent
tools: ['agent', 'edit', 'execute', 'read', 'search', 'todo', 'vscode', 'web', 'gitkraken/*', 'github/*', 'vscode.mermaid-chat-features/renderMermaidDiagram', 'pylance-mcp-server/*']
---

# Integrate Feature

## Purpose

This prompt guides the final integration of a feature: move tested code from feature branch to production via develop/main, versioning, and documentation sync.

**Use this prompt when:**
- Code is implemented and tests pass locally
- Ready to create a pull request to `develop`
- Need versioning and changelog updates
- Documentation needs synchronized with new features
- Preparing for merge to main branch

**Do NOT use for:** Initial design, implementation, or debugging. Use `/architect-feature` or `/implement-feature` instead.

---

## Pre-Integration Checklist

Before starting, ensure:

- ✅ Feature branch created from `develop`: `feature/<ticket-id>-<description>`
- ✅ All tests pass: `pytest` (100% of new code covered)
- ✅ Stress test passes: `scripts/hammer_gen.py --size 500` (ingestion features only)
- ✅ No linting errors: `ruff check .`
- ✅ Type hints complete: `pyright` or `mypy` pass cleanly
- ✅ Handoff document from Implementation phase available

---

## Integration Workflow

### Step 1: Validate Implementation

#### 1.1 Test Execution
```bash
# Backend tests
pytest -v --tb=short

# Frontend tests (if applicable)
npm run test:unit  # or similar

# Type checking
ruff check .
```

**Success criteria:**
- All tests pass
- Coverage ≥ 80% for new code
- No lint or type errors

#### 1.2 Verify Implementation Reference

Check the `NEW_IMPLEMENTATION_REFERENCE.md` created during implementation phase:
- [ ] Feature scope clearly defined
- [ ] All acceptance criteria covered
- [ ] List of changed files with line ranges
- [ ] Known limitations or TODOs documented
- [ ] Test results summarized

### Step 2: Documentation Sync

Update all documentation to reflect the new feature.

#### 2.1 Update CHANGELOG.md

Add entry under "Unreleased" section:

```markdown
## Unreleased

### Added
- [FEATURE_NAME] Brief description of what was added
  - Sub-feature 1
  - Sub-feature 2

### Changed
- [modified behavior] Description of breaking changes (if any)

### Fixed
- [bugfix] Description of fix (if applicable)
```

**Template for feature entries:**
```markdown
### Added
- **[Module X] Feature Name** - Core functionality description
  - Backend: `/api/v1/endpoint` POST/GET with request/response examples
  - Frontend: `ComponentName` with key props `prop1`, `prop2`
  - Database: New tables/columns with schema brief
  - Example use case: "User can now..."
```

#### 2.2 Update CURRENT_STATUS.md

- [ ] Bump version number (follow semver: major.minor.patch)
- [ ] Update "Date" field
- [ ] Move feature from ⚠️ "Partially Implemented" to ✅ "Fully Working Systems"
- [ ] Update performance metrics if applicable
- [ ] Add entry to "Latest Updates" section

**Version strategy:**
- Patch (x.x.Y): Bug fixes, non-breaking changes
- Minor (x.Y.0): New features, backward compatible
- Major (X.0.0): Breaking changes

#### 2.3 Update PROGRESS.md

Add completed feature to the appropriate module section:

```markdown
### Phase [N]: [Module Name]
- ✅ Feature description
  - Details about what was implemented
  - Performance or limits if known
```

#### 2.4 Update Other Docs (if affected)

- [ ] `BUILD.md` - Architecture changes
- [ ] `CONVENTIONS.md` - New code patterns
- [ ] `API_REFERENCE.md` - New endpoints
- [ ] `docs/DEVELOPMENT_WORKFLOWS.md` - New workflows for developers

---

### Step 3: Version Bump

#### 3.1 Update VERSION file

```bash
# Check current version
cat VERSION

# Update version (example: 0.2.1 → 0.3.0)
echo "0.3.0" > VERSION
```

#### 3.2 Sync Version Across Codebase

```bash
# Run version sync script
bash scripts/sync-versions.sh

# Verify sync
grep -r "0.3.0" pyproject.toml frontend/package.json VERSION CHANGELOG.md
```

Locations that MUST match:
- `VERSION` - Source of truth
- `pyproject.toml` - Python package version
- `frontend/package.json` - Frontend version
- `docs/CURRENT_STATUS.md` - Documentation version

#### 3.3 Create Git Tag (if promoting to main)

```bash
# After merge to develop/main
git tag -a v0.3.0 -m "Release v0.3.0: [Brief description]"
git push origin v0.3.0
```

---

### Step 4: Create Pull Request

#### 4.1 Branch Final Check

```bash
# Ensure on feature branch
git branch

# Push all commits
git push origin feature/<ticket-id>-<description>
```

#### 4.2 PR Template (GitHub)

Use this template when creating the PR:

```markdown
## 🎯 Purpose
[Link to GitHub Issue]

Brief description of what this PR accomplishes.

## 📝 Changes
- [ ] Backend: [list of endpoints/files]
- [ ] Frontend: [list of components/files]
- [ ] Database: [schema changes, migrations]
- [ ] Tests: [new test files]
- [ ] Documentation: [updated docs]

## ✅ Acceptance Criteria
- [x] Criterion 1
- [x] Criterion 2
- [x] Tests pass (100% coverage)
- [x] Linting passes (ruff check)
- [x] Documentation synchronized

## 🧪 Testing
- [x] Unit tests: `pytest` - X new tests, X total
- [x] Integration tests: [describe]
- [x] Stress test: `hammer_gen.py --size 500` - [results]
- [x] Manual testing: [describe scenarios tested]

## 📚 Documentation
- [x] CHANGELOG.md updated
- [x] CURRENT_STATUS.md updated
- [x] API_REFERENCE.md updated (if applicable)
- [x] CONVENTIONS.md updated (if introducing new patterns)

## 🔗 Related
- Issue: #[number]
- Depends on: [if any]
- Blocks: [if any]

## 📎 INTEGRATION_HANDOFF.md
See attached `INTEGRATION_HANDOFF.md` for detailed integration notes.
```

#### 4.3 Reference Handoff Document

In the PR description, reference the handoff document:

> See `INTEGRATION_HANDOFF.md` in this feature branch for detailed integration notes, test results, and known limitations.

---

### Step 5: Code Review & Merge

#### 5.1 Merge to Develop

```bash
# Ensure all CI checks pass
# - Linting (ruff check)
# - Tests (pytest)
# - Frontend build (npm build)

# After approval, merge from feature → develop
# Use "Squash and merge" for clean history OR "Create a merge commit" for attribution
```

#### 5.2 Promote to Main (Governance Gate)

After merge to `develop`:

1. **Verify in staging:** Code must survive integration testing in `develop` branch
2. **Manual approval:** Feature requires code review and manual sign-off
3. **Create release PR:** `develop` → `main` with detailed release notes
4. **Tag release:** After main merge, create git tag `v0.3.0`

**Release checklist before main merge:**
- [ ] Feature tested in develop for ≥1 day (if critical path)
- [ ] No blocking issues reported
- [ ] Load test passes (hammer_gen.py)
- [ ] Browser compatibility tested (Chrome, Firefox, Safari)
- [ ] Mobile responsive tested

---

### Step 6: Post-Integration

#### 6.1 Cleanup

```bash
# After merge and tag, delete feature branch
git branch -d feature/<ticket-id>-<description>
git push origin --delete feature/<ticket-id>-<description>
```

#### 6.2 Verify Release

```bash
# Pull latest from main
git fetch origin main
git checkout main
git pull origin main

# Verify version
cat VERSION

# Verify tag
git tag -l v0.3.0

# Quick smoke test
pytest -x  # Run until first failure (quick check)
npm run dev  # Test frontend loads
```

#### 6.3 Update Status

```bash
# Add entry to CURRENT_STATUS.md
# "Last Updated: [Date] - v0.3.0 released"
```

---

## Integration Handoff Document (`INTEGRATION_HANDOFF.md`)

The Implementation phase must produce `INTEGRATION_HANDOFF.md` with:

```markdown
# Integration Handoff: [Feature Name]

## Feature Summary
[What was built, why it matters]

## Acceptance Criteria Status
- [x] Criterion 1
- [x] Criterion 2
- [x] All criteria met ✅

## Test Results
- Unit tests: X/X passing
- Integration tests: X/X passing
- Stress test (hammer): X req/s, Y failures (target: 0)
- Coverage: X%

## Files Changed
- `backend/app/api/...` - [brief description]
- `backend/app/models/...` - [brief description]
- `frontend/src/...` - [brief description]
- Line ranges for each significant change

## Database Migrations
- [ ] None needed
- [ ] Migration script: `scripts/migrate_*.py`
- [ ] Manual steps: [describe]

## Known Limitations or TODOs
- [Limitation 1] - Will address in v[x.x]
- [Limitation 2] - Blocked by [dependency]

## Performance Impact
- API latency: [before → after]
- Memory usage: [if applicable]
- Database queries: [if applicable]

## Backward Compatibility
- ✅ Fully backward compatible
- ⚠️ Requires migration (see above)
- ❌ Breaking changes (document below)

Breaking changes:
- [Change 1]: [Impact and migration path]

## Next Steps
[What feature/module should be implemented next]
```

---

## Version Strategy

Reference: [VERSIONING.md](../../VERSIONING.md)

**Semantic Versioning (SemVer):**
- **MAJOR** (X.0.0): Breaking changes to API or core behavior
- **MINOR** (x.Y.0): New features, backward compatible
- **PATCH** (x.x.Z): Bug fixes

**Release Track:**
- Development: `0.2.1`, `0.2.2`, ... (pre-1.0)
- Stable: `1.0.0`, `1.1.0`, `2.0.0`, ... (post-1.0)

**Branch Protection Rules:**
- `main`: Requires PR review, all CI checks pass, version bumped
- `develop`: Requires PR review, tests pass, no merge conflicts
- `feature/*`: No restrictions (development sandbox)

---

## Governance Checklist

Before marking as complete:

- [ ] All documentation updated and synchronized
- [ ] Version bumped and synced across all files
- [ ] Tests passing (100% coverage for new code)
- [ ] Linting and type checks passing
- [ ] PR created with proper template and handoff document
- [ ] No hardcoded secrets or credentials
- [ ] Imports properly organized (stdlib → third-party → local)
- [ ] No incomplete TODO comments (complete or use `NotImplementedError`)
- [ ] Performance baseline established (latency, memory, etc.)
- [ ] Feature branch deleted after merge to develop

---

## Troubleshooting

### "Version mismatch in X files"
```bash
bash scripts/sync-versions.sh
# Manually update any files missed
```

### "Tests fail in CI but pass locally"
```bash
# Clear caches and re-run
rm -rf .pytest_cache __pycache__ .ruff_cache
pytest -v
```

### "Merge conflicts in documentation"
```bash
# Resolve conflicts manually (docs rarely have auto-conflicts)
# Favor "incoming" (feature branch) if adding new features
git checkout --theirs CHANGELOG.md
```

### "Tag already exists"
```bash
# Delete old tag if it was created in error
git tag -d v0.3.0
git push origin --delete v0.3.0
# Create new tag with correct content
```

---

## See Also

- [CONVENTIONS.md](../../CONVENTIONS.md) - Coding patterns and style
- [VERSIONING.md](../../VERSIONING.md) - Version strategy details
- [PROGRESS.md](../../PROGRESS.md) - Project execution log
- `/implement-feature` - For ongoing implementation work
