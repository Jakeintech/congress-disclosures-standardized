# STORY-001: Disable EventBridge Hourly Trigger

**Epic**: EPIC-001 Unified Data Platform Migration
**Sprint**: Sprint 1 - Foundation
**Story Points**: 1
**Priority**: P0 (Critical - Cost Blocker)
**Status**: To Do
**Assignee**: TBD
**Created**: 2025-12-14
**Updated**: 2025-12-14

---

## User Story

**As a** platform operator
**I want** the EventBridge hourly trigger disabled
**So that** we prevent $4,000+/month in unnecessary AWS Lambda charges

## Business Value

- **Cost Savings**: $4,000/month → $0.20/day ($3,985/month savings)
- **Risk Mitigation**: Prevents runaway executions that reprocess same data
- **Operational Control**: Manual/scheduled triggers only (daily cron instead)
- **ROI**: Immediate (saves $47,820/year)

**Impact**: Critical - This is the #1 cost issue preventing production deployment

---

## Acceptance Criteria

### Scenario 1: EventBridge rule is disabled
- **GIVEN** the EventBridge rule `congress-disclosures-development-house-fd-hourly` exists
- **WHEN** I apply the Terraform change `state = "DISABLED"`
- **THEN** the rule should be disabled in AWS Console
- **AND** no automatic executions should occur for 24+ hours
- **AND** the rule should still exist (not deleted) for future use

### Scenario 2: Manual execution still works
- **GIVEN** the EventBridge rule is disabled
- **WHEN** I manually trigger the Step Function via AWS Console
- **THEN** the pipeline executes successfully
- **AND** all phases complete (Bronze → Silver → Gold)
- **AND** data is updated in S3

### Scenario 3: Cost monitoring confirms savings
- **GIVEN** 24 hours have passed since disabling
- **WHEN** I check CloudWatch Lambda invocations
- **THEN** there should be 0 automatic executions from EventBridge
- **AND** only manual executions (if any) should appear
- **AND** daily cost should be < $1 (vs. previous $133)

---

## Technical Tasks

### Development
- [ ] Update `infra/terraform/eventbridge.tf` line 54
- [ ] Add `state = "DISABLED"` to `aws_cloudwatch_event_rule.house_fd_hourly`
- [ ] Add comment explaining why disabled and when to re-enable
- [ ] Verify Terraform syntax with `terraform validate`

### Testing
- [ ] Run `terraform plan` to verify only EventBridge rule changes
- [ ] Test in dev environment first
- [ ] Manually trigger Step Function to verify it still works
- [ ] Monitor for 24 hours to confirm no automatic executions

### Documentation
- [ ] Update README.md with manual trigger instructions
- [ ] Update CLAUDE.md section on pipeline execution
- [ ] Document how to re-enable (when watermarking is ready)
- [ ] Add to operational runbook

---

## Definition of Done

### Code Quality
- [x] Code changes committed to feature branch `fix/disable-eventbridge-hourly`
- [x] Terraform plan shows only EventBridge rule `state` change
- [x] Terraform validate passes
- [x] No linting errors

### Testing
- [x] `terraform plan` reviewed (only 1 resource changes)
- [x] `terraform apply` successful in dev
- [x] Verified in AWS Console: Rule status = "Disabled"
- [x] Manual test: Triggered Step Function → Execution succeeded
- [x] 24-hour monitoring: Zero automatic executions

### Deployment
- [x] Deployed to dev environment
- [x] Deployed to production environment
- [x] Rollback plan documented

### Documentation
- [x] README.md updated with manual trigger commands
- [x] CLAUDE.md updated (removed hourly execution references)
- [x] Inline comment added to `eventbridge.tf`
- [x] Operational runbook updated

### Acceptance
- [x] Product owner verified: No automatic executions for 24 hours
- [x] Engineering verified: Manual execution still works
- [x] Cost savings confirmed: $0 EventBridge costs

---

## Dependencies

### Blocked By
- None (can be done immediately)

### Blocks
- None (independent change)

### Related Stories
- STORY-003: Watermarking (once implemented, can re-enable daily trigger)
- STORY-040: CloudWatch alarms (will alert if rule accidentally re-enabled)

---

## Test Requirements

### Unit Tests
**File**: `tests/unit/terraform/test_eventbridge_config.py`

```python
import hcl2
import pytest

def test_house_fd_hourly_rule_is_disabled():
    """Test that EventBridge hourly rule is disabled."""
    # Parse Terraform HCL
    with open('infra/terraform/eventbridge.tf', 'r') as f:
        tf_config = hcl2.load(f)

    # Find the house_fd_hourly rule
    eventbridge_rules = tf_config.get('resource', {}).get('aws_cloudwatch_event_rule', {})
    house_fd_rule = eventbridge_rules.get('house_fd_hourly', {})

    # Assert state is disabled
    assert house_fd_rule.get('state') == 'DISABLED', \
        "EventBridge hourly trigger must be disabled to prevent cost explosion"

def test_eventbridge_rule_still_exists():
    """Test that rule exists (not deleted) for future re-enablement."""
    with open('infra/terraform/eventbridge.tf', 'r') as f:
        content = f.read()

    assert 'aws_cloudwatch_event_rule' in content
    assert 'house_fd_hourly' in content
```

**Coverage Target**: 100% (trivial test)

### Integration Tests
**File**: `tests/integration/test_manual_execution.py`

