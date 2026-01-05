# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a serverless data pipeline for ingesting, extracting, and standardizing US Congress financial disclosures. The pipeline processes 15+ years of PDF filings from the House Clerk website, extracting structured transaction data, assets, and compliance information into a queryable data lake.

**Core Technology**: AWS Lambda, S3, SQS, Terraform, Python 3.11

## Architecture: Bronze → Silver → Gold

The pipeline follows a **medallion architecture** with three data layers:

### Bronze Layer (Raw/Immutable)
- **Location**: `s3://congress-disclosures-standardized/bronze/house/financial/`
- **Contents**: Byte-for-byte preservation of source data
  - `year=YYYY/raw_zip/YYYYFD.zip` - Original zip from House Clerk
  - `year=YYYY/index/YYYYFD.xml` - Filing metadata index
  - `year=YYYY/filing_type={P,A,T,...}/pdfs/{doc_id}.pdf` - Individual PDFs
- **Important**: S3 object metadata tracks extraction state to prevent duplicate processing

### Silver Layer (Normalized/Queryable)
- **Location**: `s3://congress-disclosures-standardized/silver/house/financial/`
- **Format**: Parquet tables + gzipped text
- **Tables**:
  - `filings/` - Filing metadata from XML index
  - `documents/` - PDF metadata + extraction status
  - `text/extraction_method={direct_text,ocr}/` - Extracted text (gzipped)
  - `objects/filing_type=type_{p,a,t}/` - Structured extraction JSON

### Gold Layer (Query-Facing/Aggregated)
- **Location**: `s3://congress-disclosures-standardized/gold/house/financial/`
- **Structure**:
  - `dimensions/` - Member, asset, date dimensions (SCD Type 2)
  - `facts/` - Transactions, filings (star schema, partitioned by year/month)
  - `aggregates/` - Pre-computed metrics (trending stocks, member stats, document quality)

## Data Flow

```
Manual/Cron Trigger
    ↓
house_fd_ingest_zip (downloads YEARFD.zip, uploads to Bronze, queues PDFs to SQS)
    ↓
house_fd_index_to_silver (parses XML, writes Silver tables, queues extraction jobs)
    ↓
SQS Queue (5K-15K messages) → house_fd_extract_document (parallel, 10 concurrent)
    ↓ (extracts text via pypdf → OCR fallback)
house_fd_extract_structured_code (code-based extraction by filing type)
    ↓ (outputs structured JSON to Silver)
Gold Scripts (aggregate_data, compute metrics, build fact tables)
```

## Step Functions Architecture

### Overview

The pipeline uses **AWS Step Functions** to orchestrate complex data workflows with parallel processing, error handling, quality gates, and automatic retries. Step Functions replaces script-based orchestration with a visual, serverless workflow engine that provides better observability, error handling, and cost optimization.

### Deployed State Machines

The infrastructure deploys the following state machines (see `infra/terraform/step_functions.tf`):

| State Machine | Purpose | ARN Pattern | Status |
|---------------|---------|-------------|--------|
| **house_fd_pipeline** | House Financial Disclosures (Bronze→Silver→Gold) | `arn:aws:states:us-east-1:{ACCOUNT}:stateMachine:congress-disclosures-house-fd-pipeline` | ✅ Active |
| **congress_pipeline** | Congress.gov API data ingestion | `arn:aws:states:us-east-1:{ACCOUNT}:stateMachine:congress-disclosures-congress-pipeline` | ✅ Active |
| **lobbying_pipeline** | Senate LDA lobbying disclosures | `arn:aws:states:us-east-1:{ACCOUNT}:stateMachine:congress-disclosures-lobbying-pipeline` | ✅ Active |
| **cross_dataset_correlation** | Cross-dataset analytics | `arn:aws:states:us-east-1:{ACCOUNT}:stateMachine:congress-disclosures-cross-dataset-correlation` | ✅ Active |
| **congress_data_platform** | Unified pipeline (future) | `arn:aws:states:us-east-1:{ACCOUNT}:stateMachine:congress-disclosures-data-platform` | 🚧 In Development |

**Key Features**:
- **Parallel Processing**: Map states with `MaxConcurrency: 1000` for PDF extraction (S3 distributed map)
- **Error Handling**: Exponential backoff retries, catch blocks, SNS alerts
- **Quality Gates**: Soda quality checks between Bronze→Silver→Gold layers
- **Watermarking**: Prevents duplicate processing via SHA256 hashing + DynamoDB
- **X-Ray Tracing**: Distributed tracing enabled for all state machines
- **CloudWatch Logs**: Full execution logging with queryable logs

### Watermarking Patterns (STORY-003, 004, 005)

**Purpose**: Prevent duplicate processing and enable incremental updates

#### House FD Watermarking (SHA256-based)
```python
# Lambda: check_house_fd_updates
# Strategy: SHA256 hash comparison of ZIP files

def lambda_handler(event, context):
    year = event.get('year', datetime.now().year)
    
    # Get watermark from DynamoDB
    watermark = get_watermark(year)
    
    # Compute SHA256 of remote ZIP
    current_sha256 = compute_sha256_from_url(zip_url)
    
    # Compare with stored watermark
    if watermark and watermark['sha256'] == current_sha256:
        return {"has_new_filings": False, "status": "unchanged"}
    
    # Update watermark
    update_watermark(year, current_sha256, last_modified, content_length)
    return {"has_new_filings": True, "status": "updated"}
```

