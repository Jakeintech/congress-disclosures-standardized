# Multi-Year Initial Load Orchestration

## Overview

The multi-year initial load feature allows the Congress Data Platform to process multiple years of data sequentially on first deployment, automatically populating the system with historical data (2020-2025) without requiring manual year-by-year triggers.

## Key Features

- **Sequential Processing**: Years are processed one at a time (MaxConcurrency: 1) to ensure each year completes Bronze → Silver → Gold before the next year starts
- **Continue on Error**: If one year fails, processing continues with subsequent years
- **CloudWatch Metrics**: Year-by-year progress is logged to CloudWatch for monitoring
- **SNS Notifications**: Summary notification sent after all years are processed
- **Dual State Machine Support**: Available in both `house_fd_pipeline` and `congress_data_platform` state machines

## Execution Modes

The state machines support three execution modes:

### 1. Initial Load Mode
Processes multiple years sequentially from an input array.

```json
{
  "execution_type": "initial_load",
  "years": [2020, 2021, 2022, 2023, 2024, 2025]
}
```

### 2. Manual Mode
Process a single year for ad-hoc re-processing.

```json
{
  "execution_type": "manual",
  "year": 2025
}
```

### 3. Scheduled Mode
Regular scheduled execution that checks for updates and processes new data only.

```json
{
  "execution_type": "scheduled"
}
```

## State Machine Flow

### Initial Load Execution Path

1. **CheckExecutionType** - Routes to MultiYearIterator if `execution_type: "initial_load"`
2. **MultiYearIterator** - Map state that iterates over years array
3. **StartChildExecution** - Starts nested state machine execution for each year
4. **LogYearSuccess/LogYearFailure** - Publishes CloudWatch metrics for year completion
5. **YearComplete** - Marks year processing complete
6. **SummarizeInitialLoad** - Sends SNS summary notification
7. **InitialLoadComplete** - Final success state

### Error Handling Flow

```
StartChildExecution
  ├─ Success → LogYearSuccess → YearComplete
  └─ Error → LogYearFailure → YearComplete (continue to next year)
```

Key aspects:
- Errors are caught and logged but do NOT halt execution
- Failed years are tracked in CloudWatch metrics
- Summary notification includes both successful and failed years

## CloudWatch Metrics

Each year's completion publishes metrics with the following parameters:

```json
{
  "pipeline": "house_fd" | "congress_data_platform",
  "phase": "year_complete",
  "status": "success" | "failed",
  "year": 2024,
  "execution_id": "<execution-arn>"
}
```

## Usage Examples

### AWS Console

1. Navigate to Step Functions in AWS Console
2. Select `congress-disclosures-house-fd-pipeline` or `congress-disclosures-data-platform`
3. Click "Start execution"
4. Enter payload (see examples below)
5. Click "Start execution"

### AWS CLI

Full 6-year initial load:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:congress-disclosures-house-fd-pipeline \
  --input '{"execution_type":"initial_load","years":[2020,2021,2022,2023,2024,2025]}'
```

Test with 2 years:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:congress-disclosures-house-fd-pipeline \
  --input '{"execution_type":"initial_load","years":[2024,2025]}'
```

### Python (boto3)

```python
import boto3
import json

sfn = boto3.client('stepfunctions')

# Full initial load
response = sfn.start_execution(
    stateMachineArn='arn:aws:states:us-east-1:123456789012:stateMachine:congress-disclosures-house-fd-pipeline',
    input=json.dumps({
        "execution_type": "initial_load",
        "years": [2020, 2021, 2022, 2023, 2024, 2025]
    })
)

print(f"Execution started: {response['executionArn']}")
```

## Monitoring

### CloudWatch Logs

State machine logs are written to:
```
/aws/vendedlogs/states/congress-disclosures-pipelines
```

### CloudWatch Metrics

Metrics are published to:
```
Namespace: CongressDisclosures/Pipeline
Dimensions:
  - pipeline: house_fd | congress_data_platform
  - phase: year_complete
  - status: success | failed
  - year: YYYY
```

### SNS Notifications

Summary notifications are sent to the `pipeline_alerts` SNS topic after all years complete:

```
Subject: House FD Initial Load Complete

Body:
House FD initial load completed.

Years Processed: 6

Results: [
  {"year": 2020, "status": "success"},
  {"year": 2021, "status": "success"},
  {"year": 2022, "status": "failed"},
  {"year": 2023, "status": "success"},
  {"year": 2024, "status": "success"},
  {"year": 2025, "status": "success"}
]

Execution ID: arn:aws:states:...
```

## Performance Characteristics

- **Sequential Processing**: ~2 hours per year (varies by data volume)
- **Full 6-year load**: ~12 hours total execution time
- **Failure Recovery**: Individual year failures do not block subsequent years
- **Idempotency**: Safe to re-run with same input (skip_existing logic in Bronze layer)

## Testing

Unit tests validate:
- Sequential processing (MaxConcurrency: 1)
- Error handling (continue on error)
- CloudWatch metrics publishing
- SNS summary notifications

Run tests:
```bash
pytest tests/unit/test_state_machine_definition.py -v -k multi_year
```

## Troubleshooting

### Year Execution Failed

1. Check CloudWatch Logs for the specific year's execution
2. Review error details in the failure metrics
3. Manually re-process failed year using manual mode:
   ```json
   {"execution_type": "manual", "year": 2022}
   ```

### Execution Timeout

If the state machine times out (7200 seconds = 2 hours):
- Check if individual year executions are hanging
- Review Lambda timeouts for Bronze/Silver/Gold phases
- Consider processing fewer years per execution

### Missing Metrics

If year completion metrics are not appearing:
- Verify `publish_pipeline_metrics` Lambda is deployed
- Check Lambda execution role has CloudWatch PutMetricData permission
- Review Lambda logs for errors

## Architecture Decision Record

**Decision**: Process years sequentially (MaxConcurrency: 1) instead of in parallel

**Rationale**:
- Prevents overwhelming Lambda concurrency limits
- Ensures deterministic execution order
- Easier to monitor and troubleshoot
- Reduces S3 write contention
- Aligns with "each year completes Bronze → Silver → Gold" requirement

**Trade-off**: Longer total execution time (~12 hours for 6 years)

## Future Enhancements

- **Year Validation**: Add Lambda to validate years are within 5-year lookback window
- **Checkpointing**: Store completed years in DynamoDB for resume capability
- **Parallel Gold Layer**: Allow parallel Gold layer processing within a year
- **Dynamic Year Array**: Auto-generate years array from current year - 5

## Related Documentation

- [State Machine Architecture](../ARCHITECTURE.md#state-machines)
- [Bronze Layer Ingestion](../EXTRACTION_ARCHITECTURE.md#bronze-layer)
- [CloudWatch Monitoring](../DEPLOYMENT.md#monitoring)
- [STORY-046 Requirements](../agile/stories/active/STORY_046_multi_year_initial_load.md)
