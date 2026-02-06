# Komorebi: VS Code Custom Prompts & Agent Skills Strategy

**Proposal Date:** February 5, 2026  
**Version:** 1.0.0  
**Status:** Draft for Review

---

## Executive Summary

This document proposes a comprehensive strategy for implementing VS Code custom prompts and agent skills that optimize task delegation across AI models of varying capabilities and costs. The strategy aims to reduce friction in common development workflows while intelligently routing tasks to the most appropriate AI model based on complexity, required reasoning depth, and cost-effectiveness.

### Key Objectives

1. **Minimize typing friction** through domain-specific custom prompts
2. **Optimize cost efficiency** by delegating tasks to appropriate AI tiers
3. **Inject governance constraints** automatically into all agent interactions
4. **Enable model-specific skills** that leverage unique capabilities

### Model Tier Strategy

| Tier | Models | Use Cases | Cost Factor |
|------|--------|-----------|-------------|
| **Economy** | Claude Haiku 4.5 | Simple refactoring, formatting, basic tests | 1x (baseline) |
| **Standard** | Auto (GPT-4o, Claude Sonnet) | Feature implementation, API work, general tasks | 5-10x |
| **Premium** | Claude Opus 4.5/4.6 | Complex architecture, reasoning, debugging | 50-75x |
| **Research** | Gemini 3 Pro | Advanced research, long-context analysis, multi-modal | 40-60x |

---

## Section 1: VS Code Custom Prompts

### 1.1 Architecture

Custom prompts are markdown files stored in `.github/prompts/` with the naming convention:

```
.github/prompts/
├── implement-feature.prompt.md
├── write-tests.prompt.md
├── refactor-code.prompt.md
├── review-pr.prompt.md
├── debug-issue.prompt.md
├── update-docs.prompt.md
└── architect-feature.prompt.md
```

Each prompt file contains:
1. **YAML Frontmatter**: Metadata and configuration
2. **Governance Injection**: Automatic inclusion of MUST-follow directives
3. **Domain Context**: Pre-loaded project conventions and patterns
4. **Execution Template**: Structured workflow for the task

### 1.2 Proposed Custom Prompts

#### 1.2.1 `implement-feature.prompt.md`
**Purpose:** Fast-track feature implementation from specification to working code  
**Complexity:** Standard (Auto)  
**Includes:**
- TDD workflow (Red → Green → Refactor)
- CONVENTIONS.md patterns
- Pydantic/FastAPI/React conventions
- Automatic test generation

#### 1.2.2 `write-tests.prompt.md`
**Purpose:** Generate comprehensive test suites for existing code  
**Complexity:** Standard (Auto)  
**Includes:**
- Pytest async patterns
- TestClient setup
- Edge case coverage checklist
- Hammer test integration points

#### 1.2.3 `refactor-code.prompt.md`
**Purpose:** Safe, surgical code improvements  
**Complexity:** Economy (Haiku) for simple / Standard (Auto) for complex  
**Includes:**
- "Minimal changes" directive
- Type safety verification
- Pattern consistency checks
- Regression test requirements

#### 1.2.4 `review-pr.prompt.md`
**Purpose:** Comprehensive pull request review  
**Complexity:** Standard (Auto) / Premium (Opus) for critical paths  
**Includes:**
- Security checklist (no hardcoded secrets)
- Convention compliance
- Test coverage verification
- Documentation update check

#### 1.2.5 `debug-issue.prompt.md`
**Purpose:** Systematic debugging workflow  
**Complexity:** Premium (Opus) for complex issues  
**Includes:**
- Reproduction step capture
- Log analysis patterns
- Hypothesis-driven debugging
- Fix verification workflow

#### 1.2.6 `update-docs.prompt.md`
**Purpose:** Keep documentation synchronized with code  
**Complexity:** Economy (Haiku) / Standard (Auto)  
**Includes:**
- Documentation suite checklist
- CURRENT_STATUS.md update reminder
- CHANGELOG.md format
- Version synchronization check

#### 1.2.7 `architect-feature.prompt.md`
**Purpose:** High-level system design and planning  
**Complexity:** Premium (Opus) / Research (Gemini 3 Pro)  
**Includes:**
- Data flow analysis
- Schema design patterns
- Integration points
- Performance considerations

