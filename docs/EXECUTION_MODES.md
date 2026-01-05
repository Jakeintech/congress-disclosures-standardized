# State Machine Execution Modes

This document describes the execution modes for the Congress Disclosures state machines and how to use them.

## Overview

The state machines support two primary execution modes:

1. **Manual Execution** (default): Process a single year of data
2. **Initial Load**: Process multiple years sequentially for first-time deployment

## Execution Mode: Manual (Default)

Used for regular pipeline runs and single-year processing.

### Input Schema

```json
{
  "execution_type": "manual",
  "year": 2025
}
```

### Parameters

- `execution_type` (string): Set to `"manual"` for single-year execution
- `year` (integer): The year to process (e.g., 2025, 2024)

### Behavior

- Processes a single year through all pipeline stages (Bronze → Silver → Gold)
- Follows the standard execution path: CheckForNewFilings → IngestZip → IndexToSilver → etc.
- Default path when no `execution_type` is specified

## Execution Mode: Initial Load

Used for fresh deployments to populate the system with multiple years of historical data.

### Input Schema

```json
{
  "execution_type": "initial_load",
  "years": [2020, 2021, 2022, 2023, 2024, 2025]
}
```

### Parameters

- `execution_type` (string): Set to `"initial_load"` for multi-year processing
- `years` (array of integers): List of years to process in order

### Behavior

1. **Sequential Processing**: Years are processed one at a time (MaxConcurrency=1)
   - Each year completes Bronze → Silver → Gold before the next year starts
   - Prevents resource contention and ensures data consistency

2. **Continue on Error**: If one year fails, the pipeline continues with subsequent years
   - Failed years are logged with CloudWatch metrics
   - Error details are captured but do not block other years

3. **Progress Logging**: Each year completion is logged to CloudWatch
   - Success: `YearProcessingComplete` metric
   - Failure: `YearProcessingFailed` metric with error details

4. **Summary Notification**: After all years complete, an SNS notification is sent
   - Includes results for all years (successes and failures)
   - Sent to the pipeline alerts topic

### Year Validation

The system validates that years are within a reasonable range:
- Recommended: 5-year lookback window (e.g., 2020-2025)
- Older years may have incomplete or different data formats

## Example Executions

### Example 1: Process 2025 Only (Manual)

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:congress-disclosures-house-fd-pipeline \
  --input '{"execution_type": "manual", "year": 2025}'
```

### Example 2: Initial Load with 6 Years

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:congress-disclosures-house-fd-pipeline \
  --input '{
    "execution_type": "initial_load",
    "years": [2020, 2021, 2022, 2023, 2024, 2025]
  }'
```

### Example 3: Test Initial Load with 2 Years

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:congress-disclosures-house-fd-pipeline \
  --input '{
    "execution_type": "initial_load",
    "years": [2024, 2025]
  }'
```

## State Machine Flow

### Manual Execution Flow

```
CheckExecutionType (Choice)
  └─> CheckForNewFilings
      └─> IngestZip
          └─> IndexToSilver
              └─> ExtractDocumentsMap
                  └─> ... (continue through pipeline)
```

### Initial Load Flow

```
CheckExecutionType (Choice)
  └─> MultiYearIterator (Map, MaxConcurrency=1)
      └─> For each year in $.years:
          ├─> StartChildExecution (sync)
          │   ├─> Success: LogYearSuccess → YearCompleted
          │   └─> Failure: LogYearFailure → YearCompleted
          └─> Next year...
      └─> SummarizeInitialLoad (SNS notification)
          └─> InitialLoadComplete (Succeed)
```

## CloudWatch Metrics

The initial load execution publishes the following metrics:

### YearProcessingComplete

- **Namespace**: `CongressDisclosures/Pipeline`
- **Dimensions**:
  - `pipeline`: `house_fd` or `congress_data_platform`
  - `execution_type`: `initial_load`
  - `year`: The year that completed successfully
  - `status`: `success`

### YearProcessingFailed

- **Namespace**: `CongressDisclosures/Pipeline`
- **Dimensions**:
  - `pipeline`: `house_fd` or `congress_data_platform`
  - `execution_type`: `initial_load`
  - `year`: The year that failed
  - `status`: `failed`
- **Additional Data**: Error details in metric data

## Monitoring Initial Load

### CloudWatch Logs

Monitor the Step Functions execution logs:

```bash
aws logs tail /aws/vendedlogs/states/congress-disclosures-pipelines --follow
```

### Execution Status

Check execution status:

```bash
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>
```

### SNS Notifications

Subscribe to the pipeline alerts topic to receive summary notifications:

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:congress-disclosures-pipeline-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## Performance Considerations

### Expected Duration (per year)

- **Bronze Ingestion**: 5-15 minutes
- **Silver Processing**: 30-60 minutes (depends on PDF count)
- **Gold Transformation**: 10-20 minutes
- **Total per year**: ~1-2 hours

### Total Initial Load Time (6 years)

- Sequential processing: 6-12 hours total
- Can be reduced by processing fewer years or using smaller year subsets

### Resource Usage

- **MaxConcurrency=1**: Ensures no parallel execution bottlenecks
- **Lambda concurrency**: Managed per Lambda function
- **S3 operations**: Optimized with batch uploads

## Troubleshooting

### Common Issues

1. **Year processing times out**
   - Check Lambda timeout settings (max 900s)
   - Review CloudWatch logs for bottlenecks
   - Consider breaking into smaller batches

2. **One year fails but others succeed**
   - This is expected behavior (continue on error)
   - Review error logs for the failed year
   - Can re-run that specific year in manual mode

3. **All years fail**
   - Check IAM permissions
   - Verify S3 bucket access
   - Review Step Functions execution logs

### Re-running Failed Years

If a year fails during initial load, re-run it individually:

```bash
aws stepfunctions start-execution \
  --state-machine-arn <state-machine-arn> \
  --input '{"execution_type": "manual", "year": 2022}'
```

## See Also

- [Architecture Documentation](ARCHITECTURE.md)
- [Deployment Guide](DEPLOYMENT.md)
- [STORY-046: Multi-Year Initial Load Orchestration](agile/stories/active/STORY_046_multi_year_initial_load.md)