**DynamoDB Table**: `congress-disclosures-pipeline-watermarks`
- Partition Key: `table_name` (e.g., "house_fd")
- Sort Key: `watermark_type` (e.g., "2025")
- Attributes: `sha256`, `last_modified`, `content_length`, `updated_at`

#### Congress Watermarking (Timestamp-based)
```python
# Lambda: check_congress_updates
# Strategy: DynamoDB timestamp tracking with fromDateTime API parameter

def lambda_handler(event, context):
    data_type = event.get('data_type', 'bills')
    
    # Get last update timestamp
    watermark = get_watermark(data_type)
    from_date = watermark.get('last_update_date') or f"{current_year - 5}-01-01T00:00:00Z"
    
    # Query Congress.gov API with fromDateTime
    response = check_congress_api('bill', {'fromDateTime': from_date})
    
    if response['pagination']['count'] > 0:
        update_watermark(data_type, datetime.utcnow().isoformat(), count)
        return {"has_new_data": True}
    return {"has_new_data": False}
```

#### Lobbying Watermarking (S3 Existence Check)
```python
# Lambda: check_lobbying_updates
# Strategy: Check if Bronze data already exists for year/quarter

def check_bronze_exists(year: int, quarter: str) -> bool:
    prefix = f"bronze/lobbying/year={year}/quarter={quarter}/"
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
    return response.get('KeyCount', 0) > 0

def lambda_handler(event, context):
    quarters_to_process = []
    for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
        if not check_bronze_exists(year, quarter):
            quarters_to_process.append(quarter)
    
    return {"has_new_filings": len(quarters_to_process) > 0}
```

### Parallel Processing with Map States

**House FD Pipeline** - Extract Documents Map:
```json
{
  "ExtractDocumentsMap": {
    "Type": "Map",
    "ItemsPath": "$.documents",
    "MaxConcurrency": 10,
    "Iterator": {
      "StartAt": "ExtractDocument",
      "States": {
        "ExtractDocument": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:...:function:extract_document",
          "End": true
        }
      }
    }
  }
}
```

**Impact**: Reduced execution time from 41 hours → 4 hours (10x speedup)

### Error Handling & Retry Logic

**Retry Strategy**:
```json
{
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
      "Next": "NotifyFailure"
    }
  ]
}
```

**SNS Alerting**:
- Pipeline failures → `pipeline_alerts` topic
- Quality check failures → `data_quality_alerts` topic
- DLQ depth > 0 → CloudWatch alarm → SNS

### Manual Execution

You can manually trigger state machines using the AWS CLI or AWS Console.

#### Using AWS CLI

**1. Get State Machine ARN**:
```bash
# List all state machines
aws stepfunctions list-state-machines \
  --query "stateMachines[?contains(name, 'congress-disclosures')].{Name:name,ARN:stateMachineArn}" \
  --output table

# Or get specific ARN from Terraform outputs
cd infra/terraform && terraform output house_fd_pipeline_arn
```

**2. Start Execution - House FD Pipeline**:
```bash
# Simple execution (current year)
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:congress-disclosures-house-fd-pipeline \
  --name "manual-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"manual","year":2025}'

# With force refresh (reprocess all data)
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:congress-disclosures-house-fd-pipeline \
  --name "manual-force-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"manual","year":2025,"force_refresh":true}'

# Multi-year initial load (STORY-046)
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:congress-disclosures-house-fd-pipeline \
  --name "initial-load-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"initial_load","years":[2020,2021,2022,2023,2024,2025]}'
```

**3. Start Execution - Congress.gov Pipeline**:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:congress-disclosures-congress-pipeline \
  --name "manual-congress-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"manual","year":2025}'
```

**4. Start Execution - Lobbying Pipeline**:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:congress-disclosures-lobbying-pipeline \
  --name "manual-lobbying-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"manual","year":2025,"quarters":["Q1","Q2","Q3","Q4"]}'
```

**5. Check Execution Status**:
```bash
# Get execution ARN from start-execution output, then:
aws stepfunctions describe-execution \
  --execution-arn arn:aws:states:us-east-1:ACCOUNT_ID:execution:congress-disclosures-house-fd-pipeline:manual-20250105-120000

# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:congress-disclosures-house-fd-pipeline \
  --max-items 10
```

**6. Stop Execution (if needed)**:
```bash
aws stepfunctions stop-execution \
  --execution-arn arn:aws:states:us-east-1:ACCOUNT_ID:execution:congress-disclosures-house-fd-pipeline:manual-20250105-120000 \
  --cause "Manual cancellation" \
  --error "UserCancelled"
```

#### Using AWS Console

1. Navigate to **AWS Console → Step Functions**
2. Select state machine (e.g., `congress-disclosures-house-fd-pipeline`)
3. Click **Start execution**
4. Enter input JSON:
   ```json
   {
     "execution_type": "manual",
     "year": 2025
   }
   ```
