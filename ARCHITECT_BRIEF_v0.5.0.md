# Komorebi Next Steps: Architect Brief

**Date:** February 7, 2026  
**Current Version:** v0.5.0  
**Status:** Production-Ready Core, Advanced Features Pending

---

## Executive Summary

Komorebi has reached a significant milestone with v0.5.0:
- **Core capture pipeline** is production-ready and battle-tested
- **Search & filtering** (Module 4) is fully functional (backend + frontend)
- **Developer experience** is robust with 8+ prompts, 4 skills, and comprehensive tooling
- **MCP integration** infrastructure is ready but underutilized

**Next Priority:** Complete Module 4 validation, then pivot to either:
- **Path A:** Production deployment & scaling (ops-focused)
- **Path B:** Advanced features & analytics (innovation-focused)
- **Path C:** Hybrid approach (validate in production, iterate features)

---

## Completed Modules Overview

### ✅ Module 0-3: Foundation (v0.1.0 - v0.3.1)
- Fast capture pipeline (POST /chunks, 202 Accepted)
- Ollama integration for summarization
- Entity extraction (NER, relationship parsing)
- Server-sent events for real-time updates
- Developer experience (prompts, skills, telemetry)
- MCP aggregator infrastructure

### ✅ Module 4: Search & Entity Filtering (v0.4.0 - v0.5.0)
- Backend API: GET /chunks/search with 7 parameters
- Frontend UI: SearchBar, FilterPanel, seamless ChunkList integration
- Text search (LIKE queries), date filters, pagination
- Entity filtering infrastructure (EXISTS subquery)
- Comprehensive test coverage (38/41 tests passing)

---

## Immediate Next Steps (1-2 weeks)

### 1. Complete Module 4 Validation

**Goal:** Stress test search performance and fix any gaps

**Tasks:**
- [ ] **Hammer load testing** (`scripts/hammer_gen.py --mode search`)
  - Generate 500+ concurrent search requests with varied parameters
  - Validate P95 latency < 500ms, 0 failures
  - Test pagination edge cases (offset near total count)
  - Test empty result sets, special characters in queries
  - Estimated: 4-6 hours

- [ ] **Manual entity creation endpoint** (Optional)
  - POST /api/v1/entities for admin/test use
  - Unblocks 3 skipped entity filter tests
  - EntityCreate Pydantic model
  - Estimated: 2-3 hours

- [ ] **Frontend e2e testing** with Playwright
  - Test SearchBar debouncing (type, wait 300ms, verify API call)
  - Test FilterPanel collapsible behavior
  - Test result count updates
  - Test clear button resets state
  - Estimated: 3-4 hours

**Expected Outcome:** Module 4 fully validated, ready for production use

---

## Strategic Options (Choose One)

### Path A: Production Deployment & Scaling (2-3 weeks)

**Focus:** Get Komorebi into production, optimize for scale

**Key Features:**
1. **Docker containerization**
   - Multi-stage Dockerfile (backend + frontend)
   - docker-compose.yml for local dev
   - .dockerignore for lean images
   - Estimated: 4-6 hours

2. **PostgreSQL migration**
   - Replace SQLite with PostgreSQL for production
   - Migration script from SQLite → PostgreSQL
   - Connection pooling (asyncpg)
   - Estimated: 6-8 hours

3. **Redis caching layer**
   - Cache frequent queries (chunks list, stats)
   - TTL-based invalidation
   - Search result caching
   - Estimated: 4-6 hours

4. **Deployment configuration**
   - Kubernetes manifests OR Railway/Render config
   - Environment variable management
   - Health check endpoints
   - Estimated: 6-8 hours

5. **Monitoring & observability**
   - Prometheus metrics endpoint
   - Grafana dashboard (latency, throughput, error rate)
   - Structured logging (JSON format)
   - Estimated: 4-6 hours

**Total Estimated Effort:** 24-34 hours (3-4 days full-time)

**Pros:**
- Real production feedback
- Validates architecture under real load
- Unlocks user testing and feedback loops

