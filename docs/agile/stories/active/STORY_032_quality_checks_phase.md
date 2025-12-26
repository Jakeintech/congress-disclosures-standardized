# STORY-032: Implement Quality Checks Phase

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 3 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** data quality engineer
**I want** Soda quality checks in state machine
**So that** bad data doesn't reach API

## Acceptance Criteria
- **GIVEN** Quality phase in state machine
- **WHEN** Execution reaches quality checks
- **THEN** Runs Soda checks Lambda
- **AND** Evaluates pass/fail/warn
- **AND** Sends SNS alert on failure
- **AND** Continues to API update only if passed

## Technical Tasks
- [ ] Add RunSodaChecks Task state
- [ ] Add EvaluateQuality Choice state
- [ ] Add SNS publish on failure
- [ ] Configure quality gate logic
- [ ] Test fail scenarios

## Implementation
```json
"RunSodaChecks": {
  "Type": "Task",
  "Resource": "${LAMBDA_RUN_SODA_CHECKS}",
  "Catch": [{
    "ErrorEquals": ["QualityCheckFailed"],
    "Next": "NotifyQualityFailure"
  }],
  "Next": "EvaluateQuality"
},
"EvaluateQuality": {
  "Type": "Choice",
  "Choices": [{
    "Variable": "$.quality.status",
    "StringEquals": "passed",
    "Next": "UpdateAPICache"
  }],
  "Default": "NotifyQualityFailure"
}
```

## Estimated Effort: 3 hours
**Target**: Jan 2, 2026
