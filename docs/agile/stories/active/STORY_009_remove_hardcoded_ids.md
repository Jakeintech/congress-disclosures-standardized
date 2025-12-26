# STORY-009: Remove Hardcoded AWS Account IDs

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 2 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** DevOps engineer
**I want** dynamic AWS account IDs (not hardcoded)
**So that** deployment works in any AWS account

## Acceptance Criteria

### Scenario 1: Script uses environment variable
- **GIVEN** `scripts/run_congress_pipeline.py` line 162
- **WHEN** Script runs in different AWS account
- **THEN** Queue URL uses correct account ID
- **AND** No hardcoded "464813693153"

## Technical Tasks
- [ ] Find all hardcoded account IDs (grep codebase)
- [ ] Replace with Terraform data source
- [ ] Use `data.aws_caller_identity.current.account_id`
- [ ] Update scripts to use environment variables
- [ ] Test in dev account

## Current Issue
```python
# scripts/run_congress_pipeline.py line 162
fetch_queue_url = f"https://sqs.{AWS_REGION}.amazonaws.com/464813693153/congress-disclosures-development-congress-fetch-queue"
```

## Fix
```python
# Use environment variable
AWS_ACCOUNT_ID = os.environ['AWS_ACCOUNT_ID']
fetch_queue_url = f"https://sqs.{AWS_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/congress-disclosures-{ENVIRONMENT}-congress-fetch-queue"
```

```hcl
# Terraform: Pass account ID to Lambda
environment {
  variables = {
    AWS_ACCOUNT_ID = data.aws_caller_identity.current.account_id
  }
}
```

## Estimated Effort: 2 hours

**Target**: Dec 18, 2025
