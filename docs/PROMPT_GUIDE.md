# Komorebi Prompts & Skills Guide

**Version:** 1.0.0  
**Last Updated:** February 5, 2026

This guide explains how to use the custom prompts and agent skills in the Komorebi project.

---

## Quick Reference

### Available Prompts

| Prompt | Command | Model | When to Use |
|--------|---------|-------|-------------|
| Implement Feature | `/implement-feature` | Sonnet | Creating new features with TDD |
| Write Tests | `/write-tests` | Sonnet | Generating test suites |
| Debug Issue | `/debug-issue` | Opus | Complex debugging |
| Review PR | `/review-pr` | Sonnet | Code reviews |
| Update Docs | `/update-docs` | Haiku | Documentation updates |
| Refactor Code | `/refactor-code` | Sonnet | Improving code structure |
| Architect Feature | `/architect-feature` | Opus | Complex feature design |

### Available Skills

| Skill | Tier | Description |
|-------|------|-------------|
| `feature-implementer` | Standard | Full-stack feature scaffolding |
| `code-formatter` | Economy | Format and lint code |

---

## How Prompts Work

### What are Prompts?

Prompts are pre-configured workflow templates that provide:
- Task-specific instructions
- Project governance rules (automatically injected)
- Code patterns and examples
- Step-by-step workflows

### Using Prompts

**Method 1: Slash Command**

Type `/` in the VS Code Copilot chat, then select a prompt:
```
/implement-feature
```

You can add context after the prompt name:
```
/implement-feature Create a task management API with CRUD operations
```

**Method 2: Command Palette**

1. Open Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`)
2. Run **"Chat: Run Prompt"**
3. Select a prompt from the list

**Method 3: Open Prompt File**

1. Open the prompt file in `.github/prompts/`
2. Click the play button in the editor title bar

---

## Prompt Reference

### `/implement-feature`

**Purpose:** Implement new features using TDD workflow  
**Model:** Auto (Claude Sonnet 4 / GPT-4o)  
**Best for:** CRUD features, API endpoints, React components

**What it does:**
1. Guides you through TDD (Red → Green → Refactor → Hammer)
2. Provides Pydantic, FastAPI, and React patterns
3. Ensures governance compliance (docs, tests, quality)

**Example usage:**
```
/implement-feature

I need to implement a task management feature with:
- Create, read, update, delete operations
- Task has title, description, status, due_date
- Tasks can be assigned to projects
```

**Output includes:**
- Test file with stubs
- Pydantic schemas (Create/Update/Read)
- FastAPI router with endpoints
- React component with Preact Signals

---

### `/write-tests`

**Purpose:** Generate comprehensive test suites  
**Model:** Auto (Claude Sonnet 4 / GPT-4o)  
**Best for:** Unit tests, API tests, integration tests

**What it does:**
1. Analyzes code to test
2. Generates pytest test cases
3. Covers happy path + error cases + edge cases
4. Follows project testing conventions

**Example usage:**
```
/write-tests

Write tests for backend/app/api/chunks.py

Focus on:
- CRUD operations
- Validation errors
- Pagination
```

**Output includes:**
- pytest test file
- Async test patterns
- TestClient setup
- Mocking examples

---

### `/debug-issue`

**Purpose:** Systematic debugging of complex issues  
**Model:** Claude Opus 4 (Premium)  
**Best for:** Race conditions, async bugs, performance issues

**What it does:**
1. Guides through 6-phase debugging workflow
2. Helps form hypotheses
3. Provides debugging tools and techniques
4. Creates regression tests

**Example usage:**
```
/debug-issue

I'm seeing "coroutine was never awaited" errors when 
processing multiple chunks concurrently. The error is 
intermittent and only happens under load.
```

**Output includes:**
- Issue analysis
- Hypotheses ranked by probability
- Debugging steps
- Fix implementation
- Regression test

---

### `/review-pr`

**Purpose:** Comprehensive pull request review  
**Model:** Claude Sonnet 4  
**Best for:** Code review before merging

**What it does:**
1. Security review (secrets, SQL injection, XSS)
2. Convention compliance check
3. Test coverage verification
4. Documentation sync check
5. Performance review
6. Breaking change detection

**Example usage:**
```
/review-pr

Review PR #42: Add chunk favoriting feature