5. Click **Start execution** and monitor in real-time

### EventBridge Scheduling

Automatic pipeline execution is controlled by **EventBridge rules** (see `infra/terraform/eventbridge.tf`).

**Current Status**: ⚠️ **ALL SCHEDULES DISABLED** (STORY-001)
- Disabled to prevent $4,000/month cost explosion from hourly executions
- Enable only after watermarking is fully implemented and tested

#### Configured Schedules

| Pipeline | Schedule Expression | Time (EST) | Status | Rule Name |
|----------|---------------------|------------|--------|-----------|
| **House FD** | `cron(0 9 * * ? *)` | Daily at 4 AM | ⛔ DISABLED | `congress-disclosures-house-fd-daily` |
| **Congress.gov** | `cron(0 8 * * ? *)` | Daily at 3 AM | ⛔ DISABLED | `congress-disclosures-congress-daily` |
| **Lobbying** | `cron(0 11 ? * MON *)` | Weekly Mon 6 AM | ⛔ DISABLED | `congress-disclosures-lobbying-weekly` |

#### Enable/Disable Schedules

**Enable a schedule**:
```bash
# Enable House FD daily schedule
aws events enable-rule --name congress-disclosures-house-fd-daily

# Or via Terraform: Edit infra/terraform/eventbridge.tf
# Change: state = "DISABLED"  →  state = "ENABLED"
# Then: terraform apply
```

**Disable a schedule**:
```bash
# Disable House FD daily schedule
aws events disable-rule --name congress-disclosures-house-fd-daily
```

**Check schedule status**:
```bash
# List all pipeline EventBridge rules
aws events list-rules --name-prefix congress-disclosures

# Get specific rule details
aws events describe-rule --name congress-disclosures-house-fd-daily
```

#### Schedule Input Payloads

Scheduled executions receive standardized input:

**House FD Schedule**:
```json
{
  "execution_type": "scheduled",
  "year": 2025,
  "triggered_by": "eventbridge"
}
```

**Congress.gov Schedule**:
```json
{
  "execution_type": "scheduled",
  "year": 2025,
  "triggered_by": "eventbridge"
}
```

**Lobbying Schedule**:
```json
{
  "execution_type": "scheduled",
  "trigger_time": "2025-01-06T11:00:00Z"
}
```

### Execution Patterns

**Incremental Processing** (default):
```json
{
  "execution_type": "manual",
  "year": 2025
}
```
- Watermarking checks for new data
- Skips unchanged files
- Fastest execution (minutes to hours)

**Force Refresh**:
```json
{
  "execution_type": "manual",
  "year": 2025,
  "force_refresh": true
}
```
- Bypasses watermarking
- Reprocesses all data
- Used for data quality fixes or schema changes

**Multi-Year Initial Load** (STORY-046):
```json
{
  "execution_type": "initial_load",
  "years": [2020, 2021, 2022, 2023, 2024, 2025]
}
```
- Processes multiple years in parallel (MaxConcurrency: 2)
- Used for initial deployment or backfilling historical data
- Each year runs as nested execution

### Cost Optimization (STORY-001, 002)

**EventBridge Schedule**:
- ❌ Before: `rate(1 hour)` → $4,000/month
- ✅ After: `cron(0 9 * * ? *)` (daily at 4 AM EST, DISABLED) → $0/month

**MaxConcurrency**:
- ❌ Before: `1` → Sequential processing (41 hours)
- ✅ After: `10` → Parallel processing (4 hours, 90% cost reduction)

**Watermarking Impact**:
- 95% reduction in duplicate Lambda invocations
- $750/month savings in compute costs

### Monitoring & Observability

**CloudWatch Metrics**:
- Pipeline execution duration
- Success/failure rates
- Quality check pass rates
- Watermark hit rates

**X-Ray Tracing**: Distributed tracing enabled for all state machines

**Step Functions Console**: Visual execution history with state-by-state timing

See `docs/STATE_MACHINE_FLOW.md` for detailed diagrams.

### Troubleshooting Step Functions

#### Common Issues

**1. Execution Stuck in "Running" State**
- **Symptom**: Execution shows "Running" for hours, no progress
- **Cause**: Lambda timeout, infinite loop, or waiting for external resource
- **Solution**:
  ```bash
  # Check execution details
  aws stepfunctions describe-execution --execution-arn <ARN>
  
  # Get execution history
  aws stepfunctions get-execution-history --execution-arn <ARN> --max-items 100
  
  # Stop stuck execution
  aws stepfunctions stop-execution --execution-arn <ARN> --cause "Stuck execution"
  ```

**2. "Lambda.ServiceException" Errors**
- **Symptom**: State fails with `Lambda.ServiceException`
- **Cause**: Lambda execution error, timeout, or memory limit exceeded
- **Solution**:
  ```bash
  # Check Lambda logs for the specific invocation
  aws logs tail /aws/lambda/congress-disclosures-house-fd-ingest-zip --follow
  
  # Or use make commands
  make logs-ingest        # House FD ingestion logs
  make logs-extract       # Extraction logs
  make logs-extract-recent # Recent extraction errors
  ```

