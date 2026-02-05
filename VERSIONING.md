# Komorebi Versioning Governance

## Semantic Versioning (SemVer)

Komorebi follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

**Version Format:** `MAJOR.MINOR.PATCH`

- **MAJOR:** Breaking API changes, incompatible schema changes
- **MINOR:** New features, backward-compatible API additions  
- **PATCH:** Bug fixes, documentation updates, backward-compatible fixes

## Version Sources of Truth

The canonical version is stored in:
1. **`VERSION` file** (root directory) - Single source of truth
2. **`pyproject.toml`** - Python package version (must match VERSION)
3. **`frontend/package.json`** - Frontend package version (must match VERSION) 
4. **`docs/CHANGELOG.md`** - Must have entry for current version

## Development Versioning (Build System)

### Proposed Changes (Pre-Release)

While developing features or patches, use the **proposed versioning format**:

```
{proposed MAJOR.MINOR.PATCH}+buildN
```

**Examples:**
- `0.2.1+build1` - First build of proposed patch 0.2.1
- `0.3.0+build5` - Fifth iteration of proposed minor release 0.3.0  
- `1.0.0+build12` - Twelfth build of proposed major release 1.0.0

**Build Number Rules:**
- Increment +buildN for each commit/iteration during development
- Reset to +build1 when starting a new proposed version
- Remove +buildN suffix when feature/patch is complete and ready for release

### Version Validation Commands

```bash
# Check version consistency
./scripts/check-version.sh

# Update all version files to match VERSION
./scripts/sync-versions.sh

# Validate changelog has entry for current version  
./scripts/validate-changelog.sh
```

## Release Process

### 1. Development Phase
```bash
# Start new feature (minor version bump)
echo "0.3.0+build1" > VERSION
./scripts/sync-versions.sh
git commit -m "feat: start v0.3.0+build1 - new feature X"

# Iterate during development  
echo "0.3.0+build2" > VERSION
./scripts/sync-versions.sh
git commit -m "feat: v0.3.0+build2 - implement feature Y"
```

### 2. Completion Phase
```bash
# Feature complete, finalize version
echo "0.3.0" > VERSION
./scripts/sync-versions.sh

# Update CHANGELOG.md with new [0.3.0] section
vim docs/CHANGELOG.md

# Validate everything matches
./scripts/check-version.sh
./scripts/validate-changelog.sh

# Release commit
git commit -m "release: v0.3.0 - feature X complete"
git tag -a v0.3.0 -m "Release v0.3.0: Feature X"
```

### 3. Post-Release  
```bash
# Start next development cycle
echo "0.3.1+build1" > VERSION
./scripts/sync-versions.sh
git commit -m "chore: start v0.3.1+build1 development"
```

## Commit Detection & Usage Tracking

Every commit must include the full version in the commit message for tracking:

**Required Format:**
```
<type>: v<version> - <description>

Examples:
feat: v0.3.0+build1 - add entity extraction
fix: v0.2.1+build3 - resolve Ollama cold start  
docs: v0.2.0 - update module 2 verification
release: v0.3.0 - recursive compaction complete
```

**Validation:**
- CI must validate commit message contains current VERSION file content
- `scripts/check-commit-version.sh` validates current commit
- No commits allowed without version in message

## Version Dependencies & Compatibility

### API Versioning
- API endpoints include version: `/api/v1/chunks`
- Major version bumps may introduce `/api/v2/` 
- Maintain backward compatibility within same API version

### Database Schema  
- Migration scripts must include version metadata
- Schema incompatibilities trigger MAJOR version bump
- Migrations tracked in `scripts/migrations/` with version prefix

### MCP Protocol
- MCP client version must be specified in server connections
- Breaking MCP changes require MAJOR version bump

## Emergency Versioning

### Hotfix Process
```bash
# Critical production fix (current: v0.3.0)
git checkout v0.3.0
echo "0.3.1+build1" > VERSION
# ... apply fix ...
echo "0.3.1" > VERSION  
./scripts/sync-versions.sh
git commit -m "hotfix: v0.3.1 - critical security fix"
git tag -a v0.3.1 -m "Hotfix v0.3.1: Security patch"

# Merge back to main
git checkout main
git merge v0.3.1
```

### Version Rollback
```bash
# If release has critical issues
git revert v0.3.0
echo "0.2.1+build1" > VERSION
./scripts/sync-versions.sh  
git commit -m "revert: v0.2.1+build1 - rollback v0.3.0 due to critical issue"
```

## Enforcement

### Pre-commit Hooks
- Validate VERSION file format
- Ensure pyproject.toml and package.json versions match VERSION
- Check CHANGELOG.md has entry for current version (if not +buildN)

### CI/CD Pipeline
- Block merges if versions are inconsistent
- Block releases without proper CHANGELOG entry
- Validate commit message has version
- Generate release notes from CHANGELOG

### Usage Detection
- Every deployment logs its version to metrics system
- Version usage tracked via telemetry (if enabled)  
- Deprecation warnings for old API versions
- Health endpoint returns current version

---

**This governance was established:** February 5, 2026  
**Current Version:** 0.2.0  
**Next Planned:** 0.2.1 (patch), 0.3.0 (MCP integration), 1.0.0 (production ready)