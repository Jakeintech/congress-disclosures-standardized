# Complete Story Catalog

**Epic**: EPIC-001 Unified Data Platform Migration
**Total Stories**: 55
**Total Points**: 167
**Status**: ✅ All Stories Created (Rebalanced for AI-Assisted Development)

---

## Sprint 1: Foundation (16 stories, 41 points)

| ID | Title | Points | Priority | File |
|----|-------|--------|----------|------|
| STORY-001 | Disable EventBridge hourly trigger | 1 | P0 | [✅](./stories/STORY_001_disable_eventbridge.md) |
| STORY-002 | Fix MaxConcurrency in state machines | 1 | P0 | [✅](./stories/STORY_002_fix_max_concurrency.md) |
| STORY-003 | Implement watermarking - House FD | 3 | P0 | [✅](./stories/STORY_003_watermarking_house_fd.md) |
| STORY-004 | Implement watermarking - Congress | 2 | P1 | [✅](./stories/STORY_004_watermarking_congress.md) |
| STORY-005 | Implement watermarking - Lobbying | 2 | P1 | [✅](./stories/STORY_005_watermarking_lobbying.md) |
| STORY-006 | Fix GitHub Actions to trigger Step Functions | 3 | P0 | [✅](./stories/STORY_006_github_actions_stepfunctions.md) |
| STORY-007 | Add SNS email subscriptions | 2 | P1 | [✅](./stories/STORY_007_sns_email_subscriptions.md) |
| STORY-008 | Fix Terraform variable duplication | 2 | P1 | [✅](./stories/STORY_008_fix_terraform_duplication.md) |
| STORY-009 | Remove hardcoded AWS account IDs | 2 | P1 | [✅](./stories/STORY_009_remove_hardcoded_ids.md) |
| STORY-012 | Create error handling diagram | 2 | P2 | [✅](./stories/STORY_012_error_handling_diagram.md) |
| STORY-013 | Create cost optimization diagram | 2 | P2 | [✅](./stories/STORY_013_cost_optimization_diagram.md) |
| STORY-014 | Create state machine flow diagram | 3 | P2 | [✅](./stories/STORY_014_state_machine_diagram.md) |
| STORY-015 | Update CLAUDE.md with Step Functions | 5 | P1 | [✅](./stories/STORY_015_update_claude_md.md) |
| STORY-046 | Multi-year initial load orchestration | 5 | P0 | [✅](./stories/STORY_046_multi_year_initial_load.md) |
| STORY-047 | Create check_congress_updates Lambda | 3 | P0 | [✅](./stories/STORY_047_check_congress_updates.md) |
| STORY-051 | Write unit tests - Sprint 1 watermarking | 3 | P0 | [✅](./stories/STORY_051_distributed_testing_sprint1.md) |

**Sprint 1 Total**: 41 points
**Changes**: Deferred STORY-010, 011 to Sprint 4; Added STORY-046, 047, 051

---

## Sprint 2: Gold Layer (9 stories, 43 points)

### Dimension Builders (15 points)
| ID | Title | Points | Priority | File |
|----|-------|--------|----------|------|
| STORY-016 | Create build_dim_members Lambda | 5 | P0 | [✅](./stories/STORY_016_build_dim_members.md) |
| STORY-017 | Create build_dim_assets Lambda | 5 | P1 | [✅](./stories/STORY_017_build_dim_assets.md) |
| STORY-018 | Create build_dim_bills Lambda | 5 | P1 | [✅](./stories/STORY_018_build_dim_bills.md) |

### Fact Builders (18 points)
| ID | Title | Points | Priority | File |
|----|-------|--------|----------|------|
| STORY-021 | Create build_fact_transactions Lambda | 8 | P0 | [✅](./stories/STORY_021_build_fact_transactions.md) |
| STORY-022 | Create build_fact_filings Lambda | 5 | P0 | [✅](./stories/STORY_022_build_fact_filings.md) |
| STORY-023 | Create build_fact_lobbying Lambda | 5 | P1 | [✅](./stories/STORY_023_build_fact_lobbying.md) |