**3. "States.TaskFailed" with Retry Exhausted**
- **Symptom**: Task fails after 3 retry attempts
- **Cause**: Persistent error (bad data, missing S3 object, schema mismatch)
- **Solution**:
  1. Check CloudWatch Logs for the Lambda function
  2. Identify root cause (data issue, code bug, infrastructure)
  3. Fix the issue
  4. Re-run execution with same input

**4. Quality Check Failures (ValidateSilverQuality/ValidateGoldQuality)**
- **Symptom**: Execution fails at quality gate with "QualityCheckFailed"
- **Cause**: Data quality issues detected by Soda checks
- **Solution**:
  ```bash
  # Check Soda quality check logs
  aws logs tail /aws/lambda/congress-disclosures-run-soda-checks --since 1h
  
  # Review quality metrics
  aws cloudwatch get-metric-statistics \
    --namespace Congress/Pipeline \
    --metric-name QualityChecksPassed \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 3600 \
    --statistics Sum
  ```

**5. "States.Timeout" Errors**
- **Symptom**: State times out before Lambda completes
- **Cause**: Task timeout in state machine definition too short
- **Solution**:
  - Check state machine definition: `state_machines/house_fd_pipeline.json`
  - Increase timeout for specific state (e.g., `IngestZip: 600s → 900s`)
  - Update via Terraform and redeploy

**6. DynamoDB Watermark Issues**
- **Symptom**: Pipeline re-processes data that should be skipped
- **Cause**: Watermark not updated, wrong key, or table access error
- **Solution**:
  ```bash
  # Check watermark table
  aws dynamodb scan --table-name congress-disclosures-pipeline-watermarks
  
  # Check specific watermark
  aws dynamodb get-item \
    --table-name congress-disclosures-pipeline-watermarks \
    --key '{"table_name":{"S":"house_fd"},"watermark_type":{"S":"2025"}}'
  
  # Delete watermark to force refresh
  aws dynamodb delete-item \
    --table-name congress-disclosures-pipeline-watermarks \
    --key '{"table_name":{"S":"house_fd"},"watermark_type":{"S":"2025"}}'
  ```

**7. SQS Queue Backed Up (ExtractDocumentsMap)**
- **Symptom**: Extraction taking too long, thousands of messages in queue
- **Cause**: Low concurrency, Lambda throttling, or large PDFs
- **Solution**:
  ```bash
  # Check queue depth
  make check-extraction-queue
  
  # Monitor processing rate
  watch -n 5 'aws sqs get-queue-attributes \
    --queue-url https://sqs.us-east-1.amazonaws.com/ACCOUNT/congress-disclosures-extraction-queue \
    --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible'
  
  # Increase concurrency in state machine definition (if needed)
  # Edit state_machines/house_fd_pipeline.json
  # ExtractDocumentsMap.MaxConcurrency: 1000 → 1500 (if within limits)
  ```

**8. SNS Alert Spam**
- **Symptom**: Receiving too many SNS alerts
- **Cause**: Transient errors triggering NotifyPipelineFailure repeatedly
- **Solution**:
  - Review alert frequency: Check SNS topic `congress-disclosures-pipeline-alerts`
  - Adjust retry logic in state machine if errors are transient
  - Add error filtering to reduce noise

#### Debugging Workflow

**Step 1: Identify Failed Execution**
```bash
# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:congress-disclosures-house-fd-pipeline \
  --status-filter FAILED \
  --max-items 5

# Get execution details
aws stepfunctions describe-execution --execution-arn <ARN>
```

**Step 2: Get Execution History**
```bash
# Full execution history (all state transitions)
aws stepfunctions get-execution-history \
  --execution-arn <ARN> \
  --max-items 100 \
  > execution_history.json

# Find failed state
cat execution_history.json | jq '.events[] | select(.type == "TaskFailed")'
```

**Step 3: Check Lambda Logs**
```bash
# Get Lambda function name from failed state
# Then tail logs
aws logs tail /aws/lambda/<FUNCTION_NAME> --since 1h --follow

# Or search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/<FUNCTION_NAME> \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"
```

**Step 4: Check X-Ray Traces**
```bash
# Get trace ID from execution
# View in X-Ray Console or CLI
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --filter-expression 'service(id(name: "congress-disclosures-house-fd-pipeline"))'
```

**Step 5: Fix and Retry**
1. Identify root cause from logs/traces
2. Fix the issue (code, data, infrastructure)
3. Re-run execution with same input:
   ```bash
   aws stepfunctions start-execution \
     --state-machine-arn <STATE_MACHINE_ARN> \
     --name "retry-$(date +%Y%m%d-%H%M%S)" \
     --input '<SAME_INPUT_JSON>'
   ```

#### Monitoring Dashboard

**CloudWatch Dashboard**: Navigate to CloudWatch → Dashboards → `Congress-Pipeline-Metrics`

**Key Metrics to Monitor**:
- `ExecutionDuration` - Time per pipeline run
- `ExecutionsFailed` - Failed executions count
- `ExecutionsSucceeded` - Successful executions count
- `QualityChecksPassed` - Data quality gate success rate
- `WatermarkHitRate` - Percentage of skipped (unchanged) data

