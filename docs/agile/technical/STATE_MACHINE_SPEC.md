# Step Functions State Machine Specification

**Project**: Congress Disclosures Standardized Data Platform
**Last Updated**: 2025-12-14
**State Machine**: `congress-data-platform` (Unified Pipeline)

---

## Overview

This document specifies the **single unified Step Functions state machine** that replaces the previous 4 siloed pipelines. The state machine orchestrates Bronze → Silver → Gold data flow with proper error handling, retries, and monitoring.

---

## State Machine Architecture

```mermaid
stateDiagram-v2
    [*] --> CheckForUpdates
    CheckForUpdates --> HasUpdates{Has New Data?}

    HasUpdates --> BronzeIngestion: Yes
    HasUpdates --> [*]: No

    BronzeIngestion --> ParallelIngest

    state ParallelIngest {
        [*] --> HouseFDIngest
        [*] --> CongressIngest
        [*] --> LobbyingIngest

        HouseFDIngest --> [*]
        CongressIngest --> [*]
        LobbyingIngest --> [*]
    }

    ParallelIngest --> SilverTransformation

    state SilverTransformation {
        [*] --> HouseFDSilver
        [*] --> CongressSilver
        [*] --> LobbyingSilver

        HouseFDSilver --> WaitForExtraction
        CongressSilver --> [*]
        LobbyingSilver --> [*]
        WaitForExtraction --> [*]
    }

    SilverTransformation --> GoldLayer

    state GoldLayer {
        [*] --> BuildDimensions
        BuildDimensions --> BuildFacts
        BuildFacts --> BuildAggregates
        BuildAggregates --> [*]
    }

    GoldLayer --> QualityChecks
    QualityChecks --> Passed{Quality OK?}

    Passed --> UpdateAPI: Yes
    Passed --> SendAlert: No

    UpdateAPI --> PublishMetrics
    SendAlert --> PublishMetrics
    PublishMetrics --> [*]
```

---

## State Machine Definition

### File Location
**New**: `state_machines/congress_data_platform.json`

**Replaces**:
- ❌ `house_fd_pipeline.json`
- ❌ `congress_pipeline.json`
- ❌ `lobbying_pipeline.json`
- ❌ `cross_dataset_correlation.json`

### Terraform Integration
```hcl
resource "aws_sfn_state_machine" "congress_data_platform" {
  name     = "${local.name_prefix}-data-platform"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../../state_machines/congress_data_platform.json", {
    # Lambda ARNs
    LAMBDA_CHECK_HOUSE_FD = aws_lambda_function.check_house_fd_updates.arn
    LAMBDA_INGEST_ZIP = aws_lambda_function.house_fd_ingest_zip.arn
    # ... (all 47 Lambdas)

    # Resources
    SNS_ALERTS = aws_sns_topic.pipeline_alerts.arn
    SQS_EXTRACTION_QUEUE = aws_sqs_queue.extraction_queue.url
  })

  tracing_configuration {
    enabled = true
  }

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
}
```

---

## Input Schema

### Manual Execution
```json
{
  "execution_type": "manual",
  "mode": "incremental",
  "sources": {
    "house_fd": true,
    "congress_gov": true,
    "lobbying": true
  },
  "parameters": {
    "year": 2024,
    "force_refresh": false,
    "skip_quality_checks": false
  }
}
```

### Scheduled Execution (EventBridge)
```json
{
  "execution_type": "scheduled",
  "mode": "incremental",
  "sources": {
    "house_fd": true,
    "congress_gov": true,
    "lobbying": true
  }
}
```

### Year-Specific Full Refresh
```json
{
  "execution_type": "manual",
  "mode": "full_refresh",
  "parameters": {
    "year": 2024,
    "rebuild_gold": true
  }
}
```

---

## State Definitions

### Phase 1: Update Detection