### Aggregate Builders (6 points)
| ID | Title | Points | Priority | File |
|----|-------|--------|----------|------|
| STORY-026 | Create compute_trending_stocks Lambda | 3 | P1 | [✅](./stories/STORY_026_compute_trending_stocks.md) |
| STORY-027 | Create compute_member_stats Lambda | 3 | P1 | [✅](./stories/STORY_027_compute_member_stats.md) |

### Testing (4 points)
| ID | Title | Points | Priority | File |
|----|-------|--------|----------|------|
| STORY-052 | Write unit tests - Sprint 2 Gold wrappers | 4 | P0 | [✅](./stories/STORY_052_distributed_testing_sprint2.md) |

**Sprint 2 Total**: 43 points
**Changes**: Deferred STORY-019, 020, 024, 025 to Sprint 3 (-12 pts); Added STORY-052 (+4 pts)

---

## Sprint 3: Integration (16 stories, 52 points)

### State Machine & Infrastructure (26 points)
| ID | Title | Points | Priority | File |
|----|-------|--------|----------|------|
| STORY-028 | Design unified state machine JSON | 5 | P0 | [✅](./stories/STORY_028_design_unified_state_machine.md) |
| STORY-029 | Implement Bronze ingestion phase | 3 | P0 | [✅](./stories/STORY_029_bronze_ingestion_phase.md) |
| STORY-030 | Implement Silver transformation phase | 5 | P0 | [✅](./stories/STORY_030_silver_transformation_phase.md) |
| STORY-031 | Implement Gold layer phase | 5 | P0 | [✅](./stories/STORY_031_gold_layer_phase.md) |
| STORY-032 | Implement quality checks phase | 3 | P0 | [✅](./stories/STORY_032_quality_checks_phase.md) |
| STORY-033 | Create run_soda_checks Lambda | 5 | P0 | [✅](./stories/STORY_033_run_soda_checks_lambda.md) |

### Quality & Validation (14 points)
| ID | Title | Points | Priority | File |
|----|-------|--------|----------|------|
| STORY-048 | Create Soda quality check YAML definitions | 5 | P1 | [✅](./stories/STORY_048_soda_yaml_definitions.md) |
| STORY-049 | Add dimension validation step | 3 | P1 | [✅](./stories/STORY_049_dimension_validation.md) |
| STORY-053 | Write unit tests - Sprint 3 state machine | 6 | P0 | [✅](./stories/STORY_053_distributed_testing_sprint3.md) |

### Deferred from Sprint 2 (12 points)
| ID | Title | Points | Priority | File |
|----|-------|--------|----------|------|
| STORY-019 | Create build_dim_lobbyists Lambda | 3 | P2 | [✅](./stories/STORY_019_build_dim_lobbyists.md) |
| STORY-020 | Create build_dim_dates Lambda | 3 | P2 | [✅](./stories/STORY_020_build_dim_dates.md) |
| STORY-024 | Create build_fact_cosponsors Lambda | 3 | P2 | [✅](./stories/STORY_024_build_fact_cosponsors.md) |
| STORY-025 | Create build_fact_amendments Lambda | 3 | P2 | [✅](./stories/STORY_025_build_fact_amendments.md) |

**Sprint 3 Total**: 52 points
**Changes**: Removed STORY-034 (-8 pts), 035 (-5 pts), 036 (-3 pts), 037 (-2 pts); Added STORY-048 (+5 pts), 049 (+3 pts), 053 (+6 pts), plus 4 deferred from Sprint 2 (+12 pts)

---

## Sprint 4: Production (14 stories, 31 points)

### Monitoring & Observability (13 points)
| ID | Title | Points | Priority | File |
|----|-------|--------|----------|------|
| STORY-038 | Create CloudWatch pipeline dashboard | 5 | P0 | [✅](./stories/STORY_038_pipeline_dashboard.md) |
| STORY-039 | Create CloudWatch cost dashboard | 3 | P1 | [✅](./stories/STORY_039_cost_dashboard.md) |
| STORY-040 | Configure CloudWatch alarms | 3 | P0 | [✅](./stories/STORY_040_cloudwatch_alarms.md) |
| STORY-041 | Enable X-Ray tracing | 2 | P1 | [✅](./stories/STORY_041_xray_tracing.md) |