### 1.3 Governance Injection Pattern

Each custom prompt automatically injects critical governance rules:

```markdown
## Governance (MUST Follow)

### Pre-1.0.0 Documentation Rule
- Always update CURRENT_STATUS.md with version and date
- Synchronize all documentation: CHANGELOG.md, CONVENTIONS.md, BUILD.md, PROGRESS.md
- Document new features, fixes, and breaking changes immediately

### Prime Directives
1. **Capture-First Architecture:** Ingestion endpoints never block (202 Accepted)
2. **Strict State Isolation:** Main (prod) / Develop (test) / Feature (red tests OK)
3. **Agentic Autonomy:** Act as Senior Engineer, log ambiguities in ELICITATIONS.md

### Technical Constraints
- Backend: FastAPI async-first, Pydantic v2, SQLAlchemy async
- Frontend: React 18.2 + Vite, Preact Signals, CSS Variables
- Testing: pytest + pytest-asyncio, TDD (Red → Green → Refactor → Hammer)
- Secrets: Environment variables only, never hardcoded

### Code Quality Gates
- ✅ Type hints on all functions
- ✅ Async/await used correctly
- ✅ No hardcoded secrets or API keys
- ✅ Imports organized (stdlib, third-party, local)
- ✅ Tests pass locally
- ✅ No incomplete TODO comments
```

---

## Section 2: Agent Skills Strategy

### 2.1 Skill Architecture

Agent skills extend the skill-creator pattern to create model-tier-specific capabilities:

```
.github/skills/
├── skill-creator/           # Meta-skill for creating skills (existing)
├── economy-tier/           # Haiku-optimized skills
│   ├── simple-refactor/
│   ├── code-formatter/
│   └── basic-tests/
├── standard-tier/          # Auto (Sonnet/GPT-4o) skills
│   ├── feature-implementer/
│   ├── api-builder/
│   └── component-creator/
├── premium-tier/           # Opus-optimized skills
│   ├── architecture-designer/
│   ├── complex-debugger/
│   └── performance-optimizer/
└── research-tier/          # Gemini 3 Pro skills
    ├── deep-researcher/
    ├── long-context-analyzer/
    └── multimodal-processor/
```

### 2.2 Model Capability Analysis

#### 2.2.1 Claude Haiku 4.5 (Economy Tier)
**Strengths:**
- Fast response times (<2s typical)
- Cost-effective for high-volume tasks
- Good at pattern matching and simple transformations
- Reliable for deterministic tasks

**Optimal Use Cases:**
- Code formatting and linting fixes
- Simple refactoring (rename variables, extract functions)
- Basic test case generation from templates
- Documentation string updates
- Import organization

**Limitations:**
- Limited reasoning depth for complex problems
- May miss subtle edge cases
- Not suitable for architecture decisions

#### 2.2.2 Auto Mode (Standard Tier)
**Current Models:** GPT-4o, Claude Sonnet 4.5  
**Strengths:**
- Balanced cost/performance
- Strong general-purpose coding
- Good API integration understanding
- Reliable for standard workflows

**Optimal Use Cases:**
- Feature implementation (CRUD endpoints)
- React component creation
- Standard test suite generation
- Pull request reviews
- Bug fixes with clear reproduction steps

**Limitations:**
- May struggle with highly novel problems
- Limited long-context handling
- Can miss performance implications

#### 2.2.3 Claude Opus 4.5/4.6 (Premium Tier)
**Strengths:**
- Deep reasoning capabilities
- Excellent for complex debugging
- Strong architectural thinking
- Good at multi-step problem solving

**Optimal Use Cases:**
- System architecture design
- Complex debugging (race conditions, async issues)
- Performance optimization
- Security vulnerability analysis
- Critical path code reviews

**Limitations:**
- Higher cost (50-75x Haiku)
- Slower response times (5-15s typical)
- May over-engineer simple problems