#### State: CheckForUpdates (Parallel)
```json
{
  "Type": "Parallel",
  "Branches": [
    {
      "StartAt": "CheckHouseFD",
      "States": {
        "CheckHouseFD": {
          "Type": "Task",
          "Resource": "${LAMBDA_CHECK_HOUSE_FD}",
          "Parameters": {
            "year.$": "$.parameters.year"
          },
          "ResultPath": "$.updates.house_fd",
          "Retry": [
            {
              "ErrorEquals": ["States.TaskFailed"],
              "IntervalSeconds": 2,
              "MaxAttempts": 3,
              "BackoffRate": 2.0
            }
          ],
          "Catch": [
            {
              "ErrorEquals": ["States.ALL"],
              "ResultPath": "$.error",
              "Next": "NotifyCheckFailure"
            }
          ],
          "End": true
        }
      }
    },
    {
      "StartAt": "CheckCongress",
      "States": {
        "CheckCongress": {
          "Type": "Task",
          "Resource": "${LAMBDA_CHECK_CONGRESS}",
          "ResultPath": "$.updates.congress",
          "End": true
        }
      }
    },
    {
      "StartAt": "CheckLobbying",
      "States": {
        "CheckLobbying": {
          "Type": "Task",
          "Resource": "${LAMBDA_CHECK_LOBBYING}",
          "ResultPath": "$.updates.lobbying",
          "End": true
        }
      }
    }
  ],
  "ResultPath": "$.update_checks",
  "Next": "EvaluateUpdates"
}
```

#### State: EvaluateUpdates (Choice)
```json
{
  "Type": "Choice",
  "Choices": [
    {
      "Variable": "$.update_checks[0].updates.house_fd.has_new_filings",
      "BooleanEquals": true,
      "Next": "BronzeIngestion"
    },
    {
      "Variable": "$.update_checks[1].updates.congress.has_new_data",
      "BooleanEquals": true,
      "Next": "BronzeIngestion"
    },
    {
      "Variable": "$.update_checks[2].updates.lobbying.has_new_filings",
      "BooleanEquals": true,
      "Next": "BronzeIngestion"
    }
  ],
  "Default": "NoUpdatesFound"
}
```

#### State: NoUpdatesFound (Success)
```json
{
  "Type": "Succeed",
  "Comment": "No new data found, pipeline complete"
}
```

---

### Phase 2: Bronze Ingestion

#### State: BronzeIngestion (Parallel)
```json
{
  "Type": "Parallel",
  "Branches": [
    {
      "StartAt": "IngestHouseFD",
      "States": {
        "IngestHouseFD": {
          "Type": "Task",
          "Resource": "${LAMBDA_INGEST_ZIP}",
          "Parameters": {
            "year.$": "$.parameters.year",
            "force_download.$": "$.parameters.force_refresh"
          },
          "ResultPath": "$.bronze.house_fd",
          "TimeoutSeconds": 300,
          "Retry": [
            {
              "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
              "IntervalSeconds": 2,
              "MaxAttempts": 3,
              "BackoffRate": 2.0
            }
          ],
          "Catch": [
            {
              "ErrorEquals": ["States.Timeout"],
              "ResultPath": "$.error",
              "Next": "NotifyBronzeTimeout"
            },
            {
              "ErrorEquals": ["States.ALL"],
              "ResultPath": "$.error",
              "Next": "NotifyBronzeFailure"
            }
          ],
          "End": true
        },
        "NotifyBronzeTimeout": {
          "Type": "Task",
          "Resource": "arn:aws:states:::sns:publish",
          "Parameters": {
            "TopicArn": "${SNS_ALERTS}",
            "Subject": "Pipeline Alert: Bronze Ingestion Timeout",
            "Message.$": "$.error"
          },
          "Next": "FailBronze"
        },
        "NotifyBronzeFailure": {
          "Type": "Task",
          "Resource": "arn:aws:states:::sns:publish",
          "Parameters": {
            "TopicArn": "${SNS_ALERTS}",
            "Subject": "Pipeline Alert: Bronze Ingestion Failed",
            "Message.$": "$.error"
          },
          "Next": "FailBronze"
        },
        "FailBronze": {
          "Type": "Fail",
          "Error": "BronzeIngestionFailed",
          "Cause": "Failed to ingest House FD data to Bronze layer"
        }
      }
    }
    // ... Similar branches for CongressIngest, LobbyingIngest
  ],
  "ResultPath": "$.bronze_results",
  "Next": "SilverTransformation"
}
```

---

### Phase 3: Silver Transformation