**Set Up Alerts**:
```bash
# Create CloudWatch alarm for pipeline failures
aws cloudwatch put-metric-alarm \
  --alarm-name congress-pipeline-failures \
  --alarm-description "Alert when Step Functions pipeline fails" \
  --metric-name ExecutionsFailed \
  --namespace AWS/States \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:congress-disclosures-pipeline-alerts
```

#### Useful AWS Console Links

1. **Step Functions Console**: https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines
2. **CloudWatch Logs**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups
3. **X-Ray Service Map**: https://console.aws.amazon.com/xray/home?region=us-east-1#/service-map
4. **EventBridge Rules**: https://console.aws.amazon.com/events/home?region=us-east-1#/rules
5. **SNS Topics**: https://console.aws.amazon.com/sns/v3/home?region=us-east-1#/topics


## Key Lambda Functions

### Ingestion Layer
- **`house_fd_ingest_zip`** (`ingestion/lambdas/house_fd_ingest_zip/handler.py`)
  - Downloads YEARFD.zip from House Clerk
  - Uploads raw zip + XML index to Bronze
  - Extracts PDFs (from zip or parallel download from website)
  - Queues PDFs to SQS for extraction

- **`house_fd_index_to_silver`** (`ingestion/lambdas/house_fd_index_to_silver/handler.py`)
  - Parses XML index with defusedxml
  - Writes Parquet tables: `silver/filings/`, `silver/documents/`
  - Queues extraction jobs to SQS

### Extraction Layer
- **`house_fd_extract_document`** (`ingestion/lambdas/house_fd_extract_document/handler.py`)
  - Text extraction using `ExtractionPipeline` (pypdf → Tesseract OCR fallback)
  - Uploads gzipped text to `silver/text/`
  - Tags Bronze PDF metadata with `extraction-processed: true` (prevents duplicates)
  - Updates Silver documents table with extraction status
  - Queues code-based extraction

- **`house_fd_extract_structured_code`** (`ingestion/lambdas/house_fd_extract_structured_code/handler.py`)
  - Routes to filing-type-specific extractors (Type P, A, T, X, D, W)
  - Code-based extraction (NO AWS Textract - fully free!)
  - Outputs structured JSON to `silver/objects/`

### Gold Layer
- Transformations run as **scripts** (not Lambdas) via `scripts/run_smart_pipeline.py`

## Filing Types

| Code | Type | Extractor | Key Data |
|------|------|-----------|----------|
| **P** | Periodic Transaction Report (PTR) | `PTRExtractor` | Schedule B transactions |
| **A** | Annual Report | `TypeABAnnualExtractor` | Schedules A (assets), B (income), C (liabilities) |
| **T** | Termination Report | `TypeTTerminationExtractor` | Final asset disposition |
| **X** | Extension Request | `TypeXExtensionRequestExtractor` | Notice only |
| **D** | Campaign Notice | `TypeDCampaignNoticeExtractor` | Notice only |
| **W** | Withdrawal Notice | `TypeWWithdrawalNoticeExtractor` | Notice only |

**Extractor Location**: `ingestion/lib/extractors/{type_p_ptr,type_a_b_annual,type_t_termination,...}/extractor.py`

## Common Development Commands

### Setup & Installation
```bash
make setup                    # Initial setup (creates .env, installs deps)
make install                  # Install Python dependencies
make install-dev              # Install dev tools (black, flake8, pytest)
```

### Terraform (Infrastructure)
```bash
make init                     # Initialize Terraform
make plan                     # Show infrastructure changes
make deploy                   # Deploy infrastructure (interactive)
make deploy-auto              # Deploy without confirmation (CI)
make output                   # Show Terraform outputs
```

### Lambda Packaging & Deployment
```bash
make package-all              # Package all Lambdas
make package-extract          # Package extraction Lambda
make package-extract-structured  # Package structured extraction Lambda

# Quick dev cycle (package + deploy directly to Lambda)
make quick-deploy-extract     # Deploy extract Lambda (bypasses Terraform)
make quick-deploy-ingest      # Deploy ingest Lambda
make deploy-extractors        # Package + deploy structured extraction via Terraform
```

### Step Functions & State Machines
```bash
# Note: There are no Makefile targets for Step Functions yet.
# Use AWS CLI commands instead:

# List all state machines
aws stepfunctions list-state-machines \
  --query "stateMachines[?contains(name,'congress-disclosures')].{Name:name,Status:status}" \
  --output table

# Start House FD pipeline
aws stepfunctions start-execution \
  --state-machine-arn $(cd infra/terraform && terraform output -raw house_fd_pipeline_arn) \
  --name "manual-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"manual","year":2025}'

# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn $(cd infra/terraform && terraform output -raw house_fd_pipeline_arn) \
  --max-items 10

# Describe specific execution
aws stepfunctions describe-execution --execution-arn <EXECUTION_ARN>

# Get execution history (for debugging)
aws stepfunctions get-execution-history --execution-arn <EXECUTION_ARN>

# Stop running execution
aws stepfunctions stop-execution --execution-arn <EXECUTION_ARN> --cause "Manual stop"

# Enable/disable EventBridge schedules
aws events enable-rule --name congress-disclosures-house-fd-daily
aws events disable-rule --name congress-disclosures-house-fd-daily
```

