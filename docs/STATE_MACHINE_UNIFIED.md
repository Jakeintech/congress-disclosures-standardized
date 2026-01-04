# Congress Data Platform - Unified State Machine

## Overview

The **Congress Data Platform** is a unified AWS Step Functions state machine that orchestrates the entire data pipeline from Bronze ingestion through Silver transformation to Gold analytics. This state machine replaces the previous siloed pipeline approach with a single, coordinated workflow.

## Purpose

This state machine implements **STORY-029: Bronze Ingestion Phase** by providing parallel ingestion of data from three sources:
1. **House Financial Disclosures** (House Clerk website)
2. **Congress.gov API** (Bills and Members)
3. **Senate Lobbying Disclosures** (LDA database)

## Architecture

### State Flow

```
CheckExecutionType
    ├─ initial_load → MultiYearIterator → [child executions]
    └─ default → CheckForUpdates (Parallel)
                    ├─ CheckHouseFD
                    ├─ CheckCongress
                    └─ CheckLobbying
                 → BronzeIngestion (Parallel)
                    ├─ IngestHouseFD
                    ├─ IngestCongress
                    └─ IngestLobbying
                 → PublishMetrics
                 → PipelineSuccess
```

## Bronze Ingestion Phase

### Parallel Execution

The `BronzeIngestion` state runs **three Lambda functions in parallel**, enabling faster data ingestion by processing all sources simultaneously.

#### Branch 1: House FD Ingestion

**Lambda**: `LAMBDA_HOUSE_FD_INGEST_ZIP`

- **Timeout**: 600 seconds (10 minutes)
- **Function**: Downloads yearly ZIP files from House Clerk website
- **Output**: Raw ZIP files in `s3://bronze/house/financial/`
- **Retry Policy**:
  - 6 attempts
  - 2.0 backoff rate
  - 10-second initial interval

#### Branch 2: Congress.gov Ingestion

**Lambda**: `LAMBDA_FETCH_CONGRESS_BILLS`

- **Timeout**: 900 seconds (15 minutes)
- **Function**: Fetches bills and members from Congress.gov API
- **Output**: JSON files in `s3://bronze/congress/`
- **Retry Policy**:
  - Rate limit handling: 10 attempts, 60-second interval
  - Service errors: 3 attempts, 5-second interval
  - Exponential backoff with 1.5x rate

#### Branch 3: Lobbying Ingestion

**Lambda**: `LAMBDA_DOWNLOAD_LOBBYING_XML`

- **Timeout**: 600 seconds (10 minutes)
- **Function**: Downloads quarterly XML files from Senate LDA
- **Output**: XML files in `s3://bronze/lobbying/`
- **Retry Policy**:
  - 6 attempts
  - 2.0 backoff rate
  - 10-second initial interval

## Error Handling

### Retry Strategies

Each ingestion branch implements exponential backoff retry:

```json
"Retry": [
  {
    "ErrorEquals": [
      "Lambda.ServiceException",
      "Lambda.TooManyRequestsException",
      "Lambda.AWSLambdaException"
    ],
    "IntervalSeconds": 10,
    "MaxAttempts": 6,
    "BackoffRate": 2.0
  }
]
```

### Failure Handling

Each branch has dedicated error states:

1. **Timeout Errors**: SNS notification → Fail state
2. **Lambda Errors**: SNS notification → Fail state
3. **All Errors**: Caught and routed to notification handler

### Notifications

All failures trigger SNS alerts to `${SNS_PIPELINE_ALERTS_ARN}` with:
- Execution ID
- Error details
- Source (House FD, Congress, or Lobbying)

## Input Schema

### Manual Execution (Single Year)

```json
{
  "execution_type": "manual",
  "year": 2024
}
```

### Initial Load (Multiple Years)

```json
{
  "execution_type": "initial_load",
  "years": [2020, 2021, 2022, 2023, 2024]
}
```

### Scheduled Execution (Current Year)

```json
{
  "execution_type": "scheduled",
  "year": 2025
}
```

## Output Schema

After successful Bronze ingestion:

```json
{
  "bronze_results": [
    {
      "bronze": {
        "house_fd": {
          "zip_s3_key": "bronze/house/financial/2024FD.zip",
          "index_s3_key": "bronze/house/financial/2024FD.xml",
          "files_count": 1234,
          "status": "success"
        }
      }
    },
    {
      "bronze": {
        "congress": {
          "bills_fetched": 567,
          "members_fetched": 535,
          "manifest_s3_key": "bronze/congress/manifest_2024.json",
          "status": "success"
        }
      }
    },
    {
      "bronze": {
        "lobbying": {
          "files_downloaded": 89,
          "manifest_s3_key": "bronze/lobbying/manifest_2024.json",
          "status": "success"
        }
      }
    }
  ],
  "metrics_result": {
    "statusCode": 200,
    "body": "{\"message\": \"Metrics published\"}"
  }
}
```

