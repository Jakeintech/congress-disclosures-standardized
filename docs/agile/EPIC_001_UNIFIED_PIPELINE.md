# EPIC-001: Unified Data Platform Migration

**Status**: 🔴 In Progress
**Priority**: P0 - Critical
**Owner**: Engineering Team
**Created**: 2025-12-14
**Target Completion**: 2026-01-10 (4 weeks)
**Revised Story Points**: 167 (increased from 144 for realistic pacing)

---

## Epic Summary

**As a** platform operator
**I want** a production-ready, unified data pipeline with Step Functions orchestration
**So that** we have reliable, cost-effective data ingestion and transformation that scales

---

## Business Value

### Cost Savings
- **Current State**: Hourly EventBridge trigger → $4,000+/month projected
- **Target State**: Daily scheduled execution → $8-15/month
- **Savings**: $3,985+/month ($47,820/year)

### Reliability Improvements
- **Current**: 4 siloed pipelines, 15% test coverage, manual error handling
- **Target**: 1 unified pipeline, 80%+ test coverage, automatic error recovery
- **Impact**: 99%+ pipeline success rate (vs. current ~85%)

### Operational Efficiency
- **Current**: Manual interventions, no visibility, script-based orchestration
- **Target**: Visual workflows, CloudWatch dashboards, SNS alerting
- **Impact**: 90% reduction in manual operations time

### Scalability
- **Current**: Sequential processing (41 hours for 5,000 PDFs)
- **Target**: Parallel processing with MaxConcurrency=10 (4 hours)
- **Impact**: 10x faster data refresh

---

## Problem Statement

The current data platform has critical issues preventing production readiness:

### 1. Cost Explosion Risk 🔴
- EventBridge triggers pipeline **hourly** (should be daily)
- No watermarking → reprocesses same data every hour
- **Projected monthly cost**: $4,000+ (vs. budget of $5-20)

### 2. Missing Infrastructure 🔴
- **47 Lambda functions referenced but only 19 exist**
- Step Functions state machines can't execute
- Gold layer orchestration broken

### 3. Broken Orchestration 🔴
- 4 siloed pipelines with no dependency management
- Race conditions between pipelines
- GitHub Actions still use old Python scripts (not Step Functions)

### 4. Insufficient Testing 🟡
- **Current coverage: ~15%** (target: 80%)
- No integration tests for state machines
- No E2E tests for full pipeline

### 5. Poor Observability 🟡
- No CloudWatch dashboards
- No SNS alerts configured
- No visibility into pipeline execution state

---

## Scope

### In Scope ✅

**Infrastructure**:
- Create 47 Lambda functions (28 new + 19 refactored)
- Design & implement unified Step Functions state machine
- Refactor Terraform for modular deployment
- Configure EventBridge for daily (not hourly) execution

**Data Pipeline**:
- Implement watermarking for incremental updates
- Fix Bronze → Silver → Gold data flow
- Implement Soda data quality checks
- Create proper error handling & retries

**Testing** (Distributed Across All Sprints):
- 80 total tests (80%+ coverage target)
- Sprint 1: 15 tests for watermarking functions
- Sprint 2: 20 tests for Gold layer wrappers
- Sprint 3: 35 tests for state machine + integration
- Sprint 4: 10 E2E tests for full pipeline flows
- pytest + moto for AWS service mocking
- CI/CD pipeline with automated test runs

**Monitoring**:
- CloudWatch dashboards (pipeline metrics, cost tracking)
- SNS alerting (critical failures, warnings)
- X-Ray tracing (performance analysis)

**Documentation**:
- 5 Mermaid diagrams (architecture, data flow, error handling, etc.)
- Updated CLAUDE.md (Step Functions architecture)
- Operational runbooks (troubleshooting, deployment)
- Developer guides (adding Lambdas, modifying state machines)

### Out of Scope ❌

- **New data sources** (focus on existing: House FD, Congress.gov, Lobbying)
- **API redesign** (keep existing API, just update cache)
- **Website redesign** (keep existing Next.js site)
- **Database migration** (stay with Parquet + S3)
- **Machine learning features** (defer to future)
- **Mobile app**

---

## Success Criteria

### Functional Requirements

- [ ] **Pipeline executes end-to-end without errors**
  - Bronze ingestion completes for all 3 sources
  - Silver extraction processes all PDFs
  - Gold layer builds all dimensions, facts, aggregates
  - Quality checks pass
  - API cache updated

