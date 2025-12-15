# STORY-050: State Machine Rollback Procedure

**Epic**: EPIC-001 | **Sprint**: Sprint 4 | **Points**: 2 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** platform operator
**I want** documented rollback procedure for state machine deployments
**So that** I can quickly revert to previous working version if new deployment has critical issues

## Acceptance Criteria
- **GIVEN** New unified state machine deployed
- **WHEN** Critical bug discovered in production
- **THEN** Rollback procedure documented with step-by-step instructions
- **AND** Blue/green deployment strategy prevents downtime
- **AND** EventBridge trigger points to correct state machine version
- **AND** Rollback tested in dev environment
- **AND** Maximum rollback time: 10 minutes

## Technical Tasks
- [ ] Document blue/green deployment pattern for state machines
- [ ] Create rollback shell script (`scripts/rollback_state_machine.sh`)
- [ ] Add state machine version tagging in Terraform
- [ ] Document EventBridge trigger switching procedure
- [ ] Test rollback in dev environment
- [ ] Add rollback procedure to operational runbook (STORY-042)
- [ ] Create CloudWatch dashboard for state machine version monitoring

## Implementation

### Blue/Green Deployment Pattern

**Concept**:
1. Deploy new state machine with version suffix (e.g., `congress-data-platform-v2`)
2. Test new state machine with manual execution
3. Switch EventBridge trigger to new state machine
4. Keep old state machine for 24 hours (for rollback)
5. Delete old state machine after 24 hours if no issues

### Terraform Version Tagging
```hcl
# infra/terraform/step_functions.tf (update)

locals {
  state_machine_version = var.state_machine_version  # e.g., "v1", "v2"
  state_machine_name = "${var.project_name}-data-platform-${local.state_machine_version}"
}

resource "aws_sfn_state_machine" "congress_data_platform" {
  name     = local.state_machine_name
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile(
    "${path.module}/../../state_machines/congress_data_platform.json",
    local.state_machine_vars
  )

  tags = merge(
    local.standard_tags,
    {
      Version     = local.state_machine_version
      DeployedAt  = timestamp()
      PreviousARN = data.aws_ssm_parameter.previous_state_machine_arn.value
    }
  )
}

# Store current ARN in SSM for rollback reference
resource "aws_ssm_parameter" "current_state_machine_arn" {
  name  = "/${var.project_name}/state-machine/current-arn"
  type  = "String"
  value = aws_sfn_state_machine.congress_data_platform.arn

  tags = local.standard_tags
}

# Read previous ARN (for rollback)
data "aws_ssm_parameter" "previous_state_machine_arn" {
  name = "/${var.project_name}/state-machine/previous-arn"

  # Use current ARN as default if no previous exists
  default = aws_sfn_state_machine.congress_data_platform.arn
}
```

### EventBridge Trigger Management
```hcl
# infra/terraform/eventbridge.tf (update)

# Daily trigger uses SSM parameter for state machine ARN
resource "aws_cloudwatch_event_target" "daily_pipeline" {
  rule      = aws_cloudwatch_event_rule.daily_pipeline.name
  target_id = "DailyPipelineTarget"

  # Read ARN from SSM (can be switched for rollback)
  arn = data.aws_ssm_parameter.current_state_machine_arn.value

  role_arn = aws_iam_role.eventbridge_role.arn

  input = jsonencode({
    execution_type = "scheduled",
    mode           = "incremental"
  })
}
```