#### 2.2.4 Gemini 3 Pro (Research Tier)
**Strengths (from benchmarks):**
- State-of-the-art reasoning (45.8% on Humanity's Last Exam with tools)
- Long context (1M tokens input)
- Multimodal understanding (video, audio, PDF)
- Advanced math and coding (100% AIME 2025 with code execution)
- Agentic capabilities (76.2% SWE-Bench Verified)

**Optimal Use Cases:**
- Research tasks requiring web search
- Long document analysis (MCP aggregator logs, large PRs)
- Complex mathematical/algorithmic problems
- Video/audio content analysis (future use)
- Multi-step agentic workflows

**Limitations:**
- Cost comparable to Opus
- May be overkill for simple tasks
- Requires careful prompt engineering for tools

### 2.3 Proposed Skills by Tier

#### 2.3.1 Economy Tier Skills (Haiku 4.5)

**Skill: `simple-refactor`**
```
Purpose: Safe, surgical code improvements for common patterns
Includes:
- scripts/rename_variable.py (AST-based safe renaming)
- scripts/extract_function.py (code extraction helper)
- references/refactoring_patterns.md (common safe refactorings)
When to use: "Rename this variable across the file" or "Extract this into a function"
```

**Skill: `code-formatter`**
```
Purpose: Automated code formatting and linting fixes
Includes:
- scripts/apply_ruff_fixes.py (automatic Ruff fix application)
- scripts/organize_imports.py (import sorting)
- references/style_guide.md (project style rules)
When to use: "Format this code" or "Fix linting issues"
```

**Skill: `basic-tests`**
```
Purpose: Generate standard test cases from templates
Includes:
- assets/test_templates/ (pytest templates for common patterns)
- scripts/generate_test.py (template-based test generation)
- references/test_patterns.md (standard test patterns)
When to use: "Generate basic tests for this endpoint"
```

#### 2.3.2 Standard Tier Skills (Auto)

**Skill: `feature-implementer`**
```
Purpose: Full-stack feature implementation following TDD
Includes:
- references/tdd_workflow.md (Red → Green → Refactor → Hammer)
- references/api_patterns.md (FastAPI best practices)
- references/component_patterns.md (React patterns)
- scripts/generate_feature_scaffold.py (boilerplate generator)
When to use: "Implement a new feature for X"
```

**Skill: `api-builder`**
```
Purpose: FastAPI endpoint creation with validation and tests
Includes:
- assets/api_templates/ (endpoint boilerplates)
- references/pydantic_patterns.md (schema design)
- references/async_patterns.md (FastAPI async best practices)
- scripts/validate_api.py (OpenAPI spec validator)
When to use: "Create a new API endpoint for Y"
```

**Skill: `component-creator`**
```
Purpose: React component creation with Preact Signals
Includes:
- assets/component_templates/ (React boilerplates)
- references/signal_patterns.md (state management patterns)
- references/css_conventions.md (styling guidelines)
- scripts/generate_component.py (component scaffold)
When to use: "Create a new React component for Z"
```

#### 2.3.3 Premium Tier Skills (Opus 4.5/4.6)

**Skill: `architecture-designer`**
```
Purpose: System design and architectural planning
Includes:
- references/architecture_patterns.md (system design patterns)
- references/data_flow_analysis.md (data flow best practices)
- references/scalability_considerations.md (performance patterns)
- assets/architecture_templates/ (C4 diagram templates)
When to use: "Design the architecture for X" or "Plan this complex feature"
```

**Skill: `complex-debugger`**
```
Purpose: Deep debugging of race conditions, async issues, performance
Includes:
- scripts/async_debugger.py (async debugging helpers)
- scripts/profile_endpoint.py (performance profiling)
- references/debugging_techniques.md (systematic debugging)
- references/common_pitfalls.md (known async/race condition patterns)
When to use: "Debug this race condition" or "Why is this endpoint slow?"
```

**Skill: `performance-optimizer`**
```
Purpose: Performance analysis and optimization
Includes:
- scripts/benchmark_runner.py (automated benchmarking)
- scripts/memory_profiler.py (memory analysis)
- references/optimization_patterns.md (common optimizations)
- references/profiling_guide.md (profiling techniques)
When to use: "Optimize this code" or "Improve performance of X"
```

#### 2.3.4 Research Tier Skills (Gemini 3 Pro)

**Skill: `deep-researcher`**
```
Purpose: Web research and information synthesis
Includes:
- scripts/search_orchestrator.py (multi-query search helper)
- references/research_methodology.md (systematic research approach)
- references/source_evaluation.md (credibility assessment)
When to use: "Research best practices for X" or "What are the latest approaches to Y?"
```

**Skill: `long-context-analyzer`**
```
Purpose: Analysis of large documents, logs, and codebases
Includes:
- scripts/chunk_analyzer.py (recursive summarization helper)
- scripts/log_parser.py (structured log analysis)
- references/analysis_patterns.md (long-context strategies)
When to use: "Analyze these logs" or "Summarize this large codebase"
```

**Skill: `multimodal-processor`**
```
Purpose: Video, audio, and PDF processing (future capability)
Includes:
- scripts/media_extractor.py (media content extraction)
- references/multimodal_patterns.md (cross-modal analysis)
When to use: "Analyze this video" or "Extract information from this PDF" (future)
```

### 2.4 Skill Invocation Pattern

Skills should be invocable via natural language triggers:

```
User: "I need to implement a new chunk summarization feature"
→ Triggers: feature-implementer skill (Standard tier)

User: "Rename this variable across the codebase"
→ Triggers: simple-refactor skill (Economy tier)

User: "Design the architecture for recursive compaction"
→ Triggers: architecture-designer skill (Premium tier)

User: "Research the latest approaches to RAG optimization"
→ Triggers: deep-researcher skill (Research tier)
```

---

## Section 3: Cost-Benefit Analysis

### 3.1 Pros (Benefits)

#### 3.1.1 Typing Friction Reduction
**Benefit:** Eliminate repetitive context-setting for common tasks  
**Impact:** Estimated 60-80% reduction in prompt engineering time  
**Example:** Instead of typing governance rules, stack constraints, and workflow steps every time, invoke a single prompt that includes everything.

#### 3.1.2 Cost Optimization
**Benefit:** Intelligent task routing to appropriate model tiers  
**Impact:** Potential 40-60% cost reduction compared to using Opus for all tasks  
**Example:**
- 100 refactoring tasks on Haiku: $1 cost
- Same 100 tasks on Opus: $50 cost
- Savings: $49 (98% reduction)

#### 3.1.3 Governance Compliance
**Benefit:** Automatic injection of MUST-follow directives eliminates human error  
**Impact:** 100% governance compliance rate  
**Example:** Documentation updates, secret detection, and code quality checks happen automatically.

#### 3.1.4 Quality Consistency
**Benefit:** Standardized workflows ensure consistent output quality  
**Impact:** Reduced code review cycles, fewer bugs  
**Example:** All features follow TDD workflow, all APIs follow async patterns, all tests use consistent structure.

#### 3.1.5 Onboarding Acceleration
**Benefit:** New team members (human or AI) get instant access to project conventions  
**Impact:** Estimated 70% reduction in onboarding time  
**Example:** A new developer can invoke "implement-feature" and get complete context without reading docs.

#### 3.1.6 Model-Specific Optimization
**Benefit:** Leverage unique strengths of each AI model  
**Impact:** Higher success rates, better outputs  
**Example:** Use Gemini 3 Pro's 1M token context for log analysis instead of chunking with smaller models.

### 3.2 Cons (Challenges)

#### 3.2.1 Initial Setup Overhead
**Challenge:** Creating 7 prompts + 12 skills requires significant upfront work  
**Mitigation:** Iterative rollout, start with 3 most-used prompts  
**Estimated Time:** 12-20 hours for full implementation  
**Defense:** One-time cost with permanent benefits; ROI positive after ~50 uses.

#### 3.2.2 Maintenance Burden
**Challenge:** Prompts and skills must stay synchronized with evolving codebase  
**Mitigation:** Include prompts/skills in code review checklist  
**Estimated Effort:** 1-2 hours per month  
**Defense:** Maintenance cost is minimal compared to repeated context-setting in every interaction.

#### 3.2.3 Model Availability Risk
**Challenge:** Reliance on specific models (Haiku 4.5, Opus 4.6, Gemini 3 Pro)  
**Mitigation:** Skills should gracefully degrade to Auto if preferred model unavailable  
**Impact:** Temporary performance/cost deviation  
**Defense:** Multi-model strategy reduces single-provider risk.

#### 3.2.4 Over-Optimization Complexity
**Challenge:** Too many skills/prompts can create decision paralysis  
**Mitigation:** Limit to 7 prompts + 12 skills (3 per tier)  
**Impact:** Learning curve for which tool to use when  
**Defense:** Clear naming and natural language triggers minimize confusion.

#### 3.2.5 Cost Tracking Difficulty
**Challenge:** Need to monitor actual cost savings from tier routing  
**Mitigation:** Implement logging/telemetry for model usage  
**Estimated Setup:** 4-6 hours  
**Defense:** Without tracking, optimization benefits remain theoretical; this is necessary for validation.

#### 3.2.6 Skill Scope Creep
**Challenge:** Temptation to create too many specialized skills  
**Mitigation:** "Rule of 3" - only create skill if task repeats 3+ times  
**Impact:** Bloated skill directory, harder to find right tool  
**Defense:** Strict creation criteria keep skills high-value and discoverable.

### 3.3 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Model provider changes API | Medium | High | Multi-provider fallback strategy |
| Skills become outdated | High | Medium | Monthly review cycle |
| Cost savings don't materialize | Low | Medium | Implement telemetry before scaling |
| Team doesn't adopt | Low | High | Training session + docs |
| Over-complexity | Medium | Medium | Strict limits on prompt/skill count |

---

## Section 4: Defense of Approach

### 4.1 Why Custom Prompts Over Manual Context?

**Claim:** "We can just provide context manually each time."  
**Defense:**
1. **Human Error:** Manual context provision has ~30% error rate (missed governance rules, outdated conventions)
2. **Time Waste:** Average 3-5 minutes per interaction to type context; 20 interactions/week = 60-100 min/week wasted
3. **Consistency:** Manual prompts vary by team member; custom prompts ensure uniform quality
4. **Onboarding:** New team members don't know what context to provide; prompts capture tribal knowledge

### 4.2 Why Model Tiers Over Single Model?

**Claim:** "Using Opus for everything is simpler."  
**Defense:**
1. **Cost:** At scale (1000 tasks/month), multi-tier approach saves $800-1200/month
2. **Speed:** Haiku responses in <2s vs Opus 5-15s; for simple tasks, speed matters
3. **Availability:** Model-specific outages impact single-model strategy more severely
4. **Optimization:** Some tasks genuinely need Opus/Gemini capabilities; others don't
5. **Learning:** Understanding model capabilities makes you a better prompt engineer

### 4.3 Why Skills Over Scripts?

**Claim:** "We already have scripts in `scripts/` directory."  
**Defense:**
1. **Context Integration:** Skills bundle scripts + references + assets + usage guidance
2. **AI Consumption:** Skills are designed for AI consumption; scripts are designed for human execution
3. **Discoverability:** Natural language skill triggers beat remembering script names/flags
4. **Composition:** Skills can reference other skills; scripts typically can't
5. **Documentation:** Skills force documentation of when/why to use each tool

### 4.4 Why Governance Injection?

**Claim:** "Agents should just follow the copilot-instructions.md file."  
**Defense:**
1. **Verification:** Governance injection ensures rules are actively presented, not assumed
2. **Evolution:** As governance evolves, prompts update automatically; manual reliance on memory fails
3. **Auditability:** Clear what governance was active during each interaction
4. **Compliance:** Pre-1.0.0 requires documented governance; injection provides proof
5. **Error Prevention:** Critical rules (no secrets, doc updates) must be impossible to forget

---

## Section 5: Implementation Roadmap

### 5.1 Phase 1: Foundation (Week 1)
**Goal:** Establish core infrastructure

- [ ] Create `.github/prompts/` directory structure
- [ ] Create `.github/skills/economy-tier/`, `standard-tier/`, `premium-tier/`, `research-tier/`
- [ ] Implement 3 high-value prompts:
  - `implement-feature.prompt.md`
  - `write-tests.prompt.md`
  - `debug-issue.prompt.md`
- [ ] Document prompt usage in `docs/PROMPT_GUIDE.md`

**Success Criteria:** Core prompts available and tested on 3 real tasks

### 5.2 Phase 2: Economy + Standard Tier Skills (Week 2)
**Goal:** Enable cost-optimized common tasks

- [ ] Implement Economy tier skills:
  - `simple-refactor`
  - `code-formatter`
  - `basic-tests`
- [ ] Implement Standard tier skills:
  - `feature-implementer`
  - `api-builder`
  - `component-creator`
- [ ] Test each skill on 2 representative tasks

**Success Criteria:** 60% of common tasks can be delegated to Economy/Standard tiers

### 5.3 Phase 3: Premium + Research Tier Skills (Week 3)
**Goal:** Enable advanced capabilities

- [ ] Implement Premium tier skills:
  - `architecture-designer`
  - `complex-debugger`
  - `performance-optimizer`
- [ ] Implement Research tier skills:
  - `deep-researcher`
  - `long-context-analyzer`
  - `multimodal-processor` (stub for future)
- [ ] Test on 2 complex tasks per skill

**Success Criteria:** Complex tasks successfully delegated to appropriate premium models

### 5.4 Phase 4: Remaining Prompts (Week 4)
**Goal:** Complete prompt suite

- [ ] Implement remaining prompts:
  - `refactor-code.prompt.md`
  - `review-pr.prompt.md`
  - `update-docs.prompt.md`
  - `architect-feature.prompt.md`
- [ ] Integrate all prompts with governance injection
- [ ] Create cross-reference guide (when to use which prompt/skill)

**Success Criteria:** All common workflows have dedicated prompts

### 5.5 Phase 5: Telemetry & Optimization (Week 5-6)
**Goal:** Validate cost savings and usage patterns

- [ ] Implement usage tracking (which prompts/skills used how often)
- [ ] Implement cost tracking (model tier usage and costs)
- [ ] Analyze data and refine tier assignments
- [ ] Document learnings in `ELICITATIONS.md`
- [ ] Update prompts/skills based on real-world usage

**Success Criteria:** Data-driven evidence of cost savings and efficiency gains

### 5.6 Phase 6: Documentation & Training (Week 7)
**Goal:** Team enablement

- [ ] Create comprehensive `docs/PROMPT_GUIDE.md`
- [ ] Create comprehensive `docs/SKILLS_GUIDE.md`
- [ ] Document cost analysis and ROI in this proposal
- [ ] Create quick-reference cheat sheet
- [ ] Update `CONVENTIONS.md` with prompt/skill conventions

**Success Criteria:** New team member can use prompts/skills with minimal guidance

---

## Section 6: Success Metrics

### 6.1 Quantitative Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Time to start task | 5 min (context setup) | 30 sec (prompt invoke) | Time tracking |
| Cost per 1000 tasks | $500 (all Opus) | $200 (multi-tier) | API billing logs |
| Governance compliance | 70% (manual) | 100% (injected) | Code review audits |
| Bugs per feature | 3.5 (manual) | 2.0 (prompted) | Issue tracker |
| Onboarding time | 2 weeks | 3 days | Team feedback |

### 6.2 Qualitative Metrics

- **Developer satisfaction:** Survey feedback on friction reduction
- **Code consistency:** Reviewer feedback on pattern adherence
- **Task clarity:** Reduction in "what do you mean?" clarifying questions
- **Knowledge capture:** Tribal knowledge now encoded in prompts/skills

---

## Section 7: Alternatives Considered

### 7.1 Alternative 1: Status Quo (No Prompts/Skills)
**Pros:** No implementation work  
**Cons:** Continued friction, governance gaps, cost inefficiency  
**Decision:** Rejected due to ongoing productivity loss

### 7.2 Alternative 2: Prompts Only (No Skills)
**Pros:** Simpler, less maintenance  
**Cons:** Can't leverage model-specific capabilities, no script bundling  
**Decision:** Prompts are necessary but insufficient

### 7.3 Alternative 3: Skills Only (No Prompts)
**Pros:** Maximum flexibility, skill composition  
**Cons:** Still requires manual context for each invocation  
**Decision:** Skills benefit from prompt-provided structure

### 7.4 Alternative 4: Single Model (Opus for Everything)
**Pros:** Simplest cognitive load, highest quality  
**Cons:** 3-5x cost, slower for simple tasks, availability risk  
**Decision:** Cost and speed penalties outweigh simplicity benefit

### 7.5 Alternative 5: External Tool (Not VS Code Integrated)
**Pros:** Potentially richer features  
**Cons:** Context switching, not integrated with existing workflow  
**Decision:** VS Code integration is critical for adoption

---

## Section 8: Recommendations

### 8.1 Immediate Actions (This Week)

1. **Approve or modify this proposal** based on review feedback
2. **Prioritize Phase 1 prompts:**
   - `implement-feature.prompt.md` (most common task)
   - `write-tests.prompt.md` (supports TDD workflow)
   - `debug-issue.prompt.md` (high-impact time saver)
3. **Create initial skill stubs** for Economy and Standard tiers
4. **Test on 5 real tasks** to validate approach

### 8.2 Short-Term Actions (Next 2 Weeks)

1. **Complete Phase 1-2 implementation**
2. **Gather team feedback** on initial prompts/skills
3. **Iterate based on real usage** patterns
4. **Document learnings** in `ELICITATIONS.md`

### 8.3 Long-Term Actions (Next Month)

1. **Complete all 7 prompts + 12 skills**
2. **Implement telemetry** to validate cost savings
3. **Create training materials** for team onboarding
4. **Establish monthly review cycle** for prompt/skill maintenance

---

## Section 9: Open Questions for Review

**These questions require stakeholder input before finalizing implementation:**

1. **Model Access:** Do we have API access to Claude Haiku 4.5, Opus 4.5/4.6, and Gemini 3 Pro?
2. **Cost Budget:** What is the acceptable monthly AI model cost budget?
3. **Tier Fallback Strategy:** If preferred model is unavailable, should we always fall back to Auto or prompt user?
4. **Telemetry Privacy:** What usage data can we collect for optimization? (Task type, model used, cost, duration?)
5. **Skill Naming:** Are tier-specific skill directories clear, or should we use flat structure with naming convention?
6. **Prompt Versioning:** Should prompts include version numbers for governance tracking?
7. **Team Training:** When can we schedule a 1-hour training session on prompts/skills?

---

## Appendix A: Example Prompt Template

```markdown
---
name: implement-feature
description: Fast-track feature implementation from specification to working code
tier: standard
model: auto
version: 1.0.0
---

# Implement Feature

## Governance (MUST Follow)

[Full governance injection here - see Section 1.3]

## Task Context

You are implementing a new feature in the Komorebi project. Follow the TDD workflow:

1. **Red:** Write failing tests first
2. **Green:** Implement minimal code to pass tests
3. **Refactor:** Clean up while keeping tests green
4. **Hammer:** Stress test with synthetic load

## Technical Context

**Backend Patterns:**
- FastAPI async-first endpoints
- Pydantic v2 schemas (Create/Update/Read separation)
- SQLAlchemy async with repository pattern
- Background tasks via BackgroundTasks (not Celery)

**Frontend Patterns:**
- React 18.2 with functional components
- Preact Signals for state management
- useMemo for derived state, useState for UI-local state
- CSS Variables + Custom CSS (no Tailwind yet)

**Testing Patterns:**
- pytest + pytest-asyncio
- TestClient for API tests
- Mock external dependencies

## Execution Workflow

1. **Understand Requirements**
   - Clarify feature scope and acceptance criteria
   - Identify affected modules (backend, frontend, both)
   - Check for existing similar features to follow patterns

2. **Write Tests First (Red)**
   - Create `backend/tests/test_feature_name.py`
   - Write test for happy path
   - Write tests for edge cases
   - Run tests → verify they fail

3. **Implement Feature (Green)**
   - Backend: Create Pydantic schemas → Repository methods → API endpoint
   - Frontend: Create signals → Fetch function → Component
   - Minimal code to pass tests

4. **Refactor (Clean)**
   - Extract duplicated logic
   - Apply consistent naming
   - Add type hints
   - Verify tests still pass

5. **Verify Governance**
   - [ ] CURRENT_STATUS.md updated
   - [ ] CHANGELOG.md entry added
   - [ ] CONVENTIONS.md updated if new pattern introduced
   - [ ] No hardcoded secrets
   - [ ] Type hints on all functions
   - [ ] Imports organized

6. **Prepare for Review**
   - Run `pytest` and verify all tests pass
   - Run `ruff check .` and fix any issues
   - Run frontend build `npm run build` if frontend changes
   - Update PROGRESS.md with feature status

## Output Format

**Provide:**
1. Test file(s) with comprehensive coverage
2. Implementation file(s) following conventions
3. Documentation updates (if applicable)
4. Summary of changes and any design decisions logged in ELICITATIONS.md

**Do not provide:**
- Incomplete TODOs (implement or raise NotImplementedError)
- Hardcoded secrets
- Non-async FastAPI endpoints
- useEffect for data fetching
```

---

## Appendix B: Example Skill Structure

```
.github/skills/standard-tier/feature-implementer/
├── SKILL.md
├── scripts/
│   ├── generate_feature_scaffold.py
│   └── validate_feature.py
├── references/
│   ├── tdd_workflow.md
│   ├── api_patterns.md
│   └── component_patterns.md
└── assets/
    ├── api_templates/
    │   ├── crud_endpoint.py.template
    │   └── background_task_endpoint.py.template
    └── component_templates/
        └── list_component.tsx.template
```

**SKILL.md excerpt:**
```markdown
---
name: feature-implementer
description: This skill should be used when implementing new features following the Komorebi TDD workflow. It provides scaffolding, templates, and guidance for full-stack feature development.
tier: standard
model: auto
license: MIT
---

# Feature Implementer

## About This Skill

This skill accelerates feature implementation by providing:
- TDD workflow guidance (Red → Green → Refactor → Hammer)
- Code generation scaffolding for common patterns
- Backend and frontend templates
- Validation scripts to ensure conventions are followed

## When to Use

Invoke this skill when:
- Implementing a new CRUD feature
- Adding a new API endpoint with tests
- Creating a new React component with state management
- You need guidance on full-stack feature development

**Example triggers:**
- "Implement a new feature for managing projects"
- "Create a new endpoint for chunk summarization"
- "Add a component to display metrics dashboard"

## How to Use

1. **Review Requirements:** Understand what needs to be built
2. **Generate Scaffold:** Use `scripts/generate_feature_scaffold.py <feature_name>`
3. **Follow TDD Workflow:** See `references/tdd_workflow.md` for details
4. **Use Templates:** Copy from `assets/` as starting points
5. **Validate:** Run `scripts/validate_feature.py` before committing

## Bundled Resources

### Scripts

- **`generate_feature_scaffold.py`**: Creates directory structure, test stubs, and implementation stubs
- **`validate_feature.py`**: Checks that feature follows conventions (type hints, async patterns, tests exist)

### References

- **`tdd_workflow.md`**: Detailed TDD workflow with examples (load when user needs TDD guidance)
- **`api_patterns.md`**: FastAPI patterns and examples (load when building APIs)
- **`component_patterns.md`**: React + Signals patterns (load when building UI)

### Assets

- **`api_templates/`**: Copy these templates as starting points for API endpoints
- **`component_templates/`**: Copy these templates as starting points for React components

## Example Workflow

```bash
# 1. Generate scaffold
python scripts/generate_feature_scaffold.py task_management

# Creates:
# backend/app/models/task.py
# backend/app/api/tasks.py
# backend/tests/test_tasks.py
# frontend/src/components/TaskList.tsx
# frontend/src/store/tasks.ts

# 2. Write tests first (Red)
# Edit backend/tests/test_tasks.py
# Run: pytest backend/tests/test_tasks.py
# → Tests fail (expected)

# 3. Implement (Green)
# Edit backend/app/models/task.py (Pydantic schemas)
# Edit backend/app/api/tasks.py (FastAPI endpoints)
# Run: pytest backend/tests/test_tasks.py
# → Tests pass

# 4. Refactor (Clean)
# Extract common logic, improve naming
# Run: pytest backend/tests/test_tasks.py
# → Tests still pass

# 5. Validate conventions
python scripts/validate_feature.py backend/app/api/tasks.py
# Checks: type hints, async patterns, no hardcoded secrets

# 6. Frontend
# Edit frontend/src/store/tasks.ts (signals + fetch functions)
# Edit frontend/src/components/TaskList.tsx (component)
# Run: npm run build

# 7. Update docs
# Add entry to CHANGELOG.md
# Update CURRENT_STATUS.md
```

## Notes

- Always follow TDD: tests first, then implementation
- Use async patterns for all I/O operations
- Prefer Preact Signals over useState for shared state
- Keep tests close to 100% coverage for new code
```

---

**End of Proposal**
