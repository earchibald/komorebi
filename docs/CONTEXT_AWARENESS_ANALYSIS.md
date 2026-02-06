# Context Awareness Analysis for Skills & Prompts

**Date:** February 6, 2026  
**Purpose:** Assess how well skills and prompts can derive information from chat history

---

## How VS Code Copilot Context Works

### Automatic Context Injection

VS Code Copilot automatically provides:
1. **Current file** - The file open in the editor
2. **Visible code** - Code visible in the viewport
3. **Recent edits** - Recent changes in the workspace
4. **Chat history** - Recent conversation turns (limited window)

### Skill Loading Mechanism

Skills are loaded progressively:
1. **Level 1 (Always):** Skill metadata (name, description) from all `.github/skills/*/SKILL.md`
2. **Level 2 (On Match):** Full SKILL.md content when description matches user query
3. **Level 3 (On Reference):** Additional resources when explicitly mentioned

---

## Current Skills: Context Awareness Assessment

### ✅ feature-implementer (GOOD Context Awareness)

**Description:** "Guide for implementing full-stack features in Komorebi using TDD workflow. Use when creating new API endpoints, React components, or CRUD features."

**Auto-loads when user mentions:**
- "implement a feature"
- "create a CRUD API"
- "build a React component"
- "new API endpoint"

**Explicit input needed:**
- Feature name (e.g., "task_management")
- Backend-only vs full-stack

**Can derive from context:**
- ✅ Project structure (reads codebase)
- ✅ Existing patterns (reads CONVENTIONS.md)
- ✅ Tech stack (infers from imports)

**Improvement opportunities:**
- Could scan recent chat for feature name if not provided
- Could detect "backend-only" vs "full-stack" from conversation

**Score:** 7/10 - Works well with minimal input

---

### ✅ code-formatter (EXCELLENT Context Awareness)

**Description:** "Ruff-based code formatting and linting for Python files"

**Auto-loads when user mentions:**
- "format code"
- "fix linting errors"
- "clean up imports"

**Explicit input needed:**
- None! Can run on current file or entire project

**Can derive from context:**
- ✅ Current file from editor
- ✅ All Python files from workspace
- ✅ Ruff config from pyproject.toml

**Improvement opportunities:**
- None - already optimal for its purpose

**Score:** 10/10 - Zero-input operation

---

## Prompts: Context Awareness Assessment

### `/implement-feature` (MODERATE Context Awareness)

**Requires:**
- Feature description (what to implement)
- Optional: Backend vs frontend preference

**Can derive from context:**
- ✅ Project conventions (injected automatically)
- ✅ Existing code patterns
- ✅ Test patterns

**Missing auto-context:**
- ❌ Cannot infer feature name from "implement the feature we just discussed"
- ❌ Cannot read previous conversation to get requirements

**Improvement:**
- Add section: "If feature was discussed earlier, summarize requirements first"

**Score:** 6/10 - Needs explicit description

---

### `/write-tests` (GOOD Context Awareness)

**Requires:**
- File path to test (e.g., `backend/app/api/chunks.py`)

**Can derive from context:**
- ✅ Code to test (reads the file)
- ✅ Existing test patterns
- ✅ Related models and types

**Missing auto-context:**
- ❌ Doesn't auto-detect "the file I just edited"

**Improvement:**
- Could default to current editor file if path not provided

**Score:** 7/10 - Works well with file path

---

### `/debug-issue` (EXCELLENT Context Awareness)

**Requires:**
- Error description or symptoms

**Can derive from context:**
- ✅ Recent code changes (via Git)
- ✅ Related files (via search)
- ✅ Stack traces (if pasted)

**Missing auto-context:**
- None - already prompts for full context gathering

**Score:** 9/10 - Very context-driven workflow

---

### `/review-pr` (MODERATE Context Awareness)

**Requires:**
- PR number OR list of changed files

**Can derive from context:**
- ✅ File changes (via Git diff)
- ✅ Conventions to check against
- ✅ Security patterns

**Missing auto-context:**
- ❌ Cannot auto-detect current Git branch/PR
- ❌ Doesn't read GitHub PR metadata directly

**Improvement:**
- Could run `gh pr view --json` to get PR info
- Could default to current branch's diff