Changed files:
- backend/app/api/chunks.py
- backend/app/models/chunk.py
- backend/tests/test_chunks.py
```

**Output includes:**
- Structured review report
- Security findings
- Required changes
- Suggestions (non-blocking)

---

### `/update-docs`

**Purpose:** Synchronize documentation with code changes  
**Model:** Claude 3.5 Haiku (Economy)  
**Best for:** Quick documentation updates

**What it does:**
1. Identifies which docs need updating
2. Generates appropriate entries
3. Ensures Pre-1.0.0 governance compliance

**Example usage:**
```
/update-docs

Just implemented chunk favoriting feature. Need to update:
- CHANGELOG.md
- PROGRESS.md
```

**Output includes:**
- CHANGELOG.md entry
- PROGRESS.md update
- CURRENT_STATUS.md update (if version change)

---

### `/refactor-code`

**Purpose:** Refactoring while maintaining behavior  
**Model:** Claude Sonnet 4  
**Best for:** Code improvement without changing functionality

**What it does:**
1. Establishes test baseline
2. Identifies specific code smell
3. Applies appropriate refactoring pattern
4. Verifies behavior is preserved

**Example usage:**
```
/refactor-code

Refactor backend/app/core/compactor.py

The process_chunk method is too long (50+ lines). 
Extract helper methods for better readability.
```

**Output includes:**
- Smell identification
- Refactoring technique used
- Risk assessment
- Test verification
- Clean, focused changes

---

### `/architect-feature`

**Purpose:** Design complex features before implementation  
**Model:** Claude Opus 4 (Premium)  
**Best for:** Multi-layer features, new integrations

**What it does:**
1. Analyzes requirements thoroughly
2. Creates component and data model diagrams
3. Documents trade-offs explicitly
4. Produces implementation plan

**Example usage:**
```
/architect-feature

Design the MCP Tool Browser feature:
- Browse available tools from connected MCP servers
- Invoke tools with parameters
- Save results as chunks
```

**Output includes:**
- Requirements analysis
- System design (components, API, data model)
- Trade-off documentation
- Task breakdown with estimates

---

## How Skills Work

### What are Skills?

Skills are folders containing:
- Instructions (SKILL.md)
- Scripts (helper tools)
- References (documentation)
- Assets (templates)

Skills are loaded on-demand when relevant to your task.

### Skill Loading

Skills are automatically loaded based on task context:
- Copilot reads skill descriptions
- Relevant skills are loaded into context
- Scripts and references are available

You can also explicitly invoke skills by mentioning them.

---

## Skill Reference

### `feature-implementer` (Standard Tier)

**Location:** `.github/skills/standard-tier/feature-implementer/`  
**Purpose:** Full-stack feature scaffolding

**Contents:**
- `SKILL.md` - Instructions and patterns
- `scripts/generate_scaffold.py` - Code generator
- `scripts/validate_feature.py` - Convention checker

**Usage:**
```bash
# Generate feature scaffold
python .github/skills/standard-tier/feature-implementer/scripts/generate_scaffold.py task_management

# Validate implementation
python .github/skills/standard-tier/feature-implementer/scripts/validate_feature.py backend/app/api/tasks.py
```

**What it generates:**
- `backend/app/models/<feature>.py` - Pydantic schemas
- `backend/app/repositories/<feature>.py` - Data access
- `backend/app/api/<features>.py` - API endpoints
- `backend/tests/test_<features>.py` - Test stubs
- `frontend/src/store/<features>.ts` - Signals store
- `frontend/src/components/<Feature>List.tsx` - React component

---

### `code-formatter` (Economy Tier)

**Location:** `.github/skills/economy-tier/code-formatter/`  
**Purpose:** Format and lint code

**Contents:**
- `SKILL.md` - Ruff commands and lint fixes

**Usage:**
```bash
# Format all Python files
ruff format .

# Fix lint errors
ruff check --fix .

# Organize imports
ruff check --select I --fix .
```

---

## Model Tier Strategy

### Why Different Tiers?

Different tasks require different capabilities:
- **Simple tasks** (formatting, docs): Fast, cheap models work fine
- **Standard tasks** (features, tests): Balanced models needed
- **Complex tasks** (debugging, architecture): Premium models required

### Tier Definitions

| Tier | Models | Cost | Best For |
|------|--------|------|----------|
| Economy | Claude 3.5 Haiku | 1x | Formatting, simple docs |
| Standard | Auto (Sonnet/GPT-4o) | 5-10x | Features, tests, general |
| Premium | Claude Opus 4 | 50-75x | Debugging, architecture |
| Research | Gemini 3 Pro | 40-60x | Research, long-context |

### Model Selection in Prompts

Prompts automatically specify the appropriate model in their frontmatter:
```yaml
---
name: debug-issue
model: Claude Opus 4  # Uses premium model
---
```

You can override by selecting a different model in VS Code's model picker before running the prompt.

---

## Telemetry

### Tracking Usage

Track prompt/skill usage to measure value:

```bash
# Log usage
python scripts/telemetry/telemetry_tracker.py log implement-feature standard --duration 120