**Cons:**
- Delays feature development
- Ops overhead (deployment, monitoring, incidents)

---

### Path B: Advanced Features & Analytics (3-4 weeks)

**Focus:** Build high-value features that differentiate Komorebi

#### Module 5: Bulk Operations & Data Management

**Goal:** Enable power users to manage large datasets efficiently

**Features:**
1. **Bulk chunk operations**
   - POST /chunks/bulk/tag (add tags to multiple chunks)
   - POST /chunks/bulk/archive (archive by filter)
   - POST /chunks/bulk/delete (soft delete with recovery)
   - Frontend: Multi-select UI with bulk action dropdown
   - Estimated: 8-10 hours

2. **Advanced tag management**
   - GET /tags (list all tags with usage counts)
   - Tag autocomplete in capture form
   - Tag renaming (affects all chunks)
   - Tag merging (combine similar tags)
   - Estimated: 6-8 hours

3. **Chunk similarity detection**
   - Embed chunks using Ollama (nomic-embed-text)
   - Store embeddings in new table
   - GET /chunks/{id}/similar (cosine similarity search)
   - Frontend: "Related chunks" panel in drawer
   - Estimated: 10-12 hours

**Total Module 5 Estimated Effort:** 24-30 hours

#### Module 6: Analytics & Insights Dashboard

**Goal:** Surface patterns and trends in captured data

**Features:**
1. **Chunk timeline visualization**
   - Daily/weekly/monthly capture volume chart
   - Entity extraction trends over time
   - Tag usage heatmap
   - Frontend: Chart.js or Recharts integration
   - Estimated: 8-10 hours

2. **Entity relationship graph**
   - Visualize connections between entities
   - Click entity to see all related chunks
   - Filter by entity type
   - Frontend: D3.js or Cytoscape.js
   - Estimated: 10-12 hours

3. **Project health metrics**
   - Compaction rate (inbox → processed → compacted)
   - Average tokens per chunk by project
   - Entity density (entities per chunk)
   - Stale chunk alerts (inbox > 7 days)
   - Estimated: 6-8 hours

**Total Module 6 Estimated Effort:** 24-30 hours

**Pros:**
- High user value (insights unlock new workflows)
- Differentiates from note-taking apps
- Showcases AI capabilities

**Cons:**
- Requires production-scale data to be useful
- Complex frontend (new libraries, visualizations)
- Risk of feature bloat without user validation

---

### Path C: Hybrid Approach (Recommended, 2-3 weeks)

**Focus:** Deploy minimal production, iterate with user feedback

**Phase 1: Minimal Viable Deployment (Week 1)**
- Docker containerization
- Deploy to Railway or Render (managed services, no K8s)
- Keep SQLite for MVP (scales to ~100k chunks)
- Basic monitoring (health check endpoint)
- Estimated: 8-12 hours

