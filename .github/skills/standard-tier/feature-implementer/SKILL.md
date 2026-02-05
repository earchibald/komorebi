---
name: feature-implementer
description: Guide for implementing full-stack features in Komorebi using TDD workflow. Use when creating new API endpoints, React components, or CRUD features.
---

# Feature Implementer

## About This Skill

This skill accelerates feature implementation in the Komorebi project by providing:
- TDD workflow guidance (Red → Green → Refactor → Hammer)
- Code scaffolding for common patterns
- Backend (FastAPI/Pydantic) and frontend (React/Signals) templates
- Validation to ensure conventions are followed

## When to Use

Invoke this skill when:
- Implementing a new CRUD feature (e.g., task management, project tracking)
- Adding a new API endpoint with tests
- Creating a new React component with state management
- Building full-stack features from specification

**Example triggers:**
- "Implement a new feature for managing projects"
- "Create a CRUD API for tasks"
- "Build a dashboard component with real-time updates"

## Quick Start

1. **Generate Scaffold:**
   ```bash
   python .github/skills/standard-tier/feature-implementer/scripts/generate_scaffold.py <feature_name>
   ```

2. **Write Tests First (Red):**
   - Edit `backend/tests/test_<feature>.py`
   - Run: `pytest backend/tests/test_<feature>.py` → Should fail

3. **Implement (Green):**
   - Edit Pydantic schemas, repository, API endpoints
   - Run: `pytest backend/tests/test_<feature>.py` → Should pass

4. **Refactor (Clean):**
   - Extract duplicated logic
   - Verify tests still pass

5. **Update Documentation:**
   - Add CHANGELOG.md entry
   - Update PROGRESS.md

## Bundled Resources

### Scripts

**`scripts/generate_scaffold.py`** - Creates feature scaffolding:
- Pydantic models (Create/Update/Read schemas)
- Repository with CRUD methods
- FastAPI router with endpoints
- Test file with stubs
- Frontend signals store
- React list component

Usage: `python scripts/generate_scaffold.py <feature_name> [--backend-only] [--frontend-only]`

**`scripts/validate_feature.py`** - Validates conventions:
- Type hints on all functions
- Async/await patterns
- No hardcoded secrets
- Proper schema separation

Usage: `python scripts/validate_feature.py <file_path>`

### References

**`references/tdd_workflow.md`** - Detailed TDD guidance (load for TDD questions)

**`references/api_patterns.md`** - FastAPI patterns (load for API implementation)

**`references/component_patterns.md`** - React+Signals patterns (load for frontend)

### Templates

**`assets/api_templates/crud_endpoint.py.template`** - CRUD API starter

**`assets/component_templates/list_component.tsx.template`** - React list component

## TDD Workflow Summary

### Step 1: Red (Failing Tests)
```python
@pytest.mark.asyncio
async def test_create_feature_success():
    response = client.post("/api/v1/features", json={"name": "Test"})
    assert response.status_code == 201
```
Run: `pytest` → Tests fail ✅

### Step 2: Green (Minimal Implementation)
```python
@router.post("", response_model=Feature, status_code=201)
async def create_feature(feature_create: FeatureCreate):
    return await feature_repo.create(feature_create)
```
Run: `pytest` → Tests pass ✅

### Step 3: Refactor (Clean Up)
- Extract helpers
- Improve naming
- Run: `pytest` → Tests still pass ✅

### Step 4: Hammer (Stress Test)
```bash
python scripts/hammer_gen.py --size 500 --feature features
```

## Backend Patterns

### Pydantic Schema Pattern
```python
class FeatureCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class FeatureUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None

class Feature(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str
```

### FastAPI Endpoint Pattern
```python
@router.post("", response_model=Feature, status_code=201)
async def create_feature(
    feature_create: FeatureCreate,
    db: AsyncSession = Depends(get_db),
) -> Feature:
    return await feature_repo.create(feature_create)

@router.get("/{feature_id}", response_model=Feature)
async def get_feature(feature_id: UUID) -> Feature:
    feature = await feature_repo.get(feature_id)
    if not feature:
        raise HTTPException(status_code=404, detail=f"Feature {feature_id} not found")
    return feature
```

### Repository Pattern
```python
class FeatureRepository:
    async def create(self, feature_create: FeatureCreate) -> Feature:
        db_feature = FeatureTable(**feature_create.model_dump())
        self.session.add(db_feature)
        await self.session.commit()
        await self.session.refresh(db_feature)
        return self._to_model(db_feature)
```

## Frontend Patterns

### Signals Store Pattern
```typescript
export const features = signal<Feature[]>([])
export const loading = signal(false)
export const error = signal<string | null>(null)

export async function fetchFeatures(limit = 100) {
    loading.value = true
    error.value = null
    try {
        const response = await fetch(`${API_URL}/features?limit=${limit}`)
        features.value = await response.json()
    } catch (err) {
        error.value = err instanceof Error ? err.message : 'Unknown error'
    } finally {
        loading.value = false
    }
}
```

### React Component Pattern
```tsx
export function FeatureList() {
    useEffect(() => { fetchFeatures() }, [])
    
    const filteredFeatures = useMemo(() => 
        features.value.filter(f => f.status === filter),
        [features.value, filter]
    )
    
    return (
        <div>
            {loading.value ? <Loading /> : (
                filteredFeatures.map(f => <FeatureCard key={f.id} feature={f} />)
            )}
        </div>
    )
}
```

## Validation Checklist

Before completing a feature:
- [ ] Type hints on all functions
- [ ] Async/await on all I/O operations
- [ ] No hardcoded secrets
- [ ] Tests exist and pass
- [ ] CHANGELOG.md updated
- [ ] PROGRESS.md updated

## Notes

- All I/O operations must use async/await
- Use Pydantic v2 patterns (`model_validate`, not `from_orm`)
- Return Pydantic models directly (not wrapped in `{"data": ...}`)
- Frontend uses Preact Signals for shared state
- Tests use pytest + pytest-asyncio

---

**Ready to implement features efficiently!**
