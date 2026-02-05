---
name: code-formatter
description: Format and lint Python and TypeScript code using Ruff and project conventions. Use for formatting files, organizing imports, fixing lint errors.
---

# Code Formatter

## About This Skill

This skill helps format and lint Komorebi code following project conventions:
- Python formatting with Ruff
- Import organization
- Lint error fixing
- Consistent code style

This is a low-cost, high-speed skill suitable for simple formatting tasks.

## When to Use

Invoke this skill when:
- Formatting Python or TypeScript files
- Organizing imports
- Fixing lint errors
- Cleaning up code style before commit

**Example triggers:**
- "Format this file"
- "Fix the linting errors"
- "Organize the imports"
- "Clean up this code"

## Quick Commands

### Python Formatting (Ruff)

**Format entire project:**
```bash
ruff format .
```

**Format specific file:**
```bash
ruff format backend/app/api/chunks.py
```

**Check formatting (dry run):**
```bash
ruff format --check .
```

### Python Linting (Ruff)

**Check for lint errors:**
```bash
ruff check .
```

**Fix auto-fixable errors:**
```bash
ruff check --fix .
```

**Check specific file:**
```bash
ruff check backend/app/api/chunks.py --fix
```

### Import Organization

**Sort imports with Ruff:**
```bash
ruff check --select I --fix .
```

## Ruff Configuration

The project uses Ruff for both formatting and linting. Key settings:

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # Pyflakes
    "I",   # isort
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
]
ignore = [
    "E501",  # Line too long (handled by formatter)
]

[tool.ruff.lint.isort]
known-first-party = ["backend", "frontend"]
```

## Common Lint Fixes

### E401: Multiple imports on one line
```python
# ❌ Before
import os, sys, pathlib

# ✅ After
import os
import pathlib
import sys
```

### F401: Imported but unused
```python
# ❌ Before
import os  # Not used

# ✅ After (remove the import)
```

### I001: Import order
```python
# ❌ Before (wrong order)
from backend.app.models import Chunk
import os
from fastapi import APIRouter

# ✅ After (stdlib → third-party → first-party)
import os

from fastapi import APIRouter

from backend.app.models import Chunk
```

### E711: Comparison to None
```python
# ❌ Before
if result == None:

# ✅ After
if result is None:
```

### B006: Mutable default argument
```python
# ❌ Before
def process(items: list = []):

# ✅ After
def process(items: list | None = None):
    if items is None:
        items = []
```

### UP: Modern Python syntax
```python
# ❌ Before (old style)
from typing import Optional, List
items: Optional[List[str]]

# ✅ After (Python 3.11+)
items: list[str] | None
```

## TypeScript Formatting

### ESLint + Prettier (if configured)

**Check formatting:**
```bash
cd frontend && npm run lint
```

**Fix auto-fixable:**
```bash
cd frontend && npm run lint -- --fix
```

### Manual TypeScript Style

**Import organization:**
```typescript
// ✅ Correct order
// 1. React/framework imports
import { useEffect, useState } from 'react'

// 2. Third-party imports
import { signal } from '@preact/signals-react'

// 3. Local imports
import { chunks } from '../store'
import type { Chunk } from '../types'
```

**Component structure:**
```typescript
// 1. Imports
import { ... } from '...'

// 2. Types
interface Props { ... }

// 3. Component
export function MyComponent() { ... }

// 4. Helper functions (if needed)
function helperFunction() { ... }
```

## Workflow

### Pre-Commit Check

Before committing, run:
```bash
# Python
ruff format . && ruff check --fix .

# Frontend (if configured)
cd frontend && npm run lint -- --fix
```

### CI/CD Check

The GitHub Actions workflow will run:
```bash
ruff check .
ruff format --check .
```

## Integration with Other Skills

This skill is often used after:
- `feature-implementer` - Format generated code
- `debug-issue` - Clean up after fixing bugs

And before:
- `review-pr` - Ensure code is formatted before review

## Checklist

Before committing:
- [ ] Run `ruff format .`
- [ ] Run `ruff check --fix .`
- [ ] No lint errors remain
- [ ] Imports are organized
- [ ] No unused imports

---

**Ready to format and lint code efficiently!**
