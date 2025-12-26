# STORY-035: Write 20+ Integration Tests

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 5 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** QA engineer
**I want** integration tests with real AWS services
**So that** we verify end-to-end flows

## Acceptance Criteria
- **GIVEN** Integration test suite
- **WHEN** I run `pytest tests/integration/`
- **THEN** 20+ tests execute against real AWS
- **AND** All tests passing
- **AND** Resources cleaned up after tests

## Technical Tasks
- [ ] Create integration test files
- [ ] Test state machine execution (5 tests)
- [ ] Test Bronze→Silver flow (5 tests)
- [ ] Test Silver→Gold flow (5 tests)
- [ ] Test SQS queue integration (3 tests)
- [ ] Test API endpoints (2 tests)
- [ ] Add cleanup fixtures

## Test Examples
```python
def test_state_machine_executes():
    sfn = boto3.client('stepfunctions')
    response = sfn.start_execution(
        stateMachineArn='arn:...',
        input='{"execution_type":"test"}'
    )
    # Wait for completion
    # Assert succeeded

def test_bronze_to_silver_flow():
    # Upload test PDF to Bronze
    # Trigger extraction Lambda
    # Verify Silver output
    # Cleanup
```

## Estimated Effort: 5 hours
**Target**: Jan 3, 2026
