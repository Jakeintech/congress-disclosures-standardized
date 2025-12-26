# STORY-042: Write Operational Runbook

**Epic**: EPIC-001 | **Sprint**: Sprint 4 | **Points**: 3 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** on-call engineer
**I want** comprehensive troubleshooting guide
**So that** I resolve issues quickly

## Acceptance Criteria
- **GIVEN** Operational runbook document
- **WHEN** I encounter issue
- **THEN** Runbook has troubleshooting steps
- **AND** Includes 10+ common scenarios
- **AND** Has manual intervention procedures
- **AND** Lists emergency contacts

## Technical Tasks
- [ ] Create `docs/OPERATIONAL_RUNBOOK.md`
- [ ] Document common issues (10+ scenarios)
- [ ] Add troubleshooting flowcharts
- [ ] Document manual intervention procedures
- [ ] Add monitoring guide
- [ ] Include incident response playbook

## Runbook Sections
1. Common Issues
   - Pipeline timeout
   - Lambda OOM errors
   - Queue backed up
   - Extraction failures
   - Quality check failures
   - Cost spike

2. Manual Procedures
   - How to manually trigger pipeline
   - How to reprocess specific year
   - How to skip quality checks (emergency)
   - How to purge SQS queue

3. Monitoring
   - How to read dashboards
   - How to investigate failures
   - How to check costs

4. Incident Response
   - Severity levels (P0-P3)
   - Escalation paths
   - Emergency contacts

## Estimated Effort: 3 hours
**Target**: Jan 8, 2026