### Data Operations
```bash
# Ingestion
make ingest-year YEAR=2025    # Ingest specific year
make ingest-current           # Ingest current year

# Pipeline orchestration
make run-pipeline             # Smart pipeline (interactive mode selection)
make pipeline                 # Same as run-pipeline

# Re-processing
make run-silver-pipeline      # Re-extract all Bronze PDFs (full reprocess)
make run-silver-test          # Test re-extraction (10 PDFs only)

# Aggregation
make aggregate-data           # Generate Gold layer aggregates

# Full system reset
make reset-and-run-all        # Deploy infra → Wipe data → Ingest → Aggregate → Deploy website
```

### Monitoring & Queue Management
```bash
make check-extraction-queue   # Check SQS extraction queue status
make purge-extraction-queue   # Clear all messages from extraction queue
make check-dlq                # Check dead letter queue
make purge-dlq                # Clear DLQ

# Logs
make logs-ingest              # Tail ingest Lambda logs
make logs-extract             # Tail extract Lambda logs
make logs-extract-recent      # Show recent extract logs (errors + successes)
```

### Testing & Code Quality
```bash
make test                     # Run all tests
make test-unit                # Run unit tests only
make test-integration         # Run integration tests (requires AWS)
make test-cov                 # Run tests with coverage report

make lint                     # Run flake8 linting
make format                   # Format code with black
make format-check             # Check formatting without modifying
make type-check               # Run mypy type checking

make check-all                # Run all checks (format, lint, type, test)
make check-contrib            # Quick check before PR (format-check, lint, test-unit)
```

### Website & Documentation
```bash
make deploy-website           # Regenerate analytics + deploy website to S3
make update-pipeline-status   # Generate pipeline status JSON
make upload-pipeline-status   # Upload status to S3
```

### Utilities
```bash
make verify-aws               # Verify AWS credentials
make validate-pipeline        # Validate pipeline integrity
make test-extractions         # Test extraction results by filing type
make clean                    # Clean temp files and caches
make clean-packages           # Clean Lambda package directories
```

## Pipeline Orchestration

The pipeline is orchestrated by **AWS Step Functions** state machines that replace the previous script-based approach. Step Functions provide better observability, error handling, and cost optimization.

### Primary Orchestration Method: Step Functions

**Recommended Approach** - Use Step Functions state machines for all data processing:

```bash
# House FD Pipeline (most common)
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:congress-disclosures-house-fd-pipeline \
  --name "manual-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"manual","year":2025}'

# Congress.gov Pipeline
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:congress-disclosures-congress-pipeline \
  --name "manual-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"manual","year":2025}'

# Lobbying Pipeline
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:congress-disclosures-lobbying-pipeline \
  --name "manual-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"manual","year":2025}'
```

**Execution Monitoring**:
- **AWS Console**: Navigate to Step Functions → Select state machine → View execution history
- **CloudWatch Logs**: `/aws/vendedlogs/states/congress-disclosures-pipelines`
- **X-Ray**: Service map and distributed tracing for performance analysis

### Legacy: Script-Based Orchestration

⚠️ **Deprecated** - The `run_smart_pipeline.py` script is being phased out in favor of Step Functions.

**Still Available** for local development and testing:

```bash
# Using run_smart_pipeline.py (legacy)
python3 scripts/run_smart_pipeline.py --mode incremental    # Incremental update
python3 scripts/run_smart_pipeline.py --mode full --year 2025  # Full reprocess
python3 scripts/run_smart_pipeline.py --mode aggregate      # Gold layer only
```

**Script Modes**:
1. **Full Reset**: Purges queue → Ingests (overwrite) → Waits for extraction → Aggregates
2. **Incremental**: Ingests (skip existing) → Waits for extraction → Aggregates
3. **Reprocess**: Re-triggers index-to-silver → Waits → Aggregates  
4. **Aggregate Only**: Skips ingestion, just runs Gold scripts

**Migration Note**: Use Step Functions for production workflows. Scripts are useful for:
- Local development without AWS Step Functions access
- One-off data fixes
- Testing new extraction logic

## Important Scripts

### Bronze Layer
- `scripts/build_bronze_manifest.py` - Generate manifest of all Bronze PDFs

### Silver Layer Aggregation
- `scripts/generate_type_p_transactions.py` - Aggregate PTR transactions from extraction JSONs
- `scripts/generate_type_a_assets.py` - Aggregate annual report assets
- `scripts/generate_type_t_terminations.py` - Aggregate termination reports
- `scripts/rebuild_silver_manifest.py` - Rebuild Silver layer manifest

### Gold Layer
- `scripts/build_dim_members_simple.py` - Build member dimension table
- `scripts/build_fact_filings.py` - Build filings fact table
- `scripts/build_fact_ptr_transactions.py` - Build transactions fact table

### Aggregation Metrics
- `scripts/compute_agg_document_quality.py` - Member-level PDF quality scores
- `scripts/compute_agg_member_trading_stats.py` - Trading volume, compliance metrics
- `scripts/compute_agg_trending_stocks.py` - Rolling window stock activity
- `scripts/compute_agg_network_graph.py` - Member-asset network analysis