### Rollback Shell Script
```bash
#!/bin/bash
# scripts/rollback_state_machine.sh
# Purpose: Rollback to previous state machine version

set -e

PROJECT_NAME="congress-disclosures"
AWS_REGION="us-east-1"

echo "========================================="
echo "State Machine Rollback Tool"
echo "========================================="

# Step 1: Get current and previous ARNs
CURRENT_ARN=$(aws ssm get-parameter \
  --name "/${PROJECT_NAME}/state-machine/current-arn" \
  --query 'Parameter.Value' \
  --output text \
  --region $AWS_REGION)

PREVIOUS_ARN=$(aws ssm get-parameter \
  --name "/${PROJECT_NAME}/state-machine/previous-arn" \
  --query 'Parameter.Value' \
  --output text \
  --region $AWS_REGION)

echo "Current State Machine: $CURRENT_ARN"
echo "Previous State Machine: $PREVIOUS_ARN"

if [ "$CURRENT_ARN" == "$PREVIOUS_ARN" ]; then
  echo "ERROR: No previous version available for rollback"
  exit 1
fi

# Step 2: Verify previous state machine still exists
if ! aws stepfunctions describe-state-machine \
  --state-machine-arn "$PREVIOUS_ARN" \
  --region $AWS_REGION &> /dev/null; then
  echo "ERROR: Previous state machine not found. ARN: $PREVIOUS_ARN"
  exit 1
fi

echo ""
read -p "Confirm rollback to previous version? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Rollback cancelled"
  exit 0
fi

# Step 3: Test previous state machine with dry run
echo ""
echo "Testing previous state machine with dry run..."
TEST_EXECUTION=$(aws stepfunctions start-execution \
  --state-machine-arn "$PREVIOUS_ARN" \
  --name "rollback-test-$(date +%s)" \
  --input '{"execution_type":"test","mode":"incremental","parameters":{"year":2024}}' \
  --region $AWS_REGION \
  --query 'executionArn' \
  --output text)

echo "Test execution started: $TEST_EXECUTION"
echo "Waiting 30 seconds for test execution to complete..."
sleep 30

TEST_STATUS=$(aws stepfunctions describe-execution \
  --execution-arn "$TEST_EXECUTION" \
  --region $AWS_REGION \
  --query 'status' \
  --output text)

if [ "$TEST_STATUS" != "SUCCEEDED" ]; then
  echo "ERROR: Test execution failed. Status: $TEST_STATUS"
  echo "Rollback aborted. Check CloudWatch logs for details."
  exit 1
fi

echo "✓ Test execution succeeded"

# Step 4: Update SSM parameter to point to previous ARN
echo ""
echo "Switching EventBridge trigger to previous state machine..."
aws ssm put-parameter \
  --name "/${PROJECT_NAME}/state-machine/current-arn" \
  --value "$PREVIOUS_ARN" \
  --overwrite \
  --region $AWS_REGION

# Step 5: Verify EventBridge trigger updated
echo "Verifying EventBridge trigger..."
sleep 5

NEW_TARGET_ARN=$(aws events list-targets-by-rule \
  --rule "${PROJECT_NAME}-daily-pipeline" \
  --region $AWS_REGION \
  --query 'Targets[0].Arn' \
  --output text)

if [ "$NEW_TARGET_ARN" == "$PREVIOUS_ARN" ]; then
  echo "✓ EventBridge trigger successfully updated"
else
  echo "WARNING: EventBridge trigger may not have updated. Please verify manually."
fi

# Step 6: Send SNS notification
aws sns publish \
  --topic-arn "arn:aws:sns:${AWS_REGION}:$(aws sts get-caller-identity --query Account --output text):${PROJECT_NAME}-pipeline-alerts" \
  --subject "State Machine Rolled Back" \
  --message "State machine rolled back from ${CURRENT_ARN} to ${PREVIOUS_ARN} at $(date)" \
  --region $AWS_REGION

echo ""
echo "========================================="
echo "✓ Rollback Complete"
echo "========================================="
echo "Previous ARN (now active): $PREVIOUS_ARN"
echo "Old ARN (will be deleted after 24 hours): $CURRENT_ARN"
echo ""
echo "IMPORTANT:"
echo "1. Monitor next scheduled execution (6 AM UTC)"
echo "2. Check CloudWatch logs for any errors"
echo "3. Old state machine will be kept for 24 hours"
echo "4. Run 'terraform apply' to update Terraform state"
```

### Rollback Procedure Documentation (for STORY-042 Runbook)