# View usage report
python scripts/telemetry/telemetry_tracker.py report --days 7

# View cost analysis
python scripts/telemetry/telemetry_tracker.py costs --days 30
```

### Sample Report

```
📊 Telemetry Report (Last 7 days)
============================================================

📈 Overview
   Total invocations: 42
   Success rate: 95.2%
   Total time: 84.0 minutes
   Avg time per task: 120.0 seconds

🔧 By Prompt/Skill
   implement-feature: 18 (42.9%)
   write-tests: 12 (28.6%)
   debug-issue: 6 (14.3%)
   update-docs: 6 (14.3%)

🎯 By Model Tier
   standard: 30 (71.4%)
   economy: 6 (14.3%)
   premium: 6 (14.3%)
```

---

## Troubleshooting

### Prompts Not Appearing

If prompts don't appear when typing `/`:

1. Check that prompt files exist in `.github/prompts/`
2. Verify file extension is `.prompt.md`
3. Reload VS Code (`Cmd+Shift+P` → "Reload Window")
4. Check diagnostics: Right-click in Chat → "Diagnostics"

### Skills Not Loading

If skills aren't being used:

1. Verify skill folder has `SKILL.md` file
2. Check that skill description matches your task
3. Explicitly mention the skill name in your prompt
4. Check diagnostics for loading errors

### Model Not Available

If a specific model isn't available:

1. Check your Copilot subscription includes the model
2. Use the model picker to select an available model
3. The prompt will work with any model, just optimize for the specified one

### Scripts Not Working

If scaffold generator or validator fails:

1. Ensure Python 3.11+ is installed
2. Run from project root directory
3. Check file paths are correct

---

## Best Practices

### 1. Start with Prompts

Use prompts for structured workflows:
```
/implement-feature <description>
```

Prompts provide guardrails and ensure governance.

### 2. Use Skills for Scaffolding

Generate boilerplate with skills:
```bash
python .github/skills/standard-tier/feature-implementer/scripts/generate_scaffold.py my_feature
```

Then customize the generated code.

### 3. Match Task to Tier

- Simple formatting → Economy tier
- Standard development → Auto
- Complex problems → Premium tier

### 4. Log Telemetry

Track usage to measure ROI:
```bash
python scripts/telemetry/telemetry_tracker.py log <prompt> <tier> --duration <seconds>
```

### 5. Update Documentation

After every feature, run:
```
/update-docs
```

This ensures governance compliance.

---

## Quick Commands

```bash
# Generate feature scaffold
python .github/skills/standard-tier/feature-implementer/scripts/generate_scaffold.py <feature_name>

# Validate feature
python .github/skills/standard-tier/feature-implementer/scripts/validate_feature.py <file_path>

# Format code
ruff format . && ruff check --fix .

# Run tests
pytest backend/tests/

# Log telemetry
python scripts/telemetry/telemetry_tracker.py log <prompt> <tier>

# View telemetry
python scripts/telemetry/telemetry_tracker.py report --days 7
```

---

## Next Steps

1. **Try a prompt:** `/implement-feature Create a simple task list`
2. **Generate scaffold:** Use the scaffold generator for your next feature
3. **Track usage:** Start logging telemetry to measure value
4. **Provide feedback:** Note what works and what doesn't for iteration

---

## Related Documentation

- [PROMPTS_AND_SKILLS_PROPOSAL.md](./PROMPTS_AND_SKILLS_PROPOSAL.md) - Full strategy document
- [PROMPTS_SKILLS_AUDIT.md](./PROMPTS_SKILLS_AUDIT.md) - Audit and recommendations
- [CONVENTIONS.md](../CONVENTIONS.md) - Code patterns and best practices
- [copilot-instructions.md](../.github/copilot-instructions.md) - Project governance

---

**Happy coding with AI assistance!** 🚀