### Utilities
- `scripts/validate_pipeline_integrity.py` - Validate S3 data vs XML index
- `scripts/generate_pipeline_errors.py` - Generate error tracking report
- `scripts/sync_terraform_outputs.sh` - Sync Terraform outputs to .env
- `scripts/sync-api-url.sh` - Sync API Gateway URL to website config

## Shared Libraries (`ingestion/lib/`)

### Core Utilities
- **`s3_utils.py`**: Download/upload files, SHA256 calculation, object existence checks
- **`parquet_writer.py`**: Upsert Parquet records (read → dedupe → write back)
- **`manifest_generator.py`**: Generate website manifest JSONs
- **`metadata_tagger.py`**: Calculate quality scores for PDFs
- **`simple_member_lookup.py`**: Fuzzy name matching against Congress.gov data
- **`reference_data.py`**: Filing type codes, amount range mappings

### Extraction Framework
- **`extraction/ExtractionPipeline`**: Multi-strategy extraction with confidence scoring
- **`extractors/base_extractor.py`**: Base class for all extractors (text-first, OCR-fallback)
- **`extractors/pdf_analyzer.py`**: PDF format detection (TEXT/IMAGE/HYBRID)
- **Type-specific extractors**: `type_p_ptr/`, `type_a_b_annual/`, `type_t_termination/`, etc.

## Testing Approach

### Unit Tests
```bash
pytest tests/unit/ -v
```
Test individual functions in isolation (e.g., PDF text detection, regex parsing)

### Integration Tests
```bash
pytest tests/integration/ -v
```
Test end-to-end workflows with AWS services (requires credentials)

### Test a Single File
```bash
pytest tests/unit/test_pdf_extractor.py::test_detect_text_layer -v
```

## Architectural Decisions

### Why Code-Based Extraction (No Textract)?
- **Cost**: Textract costs $1.50/1000 pages; code-based is free
- **Solution**: Code-based extraction with Tesseract OCR fallback
- **Trade-off**: Lower accuracy on complex layouts, but acceptable for most filings

### Why Bronze Metadata Tagging?
- Prevents duplicate OCR processing across pipeline re-runs
- Each PDF tagged with `extraction-processed: true` after processing
- Checked before queuing expensive operations

### Why Scripts Instead of Event-Driven Gold Layer?
- Gold scripts are CPU/memory-intensive (Pandas, Parquet operations)
- Running as scripts provides better error handling, debugging, and cost control
- No Lambda timeout issues for large aggregations

### Why Parquet + S3 (Not RDS/DynamoDB)?
- **Cost**: S3 storage is 10x cheaper
- **Scalability**: No database size limits
- **Analytics**: Parquet optimized for analytical queries
- **Trade-off**: Slightly higher query latency vs. managed database

## Important Patterns

### Parquet Upsert Pattern
When updating Parquet tables incrementally:
```python
# 1. Read existing records
existing_df = read_parquet(bucket, s3_key)
# 2. Remove old records with same keys
existing_clean = existing_df[~existing_df['doc_id'].isin(new_df['doc_id'])]
# 3. Append new records
combined = pd.concat([existing_clean, new_df])
# 4. Write back (atomic replace)
combined.to_parquet(s3_key)
```
Used in: `ingestion/lib/parquet_writer.py`

### Bronze Metadata State Machine
Before queuing extraction:
```python
try:
    response = s3_client.head_object(Bucket=bucket, Key=pdf_key)
    if response['Metadata'].get('extraction-processed') == 'true':
        return "skipped"  # Already processed
except ClientError:
    pass  # Object doesn't exist or no metadata
```
After extraction, tag the PDF:
```python
s3_client.copy_object(
    CopySource={'Bucket': bucket, 'Key': pdf_key},
    Bucket=bucket,
    Key=pdf_key,
    Metadata={'extraction-processed': 'true'},
    MetadataDirective='REPLACE'
)
```

### SQS Partial Batch Failure
```python
failed_items = []
for record in event['Records']:
    try:
        process(record)
    except Exception as e:
        failed_items.append({'itemIdentifier': record['messageId']})
return {'batchItemFailures': failed_items}
```
Failed messages stay in queue, successful ones are deleted

## Code Style

### Python (PEP 8 + Black)
- **Line length**: 88 characters (Black default)
- **Type hints**: Always use type annotations
- **Docstrings**: Google style
- **Imports**: Organized (stdlib → third-party → local)

Example:
```python
from typing import Dict, List

def extract_text(pdf_path: str, use_ocr: bool = False) -> Dict[str, str]:
    """Extract text from a PDF file.

    Args:
        pdf_path: Path to PDF file
        use_ocr: Whether to use OCR fallback

    Returns:
        Dictionary with 'text', 'confidence_score', 'method'

    Raises:
        FileNotFoundError: If PDF doesn't exist
    """
```

### Formatting Commands
```bash
black ingestion/ tests/        # Format code
flake8 ingestion/              # Lint
mypy ingestion/                # Type check
```

