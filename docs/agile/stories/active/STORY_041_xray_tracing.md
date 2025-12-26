# STORY-041: Enable X-Ray Tracing

**Epic**: EPIC-001 | **Sprint**: Sprint 4 | **Points**: 2 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** performance engineer
**I want** X-Ray tracing enabled
**So that** I identify bottlenecks

## Acceptance Criteria
- **GIVEN** X-Ray enabled for all Lambdas
- **WHEN** Pipeline executes
- **THEN** Traces visible in X-Ray console
- **AND** Service map shows Lambda dependencies
- **AND** Can drill into slow operations

## Technical Tasks
- [ ] Enable X-Ray in Terraform for all Lambdas
- [ ] Enable X-Ray for Step Functions
- [ ] Add X-Ray SDK to Lambda code (if needed)
- [ ] Verify service map
- [ ] Create sample trace analysis

## Terraform
```hcl
resource "aws_lambda_function" "example" {
  tracing_config {
    mode = "Active"
  }
}

resource "aws_sfn_state_machine" "platform" {
  tracing_configuration {
    enabled = true
  }
}
```

## Estimated Effort: 2 hours
**Target**: Jan 7, 2026
