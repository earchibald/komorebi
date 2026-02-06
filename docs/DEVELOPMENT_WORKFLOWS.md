# Komorebi Development Workflows

*A comprehensive guide to human and AI agent collaboration in the GitHub Copilot ecosystem.*

---

## Table of Contents

1. [Overview](#overview)
2. [The Agent Ecosystem](#the-agent-ecosystem)
3. [Local Development Agents](#local-development-agents)
4. [Cloud-Based Agents](#cloud-based-agents)
5. [Background Agents](#background-agents)
6. [Workflow Patterns](#workflow-patterns)
7. [Agent Collaboration Strategies](#agent-collaboration-strategies)
8. [Best Practices](#best-practices)

---

## Overview

Modern software development leverages multiple AI agents working alongside human developers. The GitHub Copilot ecosystem provides a spectrum of agents optimized for different tasks, contexts, and response times.

### The Development Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HUMAN DEVELOPER                               │
│                    (Creative Direction & Review)                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    LOCAL      │     │     CLOUD       │     │   BACKGROUND    │
│    AGENTS     │     │     AGENTS      │     │     AGENTS      │
│               │     │                 │     │                 │
│ • Copilot     │     │ • Copilot Chat  │     │ • Copilot       │
│   Completions │     │   (github.com)  │     │   Coding Agent  │
│ • Copilot     │     │ • PR Review     │     │ • Scheduled     │
│   Chat (IDE)  │     │   Agent         │     │   Tasks         │
│ • CLI Agent   │     │ • Code Search   │     │ • Auto-fixes    │
└───────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          CODEBASE                                    │
│              (Repository, Tests, Documentation)                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## The Agent Ecosystem

### Agent Types by Response Time

| Agent Type | Latency | Context | Best For |
|------------|---------|---------|----------|
| **Local** | Milliseconds | Current file/selection | Real-time coding |
| **Cloud** | Seconds | Repository-wide | Complex questions, reviews |
| **Background** | Minutes-Hours | Full codebase + issues | Large tasks, PRs |

### Agent Capabilities Matrix

| Capability | Local | Cloud | Background |
|------------|:-----:|:-----:|:----------:|
| Code completion | ✅ | ➖ | ➖ |
| Code explanation | ✅ | ✅ | ✅ |
| Code generation | ✅ | ✅ | ✅ |
| Multi-file edits | ➖ | ✅ | ✅ |
| Test creation | ✅ | ✅ | ✅ |
| PR creation | ➖ | ➖ | ✅ |
| Issue resolution | ➖ | ➖ | ✅ |
| Code review | ➖ | ✅ | ✅ |
| Documentation | ✅ | ✅ | ✅ |
| Git operations | ➖ | ➖ | ✅ |

---

## Local Development Agents

### GitHub Copilot (Inline Completions)

**What it is:** Real-time code suggestions as you type.

**Best for:**
- Writing boilerplate code
- Completing function implementations
- Generating repetitive patterns
- Learning API syntax

**Komorebi Example:**
```python
# Type this comment, Copilot suggests the implementation
def calculate_token_count(content: str) -> int:
    # Copilot suggests: return len(content) // 4
```

**Tips:**
- Write descriptive comments to guide suggestions
- Accept partial suggestions with `Ctrl+Right`
- Cycle through alternatives with `Alt+]` / `Alt+[`

---

### GitHub Copilot Chat (IDE)

**What it is:** Conversational AI assistant integrated into VS Code, JetBrains, etc.

**Best for:**
- Explaining code
- Refactoring suggestions
- Debugging help
- Quick questions about the codebase

**Invocation:**
- `Ctrl+I` (inline chat)
- `Ctrl+Shift+I` (chat panel)
- `/` commands for specific actions

**Useful Commands:**

| Command | Purpose | Example |
|---------|---------|---------|
| `/explain` | Explain selected code | Select chunk model, `/explain` |
| `/fix` | Fix errors in selection | Select broken code, `/fix` |
| `/tests` | Generate tests | Select function, `/tests` |
| `/doc` | Generate documentation | Select class, `/doc` |
| `@workspace` | Query entire workspace | `@workspace how does compaction work?` |

**Komorebi Example:**
```
User: @workspace explain the chunk processing flow

Copilot: The chunk processing flow in Komorebi works as follows:
1. Chunks are captured via API/CLI → status: INBOX
2. CompactorService.process_chunk() analyzes content
3. Summary is generated, status → PROCESSED
4. Project compaction combines chunks → COMPACTED
...
```

---

### Copilot CLI

**What it is:** Command-line AI assistant for shell commands.

**Installation:**
```bash
gh extension install github/gh-copilot
```

**Usage:**
```bash
# Explain a command
gh copilot explain "find . -name '*.py' -exec grep -l 'async' {} \;"

# Suggest a command
gh copilot suggest "find all Python files with async functions"

# Get help with git
gh copilot suggest "undo last commit but keep changes"
```

**Komorebi Example:**
```bash
$ gh copilot suggest "run pytest with coverage for backend"

Suggestion: python -m pytest backend/tests/ --cov=backend --cov-report=html
```

---

## Cloud-Based Agents

### Copilot Chat on GitHub.com

**What it is:** AI chat integrated into GitHub's web interface.

**Access:** Click the Copilot icon on any repository page.

**Best for:**
- Understanding unfamiliar repositories
- Navigating large codebases
- Getting context without cloning

**Komorebi Example:**
```
User: What testing frameworks does this project use?

Copilot: This project uses:
- pytest for Python backend tests
- pytest-asyncio for async test support
- Playwright for frontend E2E tests
See pyproject.toml and frontend/package.json for details.
```

---

### Pull Request Review Agent

**What it is:** AI-powered code review suggestions on PRs.

**Activation:** Automatic on PRs or via `@github-copilot` mention.

**Capabilities:**
- Security vulnerability detection
- Bug identification
- Performance suggestions
- Style consistency checks

**Komorebi Example:**
```markdown
## Copilot Review Summary

### 🔒 Security
- No security issues detected

### 🐛 Potential Issues
- Line 42: `datetime.utcnow()` is deprecated, use `datetime.now(UTC)`

### 💡 Suggestions
- Consider adding error handling for the SSE connection
```

---

### Code Search with Copilot

**What it is:** Natural language code search across repositories.

**Usage:** Use the GitHub search bar with natural language.

**Examples:**
```
"function that handles chunk compaction"
"where is the SQLAlchemy session created"
"tests for the API endpoints"
```

---

## Background Agents

### GitHub Copilot Coding Agent

**What it is:** Autonomous agent that can work on issues and create PRs.

**Invocation:**
1. Assign Copilot to a GitHub Issue
2. Copilot creates a branch and works autonomously
3. Copilot opens a PR when complete
4. Human reviews and merges

**Best for:**
- Well-defined issues with clear requirements
- Bug fixes with reproduction steps
- Feature implementations with specifications
- Documentation updates
- Test additions

**Workflow:**

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   GitHub    │     │  Copilot Coding  │     │   GitHub    │
│   Issue     │────▶│      Agent       │────▶│     PR      │
│             │     │                  │     │             │
│ "Add tests  │     │ 1. Analyze issue │     │ Ready for   │
│  for stats  │     │ 2. Clone repo    │     │ review      │
│  endpoint"  │     │ 3. Write code    │     │             │
│             │     │ 4. Run tests     │     │             │
│             │     │ 5. Create PR     │     │             │
└─────────────┘     └──────────────────┘     └─────────────┘
```

**Komorebi Example Issue:**
```markdown
Title: Add integration test for SSE events

Description:
Create a test that verifies SSE events are broadcast
when chunks are created via the API.

Acceptance Criteria:
- [ ] Test connects to /api/v1/sse/events
- [ ] Test creates a chunk via API
- [ ] Test verifies event is received
- [ ] Test passes in CI
```

**Agent Output:**
- Creates branch `copilot/add-sse-integration-test`
- Implements test in `backend/tests/test_sse.py`
- Runs tests to verify
- Opens PR with description and test results

---

### Background Agent Capabilities

| Capability | Description |
|------------|-------------|
| **File Operations** | Create, edit, delete files |
| **Git Operations** | Branch, commit, push |
| **Command Execution** | Run tests, linters, builds |
| **Web Browsing** | Fetch documentation, research |
| **GitHub API** | Read issues, PRs, workflows |
| **Multi-step Planning** | Break complex tasks into steps |

---

### When to Use Background Agents

✅ **Good Candidates:**
- Clear, specific issues
- Tasks with defined acceptance criteria
- Repeatable patterns (add tests, update docs)
- Refactoring with clear scope

❌ **Poor Candidates:**
- Vague requirements
- Tasks requiring design decisions
- Security-critical changes
- Major architectural changes

---

## Workflow Patterns

### Pattern 1: Human-Led with AI Assistance

```
Human writes code → Copilot suggests completions → Human reviews
```

**Use when:** Writing new features, creative work

### Pattern 2: AI-Led with Human Review

```
Human creates issue → Agent implements → Human reviews PR
```

**Use when:** Well-defined tasks, routine work

### Pattern 3: Pair Programming with Chat

```
Human asks question → Chat explains/suggests → Human implements
```

**Use when:** Learning, debugging, exploring options

### Pattern 4: Iterative Refinement

```
Human drafts → AI suggests improvements → Human refines → AI tests
```

**Use when:** Documentation, test writing, refactoring

---

## Agent Collaboration Strategies

### Strategy 1: Divide by Layer

```
┌─────────────────────────────────────────────────┐
│ HUMAN: Architecture, Design, Critical Logic    │
├─────────────────────────────────────────────────┤
│ BACKGROUND AGENT: Tests, Docs, Routine PRs     │
├─────────────────────────────────────────────────┤
│ LOCAL AGENT: Real-time coding assistance       │
└─────────────────────────────────────────────────┘
```

### Strategy 2: Review Chain

```
Developer writes code
        │
        ▼
Local Copilot suggests improvements
        │
        ▼
Developer commits & pushes
        │
        ▼
PR Review Agent checks for issues
        │
        ▼
Human reviewer approves
```

### Strategy 3: Issue Triage

```
New Issue Created
        │
        ├─── Simple/Routine ──────▶ Assign to Copilot Agent
        │
        ├─── Medium Complexity ───▶ Human + Local Copilot
        │
        └─── Complex/Critical ────▶ Human + Cloud Chat + Review
```

---

## Best Practices

### For Local Agents

1. **Write clear comments** - Guide suggestions with intent
2. **Review all suggestions** - AI can hallucinate APIs
3. **Use @workspace** - Give context for better answers
4. **Learn the shortcuts** - Speed up your workflow

### For Cloud Agents

1. **Be specific in questions** - "How does X work in file Y?"
2. **Reference files directly** - Include paths and line numbers
3. **Iterate on answers** - Ask follow-ups for clarity
4. **Verify with docs** - Cross-reference official documentation

### For Background Agents

1. **Write detailed issues** - Include acceptance criteria
2. **Start small** - Build trust with simple tasks first
3. **Review thoroughly** - Agent output needs human verification
4. **Provide feedback** - Help the agent learn your preferences

### Security Considerations

| Practice | Reason |
|----------|--------|
| Never include secrets in prompts | Prompts may be logged |
| Review generated code for vulnerabilities | AI can introduce security issues |
| Use branch protection | Prevent direct pushes from agents |
| Enable required reviews | Human must approve agent PRs |

---

## Komorebi-Specific Workflows

### Adding a New API Endpoint

1. **Human:** Design the endpoint (method, path, payload)
2. **Local Copilot:** Generate Pydantic models from description
3. **Local Copilot:** Generate route handler with `/doc` comment
4. **Human:** Review and refine implementation
5. **Background Agent:** (via issue) Add tests for new endpoint
6. **PR Review Agent:** Check the combined PR

### Debugging an Issue

1. **Human:** Identify the symptom
2. **Local Chat:** `@workspace where is error X raised?`
3. **Local Chat:** `/explain` on the suspicious code
4. **Human:** Form hypothesis and fix
5. **Local Copilot:** Suggest test for the fix

### Documentation Updates

1. **Human:** Create issue "Update docs for feature X"
2. **Background Agent:** Analyze code and existing docs
3. **Background Agent:** Generate updated documentation
4. **Human:** Review and merge PR

---

## Quick Reference

### Local Agent Commands (VS Code)

| Shortcut | Action |
|----------|--------|
| `Tab` | Accept suggestion |
| `Esc` | Dismiss suggestion |
| `Ctrl+Right` | Accept word |
| `Alt+]` | Next suggestion |
| `Alt+[` | Previous suggestion |
| `Ctrl+I` | Inline chat |
| `Ctrl+Shift+I` | Chat panel |

### Chat Commands

| Command | Purpose |
|---------|---------|
| `/explain` | Explain code |
| `/fix` | Fix errors |
| `/tests` | Generate tests |
| `/doc` | Generate docs |
| `/simplify` | Simplify code |
| `/optimize` | Optimize code |
| `@workspace` | Full repo context |
| `@terminal` | Terminal context |

### Issue Labels for Agents

| Label | Meaning |
|-------|---------|
| `copilot` | Suitable for Copilot agent |
| `good-first-issue` | Simple, good for agent |
| `needs-design` | Not suitable for agent |
| `security` | Human review required |

---

## References

1. [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
2. [Copilot Chat Guide](https://docs.github.com/en/copilot/github-copilot-chat)
3. [Copilot CLI](https://docs.github.com/en/copilot/github-copilot-in-the-cli)
4. [Copilot for PRs](https://docs.github.com/en/copilot/github-copilot-enterprise/copilot-pull-request-summaries)

---

*This document is part of the Komorebi project documentation. For testing workflows, see [TEST_MANIFEST.md](./TEST_MANIFEST.md). For getting started, see [GETTING_STARTED.md](./GETTING_STARTED.md).*