## Environment Variables

Key variables in `.env` (see `.env.example`):
- `AWS_REGION` - AWS region (default: us-east-1)
- `AWS_ACCOUNT_ID` - Your AWS account ID
- `S3_BUCKET_NAME` - S3 bucket name (default: congress-disclosures-standardized)
- `PROJECT_NAME` - Project name (default: congress-disclosures)
- `ENVIRONMENT` - Environment (development/production)
- `LOG_LEVEL` - Logging level (INFO/DEBUG)

**Important**: Never commit `.env` to Git. Use `.env.example` as a template.

## Deployment Workflow

### Fresh Deployment
```bash
# 1. Setup environment
make setup
# Edit .env with your AWS credentials

# 2. Deploy infrastructure (includes Step Functions state machines)
make init
make deploy

# 3. Verify deployment
cd infra/terraform && terraform output

# 4. Run initial pipeline via Step Functions
aws stepfunctions start-execution \
  --state-machine-arn $(cd infra/terraform && terraform output -raw house_fd_pipeline_arn) \
  --name "initial-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"manual","year":2025}'

# 5. Monitor execution
# Navigate to AWS Console → Step Functions → congress-disclosures-house-fd-pipeline
```

### Daily Incremental Update

**Recommended**: Use EventBridge scheduled execution (currently DISABLED):
```bash
# Enable daily schedule (after watermarking is tested)
aws events enable-rule --name congress-disclosures-house-fd-daily

# Or trigger manually via Step Functions
aws stepfunctions start-execution \
  --state-machine-arn $(cd infra/terraform && terraform output -raw house_fd_pipeline_arn) \
  --name "daily-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"scheduled","year":2025}'
```

**Legacy**: Automated via GitHub Actions (`.github/workflows/daily_incremental.yml`):
```bash
python3 scripts/run_smart_pipeline.py --mode incremental
```

### Manual Re-processing

**Using Step Functions** (recommended):
```bash
# Full refresh (force reprocess all data)
aws stepfunctions start-execution \
  --state-machine-arn $(cd infra/terraform && terraform output -raw house_fd_pipeline_arn) \
  --name "reprocess-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"manual","year":2025,"force_refresh":true}'
```

**Using Scripts** (legacy):
```bash
# Re-extract all Bronze PDFs
make run-silver-pipeline

# Just rebuild Gold layer
python3 scripts/run_smart_pipeline.py --mode aggregate
```

## Debugging Tips

### Check Extraction Queue Status
```bash
make check-extraction-queue
```
Shows: messages in queue, messages in flight, messages delayed

### View Recent Extraction Errors
```bash
make logs-extract-recent
```

### Inspect a Specific PDF
```python
python3 scripts/inspect_pdf.py --doc-id 10063228
```

### Test Extraction Locally
```python
from ingestion.lib.extraction.ExtractionPipeline import ExtractionPipeline

pipeline = ExtractionPipeline(pdf_path="sample.pdf")
result = pipeline.extract()
print(result['text'], result['confidence_score'])
```

## Common Issues

### Lambda Timeout During Extraction
- **Symptom**: Extraction Lambda times out (5 min limit)
- **Solution**: Large PDFs may exceed timeout. Check CloudWatch logs. Consider splitting into smaller batches.

### SQS Queue Backed Up
- **Symptom**: Extraction queue has thousands of messages
- **Solution**: Increase Lambda concurrency or wait for processing to complete
```bash
make check-extraction-queue  # Monitor progress
```

### Parquet Schema Mismatch
- **Symptom**: `ArrowInvalid: Schema mismatch` when upserting
- **Solution**: Ensure new DataFrame has same column types as existing Parquet
```python
# Cast types explicitly
df['filing_date'] = pd.to_datetime(df['filing_date'])
df['amount_low'] = df['amount_low'].astype('int64')
```

### Duplicate Processing
- **Symptom**: PDFs being extracted multiple times
- **Solution**: Check Bronze metadata tagging is working
```bash
aws s3api head-object --bucket congress-disclosures-standardized \
  --key bronze/.../pdfs/20026590.pdf | jq '.Metadata'
```

## Security Considerations

- **Never commit** AWS credentials, API keys, or `.env` files
- **Use IAM roles** instead of hardcoded credentials
- **Store secrets** in AWS Secrets Manager or SSM Parameter Store
- **Rotate credentials** immediately if accidentally committed

## Legal Compliance

All usage must comply with **5 U.S.C. § 13107** (see `docs/LEGAL_NOTES.md`):
- ✅ Transparency, research, news purposes
- ❌ Commercial purposes (except news/media)
- ❌ Credit rating determination
- ❌ Fundraising or solicitation

## Additional Documentation

- `README.md` - Quick start guide
- `CONTRIBUTING.md` - Contribution guidelines, commit conventions
- `docs/ARCHITECTURE.md` - Detailed architecture documentation
- `docs/DEPLOYMENT.md` - Self-hosting deployment guide
- `docs/EXTRACTION_ARCHITECTURE.md` - Extraction pipeline deep dive
- `docs/API_STRATEGY.md` - API design and endpoints
- Refer to files in .github which outline templates, processes, SOPs.