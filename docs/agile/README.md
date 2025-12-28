# Congress Data Platform - Agile Project Management

**Project**: EPIC-001 Unified Data Platform Migration
**Duration**: 4 weeks (Dec 16, 2025 - Jan 11, 2026)
**Status**: 🔄 **In Progress** (Sprint 2 Complete, Sprint 3 Active)

## 📊 Current Status (Dec 26, 2025)

| Metric | Value | Status |
|--------|-------|--------|
| **Overall Progress** | 31% (51/167 points) | 🔄 On Track |
| **Stories Complete** | 15/55 | ✅ 27% |
| **Current Sprint** | Sprint 3 (Week 2) | 🔄 Active |
| **Last Completed** | Sprint 2 - Gold Layer | ✅ Dec 16 |
| **Sprint Velocity** | 43 pts/sprint | ⚡ Strong |
| **Days to Completion** | 16 days | 📅 Jan 11 target |

**Quick Links**:
- 📋 [**Current Status**](./active/CURRENT_STATUS.md) - Real-time progress
- 📅 [**Timeline**](./active/TIMELINE.md) - Actual vs. planned delivery
- 📊 [**Story Catalog**](./STORY_CATALOG.md) - All 55 stories

---

## Quick Start

### For Developers
1. **Check Current Work**: [active/CURRENT_STATUS.md](./active/CURRENT_STATUS.md)
2. **Current Sprint**: [sprints/SPRINT_03_INTEGRATION.md](./sprints/SPRINT_03_INTEGRATION.md)
3. **Active Stories**: [stories/active/](./stories/active/) (43 stories)
4. **Pick a Task**: Choose from Sprint 3 backlog
5. **Use Template**: [templates/user_story_template.md](./templates/user_story_template.md)