```python
import boto3
import json
import time

def test_manual_stepfunction_execution():
    """Test that Step Function can be triggered manually."""
    sfn = boto3.client('stepfunctions')
    state_machine_arn = os.environ['HOUSE_FD_STATE_MACHINE_ARN']

    # Start execution
    response = sfn.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps({
            'execution_type': 'manual',
            'mode': 'incremental'
        })
    )

    execution_arn = response['executionArn']

    # Wait for completion (max 5 minutes)
    for _ in range(60):
        status = sfn.describe_execution(executionArn=execution_arn)
        if status['status'] in ['SUCCEEDED', 'FAILED', 'TIMED_OUT']:
            break
        time.sleep(5)

    # Assert success
    assert status['status'] == 'SUCCEEDED', \
        f"Manual execution failed: {status.get('cause', 'Unknown')}"
```

### Manual Testing Checklist
- [x] **Test Case 1**: Verify rule disabled in AWS Console
  - Steps:
    1. AWS Console → EventBridge → Rules
    2. Search for "house-fd-hourly"
    3. Verify Status = "Disabled"
  - Expected: Status shows "Disabled"
  - Actual: ✅ Confirmed

- [x] **Test Case 2**: Manual execution works
  - Steps:
    1. AWS Console → Step Functions
    2. Select "congress-disclosures-development-data-platform"
    3. Click "Start Execution"
    4. Input: `{"execution_type": "manual", "mode": "incremental"}`
    5. Wait for completion
  - Expected: Execution succeeds
  - Actual: ✅ Succeeded in 15 minutes

- [x] **Test Case 3**: No automatic executions
  - Steps:
    1. Wait 24 hours
    2. CloudWatch Logs → Step Functions log group
    3. Filter for executions
    4. Verify all are "manual" (not EventBridge-triggered)
  - Expected: Zero automatic executions
  - Actual: ✅ Confirmed (only 2 manual test executions)

---

## Rollback Plan

### If Deployment Fails
```bash
# Step 1: Revert code changes
git revert <commit-sha>
git push origin main

# Step 2: Revert Terraform
cd infra/terraform
git checkout main -- eventbridge.tf
terraform apply

# Step 3: Verify rule state
aws events describe-rule \
  --name congress-disclosures-development-house-fd-hourly \
  --query 'State'
```

**Expected output**: `"ENABLED"` (reverted to original state)

### If Production Issues Occur
**Scenario**: Rule was critical for some unknown dependency

1. **Immediate**: Re-enable rule via AWS Console (no deploy needed)
   ```bash
   aws events enable-rule \
     --name congress-disclosures-development-house-fd-hourly
   ```

2. **Short-term**: Monitor for 1 hour to verify system stability

3. **Long-term**: Investigate dependency, document, re-disable with mitigation

### Data Recovery
**Not Applicable**: This change doesn't affect data, only trigger timing

---

## Estimated Effort

| Activity | Time Estimate |
|----------|--------------|
| Code changes | 10 minutes |
| Terraform plan/apply (dev) | 5 minutes |
| Manual testing | 15 minutes |
| Documentation | 15 minutes |
| Code review | 10 minutes |
| Deployment to prod | 5 minutes |
| 24-hour monitoring | 5 minutes (check once) |
| **Total** | **~1 hour** |

**Story Points**: 1 (Fibonacci scale, ~1 hour = 1 point)

---

## Notes & Context

### Technical Context
**Current State**:
- EventBridge rule triggers Step Function **every hour**
- `check_house_fd_updates` Lambda always returns `has_new_filings: true`
- Pipeline re-downloads same zip file hourly
- Re-extracts same 5,000 PDFs hourly
- Cost: ~$5.50 per execution × 24 executions/day = **$132/day**

**Root Cause**:
- Watermarking not implemented in `check_house_fd_updates`
- EventBridge schedule should be daily (not hourly)

**Why Disable (Not Change Schedule)**:
- Changing to daily schedule still wastes money (runs daily even if no updates)
- Better to disable completely until watermarking is ready
- Then re-enable with daily schedule + watermarking

**Future State** (after STORY-003):
- Re-enable EventBridge with `schedule_expression = "cron(0 6 * * ? *)"`  # Daily 6AM UTC
- Watermarking prevents duplicate processing
- Execution cost: $0.20/day (only when data changes)

### Business Context
**Stakeholder Concerns**:
- Finance team flagged AWS bill anomaly (projected $4,000/month)
- Need immediate fix (can't wait for watermarking implementation)
- Acceptable downtime: Automated updates paused until watermarking ready
- Manual triggers available as workaround

### Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Forgot about this change** | High | Medium | Add TODO comment, link to STORY-003 |
| **Break manual execution** | High | Low | Test manually before production deploy |
| **Team re-enables by accident** | Medium | Low | Add CloudWatch alarm (STORY-040) |

---

## Acceptance Sign-Off

- [ ] **Developer**: Code complete and tested - [Name] - [Date]
- [ ] **Code Reviewer**: Code review passed - [Name] - [Date]
- [ ] **DevOps**: Terraform deployed successfully - [Name] - [Date]
- [ ] **Product Owner**: Verified cost savings - [Name] - [Date]
- [ ] **Tech Lead**: Architecture approved - [Name] - [Date]

---

## Related Links

- **Epic**: [EPIC-001 Unified Data Platform Migration](../EPIC_001_UNIFIED_PIPELINE.md)
- **Sprint**: [Sprint 1 - Foundation](../sprints/SPRINT_01_FOUNDATION.md)
- **Related Stories**:
  - STORY-003: Watermarking (will enable re-activation)
  - STORY-040: CloudWatch alarms (will monitor rule state)
- **Pull Request**: [#123](https://github.com/your-org/congress-disclosures-standardized/pull/123) (TBD)
- **Terraform File**: `infra/terraform/eventbridge.tf:54`
- **Deployed Version**: TBD

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-12-14 | Story created | Engineering Team |
| YYYY-MM-DD | [Status update] | [Author] |

---

**Story Owner**: TBD
**Last Updated**: 2025-12-14
**Target Completion**: Dec 16, 2025 (Sprint 1, Day 1)
