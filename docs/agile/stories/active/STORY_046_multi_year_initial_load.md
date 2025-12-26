# STORY-046: Multi-Year Initial Load Orchestration

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 5 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** platform operator
**I want** initial pipeline execution to process 5 years of data automatically
**So that** the system is fully populated on first deployment without manual year-by-year triggers

## Acceptance Criteria
- **GIVEN** Fresh deployment with no existing data
- **WHEN** Pipeline executes in "initial_load" mode
- **THEN** State machine processes years 2020-2025 sequentially
- **AND** Each year completes Bronze → Silver → Gold before next year starts
- **AND** Progress is logged for each year completion
- **AND** Failure in one year does not block subsequent years (continue on error)

## Technical Tasks
- [ ] Add `execution_mode` parameter to state machine input schema
- [ ] Create Map state for multi-year iteration
- [ ] Update CheckForUpdates to accept year array input
- [ ] Add year validation (5-year lookback window)
- [ ] Implement sequential year processing with checkpointing
- [ ] Add CloudWatch metrics for year-by-year progress
- [ ] Test with 2 years (2024, 2025) in dev environment

## Implementation

### State Machine Input Schema (Updated)
```json
{
  "execution_type": "initial_load",
  "mode": "full_refresh",
  "parameters": {
    "years": [2020, 2021, 2022, 2023, 2024, 2025],
    "force_refresh": false
  }
}
```

### State Machine Modification (congress_data_platform.json)
```json
{
  "Comment": "Multi-Year Initial Load",
  "StartAt": "DetermineExecutionMode",
  "States": {
    "DetermineExecutionMode": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.execution_type",
          "StringEquals": "initial_load",
          "Next": "ProcessMultipleYears"
        }
      ],
      "Default": "CheckForUpdates"
    },
    "ProcessMultipleYears": {
      "Type": "Map",
      "ItemsPath": "$.parameters.years",
      "MaxConcurrency": 1,
      "Parameters": {
        "year.$": "$$.Map.Item.Value",
        "execution_type": "manual",
        "mode": "full_refresh"
      },
      "Iterator": {
        "StartAt": "ProcessSingleYear",
        "States": {
          "ProcessSingleYear": {
            "Type": "Task",
            "Resource": "arn:aws:states:::states:startExecution.sync:2",
            "Parameters": {
              "StateMachineArn": "${SELF_STATE_MACHINE_ARN}",
              "Input": {
                "execution_type": "manual",
                "mode": "full_refresh",
                "parameters": {
                  "year.$": "$.year"
                }
              }
            },
            "End": true,
            "Catch": [
              {
                "ErrorEquals": ["States.ALL"],
                "ResultPath": "$.error",
                "Next": "LogYearFailure"
              }
            ]
          },
          "LogYearFailure": {
            "Type": "Pass",
            "Parameters": {
              "year.$": "$.year",
              "error.$": "$.error",
              "status": "failed"
            },
            "End": true
          }
        }
      },
      "ResultPath": "$.year_results",
      "Next": "SummarizeInitialLoad"
    },
    "SummarizeInitialLoad": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "${SNS_PIPELINE_ALERTS_ARN}",
        "Subject": "Initial Load Complete",
        "Message.$": "States.JsonToString($.year_results)"
      },
      "End": true
    },
    "CheckForUpdates": {
      "Comment": "Regular incremental execution path",
      "Type": "Parallel",
      "Next": "EvaluateUpdates"
    }
  }
}
```

## Testing Strategy

### Unit Tests
```python
def test_initial_load_mode_triggers_multi_year():
    """Test that initial_load mode processes multiple years."""
    input_data = {
        "execution_type": "initial_load",
        "parameters": {"years": [2024, 2025]}
    }
    # Assert Map state is triggered with 2 iterations
    assert get_next_state(input_data) == "ProcessMultipleYears"

def test_year_array_validation():
    """Test that years outside 5-year window are rejected."""
    input_data = {
        "execution_type": "initial_load",
        "parameters": {"years": [2015, 2024]}  # 2015 is outside window
    }
    result = validate_years(input_data)
    assert result['valid_years'] == [2024]
    assert 2015 not in result['valid_years']
```

### Integration Test
```python
def test_multi_year_execution_completes():
    """Test full multi-year execution in dev environment."""
    sfn = boto3.client('stepfunctions')

    response = sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps({
            "execution_type": "initial_load",
            "parameters": {"years": [2024, 2025]}  # Small test set
        })
    )

    # Wait for completion
    wait_for_execution(response['executionArn'])

    # Assert both years processed
    execution = sfn.describe_execution(executionArn=response['executionArn'])
    assert execution['status'] == 'SUCCEEDED'

    # Verify Bronze data exists for both years
    s3 = boto3.client('s3')
    assert object_exists(s3, 'bronze/house/financial/year=2024/')
    assert object_exists(s3, 'bronze/house/financial/year=2025/')
```

## Estimated Effort: 5 hours
- 2 hours: State machine design + JSON updates
- 1 hour: Input validation + year array logic
- 1 hour: Testing (unit + integration)
- 1 hour: Documentation + deployment

## AI Development Notes
**Baseline**: state_machines/house_fd_pipeline.json:1-50 (existing CheckForUpdates pattern)
**Pattern**: AWS Step Functions Map state with sync execution
**Files to Modify**:
- state_machines/congress_data_platform.json:15-80 (add new states)
- infra/terraform/step_functions.tf:95 (add SELF_STATE_MACHINE_ARN variable)

**Token Budget**: 3,000 tokens (state machine JSON + terraform + tests)

**Dependencies**:
- STORY-028 (Unified state machine design) must be complete first
- State machine must support self-invocation (nested execution)

**Acceptance Criteria Verification**:
1. ✅ Manual execution with `execution_type: "initial_load"` processes all 6 years
2. ✅ Each year logged in CloudWatch with completion status
3. ✅ Failure in year 2021 does not prevent 2022-2025 from processing
4. ✅ Total execution time < 12 hours (2 hours/year × 6 years)

**Target**: Sprint 1, Day 2 (December 17, 2025)
