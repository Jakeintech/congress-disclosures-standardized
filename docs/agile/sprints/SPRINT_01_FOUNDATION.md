# Sprint 1: Foundation

**Sprint Goal**: Fix critical blockers, stop cost bleeding, and establish architectural foundation

**Duration**: Week 1 (Dec 16-20, 2025)
**Story Points**: 34
**Status**: 🟡 Not Started

---

## Sprint Objectives

### Primary Goal 🎯
Stop the $4,000/month cost explosion and establish a solid foundation for the unified pipeline.

### Key Results
1. ✅ EventBridge hourly trigger disabled → Prevent runaway costs
2. ✅ Watermarking implemented → Prevent duplicate processing
3. ✅ GitHub Actions triggering Step Functions → Modern orchestration
4. ✅ SNS alerts configured → Operational visibility
5. ✅ Architecture documented → 5 Mermaid diagrams complete

---

## Sprint Backlog

| ID | Story | Points | Status | Assignee | Priority |
|----|-------|--------|----------|----------|----------|
| STORY-001 | Disable EventBridge hourly trigger | 1 | To Do | - | P0 |
| STORY-002 | Fix MaxConcurrency in state machines | 1 | To Do | - | P0 |
| STORY-003 | Implement watermarking in check_house_fd_updates | 3 | To Do | - | P0 |
| STORY-004 | Implement watermarking in check_congress_updates | 2 | To Do | - | P1 |
| STORY-005 | Implement watermarking in check_lobbying_updates | 2 | To Do | - | P1 |
| STORY-006 | Fix GitHub Actions to trigger Step Functions | 3 | To Do | - | P0 |
| STORY-046 | Multi-year initial load orchestration | 5 | To Do | - | P0 |
| STORY-047 | Create check_congress_updates Lambda | 3 | To Do | - | P0 |
| STORY-007 | Add SNS email subscriptions for alerts | 2 | To Do | - | P1 |
| STORY-008 | Fix Terraform variable duplication | 2 | To Do | - | P1 |
| STORY-009 | Remove hardcoded AWS account IDs | 2 | To Do | - | P1 |
| STORY-012 | Create error handling Mermaid diagram | 2 | To Do | - | P2 |
| STORY-013 | Create cost optimization diagram | 2 | To Do | - | P2 |
| STORY-014 | Create state machine flow diagram | 3 | To Do | - | P2 |
| STORY-015 | Update CLAUDE.md with Step Functions architecture | 5 | To Do | - | P1 |
| STORY-051 | Write unit tests - Sprint 1 watermarking | 3 | To Do | - | P0 |
| **Total** | **16 stories** | **41** | | | |

**Changes from Original Plan**:
- ✅ Added STORY-046: Multi-year initial load orchestration (5 points)
- ✅ Added STORY-047: Check Congress Updates Lambda (3 points)
- ✅ Added STORY-051: Unit tests for watermarking (3 points)
- ❌ Deferred STORY-010: Pipeline architecture diagram (2 points) → Sprint 4
- ❌ Deferred STORY-011: Data flow diagram (2 points) → Sprint 4

---

## Sprint Capacity

### Team Capacity
- **Team Size**: 1 engineer
- **Working Days**: 5 days
- **Hours per Day**: 8 hours
- **Total Hours**: 40 hours

### Story Point Conversion
- **Team Velocity**: ~30-35 points per sprint (estimated)
- **Hours per Point**: ~1.2 hours

### Capacity Planning
- **Planned Points**: 41
- **Team Velocity**: 40-45 points/week (AI-assisted development)
- **Buffer**: Included in realistic estimates
- **Stretch Goals**: None (focus on critical path)

---

## Day-by-Day Plan

### Day 1 (Monday, Dec 16)
**Focus**: Stop the bleeding - Critical cost fixes

**Tasks**:
- ✅ STORY-001: Disable EventBridge (15 min)
- ✅ STORY-002: Fix MaxConcurrency (15 min)
- ✅ STORY-003: Implement watermarking - House FD (3 hours)
  - Design watermarking approach
  - Implement SHA256 comparison
  - Test against real data
  - Deploy via Terraform

**Goal**: Cost explosion prevented, watermarking pattern established

---

### Day 2 (Tuesday, Dec 17)
**Focus**: Complete watermarking, fix orchestration, add critical missing Lambdas

**Tasks**:
- ✅ STORY-004: Watermarking - Congress.gov (2 hours)
- ✅ STORY-047: Check Congress Updates Lambda (3 hours)
  - Create Lambda function + Terraform resource
  - Implement DynamoDB watermarking
  - Test with real Congress.gov API
- ✅ STORY-005: Watermarking - Lobbying (2 hours)
- ✅ STORY-046: Multi-year initial load orchestration (Start, 2 hours)
  - Design state machine input schema for year arrays
  - Create Map state for multi-year processing

**Goal**: All update detection functions complete, orchestration patterns established

---

### Day 3 (Wednesday, Dec 18)
**Focus**: Alerting + Terraform cleanup + finish multi-year orchestration

**Tasks**:
- ✅ STORY-046: Multi-year initial load orchestration (Finish, 3 hours)
  - Implement state machine JSON
  - Add Terraform variables
  - Test with 2-year array in dev
- ✅ STORY-006: Fix GitHub Actions (3 hours)
  - Update workflows to use `aws stepfunctions start-execution`
  - Test with manual trigger
  - Verify execution completes
