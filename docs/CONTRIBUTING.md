# Contributing to Komorebi

*Thank you for your interest in contributing to Komorebi! This guide will help you get started.*

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Pull Request Process](#pull-request-process)
7. [Issue Guidelines](#issue-guidelines)
8. [Documentation](#documentation)
9. [Community](#community)

---

## Code of Conduct

We are committed to providing a welcoming and inspiring community for all. Please:

- **Be respectful** and considerate
- **Be collaborative** and constructive
- **Be patient** with newcomers
- **Focus on the work**, not the person

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Git

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/komorebi.git
cd komorebi
```

3. Add upstream remote:

```bash
git remote add upstream https://github.com/earchibald/komorebi.git
```

### Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies with dev extras
pip install -e ".[dev]"

# Install frontend dependencies
cd frontend
npm install
cd ..

# Verify setup
python -m pytest  # Should pass all tests
```

### Running Locally

```bash
# Start backend (with hot reload)
komorebi serve --reload

# In another terminal, start frontend
cd frontend
npm run dev
```

---

## Development Workflow

### Branching Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable, production-ready code |
| `develop` | Integration branch for features |
| `feature/*` | New features |
| `fix/*` | Bug fixes |
| `docs/*` | Documentation updates |

### Creating a Feature Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, no code change
- `refactor`: Code change, no new feature
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
feat(api): add chunk search endpoint
fix(db): resolve race condition in compaction
docs(readme): update installation instructions
test(api): add tests for project deletion
```

### Keeping Your Branch Updated

```bash
git fetch upstream
git rebase upstream/main
```

---

## Coding Standards

### Python Style

We follow [PEP 8](https://pep8.org/) with these additions:

- **Line length:** 100 characters
- **Quotes:** Double quotes for strings
- **Docstrings:** Google style
- **Type hints:** Required for all public functions

**Example:**

```python
"""Module docstring explaining purpose."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ChunkCreate(BaseModel):
    """Schema for creating a new chunk.
    
    Args:
        content: The text content to capture.
        project_id: Optional project association.
        tags: Optional categorization tags.
    """
    
    content: str
    project_id: Optional[UUID] = None
    tags: list[str] = []


async def create_chunk(
    content: str,
    project_id: Optional[UUID] = None,
    tags: Optional[list[str]] = None,
) -> Chunk:
    """Create a new chunk in the database.
    
    Args:
        content: The text content to capture.
        project_id: Optional project to associate with.
        tags: Optional list of tags.
        
    Returns:
        The created Chunk object.
        
    Raises:
        ValidationError: If content is empty.
    """
    if not content.strip():
        raise ValidationError("Content cannot be empty")
    
    # Implementation...
    return chunk
```

### TypeScript Style

- **ESLint:** Use provided configuration
- **Prettier:** For formatting
- **Type annotations:** Prefer explicit types

**Example:**

```typescript
interface ChunkProps {
  chunk: Chunk;
  onDelete?: (id: string) => void;
}

function ChunkCard({ chunk, onDelete }: ChunkProps): JSX.Element {
  const handleDelete = (): void => {
    if (onDelete) {
      onDelete(chunk.id);
    }
  };

  return (
    <div className="chunk-card">
      <p>{chunk.content}</p>
      <button onClick={handleDelete}>Delete</button>
    </div>
  );
}
```

### Code Organization

```
backend/
├── app/
│   ├── api/          # HTTP endpoints (thin layer)
│   ├── core/         # Business logic
│   ├── db/           # Database access
│   ├── mcp/          # MCP integration
│   └── models/       # Pydantic schemas
└── tests/            # Test files mirror structure

frontend/
├── src/
│   ├── components/   # React components
│   ├── store/        # State management
│   └── theme/        # Styling
└── e2e/              # Playwright tests
```

---

## Testing Guidelines

### Running Tests

```bash
# All backend tests
python -m pytest

# With coverage
python -m pytest --cov=backend --cov-report=html

# Specific test file
python -m pytest backend/tests/test_api.py

# With verbose output
python -m pytest -v

# Frontend E2E tests
cd frontend
npm test
```

### Writing Tests

**Backend tests:**

```python
# backend/tests/test_api.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_chunk_success(client: AsyncClient):
    """Test successful chunk creation."""
    response = await client.post(
        "/api/v1/chunks",
        json={"content": "Test content"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Test content"
    assert data["status"] == "inbox"
```

**Frontend E2E tests:**

```typescript
// frontend/e2e/dashboard.spec.ts

import { test, expect } from './fixtures';

test('should capture a chunk', async ({ dashboardPage, inboxPage }) => {
  await dashboardPage.goto();
  
  await inboxPage.captureChunk('Test content');
  
  await expect(inboxPage.captureInput).toHaveValue('');
});
```

### Test Coverage

- **Minimum:** 70% coverage for new code
- **Goal:** 80%+ overall coverage
- **Required:** Tests for all public API endpoints

---

## Pull Request Process

### Before Submitting

1. **Run tests:**
   ```bash
   python -m pytest
   ```

2. **Check formatting:**
   ```bash
   # Python (if using black)
   black --check backend/ cli/
   
   # Frontend
   cd frontend && npm run lint
   ```

3. **Update documentation** if needed

4. **Add tests** for new functionality

### PR Template

When creating a PR, include:

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Self-reviewed the code
- [ ] Documented new functionality
- [ ] Updated CHANGELOG.md (if applicable)

## Related Issues
Closes #123
```

### Review Process

1. **Automated checks** must pass
2. **At least one approval** required
3. **Address all feedback** or explain why not
4. **Squash and merge** when approved

### After Merge

```bash
# Delete local branch
git branch -d feature/your-feature

# Update main
git checkout main
git pull upstream main
```

---

## Issue Guidelines

### Reporting Bugs

Include:

1. **Description:** Clear summary of the bug
2. **Steps to reproduce:** Numbered steps
3. **Expected behavior:** What should happen
4. **Actual behavior:** What actually happens
5. **Environment:** OS, Python version, browser
6. **Logs/Screenshots:** If applicable

**Template:**

```markdown
## Bug Description
Brief description of the bug.

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior
What should happen.

## Actual Behavior
What actually happens.

## Environment
- OS: Ubuntu 22.04
- Python: 3.12.1
- Browser: Chrome 120

## Additional Context
Add any other context, logs, or screenshots.
```

### Feature Requests

Include:

1. **Problem:** What problem does this solve?
2. **Solution:** Proposed solution
3. **Alternatives:** Other approaches considered
4. **Additional context:** Use cases, examples

### Good First Issues

Look for issues labeled:
- `good-first-issue` - Beginner friendly
- `help-wanted` - Community help welcome
- `documentation` - Docs improvements

---

## Documentation

### Where to Document

| Content | Location |
|---------|----------|
| API endpoints | `docs/API_REFERENCE.md` |
| Configuration | `docs/CONFIGURATION.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Deployment | `docs/DEPLOYMENT.md` |
| Code docstrings | In source files |

### Documentation Style

- **Clear and concise** - Get to the point
- **Examples** - Show, don't just tell
- **Keep updated** - Update with code changes
- **Markdown** - Use proper formatting

### Building Docs

```bash
# Generate API docs from OpenAPI
curl http://localhost:8000/openapi.json > docs/openapi.json

# View generated docs
open http://localhost:8000/docs
```

---

## Community

### Getting Help

- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - Questions and ideas
- **Code Review** - Feedback on PRs

### Recognition

Contributors are recognized in:
- `CHANGELOG.md` - For significant contributions
- GitHub contributors list

### Maintainers

Current maintainers:
- @earchibald - Project lead

---

## Quick Reference

### Commands

```bash
# Setup
pip install -e ".[dev]"

# Run backend
komorebi serve --reload

# Run tests
python -m pytest -v

# Run frontend
cd frontend && npm run dev

# Run E2E tests
cd frontend && npm test
```

### Checklist for Contributors

- [ ] Forked repository
- [ ] Created feature branch
- [ ] Made changes
- [ ] Added tests
- [ ] Ran tests locally
- [ ] Updated documentation
- [ ] Created pull request
- [ ] Addressed review feedback

---

## Related Documentation

- [Getting Started](./GETTING_STARTED.md) - Installation and usage
- [API Reference](./API_REFERENCE.md) - Complete API documentation
- [Architecture](./ARCHITECTURE.md) - Technical deep dive
- [Test Manifest](./TEST_MANIFEST.md) - Testing documentation

---

*Thank you for contributing to Komorebi! Your help makes this project better for everyone.*