#### State: SilverTransformation (Parallel)
```json
{
  "Type": "Parallel",
  "Branches": [
    {
      "StartAt": "IndexToSilver",
      "States": {
        "IndexToSilver": {
          "Type": "Task",
          "Resource": "${LAMBDA_INDEX_TO_SILVER}",
          "Parameters": {
            "index_s3_key.$": "$.bronze_results[0].bronze.house_fd.index_s3_key",
            "year.$": "$.parameters.year"
          },
          "ResultPath": "$.silver.index_result",
          "TimeoutSeconds": 180,
          "Next": "ExtractDocumentsMap"
        },
        "ExtractDocumentsMap": {
          "Type": "Map",
          "ItemsPath": "$.silver.index_result.documents_to_extract",
          "MaxConcurrency": 10,
          "Parameters": {
            "doc_id.$": "$$.Map.Item.Value.doc_id",
            "pdf_s3_key.$": "$$.Map.Item.Value.pdf_s3_key"
          },
          "Iterator": {
            "StartAt": "QueueExtraction",
            "States": {
              "QueueExtraction": {
                "Type": "Task",
                "Resource": "arn:aws:states:::sqs:sendMessage",
                "Parameters": {
                  "QueueUrl": "${SQS_EXTRACTION_QUEUE}",
                  "MessageBody.$": "$"
                },
                "End": true
              }
            }
          },
          "ResultPath": "$.silver.queued_extractions",
          "Next": "WaitForExtractionComplete"
        },
        "WaitForExtractionComplete": {
          "Type": "Task",
          "Resource": "arn:aws:states:::sqs:getQueueAttributes",
          "Parameters": {
            "QueueUrl": "${SQS_EXTRACTION_QUEUE}",
            "AttributeNames": ["ApproximateNumberOfMessages"]
          },
          "ResultPath": "$.silver.queue_status",
          "Next": "CheckQueueEmpty"
        },
        "CheckQueueEmpty": {
          "Type": "Choice",
          "Choices": [
            {
              "Variable": "$.silver.queue_status.Attributes.ApproximateNumberOfMessages",
              "NumericEquals": 0,
              "Next": "ExtractionComplete"
            }
          ],
          "Default": "WaitThenCheckAgain"
        },
        "WaitThenCheckAgain": {
          "Type": "Wait",
          "Seconds": 60,
          "Next": "WaitForExtractionComplete"
        },
        "ExtractionComplete": {
          "Type": "Pass",
          "End": true
        }
      }
    }
    // ... Similar branches for CongressSilver, LobbyingSilver
  ],
  "ResultPath": "$.silver_results",
  "Next": "GoldDimensions"
}
```

**Key Improvements**:
1. ✅ **MaxConcurrency: 10** (was 1) - 10x faster extraction
2. ✅ **SQS queue polling** - Wait until queue empty (not fixed 10s)
3. ✅ **Exponential backoff** - Retry with backoff on failures

---

### Phase 4: Gold Layer

#### State: GoldDimensions (Parallel)
```json
{
  "Type": "Parallel",
  "Branches": [
    {
      "StartAt": "BuildDimMembers",
      "States": {
        "BuildDimMembers": {
          "Type": "Task",
          "Resource": "${LAMBDA_BUILD_DIM_MEMBERS}",
          "Parameters": {
            "rebuild.$": "$.parameters.rebuild_gold",
            "incremental_date.$": "$.execution_start_time"
          },
          "ResultPath": "$.gold.dim_members",
          "TimeoutSeconds": 600,
          "End": true
        }
      }
    },
    {
      "StartAt": "BuildDimAssets",
      "States": {
        "BuildDimAssets": {
          "Type": "Task",
          "Resource": "${LAMBDA_BUILD_DIM_ASSETS}",
          "ResultPath": "$.gold.dim_assets",
          "End": true
        }
      }
    }
    // ... BuildDimBills, BuildDimLobbyists, BuildDimDates
  ],
  "ResultPath": "$.gold.dimensions",
  "Next": "GoldFacts"
}
```

#### State: GoldFacts (Sequential - Dependencies)
```json
{
  "Type": "Task",
  "Resource": "${LAMBDA_BUILD_FACT_TRANSACTIONS}",
  "Parameters": {
    "dim_members_key.$": "$.gold.dimensions[0].dim_members.output_s3_key",
    "dim_assets_key.$": "$.gold.dimensions[1].dim_assets.output_s3_key"
  },
  "ResultPath": "$.gold.fact_transactions",
  "Next": "BuildFactFilings"
}
```

**Note**: Facts are sequential because they depend on dimensions

#### State: GoldAggregates (Parallel)
```json
{
  "Type": "Parallel",
  "Branches": [
    {
      "StartAt": "ComputeTrendingStocks",
      "States": {
        "ComputeTrendingStocks": {
          "Type": "Task",
          "Resource": "${LAMBDA_COMPUTE_TRENDING_STOCKS}",
          "End": true
        }
      }
    }
    // ... All other aggregate functions
  ],
  "ResultPath": "$.gold.aggregates",
  "Next": "RunSodaChecks"
}
```