- [ ] **All 47 Lambda functions deployed and working**
  - Update detection functions (3)
  - Bronze ingestion functions (3)
  - Silver transformation functions (4)
  - Gold builders (25)
  - Quality & publish functions (3)
  - Monitoring functions (1)

- [ ] **State machine handles all scenarios**
  - No updates detected → Exit gracefully
  - Partial updates → Process only updated sources
  - Full refresh → Process all data
  - Errors → Retry with exponential backoff
  - Critical failures → Alert SNS, fail gracefully

- [ ] **Data quality maintained**
  - 100% of Bronze data preserved
  - 95%+ extraction success rate (Silver)
  - All Soda checks passing (Gold)
  - Zero data loss during processing

### Non-Functional Requirements

- [ ] **Cost within budget**
  - Monthly AWS cost < $20 (target: $8-15)
  - Daily incremental run < $0.50
  - Lambda stays within free tier (400K GB-seconds/month)

- [ ] **Performance targets met**
  - Full pipeline execution < 2 hours
  - Incremental pipeline < 30 minutes
  - API response time < 5 seconds (p99)

- [ ] **Reliability targets met**
  - Pipeline success rate ≥ 99%
  - Automatic retry on transient failures
  - Manual intervention required < 1% of executions

- [ ] **Test coverage ≥ 80%**
  - Total tests: 80 tests (distributed across all 4 sprints)
  - Sprint 1: 15 tests for watermarking (STORY-051)
  - Sprint 2: 20 tests for Gold wrappers (STORY-052)
  - Sprint 3: 35 tests for state machine + integration (STORY-053)
  - Sprint 4: 10 E2E tests (STORY-036)
  - All critical paths tested
  - pytest + moto for AWS service mocking

- [ ] **Observability in place**
  - CloudWatch dashboards deployed
  - SNS alerts configured and tested
  - X-Ray tracing enabled
  - Logs searchable for 7+ days

### Documentation Complete

- [ ] **Architecture documentation**
  - 5 Mermaid diagrams created
  - ADR (Architecture Decision Record) complete
  - Data contracts documented
  - Lambda requirements spec complete
  - State machine specification complete
  - Testing strategy documented

- [ ] **Operational documentation**
  - Deployment guide (fresh setup)
  - Troubleshooting runbook (common issues)
  - Monitoring guide (dashboards, alerts)
  - Incident response playbook

- [ ] **Developer documentation**
  - CLAUDE.md updated with Step Functions
  - README updated with new workflows
  - Contributing guide updated
  - All make commands documented

---

## Sprints Breakdown

### Sprint 1: Foundation (Week 1, Dec 16-20) - 41 Story Points

**Goal**: Fix critical blockers, stop cost bleeding, establish foundation

**Key Deliverables**:
- EventBridge hourly trigger disabled → Prevent cost explosion
- Watermarking implemented (3 check Lambdas) → Incremental processing
- Multi-year initial load orchestration → 5-year lookback window
- check_congress_updates Lambda created → Missing critical Lambda
- GitHub Actions trigger Step Functions → Modern orchestration
- SNS alerts configured → Operational visibility
- 15 unit tests for watermarking → Testing foundation

**Stories**: 16 stories (added STORY-046, 047, 051; deferred STORY-010, 011)

**Changes from Original**:
- Added multi-year orchestration (STORY-046: 5 pts)
- Added check_congress_updates Lambda (STORY-047: 3 pts)
- Added Sprint 1 unit tests (STORY-051: 3 pts)
- Deferred 2 diagrams to Sprint 4 (STORY-010, 011: -4 pts)

---

### Sprint 2: Gold Layer (Week 2, Dec 23-27) - 43 Story Points

**Goal**: Create core Gold layer Lambda functions

**Key Deliverables**:
- 8 Gold layer Lambda wrappers (3 dim + 3 fact + 2 agg)
- dim_members, dim_assets, dim_bills (dimensions)
- fact_transactions, fact_filings, fact_lobbying (facts)
- trending_stocks, member_stats (aggregates)
- 20 unit tests for Gold wrappers (STORY-052)

**Stories**: 9 stories (deferred 4 lower-priority Lambdas to Sprint 3)

**Changes from Original**:
- Deferred dim_lobbyists, dim_dates to Sprint 3 (-6 pts)
- Deferred fact_cosponsors, fact_amendments to Sprint 3 (-6 pts)
- Added Sprint 2 unit tests (STORY-052: +4 pts)
- Focus on highest-priority Lambdas for MVP