### Documentation & Diagrams (9 points)
| ID | Title | Points | Priority | File |
|----|-------|--------|----------|------|
| STORY-010 | Create pipeline architecture diagram | 2 | P2 | [✅](./stories/STORY_010_pipeline_architecture_diagram.md) |
| STORY-011 | Create data flow diagram | 2 | P2 | [✅](./stories/STORY_011_data_flow_diagram.md) |
| STORY-042 | Write operational runbook | 3 | P0 | [✅](./stories/STORY_042_operational_runbook.md) |
| STORY-043 | Write deployment guide | 2 | P1 | [✅](./stories/STORY_043_deployment_guide.md) |
| STORY-044 | Write developer guide | 2 | P1 | [✅](./stories/STORY_044_developer_guide.md) |

### Testing & CI/CD (6 points)
| ID | Title | Points | Priority | File |
|----|-------|--------|----------|------|
| STORY-036 | Write 10+ E2E tests | 3 | P1 | [✅](./stories/STORY_036_write_e2e_tests.md) |
| STORY-037 | Configure CI/CD test pipeline | 2 | P1 | [✅](./stories/STORY_037_configure_cicd_tests.md) |
| STORY-050 | State machine rollback procedure | 2 | P1 | [✅](./stories/STORY_050_state_machine_rollback.md) |

### Production Deployment (3 points)
| ID | Title | Points | Priority | File |
|----|-------|--------|----------|------|
| STORY-045 | Production deployment & validation | 3 | P0 | [✅](./stories/STORY_045_production_deployment.md) |

**Sprint 4 Total**: 31 points
**Changes**: Added STORY-010, 011 from Sprint 1 (+4 pts); Added STORY-036, 037, 050 from Sprint 3 (+7 pts)

---

## Summary by Priority

| Priority | Stories | Points | Percentage |
|----------|---------|--------|------------|
| **P0 (Critical)** | 26 | 102 | 61% |
| **P1 (High)** | 21 | 51 | 31% |
| **P2 (Medium)** | 8 | 14 | 8% |
| **P3 (Low)** | 0 | 0 | 0% |
| **Total** | **55** | **167** | **100%** |

---

## Summary by Size

| Size | Count | Total Points | Avg Points |
|------|-------|--------------|------------|
| **1 point** (Trivial) | 2 | 2 | 1.0 |
| **2 points** (Small) | 10 | 20 | 2.0 |
| **3 points** (Medium) | 15 | 45 | 3.0 |
| **5 points** (Large) | 15 | 75 | 5.0 |
| **8 points** (Very Large) | 2 | 16 | 8.0 |
| **Total** | **44** | **158** | **3.6** |

Note: Total is 44 stories with 158 points due to Sprint 3 adjustment (STORY-034 is 8 points)

---

## Story Types

| Type | Count | Points |
|------|-------|--------|
| **Lambda Development** | 15 | 55 |
| **Infrastructure** | 10 | 34 |
| **Testing** | 4 | 18 |
| **Documentation** | 10 | 25 |
| **Monitoring** | 4 | 13 |
| **State Machine** | 5 | 21 |

---

## Completion Status

| Status | Stories | Points | Percentage |
|--------|---------|--------|------------|
| ✅ **Created** | 55 | 167 | 100% |
| 🔴 **To Do** | 55 | 167 | 100% |
| 🟡 **In Progress** | 0 | 0 | 0% |
| 🟢 **Done** | 0 | 0 | 0% |

**New Stories Added** (Dec 14, 2025 rebalancing):
- STORY-046: Multi-year initial load orchestration
- STORY-047: Create check_congress_updates Lambda
- STORY-048: Create Soda quality check YAML definitions
- STORY-049: Add dimension validation step
- STORY-050: State machine rollback procedure
- STORY-051: Write unit tests - Sprint 1 watermarking
- STORY-052: Write unit tests - Sprint 2 Gold wrappers
- STORY-053: Write unit tests - Sprint 3 state machine