### For Product Owners
1. **Review Epic Goals**: [EPIC_001_UNIFIED_PIPELINE.md#success-criteria](./EPIC_001_UNIFIED_PIPELINE.md#success-criteria)
2. **Track Progress**: [active/CURRENT_STATUS.md](./active/CURRENT_STATUS.md)
3. **Review Metrics**: [metrics/VELOCITY_TRACKING.md](./metrics/VELOCITY_TRACKING.md)
4. **Completed Work**: [completed/](./completed/) & [sprints/completed/](./sprints/completed/)

### For Stakeholders
1. **Business Value**: [EPIC_001#business-value](./EPIC_001_UNIFIED_PIPELINE.md#business-value)
2. **Timeline**: [active/TIMELINE.md](./active/TIMELINE.md)
3. **Budget**: [EPIC_001#budget](./EPIC_001_UNIFIED_PIPELINE.md#budget)
4. **Sprint Reports**: [sprints/completed/](./sprints/completed/)

---

## Project Structure

```
docs/agile/
├── README.md                          # This file
├── INDEX.md                           # Complete navigation guide
├── EPIC_001_UNIFIED_PIPELINE.md       # Main epic definition
├── STORY_CATALOG.md                   # All 55 stories (15 complete)
│
├── active/                            # 🔄 CURRENT WORK
│   ├── CURRENT_STATUS.md              # Real-time sprint progress
│   └── TIMELINE.md                    # Actual vs. planned delivery
│
├── sprints/                           # Sprint plans
│   ├── SPRINT_01_FOUNDATION.md        # Week 1 (merged into Sprint 2)
│   ├── SPRINT_03_INTEGRATION.md       # Week 3 (46 points) 🔄 ACTIVE
│   ├── SPRINT_04_PRODUCTION.md        # Week 4 (31 points)
│   └── completed/                     # ✅ FINISHED SPRINTS
│       └── SPRINT_02_REPORT.md        # Week 2 (43 points) ✅ COMPLETE
│
├── stories/                           # User stories (55 total)
│   ├── active/                        # 📋 ACTIVE (43 stories)
│   │   ├── STORY_001_disable_eventbridge.md
│   │   ├── STORY_002_fix_max_concurrency.md
│   │   └── ... (41 more active stories)
│   ├── completed/                     # ✅ DONE (12 stories)
│   │   ├── STORY_016_build_dim_members.md
│   │   ├── STORY_017_build_dim_assets.md
│   │   └── ... (10 more completed stories)
│   └── backlog/                       # Future stories
│
├── completed/                         # ✅ ARCHIVED WORK
│   ├── README.md                      # Archive guide
│   └── archive/                       # Pre-Epic session docs
│       ├── WEEK1_PROGRESS.md
│       ├── WEEK2_COMPLETE.md
│       └── ... (8 more archived docs)
│
├── technical/                         # Technical specifications
│   ├── ARCHITECTURE_DECISION_RECORD.md
│   ├── DATA_CONTRACTS.md
│   ├── LAMBDA_REQUIREMENTS_SPEC.md
│   ├── STATE_MACHINE_SPEC.md
│   └── TESTING_STRATEGY.md
│
├── templates/                         # Templates for creating new items
│   ├── user_story_template.md
│   ├── technical_task_template.md
│   └── bug_template.md
│
└── metrics/                           # Progress tracking
    ├── VELOCITY_TRACKING.md
    ├── BURNDOWN_CHARTS.md
    └── COMPLETION_CRITERIA.md
```

---

## Epic Overview

### Goal
Migrate from script-based orchestration to AWS Step Functions with production-quality infrastructure.

### Business Value
- **Cost Savings**: $47,820/year (prevent $4K/month runaway costs)
- **Reliability**: 99%+ success rate (vs. current ~85%)
- **Performance**: 10x faster processing (4 hours vs. 41 hours)

### Timeline
- **Sprint 1**: Dec 16-20 (Foundation) - Merged into Sprint 2
- **Sprint 2**: Dec 16, 2025 (Gold Layer) - ✅ **COMPLETE** (1-day sprint!)
- **Sprint 3**: Dec 27 - Jan 3 (Integration) - 🔄 **IN PROGRESS**
- **Sprint 4**: Jan 6-10 (Production) - 📋 Planned
- **Launch**: January 11, 2026

### Budget
- **Labor**: $16,000 (160 hours)
- **AWS**: $50 (one-time) + $10/month (ongoing)
- **ROI**: 4-month payback period

---

## Sprint Summary

| Sprint | Goal | Points | Stories | Completed | Status |
|--------|------|--------|---------|-----------|--------|
| Sprint 1 | Fix critical blockers | 41 | 16 | - | ⚠️ Merged into Sprint 2 |
| [**Sprint 2**](./sprints/completed/SPRINT_02_REPORT.md) | **Gold layer Lambdas** | **43** | **12** | **43/43** | ✅ **COMPLETE** (Dec 16) |
| [**Sprint 3**](./sprints/SPRINT_03_INTEGRATION.md) | **State machine + tests** | **46** | **16** | **8/46** | 🔄 **IN PROGRESS** |
| [Sprint 4](./sprints/SPRINT_04_PRODUCTION.md) | Monitoring + production | 31 | 14 | 0/31 | 📋 Planned |
| **Total** | **Unified Data Platform** | **167** | **55** | **51/167** | **🔄 31% Complete** |

## ✅ Recently Completed

### Sprint 2: Gold Layer Lambdas (Dec 16, 2025)
**Delivered**: 43 points in 1 day (exceptional velocity!)
**Deployed**:
- ✅ 8 Lambda functions (dimensions, facts, aggregates)
- ✅ DuckDB v1.1.3 integration
- ✅ 2 endpoints end-to-end tested
- ✅ All analytics endpoints operational

**Report**: [Sprint 2 Completion Report](./sprints/completed/SPRINT_02_REPORT.md)

### Phase 0: Emergency Hotfixes (Dec 19-26, 2025)
**Delivered**: 8 points (85% complete)
**Fixed**:
- ✅ Transactions page loading issues (5 commits)
- ✅ DuckDB version mismatch (21 failing endpoints now working)
- 🔄 Health endpoint Lambda (API Gateway integration pending)

**Details**: [Implementation Status](../IMPLEMENTATION_STATUS.md)

---

## Story Catalog

### Sprint 1: Foundation (15 stories, 34 points)

#### Critical Path (P0)
- [STORY-001](./stories/STORY_001_disable_eventbridge.md) - Disable EventBridge hourly trigger (1 point)
- [STORY-002](./stories/STORY_002_fix_max_concurrency.md) - Fix MaxConcurrency in state machines (1 point)
- [STORY-003](./stories/STORY_003_watermarking_house_fd.md) - Implement watermarking (3 points)
- [STORY-006](./stories/STORY_006_github_actions_stepfunctions.md) - Fix GitHub Actions (3 points)

#### High Priority (P1)
- STORY-004 - Watermarking Congress.gov (2 points)
- STORY-005 - Watermarking Lobbying (2 points)
- STORY-007 - SNS email subscriptions (2 points)
- STORY-008 - Fix Terraform duplication (2 points)
- STORY-009 - Remove hardcoded account IDs (2 points)
- STORY-015 - Update CLAUDE.md (5 points)

#### Medium Priority (P2)
- STORY-010 - Pipeline architecture diagram (2 points)
- STORY-011 - Data flow diagram (2 points)
- STORY-012 - Error handling diagram (2 points)
- STORY-013 - Cost optimization diagram (2 points)
- STORY-014 - State machine flow diagram (3 points)

### Sprint 2: Gold Layer (12 stories, 55 points)

#### Dimension Builders (21 points)
- STORY-016 - build_dim_members Lambda (5 points)
- STORY-017 - build_dim_assets Lambda (5 points)
- STORY-018 - build_dim_bills Lambda (5 points)
- STORY-019 - build_dim_lobbyists Lambda (3 points)
- STORY-020 - build_dim_dates Lambda (3 points)

#### Fact Builders (24 points)
- STORY-021 - build_fact_transactions Lambda (8 points)
- STORY-022 - build_fact_filings Lambda (5 points)
- STORY-023 - build_fact_lobbying Lambda (5 points)
- STORY-024 - build_fact_cosponsors Lambda (3 points)
- STORY-025 - build_fact_amendments Lambda (3 points)

#### Aggregate Builders (10 points)
- STORY-026 - compute_trending_stocks Lambda (3 points)
- STORY-027 - compute_member_stats Lambda (3 points)
- (Additional aggregate stories in full backlog)

### Sprint 3: Integration (10 stories, 34 points)

- STORY-028 - Design unified state machine (5 points)
- STORY-029 - Bronze ingestion phase (3 points)
- STORY-030 - Silver transformation phase (5 points)
- STORY-031 - Gold layer phase (5 points)
- STORY-032 - Quality checks phase (3 points)
- STORY-033 - Create run_soda_checks Lambda (5 points)
- STORY-034 - Write 70+ unit tests (8 points)
- STORY-035 - Write 20+ integration tests (5 points)
- STORY-036 - Write 10+ E2E tests (3 points)
- STORY-037 - Configure CI/CD test pipeline (2 points)

### Sprint 4: Production (8 stories, 21 points)

- STORY-038 - CloudWatch pipeline dashboard (5 points)
- STORY-039 - CloudWatch cost dashboard (3 points)
- STORY-040 - Configure CloudWatch alarms (3 points)
- STORY-041 - Enable X-Ray tracing (2 points)
- STORY-042 - Operational runbook (3 points)
- STORY-043 - Deployment guide (2 points)
- STORY-044 - Developer guide (2 points)
- STORY-045 - Production deployment (3 points)

---

## Workflow

### Creating a New Story

1. **Copy Template**
```bash
cp templates/user_story_template.md stories/STORY_XXX_title.md
```

2. **Fill Out Story**
   - User story (As a... I want... So that...)
   - Acceptance criteria (Given/When/Then)
   - Technical tasks
   - Test requirements
   - Definition of Done

3. **Add to Sprint**
   - Update sprint plan with story ID
   - Assign story points (Fibonacci: 1, 2, 3, 5, 8)
   - Assign priority (P0-P3)
   - Assign to team member

4. **Track Progress**
   - Update status (To Do → In Progress → In Review → Done)
   - Update todo list in story
   - Link Pull Request when code complete

### Daily Standup Format

**Each team member answers**:
1. What did I complete yesterday?
2. What am I working on today?
3. Any blockers?

### Definition of Done (Story Level)

- [ ] Code complete and merged to main
- [ ] Unit tests passing (≥80% coverage)
- [ ] Integration tests passing (if applicable)
- [ ] Code review approved
- [ ] Documentation updated
- [ ] Deployed to dev/staging
- [ ] Acceptance criteria verified
- [ ] No critical bugs

---

## Technical Specs

### Architecture
- [ADR](./technical/ARCHITECTURE_DECISION_RECORD.md) - All architectural decisions documented
- [State Machine Spec](./technical/STATE_MACHINE_SPEC.md) - Step Functions design
- [Lambda Spec](./technical/LAMBDA_REQUIREMENTS_SPEC.md) - All 47 Lambda functions

### Data
- [Data Contracts](./technical/DATA_CONTRACTS.md) - Bronze/Silver/Gold schemas
- [Testing Strategy](./technical/TESTING_STRATEGY.md) - Unit/Integration/E2E approach

---

## Progress Tracking

### Velocity Tracking
See [metrics/VELOCITY_TRACKING.md](./metrics/VELOCITY_TRACKING.md)

**Current Sprint**: Sprint 1
**Planned Points**: 34
**Completed Points**: 0
**Velocity**: TBD (baseline sprint)

### Burndown Chart
See [metrics/BURNDOWN_CHARTS.md](./metrics/BURNDOWN_CHARTS.md)

**Epic Progress**: 0/144 points (0%)

### Test Coverage
**Current**: ~15%
**Target**: 80%
**Sprint 3 Target**: 80% (quality gate)

---

## Key Decisions

### ADR Summary
| ADR | Decision | Status |
|-----|----------|--------|
| ADR-001 | Adopt Step Functions | ✅ Accepted |
| ADR-002 | Unified Pipeline vs Siloed | ✅ Accepted |
| ADR-003 | Bronze-Silver-Gold Medallion | ✅ Accepted |
| ADR-004 | Lambda Functions vs Scripts | ⚠️ In Progress |
| ADR-009 | Watermarking for Incremental | ⚠️ In Progress |
| ADR-010 | Testing Strategy | ⚠️ In Progress |

See [technical/ARCHITECTURE_DECISION_RECORD.md](./technical/ARCHITECTURE_DECISION_RECORD.md) for full details.

---

## Glossary

### Story Points (Fibonacci Scale)
- **1 point**: < 1 hour (trivial change)
- **2 points**: 1-2 hours (simple feature)
- **3 points**: 3-4 hours (moderate feature)
- **5 points**: 1 day (complex feature)
- **8 points**: 2 days (very complex or risky)
- **13 points**: 3+ days (too large, break down)

### Priority Levels
- **P0 (Critical)**: Blocker, must do immediately
- **P1 (High)**: Important, do this sprint
- **P2 (Medium)**: Should do, can slip if needed
- **P3 (Low)**: Nice to have, backlog

### Status Values
- **To Do**: Not started
- **In Progress**: Currently being worked on
- **In Review**: Code review or testing
- **Done**: Meets Definition of Done

---

## Links

### Internal
- [Main Project README](../../README.md)
- [CLAUDE.md](../../CLAUDE.md)
- [Contributing Guide](../../CONTRIBUTING.md)

### External
- [GitHub Project Board](https://github.com/your-org/congress-disclosures-standardized/projects/1)
- [Confluence Space](https://confluence.example.com/epic-001)
- [Slack Channel](https://slack.com/app_redirect?channel=congress-data-platform)

---

## Contact

- **Epic Owner**: Engineering Team Lead
- **Product Owner**: [Name]
- **Tech Lead**: [Name]
- **Slack**: #congress-data-platform
- **Email**: team@example.com

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-14 | Initial agile structure created | Engineering Team |

---

**Last Updated**: 2025-12-14
**Next Review**: Sprint 1 Retrospective (Dec 20, 2025)