---

### Sprint 3: Integration (Week 3, Dec 30-Jan 3) - 52 Story Points

**Goal**: Unified state machine + quality infrastructure + deferred Lambdas

**Key Deliverables**:
- Unified `congress_data_platform` state machine
- Soda quality checks Lambda + 15+ YAML check definitions
- Dimension validation step (prevents orphaned foreign keys)
- 4 deferred Gold layer Lambdas (dim_lobbyists, dim_dates, fact_cosponsors, fact_amendments)
- 35 unit + integration tests for Sprint 3 modules

**Stories**: 16 stories (added STORY-048, 049, 053; included deferred from Sprint 2)

**Changes from Original**:
- Removed unrealistic STORY-034 (70 tests, -8 pts)
- Added Soda YAML definitions (STORY-048: 5 pts)
- Added dimension validation (STORY-049: 3 pts)
- Added Sprint 3 distributed testing (STORY-053: 6 pts)
- Added 4 deferred stories from Sprint 2 (+12 pts)

---

### Sprint 4: Production Readiness (Week 4, Jan 6-10) - 31 Story Points

**Goal**: Monitoring, documentation, testing, production launch

**Key Deliverables**:
- CloudWatch dashboards (pipeline metrics + cost tracking)
- SNS alerting + CloudWatch alarms configured
- X-Ray tracing enabled
- All documentation complete (runbook, deployment guide, developer guide)
- Architecture diagrams (pipeline, data flow) - deferred from Sprint 1
- 10 E2E tests (full pipeline validation)
- CI/CD test pipeline configured
- State machine rollback procedure
- Production deployment + first successful run

**Stories**: 14 stories (added STORY-010, 011, 036, 037, 050)

**Changes from Original**:
- Added E2E tests from Sprint 3 (STORY-036: 3 pts)
- Added CI/CD pipeline from Sprint 3 (STORY-037: 2 pts)
- Added rollback procedure (STORY-050: 2 pts)
- Added 2 diagrams from Sprint 1 (STORY-010, 011: 4 pts)

---

**Total**: 167 Story Points across 55 Stories

**Testing Summary**:
- Sprint 1: 15 tests (watermarking) - STORY-051
- Sprint 2: 20 tests (Gold wrappers) - STORY-052
- Sprint 3: 35 tests (state machine + integration) - STORY-053
- Sprint 4: 10 tests (E2E) - STORY-036
- **Total: 80 tests** (80%+ coverage target)

---

## Dependencies

### External Dependencies
- ✅ AWS account with appropriate permissions
- ✅ Congress.gov API key (already have)
- ✅ GitHub Actions configured with AWS OIDC
- ⚠️ Terraform deployed to create base infrastructure

### Internal Dependencies
- Must complete Sprint 1 before Sprint 2 (foundation required)
- Must complete Sprint 2 before Sprint 3 (Lambdas needed for state machine)
- Must complete Sprint 3 before Sprint 4 (tests needed for production)

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Lambda timeout on large PDFs** | High | Medium | Increase timeout to 900s, implement chunking |
| **Terraform state corruption** | Critical | Low | Use remote state (S3), enable versioning |
| **AWS cost overruns** | High | Medium | CloudWatch alarms at $15, daily cost monitoring |
| **Missing test coverage** | Medium | High | Mandatory coverage checks in CI/CD (>80%) |
| **State machine too complex** | Medium | Medium | Break into smaller sub-state machines if needed |
| **Data quality issues** | High | Low | Soda checks as quality gates (fail pipeline on critical errors) |

---

## Stakeholders

| Stakeholder | Role | Involvement |
|------------|------|-------------|
| Engineering Team | Implementation | Daily development, code review |
| DevOps/Platform | Infrastructure | Terraform, AWS configuration, CI/CD |
| Data Owner | Requirements | Data contracts, quality requirements |
| Product Owner | Acceptance | Sprint demos, story acceptance |

---

## Definition of Done (Epic)

### All Sprints Complete
- [ ] Sprint 1: Foundation ✅
- [ ] Sprint 2: Gold Layer ✅
- [ ] Sprint 3: Integration ✅
- [ ] Sprint 4: Production ✅

### Production Deployment
- [ ] Deployed to production AWS account
- [ ] EventBridge daily trigger enabled
- [ ] Pipeline executed successfully (end-to-end)
- [ ] API serving fresh data
- [ ] Website displaying updated metrics