**Removed Stories**:
- STORY-034: Write 70+ unit tests (replaced by distributed testing: STORY-051, 052, 053)
- STORY-035: Write 20+ integration tests (merged into STORY-053)

---

## File Locations

All user stories are located in: `docs/agile/stories/`

```
stories/
├── STORY_001_disable_eventbridge.md
├── STORY_002_fix_max_concurrency.md
├── STORY_003_watermarking_house_fd.md
├── STORY_004_watermarking_congress.md
├── STORY_005_watermarking_lobbying.md
├── STORY_006_github_actions_stepfunctions.md
├── STORY_007_sns_email_subscriptions.md
├── STORY_008_fix_terraform_duplication.md
├── STORY_009_remove_hardcoded_ids.md
├── STORY_010_pipeline_architecture_diagram.md
├── STORY_011_data_flow_diagram.md
├── STORY_012_error_handling_diagram.md
├── STORY_013_cost_optimization_diagram.md
├── STORY_014_state_machine_diagram.md
├── STORY_015_update_claude_md.md
├── STORY_016_build_dim_members.md
├── STORY_017_build_dim_assets.md
├── STORY_018_build_dim_bills.md
├── STORY_019_build_dim_lobbyists.md
├── STORY_020_build_dim_dates.md
├── STORY_021_build_fact_transactions.md
├── STORY_022_build_fact_filings.md
├── STORY_023_build_fact_lobbying.md
├── STORY_024_build_fact_cosponsors.md
├── STORY_025_build_fact_amendments.md
├── STORY_026_compute_trending_stocks.md
├── STORY_027_compute_member_stats.md
├── STORY_028_design_unified_state_machine.md
├── STORY_029_bronze_ingestion_phase.md
├── STORY_030_silver_transformation_phase.md
├── STORY_031_gold_layer_phase.md
├── STORY_032_quality_checks_phase.md
├── STORY_033_run_soda_checks_lambda.md
├── STORY_034_write_unit_tests.md
├── STORY_035_write_integration_tests.md
├── STORY_036_write_e2e_tests.md
├── STORY_037_configure_cicd_tests.md
├── STORY_038_pipeline_dashboard.md
├── STORY_039_cost_dashboard.md
├── STORY_040_cloudwatch_alarms.md
├── STORY_041_xray_tracing.md
├── STORY_042_operational_runbook.md
├── STORY_043_deployment_guide.md
├── STORY_044_developer_guide.md
└── STORY_045_production_deployment.md
```

**Total Files**: 45 user stories

---

## Next Steps

1. **Review**: Team reviews all 55 stories for clarity
2. **Refine**: Adjust story points if needed during sprint planning
3. **Execute**: Begin Sprint 1 (Dec 16, 2025)
4. **Track**: Update story status daily using agile board
5. **Complete**: Ship production-ready system (Jan 10, 2026)

## Rebalancing Summary

**Original Plan**: 45 stories, 144 points
**Revised Plan**: 55 stories, 167 points (+23 points, +10 stories)

**Rationale for Changes**:
1. **Distributed Testing**: Broke unrealistic 70-test story into 3 sprint-specific stories (15+20+35 tests)
2. **Missing Infrastructure**: Added check_congress_updates Lambda (critical gap)
3. **Multi-Year Orchestration**: Added proper initial load handling (5-year lookback)
4. **Quality Infrastructure**: Added Soda YAML definitions + dimension validation
5. **Production Readiness**: Added rollback procedure + 2 deferred diagrams from Sprint 1
6. **Realistic Velocity**: Increased from 36 pts/sprint to 40-50 pts/sprint (AI-assisted development)

---

**Last Updated**: 2025-12-14 (Rebalanced)
**Created By**: Engineering Team
**Status**: ✅ Ready for Sprint 1 (Optimized for AI-Assisted Development)