---

### Phase 5: Quality Checks

#### State: RunSodaChecks
```json
{
  "Type": "Task",
  "Resource": "${LAMBDA_RUN_SODA_CHECKS}",
  "Parameters": {
    "layer": "gold",
    "checks_to_run": ["all"]
  },
  "ResultPath": "$.quality.soda_results",
  "Catch": [
    {
      "ErrorEquals": ["QualityCheckFailed"],
      "ResultPath": "$.error",
      "Next": "NotifyQualityFailure"
    }
  ],
  "Next": "EvaluateQuality"
}
```

#### State: EvaluateQuality (Choice)
```json
{
  "Type": "Choice",
  "Choices": [
    {
      "Variable": "$.quality.soda_results.status",
      "StringEquals": "passed",
      "Next": "UpdateAPICache"
    },
    {
      "Variable": "$.quality.soda_results.status",
      "StringEquals": "warned",
      "Next": "NotifyQualityWarning"
    }
  ],
  "Default": "NotifyQualityFailure"
}
```

**Behavior**:
- `passed` → Continue to API update
- `warned` → Send SNS alert, continue
- `failed` → Send SNS alert, FAIL state machine

---

### Phase 6: Publish

#### State: UpdateAPICache
```json
{
  "Type": "Task",
  "Resource": "${LAMBDA_UPDATE_API_CACHE}",
  "Parameters": {
    "api_id": "${API_GATEWAY_ID}",
    "stage": "prod"
  },
  "ResultPath": "$.publish.api_cache",
  "Next": "PublishMetrics"
}
```

#### State: PublishMetrics
```json
{
  "Type": "Task",
  "Resource": "${LAMBDA_PUBLISH_METRICS}",
  "Parameters": {
    "execution_id.$": "$$.Execution.Id",
    "execution_start_time.$": "$$.Execution.StartTime",
    "bronze_results.$": "$.bronze_results",
    "silver_results.$": "$.silver_results",
    "gold_results.$": "$.gold",
    "quality_results.$": "$.quality"
  },
  "ResultPath": "$.metrics",
  "Next": "PipelineSuccess"
}
```

#### State: PipelineSuccess (Succeed)
```json
{
  "Type": "Succeed",
  "Comment": "Pipeline completed successfully"
}
```

---

## Error Handling Strategy

### Error Categories

#### Transient Errors (Retry)
```json
"Retry": [
  {
    "ErrorEquals": [
      "Lambda.ServiceException",
      "Lambda.TooManyRequestsException",
      "States.TaskFailed"
    ],
    "IntervalSeconds": 2,
    "MaxAttempts": 3,
    "BackoffRate": 2.0
  }
]
```

#### Timeout Errors (Alert + Retry)
```json
"Catch": [
  {
    "ErrorEquals": ["States.Timeout"],
    "ResultPath": "$.error",
    "Next": "NotifyTimeout"
  }
]
```

#### Critical Errors (Alert + Fail)
```json
"Catch": [
  {
    "ErrorEquals": ["States.ALL"],
    "ResultPath": "$.error",
    "Next": "NotifyFailure"
  }
]
```

### SNS Notification Pattern
```json
{
  "Type": "Task",
  "Resource": "arn:aws:states:::sns:publish",
  "Parameters": {
    "TopicArn": "${SNS_ALERTS}",
    "Subject": "Pipeline Alert: [Phase] Failed",
    "Message": {
      "execution_id.$": "$$.Execution.Id",
      "error.$": "$.error",
      "context.$": "$$"
    }
  },
  "Next": "FailState"
}
```

---

## Execution Timeouts

| Phase | Timeout | Justification |
|-------|---------|---------------|
| Update Detection | 300s | 3 parallel checks @ 60s each |
| Bronze Ingestion | 900s | Large zip download (100MB) |
| Silver Transformation | 3600s | Queue-based extraction (1-4 hours) |
| Gold Dimensions | 1800s | Pandas operations on large datasets |
| Gold Facts | 2700s | Join operations |
| Gold Aggregates | 1800s | Parallel aggregation |
| Quality Checks | 300s | Soda checks |
| Publish | 180s | Cache invalidation |
| **Total Pipeline** | **7200s (2 hours)** | Max execution time |