## Metrics

The state machine publishes the following CloudWatch metrics via the `PublishMetrics` Lambda:

- **Metric Namespace**: `CongressDisclosures/Pipeline`
- **Metrics**:
  - `BronzeIngestionDuration` (Milliseconds)
  - `HouseFDIngestionDuration` (Milliseconds)
  - `CongressIngestionDuration` (Milliseconds)
  - `LobbyingIngestionDuration` (Milliseconds)
  - `BronzeIngestionSuccess` (Count)
  - `BronzeIngestionFailures` (Count)

## Deployment

### Terraform Resource

```hcl
resource "aws_sfn_state_machine" "congress_data_platform" {
  name     = "${var.project_name}-data-platform"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile(
    "${path.module}/../../state_machines/congress_data_platform.json",
    local.state_machine_vars
  )

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }
}
```

### Deploy

```bash
cd infra/terraform
terraform plan -target=aws_sfn_state_machine.congress_data_platform
terraform apply -target=aws_sfn_state_machine.congress_data_platform
```

## Testing

### Unit Tests

Run state machine definition tests:

```bash
pytest tests/unit/test_state_machine_definition.py -v
```

Tests verify:
- ✅ Valid JSON structure
- ✅ BronzeIngestion Parallel state exists
- ✅ Three branches (House FD, Congress, Lobbying)
- ✅ Error handling (Retry, Catch) configured
- ✅ Timeouts properly set
- ✅ Global state machine timeout (7200s)

### Integration Tests

Execute state machine with test data:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:congress-disclosures-data-platform \
  --name "test-$(date +%s)" \
  --input '{"execution_type": "manual", "year": 2020}'
```

Monitor execution:

```bash
aws stepfunctions describe-execution \
  --execution-arn arn:aws:states:us-east-1:ACCOUNT:execution:congress-disclosures-data-platform:test-1234567890
```

## Monitoring

### CloudWatch Logs

View execution logs:

```bash
aws logs tail /aws/vendedlogs/states/congress-disclosures-pipelines --follow
```

### X-Ray Tracing

View service map and trace details in the AWS X-Ray console to identify:
- Execution bottlenecks
- Lambda duration by source
- Error rates per branch

## Cost Estimation

### Step Functions

**Per execution**:
- CheckExecutionType: 1 transition
- CheckForUpdates: 6 transitions (3 parallel + 3 merges)
- BronzeIngestion: 6 transitions (3 parallel + 3 merges)
- PublishMetrics: 1 transition
- **Total**: ~14 transitions per execution

**Monthly cost** (30 executions):
- 30 × 14 = 420 transitions
- Free tier: 4,000 transitions/month
- **Cost**: $0 (within free tier)

### Lambda Invocations

**Per execution**:
- 3 check Lambdas (60s each)
- 3 ingestion Lambdas (600-900s each)
- 1 metrics Lambda (30s)

**Monthly compute**:
- ~7 Lambda invocations × 30 executions = 210 invocations
- Avg duration: 300s
- **Cost**: ~$5-10/month (varies by data volume)

## Future Enhancements

The Bronze Ingestion phase is the foundation for the full unified pipeline. Future sprints will add:

1. **Silver Transformation** (STORY-030)
   - Parse Bronze data into normalized Parquet tables
   - Extract text from PDFs
   - Validate data quality with Soda checks

2. **Gold Layer** (STORY-031)
   - Build dimensional model (Members, Assets, Bills)
   - Create fact tables (Transactions, Filings, Lobbying)
   - Generate pre-computed aggregates

3. **Analytics & API** (STORY-032)
   - Update API response cache
   - Trigger cross-dataset correlations
   - Publish final metrics

## References

- **Story**: `docs/agile/stories/active/STORY_029_bronze_ingestion_phase.md`
- **Spec**: `docs/agile/technical/STATE_MACHINE_SPEC.md`
- **Definition**: `state_machines/congress_data_platform.json`
- **Terraform**: `infra/terraform/step_functions.tf`

## Change Log

| Date       | Version | Author    | Description                          |
|------------|---------|-----------|--------------------------------------|
| 2026-01-04 | 1.0.0   | Copilot   | Initial implementation of Bronze phase |