### Quality Gates Passed
- [ ] All unit tests passing (80%+ coverage)
- [ ] All integration tests passing
- [ ] All E2E tests passing
- [ ] No critical bugs outstanding
- [ ] Performance targets met
- [ ] Cost targets met ($8-15/month)

### Documentation Complete
- [ ] All technical specs complete
- [ ] All operational docs complete
- [ ] All developer docs complete
- [ ] All Mermaid diagrams created
- [ ] README and CLAUDE.md updated

### Sign-Off
- [ ] Engineering team sign-off
- [ ] Tech lead sign-off
- [ ] Product owner acceptance
- [ ] Post-deployment review completed

---

## Metrics & KPIs

### Development Metrics
- **Velocity**: Track story points completed per sprint
- **Bug Rate**: < 1 bug per 10 story points
- **Test Coverage**: ≥ 80% by end of Sprint 3
- **Code Review Time**: < 24 hours average

### Operational Metrics (Post-Launch)
- **Pipeline Success Rate**: ≥ 99%
- **Mean Time to Recovery (MTTR)**: < 1 hour
- **Execution Duration**: < 2 hours (full), < 30 min (incremental)
- **Monthly Cost**: $8-15 (target), < $20 (max)

### Data Quality Metrics
- **Bronze Completeness**: 100%
- **Silver Extraction Success**: ≥ 95%
- **Gold Soda Checks Pass Rate**: ≥ 98%
- **Data Freshness**: < 48 hours from source

---

## Timeline

```
Week 1 (Dec 16-20):  Sprint 1 - Foundation
Week 2 (Dec 23-27):  Sprint 2 - Gold Layer
Week 3 (Dec 30-Jan 3): Sprint 3 - Integration
Week 4 (Jan 6-10):   Sprint 4 - Production
Jan 11:              Epic complete, production launch
```

**Note**: Accounting for holidays (Dec 25, Jan 1) - may adjust dates

---

## Budget

### Labor
- 4 weeks × 40 hours/week × 1 engineer = 160 hours
- Estimated rate: $100/hour (fully loaded)
- **Labor cost**: $16,000

### AWS Costs
- Development/testing (4 weeks): $50
- Production (monthly): $8-15
- **AWS cost**: $50 (one-time) + $10/month (ongoing)

**Total Epic Budget**: $16,050 (one-time) + $10/month (ongoing)

**ROI**: Saves $3,985/month in AWS costs = **4-month payback period**

---

## Communication Plan

### Daily Standup
- Time: 9:00 AM daily
- Duration: 15 minutes
- Format: What did I complete yesterday? What am I working on today? Any blockers?

### Sprint Planning
- Time: Monday start of each sprint
- Duration: 2 hours
- Attendees: Engineering team, product owner, tech lead

### Sprint Review/Demo
- Time: Friday end of each sprint
- Duration: 1 hour
- Attendees: All stakeholders
- Format: Demo working features, review metrics

### Sprint Retrospective
- Time: Friday after sprint review
- Duration: 1 hour
- Attendees: Engineering team
- Format: What went well? What didn't? Action items

---

## Related Links

- **Sprints**:
  - [Sprint 1 - Foundation](./sprints/SPRINT_01_FOUNDATION.md)
  - [Sprint 2 - Gold Layer](./sprints/SPRINT_02_GOLD_LAYER.md)
  - [Sprint 3 - Integration](./sprints/SPRINT_03_INTEGRATION.md)
  - [Sprint 4 - Production](./sprints/SPRINT_04_PRODUCTION.md)

- **Technical Specs**:
  - [Architecture Decision Record](./technical/ARCHITECTURE_DECISION_RECORD.md)
  - [Data Contracts](./technical/DATA_CONTRACTS.md)
  - [Lambda Requirements Spec](./technical/LAMBDA_REQUIREMENTS_SPEC.md)
  - [State Machine Spec](./technical/STATE_MACHINE_SPEC.md)
  - [Testing Strategy](./technical/TESTING_STRATEGY.md)

- **Project Board**: [GitHub Projects](https://github.com/your-org/congress-disclosures-standardized/projects/1)
- **Slack Channel**: #congress-data-platform
- **Confluence**: [Epic-001 Page](https://confluence.example.com/epic-001)

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-12-14 | Epic created | Engineering Team |
| YYYY-MM-DD | [Change description] | [Author] |

---

**Epic Owner**: Engineering Team Lead
**Last Updated**: 2025-12-14
**Next Review**: End of Sprint 1 (2025-12-20)
