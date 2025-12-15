# Sprint 3: State Machine Integration & Testing

**Sprint Goal**: Build unified state machine and comprehensive test suite

**Duration**: Week 3 (Dec 30-Jan 3, 2026)
**Story Points**: 52
**Status**: 🔴 Not Started

---

## Sprint Objectives

### Primary Goal 🎯
Create the unified `congress_data_platform` state machine and achieve 80%+ test coverage.

### Key Results
1. ✅ Unified state machine created and deployed
2. ✅ Soda quality checks Lambda created + 15+ YAML check definitions
3. ✅ Dimension validation step implemented
4. ✅ 4 deferred Gold layer Lambdas completed (dim_lobbyists, dim_dates, fact_cosponsors, fact_amendments)
5. ✅ 35 unit + integration tests (80%+ coverage for Sprint 3 modules)

---

## Sprint Backlog

### State Machine & Infrastructure (26 points)
| ID | Story | Points | Priority |
|----|-------|--------|----------|
| STORY-028 | Design unified state machine JSON | 5 | P0 |
| STORY-029 | Implement Bronze ingestion phase | 3 | P0 |
| STORY-030 | Implement Silver transformation phase | 5 | P0 |
| STORY-031 | Implement Gold layer phase | 5 | P0 |
| STORY-032 | Implement quality checks phase | 3 | P0 |
| STORY-033 | Create run_soda_checks Lambda | 5 | P0 |

### Quality & Validation (14 points)
| ID | Story | Points | Priority |
|----|-------|--------|----------|
| STORY-048 | Create Soda quality check YAML definitions | 5 | P1 |
| STORY-049 | Add dimension validation step | 3 | P1 |
| STORY-053 | Write unit tests - Sprint 3 state machine + integration | 6 | P0 |

### Deferred from Sprint 2 (12 points)
| ID | Story | Points | Priority |
|----|-------|--------|----------|
| STORY-019 | Create build_dim_lobbyists Lambda wrapper | 3 | P2 |
| STORY-020 | Create build_dim_dates Lambda wrapper | 3 | P2 |
| STORY-024 | Create build_fact_cosponsors Lambda wrapper | 3 | P2 |
| STORY-025 | Create build_fact_amendments Lambda wrapper | 3 | P2 |

| **Total** | **16 stories** | **52** | |

**Changes from Original Plan**:
- ❌ Removed STORY-034: Unrealistic 70+ test target (8 points)
- ❌ Removed STORY-035: Integration tests (5 points) → merged into STORY-053
- ❌ Removed STORY-036: E2E tests (3 points) → moved to Sprint 4
- ❌ Removed STORY-037: CI/CD pipeline (2 points) → moved to Sprint 4
- ✅ Added STORY-048: Soda YAML definitions (5 points)
- ✅ Added STORY-049: Dimension validation (3 points)
- ✅ Added STORY-053: Sprint 3 distributed testing (6 points)
- ✅ Added 4 deferred stories from Sprint 2 (12 points)

---

## Day-by-Day Plan

### Day 1 (Mon, Dec 30): State Machine Design + Bronze Phase (8 points)
- STORY-028: Design unified state machine (5 hours)
  - Define all states with error handling
  - Map Lambda ARNs from Terraform outputs
  - Design Choice states for conditional logic
  - Document flow in Mermaid diagram
- STORY-029: Implement Bronze ingestion phase (3 hours)

**Goal**: State machine architecture designed, Bronze phase implemented

---

### Day 2 (Tue, Dec 31): Silver + Gold Phases (13 points)
- STORY-030: Implement Silver transformation phase (5 hours)
- STORY-031: Implement Gold layer phase (5 hours)
- STORY-032: Implement quality checks phase (3 hours)

**Goal**: Core pipeline orchestration complete (Bronze → Silver → Gold → Quality)

---

### Day 3 (Wed, Jan 1): Quality Infrastructure + Deferred Lambdas (19 points)
- STORY-033: Create run_soda_checks Lambda (5 hours)
- STORY-048: Create Soda YAML definitions (5 hours)
  - 15+ quality checks across Bronze/Silver/Gold
  - Critical vs warning severity levels
- STORY-049: Add dimension validation step (3 hours)
- STORY-019: dim_lobbyists Lambda (3 hours)
- STORY-020: dim_dates Lambda (3 hours)

**Goal**: Quality checks operational, 2 deferred dimensions complete

---

### Day 4 (Thu, Jan 2): Finish Deferred Lambdas + Testing Start (12 points)
- STORY-024: fact_cosponsors Lambda (3 hours)
- STORY-025: fact_amendments Lambda (3 hours)
- STORY-053: Write unit tests - Sprint 3 (start, 3 hours)
  - 15 tests for state machine logic
  - 10 tests for Soda checks Lambda
  - 10 tests for deferred Lambdas