**Score:** 6/10 - Needs PR context explicitly

---

### `/update-docs` (GOOD Context Awareness)

**Requires:**
- Brief description of what changed

**Can derive from context:**
- ✅ Recent commits (via `git log`)
- ✅ Changed files (via `git diff`)
- ✅ Version from CURRENT_STATUS.md

**Missing auto-context:**
- None - designed to be lightweight

**Score:** 8/10 - Works with minimal input

---

### `/refactor-code` (GOOD Context Awareness)

**Requires:**
- File to refactor
- Optional: Specific smell to fix

**Can derive from context:**
- ✅ Code to refactor (reads file)
- ✅ Test coverage (runs pytest)
- ✅ Related files

**Missing auto-context:**
- ❌ Doesn't default to current editor file

**Improvement:**
- Could assume current file if in editor

**Score:** 7/10 - Works with file path

---

### `/architect-feature` (MODERATE Context Awareness)

**Requires:**
- Feature requirements (user stories)
- Constraints

**Can derive from context:**
- ✅ Existing architecture (reads ARCHITECTURE.md)
- ✅ Tech stack conventions
- ✅ Related components

**Missing auto-context:**
- ❌ Cannot infer requirements from prior discussion
- ❌ Doesn't read GitHub issues directly

**Improvement:**
- Could integrate `gh issue view` to pull requirement
- Could prompt to scan recent chat for requirements

**Score:** 6/10 - Needs explicit requirements

---

## Overall Analysis

### Strengths
1. **Structural context** - All prompts/skills understand project structure well
2. **Convention awareness** - Governance rules are injected automatically
3. **Code patterns** - Can derive patterns from existing code

### Weaknesses
1. **Chat history** - Cannot reference "the feature we discussed earlier"
2. **External systems** - Don't integrate with GitHub API for PRs/issues
3. **Editor state** - Don't default to "current file in editor"

---

## Recommendations for Improvement

### Quick Wins (High Impact, Low Effort)

1. **Default to Editor File:**
   ```
   If no file path provided:
   1. Check if a file is open in editor
   2. Use that file as default target
   ```

2. **Add Chat History Reminder:**
   ```
   Add to each prompt's intro:
   "If this relates to a previous discussion, please summarize
   the key requirements first."
   ```

3. **Git Integration:**
   ```
   For /review-pr and /update-docs:
   - Run `git diff main...HEAD` to get changes
   - Run `git branch --show-current` for PR context
   ```

### Medium Wins (High Impact, Medium Effort)

4. **GitHub CLI Integration:**
   ```
   For /review-pr:
   - Run `gh pr view --json files,title,body`
   - Auto-populate PR context
   ```

5. **File Watcher:**
   ```
   For /write-tests:
   - Watch for saved files in last 5 minutes
   - Suggest "Write tests for recently edited <file>"
   ```

### Advanced Wins (High Impact, High Effort)

6. **MCP Memory Integration:**
   ```
   Store conversation context in MCP memory:
   - Feature requirements from chat
   - Design decisions made
   - User preferences
   ```

7. **VS Code Extension:**
   ```
   Build custom extension to:
   - Track editor state (current file, cursor position)
   - Inject into Copilot context automatically
   ```

---

## Implementation Priority

### Phase 1 (Immediate - This Session)
- [x] Document context requirements in each prompt
- [ ] Add "chat summary" reminder to prompts
- [ ] Implement Git integration for /review-pr

### Phase 2 (Next Session)
- [ ] GitHub CLI integration
- [ ] Default-to-editor-file logic
- [ ] File watcher for test generation

### Phase 3 (Future)
- [ ] MCP memory integration (when MCP is production-ready)
- [ ] Custom VS Code extension (if needed)

---

## Conclusion

**Current Score:** 7/10 - Good, but can improve

**Strengths:**
- Skills load automatically when relevant
- Structural context is excellent
- Conventions are auto-injected

**Key Gap:**
- Cannot reference prior conversation without explicit re-stating

**Next Step:**
- Add explicit "context gathering" phase to each prompt
- Integrate Git/GitHub CLI for automatic context
- Consider MCP memory for conversation persistence