- ✅ STORY-007: SNS email subscriptions (2 hours)
  - Configure email subscriptions
  - Test alert delivery

**Goal**: Multi-year orchestration working, GitHub Actions modernized, alerting configured

---

### Day 4 (Thursday, Dec 19)
**Focus**: Terraform cleanup + documentation

**Tasks**:
- ✅ STORY-008: Fix Terraform variable duplication (2 hours)
- ✅ STORY-009: Remove hardcoded account IDs (2 hours)
- ✅ STORY-012: Error handling diagram (2 hours)
- ✅ STORY-013: Cost optimization diagram (2 hours)

**Goal**: Terraform cleaned up, error handling + cost diagrams complete

---

### Day 5 (Friday, Dec 20)
**Focus**: State machine diagram + documentation + unit tests

**Tasks**:
- ✅ STORY-014: State machine flow diagram (3 hours)
- ✅ STORY-051: Write unit tests - Sprint 1 watermarking (3 hours)
  - 6 tests for check_house_fd_updates
  - 5 tests for check_congress_updates
  - 4 tests for check_lobbying_updates
  - Configure pytest-cov (85% coverage target)
- ✅ STORY-015: Update CLAUDE.md (2 hours, partial)
  - Document Step Functions architecture
  - Update key workflows
  - (Full update continues in Sprint 4)

**End of Day**:
- Sprint Review (1 hour) - Demo working features
- Sprint Retrospective (1 hour) - Team reflection

**Goal**: Testing infrastructure in place, 15 unit tests passing, documentation started

---

## Definition of Done (Sprint Level)

### Code Quality
- [ ] All code changes committed and merged to main
- [ ] Terraform plan shows no unexpected changes
- [ ] All linting passing (flake8, black)
- [ ] No security vulnerabilities (bandit scan)

### Testing
- [ ] Unit tests added for new functions (coverage ≥ 80%)
- [ ] Manual testing completed and documented
- [ ] No regressions in existing functionality

### Deployment
- [ ] Terraform changes deployed to dev
- [ ] Terraform changes deployed to production
- [ ] Smoke tests passing in production
- [ ] Rollback plan documented and tested

### Documentation
- [ ] 5 Mermaid diagrams created
- [ ] CLAUDE.md updated with new architecture
- [ ] README updated (if applicable)
- [ ] All user stories marked "Done"

### Acceptance
- [ ] Sprint review completed
- [ ] Demo to stakeholders
- [ ] Product owner acceptance
- [ ] Sprint retrospective completed

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Terraform state corruption** | High | Use remote state, test in dev first |
| **EventBridge disable breaks scheduled runs** | Medium | Verify manual execution works before disabling |
| **Watermarking logic error** | High | Extensive unit tests, test with real data |
| **GitHub Actions permissions** | Medium | Test with OIDC auth, verify IAM roles |

---

## Dependencies

### Blockers
- ✅ AWS credentials configured in GitHub Actions
- ✅ Terraform deployed (base infrastructure exists)

### Blocks
- Sprint 2 (Gold Layer) - Needs watermarking and Terraform fixes from Sprint 1
- Sprint 3 (Integration) - Needs documentation and architectural foundation

---

## Success Metrics

### Functional Metrics
- [ ] EventBridge rule disabled (verified in AWS Console)
- [ ] Watermarking working (no duplicate ingestion)
- [ ] GitHub Actions triggering Step Functions (execution ARN returned)
- [ ] SNS alerts delivered (test alert received via email)

### Quality Metrics
- [ ] 0 critical bugs introduced
- [ ] Test coverage for new code ≥ 80%
- [ ] All stories completed (15/15)

### Business Metrics
- [ ] **Cost reduced**: Hourly → Daily execution saves $3,985/month
- [ ] **Documentation complete**: 5 Mermaid diagrams + updated CLAUDE.md

---

## Sprint Ceremonies

### Sprint Planning (Monday, Dec 16, 9:00 AM)
**Attendees**: Engineering team, product owner, tech lead
**Duration**: 2 hours
**Agenda**:
1. Review sprint goal
2. Review and commit to sprint backlog
3. Break down stories into tasks
4. Identify dependencies and risks

### Daily Standup (Daily, 9:00 AM)
**Duration**: 15 minutes
**Format**:
- What did I complete yesterday?
- What am I working on today?
- Any blockers?

### Sprint Review (Friday, Dec 20, 3:00 PM)
**Attendees**: All stakeholders
**Duration**: 1 hour
**Agenda**:
1. Demo completed stories
2. Review metrics (velocity, bugs)
3. Gather feedback

### Sprint Retrospective (Friday, Dec 20, 4:00 PM)
**Attendees**: Engineering team
**Duration**: 1 hour
**Format**:
- What went well?
- What didn't go well?
- What should we change for Sprint 2?

---

## Notes

### Assumptions
- AWS credentials are already configured
- Terraform state is healthy
- Team has access to all required AWS services

### Open Questions
- Should we add CloudWatch alarms in Sprint 1 or defer to Sprint 4?
  - **Decision**: Defer to Sprint 4 (focus on critical path)

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-12-14 | Sprint 1 plan created | Engineering Team |

---

**Sprint Owner**: Engineering Team Lead
**Last Updated**: 2025-12-14
**Next Review**: Daily standup