**Goal**: All 4 deferred Lambdas deployed, testing infrastructure in place

---

### Day 5 (Fri, Jan 3): Testing + Review (6 points)
- STORY-053: Write unit tests - Sprint 3 (finish, 3 hours)
  - Complete 35 tests total
  - Integration tests for state machine execution
  - Coverage report (target 80%)
- Sprint Review (1 hour) - Demo unified state machine
- Sprint Retrospective (1 hour)

**Goal**: 35 tests passing, 80%+ coverage, unified state machine production-ready

---

## Unified State Machine Structure

```json
{
  "Comment": "Congress Data Platform - Unified Pipeline",
  "StartAt": "CheckForUpdates",
  "States": {
    "CheckForUpdates": {
      "Type": "Parallel",
      "Next": "EvaluateUpdates"
    },
    "EvaluateUpdates": {
      "Type": "Choice",
      "Choices": [...]
    },
    "BronzeIngestion": {
      "Type": "Parallel",
      "Next": "SilverTransformation"
    },
    "SilverTransformation": {
      "Type": "Parallel",
      "Next": "WaitForQueueEmpty"
    },
    "WaitForQueueEmpty": {
      "Type": "Wait",
      "Next": "CheckQueueStatus"
    },
    "GoldDimensions": {
      "Type": "Parallel",
      "Next": "GoldFacts"
    },
    "GoldFacts": {
      "Type": "Task",
      "Next": "GoldAggregates"
    },
    "GoldAggregates": {
      "Type": "Parallel",
      "Next": "RunSodaChecks"
    },
    "RunSodaChecks": {
      "Type": "Task",
      "Next": "EvaluateQuality"
    },
    "UpdateAPICache": {
      "Type": "Task",
      "Next": "PublishMetrics"
    },
    "PublishMetrics": {
      "Type": "Task",
      "End": true
    }
  }
}
```

---

## Testing Breakdown (STORY-053)

### Sprint 3 Testing Scope: 35 tests
**Target**: 80%+ coverage for Sprint 3 modules

### Unit Tests (25 tests)
- **State machine integration** (15 tests)
  - State transition logic (5 tests)
  - Error handling and retries (5 tests)
  - Choice state evaluation (3 tests)
  - Parallel state execution (2 tests)

- **Soda checks Lambda** (10 tests)
  - YAML parsing and execution (4 tests)
  - Critical vs warning severity handling (3 tests)
  - Quality report generation (3 tests)

### Integration Tests (10 tests)
- **State machine execution** (5 tests)
  - Full pipeline execution (incremental mode)
  - Bronze → Silver → Gold flow
  - Quality check integration
  - Error recovery scenarios
  - SNS notification delivery

- **Deferred Lambdas** (5 tests)
  - dim_lobbyists, dim_dates (2 tests)
  - fact_cosponsors, fact_amendments (2 tests)
  - Dimension validation step (1 test)

### Distributed Testing Plan Summary
- **Sprint 1**: 15 tests for watermarking (STORY-051) ✓
- **Sprint 2**: 20 tests for Gold wrappers (STORY-052) ✓
- **Sprint 3**: 35 tests for state machine + integration (STORY-053) ← This sprint
- **Sprint 4**: 10 E2E tests (STORY-036)
- **Total**: 80 tests across 4 sprints

---

## Definition of Done

### State Machine & Infrastructure
- [ ] Unified state machine JSON created and deployed
- [ ] All 6 phases implemented (CheckUpdates → Bronze → Silver → Gold → Quality → Publish)
- [ ] Error handling and retry logic implemented
- [ ] SNS notifications for failures

### Quality Infrastructure
- [ ] run_soda_checks Lambda deployed
- [ ] 15+ Soda YAML check definitions created
- [ ] Dimension validation step added to Gold phase
- [ ] Critical checks fail pipeline execution

### Deferred Lambdas from Sprint 2
- [ ] dim_lobbyists Lambda deployed (STORY-019)
- [ ] dim_dates Lambda deployed (STORY-020)
- [ ] fact_cosponsors Lambda deployed (STORY-024)
- [ ] fact_amendments Lambda deployed (STORY-025)

### Testing
- [ ] 35 unit + integration tests passing (STORY-053)
- [ ] Test coverage ≥ 80% for Sprint 3 modules
- [ ] All tests passing in CI/CD pipeline

### Documentation
- [ ] State machine Mermaid diagram updated
- [ ] CLAUDE.md updated with orchestration changes
- [ ] Soda checks README created

### Capacity Planning
- **Planned Points**: 52
- **Team Velocity**: 40-50 points/week (AI-assisted development)
- **Stretch**: Acceptable for integration-heavy sprint

---

**Sprint Owner**: Engineering Team Lead
**Last Updated**: 2025-12-14