---

## Cost Estimation

### Step Functions Costs

**State Transitions** (per execution):
- Update Detection: 6 transitions
- Bronze Ingestion: 9 transitions
- Silver Transformation: 12 transitions
- Gold Layer: 25 transitions
- Quality & Publish: 8 transitions
- **Total**: ~60 transitions per execution

**Monthly Cost** (30 daily executions):
- 30 executions × 60 transitions = 1,800 transitions/month
- Free tier: 4,000 transitions/month
- **Cost**: $0 (within free tier)

### CloudWatch Logs

**Log Volume**:
- Per execution: ~5MB of logs (ALL level)
- Monthly: 30 × 5MB = 150MB
- Free tier: 5GB/month
- **Cost**: $0 (within free tier)

### X-Ray Tracing

**Traces**:
- Per execution: ~60 trace segments
- Monthly: 30 × 60 = 1,800 segments
- Free tier: 100,000 traces/month
- **Cost**: $0 (within free tier)

**Total State Machine Cost**: **$0/month** (all within free tier)

---

## Monitoring & Observability

### CloudWatch Metrics (Custom)

**Published by state machine**:
- `PipelineExecutions` (Count)
- `PipelineSuccessRate` (Percentage)
- `PipelineDuration` (Milliseconds)
- `BronzeIngestionDuration` (Milliseconds)
- `SilverTransformationDuration` (Milliseconds)
- `GoldLayerDuration` (Milliseconds)
- `QualityCheckFailures` (Count)

### CloudWatch Alarms

```hcl
resource "aws_cloudwatch_metric_alarm" "pipeline_failure" {
  alarm_name          = "congress-data-platform-failure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert when pipeline execution fails"
  alarm_actions       = [aws_sns_topic.pipeline_alerts.arn]

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.congress_data_platform.arn
  }
}
```

### X-Ray Service Map

Visualize:
- Lambda invocation chains
- Service dependencies
- Bottlenecks (slow steps)
- Error rates per service

---

## Testing Strategy

### Unit Tests (State Machine Definition)

**Test**: Valid JSON syntax
```bash
python -m json.tool state_machines/congress_data_platform.json
```

**Test**: Terraform template rendering
```bash
terraform plan -target=aws_sfn_state_machine.congress_data_platform
```

### Integration Tests

**Test**: Execute with test data
```python
import boto3

sfn = boto3.client('stepfunctions')

response = sfn.start_execution(
    stateMachineArn='arn:aws:states:...',
    input=json.dumps({
        'execution_type': 'test',
        'mode': 'incremental',
        'parameters': {'year': 2020}  # Small dataset
    })
)

# Wait for completion
execution_arn = response['executionArn']
while True:
    status = sfn.describe_execution(executionArn=execution_arn)
    if status['status'] in ['SUCCEEDED', 'FAILED', 'TIMED_OUT']:
        break
    time.sleep(10)

assert status['status'] == 'SUCCEEDED'
```

### End-to-End Tests

**Test**: Full pipeline execution
1. Trigger state machine manually
2. Monitor CloudWatch logs
3. Verify Bronze data in S3
4. Verify Silver data in S3
5. Verify Gold data in S3
6. Verify API returns updated data

---

## Deployment Process

### Step 1: Terraform Apply
```bash
cd infra/terraform
terraform plan -target=aws_sfn_state_machine.congress_data_platform
terraform apply -target=aws_sfn_state_machine.congress_data_platform
```

### Step 2: Verify Deployment
```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:... \
  --query 'status'
```

### Step 3: Test Execution
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:... \
  --input file://test_input.json
```

### Step 4: Monitor
```bash
aws stepfunctions describe-execution \
  --execution-arn arn:aws:states:...:execution/...
```

---

## Rollback Plan

### If State Machine Deployment Fails

```bash
# Revert to previous version
cd infra/terraform
git checkout HEAD~1 -- step_functions.tf
terraform apply

# Verify old state machine works
aws stepfunctions start-execution --state-machine-arn ...
```

### If Execution Fails Repeatedly

1. **Immediate**: Disable EventBridge trigger
2. **Short-term**: Manual executions only
3. **Fix**: Debug failed step, deploy fix
4. **Re-enable**: EventBridge trigger

---

**Document Owner**: Engineering Team
**Status**: Design Complete - Ready for Implementation
**Next Steps**: Create state machine JSON file, test Terraform deployment