**Phase 2: User Onboarding & Feedback (Week 1-2)**
- Invite 5-10 alpha users
- Collect usage data (what features are used, what's missing)
- Monitor error logs and performance
- Quick bug fixes and UX improvements
- Estimated: variable, continuous

**Phase 3: Prioritized Features (Week 2-3)**
- Based on user feedback, implement 1-2 high-value features from Module 5/6
- Examples:
  - Bulk tagging (if users struggle with organization)
  - Chunk similarity (if users want discovery)
  - Timeline viz (if users want insights)
- Estimated: 12-16 hours per feature

**Total Hybrid Effort:** Continuous, but focused sprints

**Pros:**
- Fastest path to production value
- Data-driven feature prioritization
- Iterative risk reduction

**Cons:**
- Requires finding alpha users
- Potential for scope creep if feedback is broad

---

## Technical Debt & Maintenance

### High Priority (Address in next sprint)
1. **FTS5 migration for search**
   - SQLite LIKE queries don't scale to >10k chunks
   - Implement FTS5 virtual table with triggers
   - Add relevance ranking (RANK column)
   - Transparent upgrade (no breaking changes)
   - Estimated: 4-6 hours

2. **Test coverage gaps**
   - 3 skipped entity filter tests (need manual entity creation)
   - Add integration tests for SSE streaming
   - Add stress tests for compaction (large projects)
   - Estimated: 6-8 hours

### Medium Priority (v1.0 release blockers)
1. **Error handling improvements**
   - Standardize error responses (RFC 7807 Problem Details)
   - Add retry logic for Ollama requests
   - Graceful degradation when MCP servers fail
   - Estimated: 4-6 hours

2. **Security hardening**
   - Rate limiting on capture endpoint
   - Input sanitization (prevent XSS)
   - CORS configuration review
   - Estimated: 4-6 hours

### Low Priority (Nice to have)
1. **Performance optimization**
   - Database query optimization (EXPLAIN ANALYZE)
   - Frontend bundle size reduction (lazy loading)
   - Compaction parallelization (batch summarization)
   - Estimated: 8-10 hours

---

## Recommended Next Action

**Immediate (This Week):**
1. Complete Module 4 validation (hammer testing, e2e tests) - 7-10 hours
2. Fix any critical bugs found during testing
3. Document deployment requirements (README update)

**Next Sprint (Week 2):**
- **If choosing Path C (Hybrid):** Set up Docker + Railway deployment
- **If choosing Path B (Features):** Start Module 5 design (bulk operations)
- **If choosing Path A (Ops):** PostgreSQL migration + monitoring

**Decision Point:** After Module 4 validation, review with stakeholders to choose strategic path.

---

## Open Questions for Architect

1. **Target Users:** Is Komorebi for:
   - Personal use (knowledge management)?
   - Team collaboration (shared memory)?
   - Developer tooling (code context)?

2. **Scale Target:** How many chunks/users should v1.0 support?
   - Small: 1 user, 10k chunks (SQLite OK)
   - Medium: 10 users, 100k chunks (needs PostgreSQL)
   - Large: 100+ users, 1M+ chunks (needs caching, sharding)

3. **AI Model Strategy:** Should Komorebi:
   - Stick with Ollama (local, private, resource-intensive)?
   - Add OpenAI/Anthropic integration (cloud, faster, $$$)?
   - Support both with provider abstraction?

4. **MCP Utilization:** Current MCP servers (GitHub, GitKraken, Playwright) are configured but unused. Should we:
   - Build a "Tool Browser" UI to invoke MCP tools from dashboard?
   - Auto-capture tool results → chunks (pipeline already exists)?
   - Keep MCP for backend use only (admin/dev tools)?

5. **Compaction Strategy:** Recursive summarization works but:
   - Should we add user-configurable prompts (e.g., "Summarize as bullet points")?
   - Should compaction be automatic (scheduled) or manual-only?
   - Should we support different summary styles per project?

---

## Appendix: Feature Ideas Backlog

*(Not prioritized, capture for future consideration)*

### Export & Integration
- Export chunks to Markdown/JSON
- Import from Obsidian, Notion, Roam
- Webhook support for external triggers
- Browser extension for web clipping

### Advanced Search
- Regex search support
- Saved search filters
- Search history tracking
- Natural language queries (AI-powered)

### Collaboration
- Project sharing with permissions
- Comments on chunks
- Collaborative compaction (vote on best summary)
- Activity feed (who edited what)

### Mobile
- Progressive Web App (PWA) support
- Mobile-optimized UI
- Voice capture (speech-to-text)
- Native iOS/Android apps (future)

---

## Conclusion

Komorebi v0.5.0 represents a solid foundation with production-ready core features and a complete search interface. The next phase should balance:
- **Validation:** Test Module 4 under load
- **Deployment:** Get real users and feedback
- **Innovation:** Build differentiating features

**Recommended Path:** Hybrid approach (Path C) for lowest risk and fastest learning.

**Next Step:** Create architecture document for chosen path using `/architect-feature` prompt.

---

**Document Version:** 1.0  
**Last Updated:** February 7, 2026  
**Target Audience:** Senior Engineers, Product Architect, Technical Lead
