# STORY-006: Fix GitHub Actions to Trigger Step Functions

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 3 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** DevOps engineer
**I want** GitHub Actions to trigger Step Functions (not Python scripts)
**So that** we use modern orchestration in CI/CD

## Acceptance Criteria

### Scenario 1: Daily workflow triggers state machine
- **GIVEN** GitHub Actions workflow `daily_incremental.yml`
- **WHEN** Cron triggers at 6AM UTC
- **THEN** AWS Step Functions execution starts
- **AND** Execution ARN is returned
- **AND** Workflow waits for completion

### Scenario 2: Manual workflow with parameters
- **GIVEN** `workflow_dispatch` trigger
- **WHEN** User specifies year=2024, mode=full_refresh
- **THEN** State machine receives correct input
- **AND** Pipeline processes year 2024 only

## Technical Tasks
- [ ] Update `.github/workflows/daily_incremental.yml`
- [ ] Replace `python scripts/run_smart_pipeline.py` with AWS CLI
- [ ] Add `aws stepfunctions start-execution`
- [ ] Add `aws stepfunctions describe-execution` (wait loop)
- [ ] Update secrets (add STATE_MACHINE_ARN)
- [ ] Test manual trigger

## Implementation
```yaml
# .github/workflows/daily_incremental.yml
- name: Trigger Step Function
  run: |
    EXECUTION_ARN=$(aws stepfunctions start-execution \
      --state-machine-arn ${{ secrets.STATE_MACHINE_ARN }} \
      --input '{"execution_type":"scheduled","mode":"incremental"}' \
      --query 'executionArn' \
      --output text)

    # Wait for completion
    while true; do
      STATUS=$(aws stepfunctions describe-execution \
        --execution-arn $EXECUTION_ARN \
        --query 'status' \
        --output text)

      if [[ "$STATUS" == "SUCCEEDED" ]]; then
        echo "Pipeline completed successfully"
        exit 0
      elif [[ "$STATUS" == "FAILED" ]]; then
        echo "Pipeline failed"
        exit 1
      fi

      sleep 30
    done
```

## Estimated Effort: 3 hours

**Target**: Dec 17, 2025