```markdown
## Rollback Procedure: State Machine Deployment

### When to Rollback
- Critical bug in new state machine causing pipeline failures
- Unexpected behavior after deployment
- Performance degradation (execution time > 3 hours)
- Data quality issues traced to state machine logic

### Prerequisites
- Previous state machine still deployed (kept for 24 hours after new deployment)
- AWS CLI configured with admin permissions
- Access to rollback script: `scripts/rollback_state_machine.sh`

### Step-by-Step Rollback (10 minutes)

#### 1. Identify Issue (2 minutes)
```bash
# Check recent executions
aws stepfunctions list-executions \
  --state-machine-arn <CURRENT_ARN> \
  --status-filter FAILED \
  --max-items 10

# Check CloudWatch logs
aws logs tail /aws/vendedlogs/states/congress-disclosures-pipelines --follow
```

#### 2. Execute Rollback Script (5 minutes)
```bash
cd /path/to/congress-disclosures-standardized
chmod +x scripts/rollback_state_machine.sh
./scripts/rollback_state_machine.sh
```

Script will:
- ✓ Verify previous state machine exists
- ✓ Test previous state machine with dry run
- ✓ Switch EventBridge trigger to previous version
- ✓ Send SNS notification

#### 3. Verify Rollback (3 minutes)
```bash
# Verify EventBridge trigger
aws events list-targets-by-rule \
  --rule congress-disclosures-daily-pipeline

# Trigger manual execution to test
aws stepfunctions start-execution \
  --state-machine-arn <PREVIOUS_ARN> \
  --input '{"execution_type":"manual","mode":"incremental"}'

# Monitor execution
aws stepfunctions describe-execution --execution-arn <EXECUTION_ARN>
```

#### 4. Post-Rollback Actions
- [ ] Notify team in Slack/email
- [ ] Create incident report (document what went wrong)
- [ ] Update Terraform state: `terraform refresh`
- [ ] Fix bug in new state machine
- [ ] Test fix in dev environment before redeploying

### Rollback Failure Scenarios

**Scenario 1: Previous state machine deleted**
- **Solution**: Redeploy last known good version from git history
- **Command**: `git checkout <COMMIT_SHA> -- state_machines/congress_data_platform.json`
- **Time**: 15-20 minutes

**Scenario 2: Both versions broken**
- **Solution**: Disable EventBridge trigger, deploy emergency fix
- **Command**: `aws events disable-rule --name congress-disclosures-daily-pipeline`
- **Time**: 30 minutes

**Scenario 3: Terraform state out of sync**
- **Solution**: `terraform import` previous state machine
- **Command**: `terraform import aws_sfn_state_machine.congress_data_platform <ARN>`
- **Time**: 10 minutes
```

## Testing Strategy

### Dev Environment Test
```bash
# 1. Deploy "broken" state machine (simulated)
terraform apply -var="state_machine_version=v2-broken"

# 2. Verify it fails
aws stepfunctions start-execution --state-machine-arn <NEW_ARN> --input '{}'

# 3. Execute rollback
./scripts/rollback_state_machine.sh

# 4. Verify rollback succeeded
aws stepfunctions start-execution --state-machine-arn <OLD_ARN> --input '{}'
```

## Estimated Effort: 2 hours
- 30 min: Terraform version tagging setup
- 30 min: Rollback script creation
- 30 min: Documentation (add to runbook)
- 30 min: Testing in dev environment

## AI Development Notes
**Baseline**: AWS Step Functions best practices + blue/green deployment patterns
**Pattern**: Version tagging + SSM parameter switching
**Files to Create**:
- scripts/rollback_state_machine.sh (new, ~150 lines)
- docs/OPERATIONAL_RUNBOOK.md:250-350 (add rollback section)

**Files to Modify**:
- infra/terraform/step_functions.tf:170-200 (add version tagging)
- infra/terraform/eventbridge.tf:15-30 (use SSM parameter for ARN)

**Token Budget**: 2,000 tokens (script + terraform + documentation)

**Dependencies**:
- STORY-042 (Operational Runbook) must be ready for rollback section
- Dev environment for testing

**Acceptance Criteria Verification**:
1. ✅ Rollback script executes in < 10 minutes
2. ✅ Blue/green deployment prevents downtime
3. ✅ EventBridge trigger switches correctly
4. ✅ Tested successfully in dev environment
5. ✅ Documentation added to operational runbook

**Target**: Sprint 4, Day 2 (January 7, 2026)
