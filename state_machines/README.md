# Congress Data Platform State Machines

## Overview

This directory contains AWS Step Functions state machine definitions for the Congress Disclosures Data Platform.

## State Machines

### Unified Pipeline (NEW)

**File**: `congress_data_platform.json`  
**Status**: ✅ Active (Replaces 4 legacy pipelines)  
**Purpose**: Single orchestrated pipeline for all data sources

**Architecture**:
```
ValidateInput (5-year lookback: 2020-2025)
    ↓
CheckForUpdates (Parallel)
    ├── CheckHouseFD
    ├── CheckCongress
    └── CheckLobbying
    ↓
EvaluateUpdates (Choice)
    ↓
BronzeIngestion (Parallel)
    ├── IngestHouseFD
    ├── IngestCongress
    └── IngestLobbying
    ↓
SilverTransformation (Parallel)
    ├── IndexToSilver → ExtractDocumentsMap (MaxConcurrency: 10)
    ├── ProcessCongressBillsMap (MaxConcurrency: 10)
    └── ParseLobbyingXMLToSilver
    ↓
ValidateSilverQuality
    ↓
GoldDimensions (Parallel)
    ├── BuildDimMembers
    ├── BuildDimAssets
    └── BuildDimBills
    ↓
GoldFacts (Parallel)
    ├── BuildFactTransactions
    ├── BuildFactFilings
    └── BuildFactLobbying
    ↓
GoldAggregates (Parallel)
    ├── ComputeTrendingStocks
    ├── ComputeMemberStats
    └── ComputeBillTradeCorrelations
    ↓
ValidateGoldQuality
    ↓
EvaluateQuality (Choice)
    ↓
PublishMetrics
    ↓
PipelineSuccess
```

**Key Features**:
- ✅ **6 Phases**: UpdateDetection, Bronze, Silver, Gold, Quality, Publish
- ✅ **Parallel Execution**: 3 data sources processed concurrently
- ✅ **Map States**: MaxConcurrency=10 for distributed processing
- ✅ **Error Handling**: Comprehensive Catch/Retry blocks with exponential backoff
- ✅ **Quality Gates**: Soda checks between Silver and Gold layers
- ✅ **22 Lambda Functions**: All critical functions referenced
- ✅ **Year Validation**: 5-year lookback window (2020-2025) for initial ingestion
- ✅ **Timeout**: 7200s (2 hours) max execution time

**Lambda Functions Referenced (22)**:
1. `LAMBDA_CHECK_HOUSE_FD_UPDATES` - Check House FD updates
2. `LAMBDA_CHECK_CONGRESS_UPDATES` - Check Congress.gov updates
3. `LAMBDA_CHECK_LOBBYING_UPDATES` - Check lobbying updates
4. `LAMBDA_HOUSE_FD_INGEST_ZIP` - Ingest House FD ZIP files
5. `LAMBDA_CONGRESS_ORCHESTRATOR` - Orchestrate Congress.gov ingestion
6. `LAMBDA_LDA_INGEST_FILINGS` - Ingest lobbying filings
7. `LAMBDA_INDEX_TO_SILVER` - Parse House FD index to Silver
8. `LAMBDA_EXTRACT_DOCUMENT` - Extract text from PDFs
9. `LAMBDA_EXTRACT_STRUCTURED_CODE` - Code-based structured extraction
10. `LAMBDA_CONGRESS_FETCH_ENTITY` - Fetch Congress.gov entities
11. `LAMBDA_CONGRESS_BRONZE_TO_SILVER` - Transform Congress.gov Bronze to Silver
12. `LAMBDA_RUN_SODA_CHECKS` - Run data quality checks
13. `LAMBDA_BUILD_DIM_MEMBERS` - Build member dimension
14. `LAMBDA_BUILD_DIM_ASSETS` - Build asset dimension
15. `LAMBDA_BUILD_DIM_BILLS` - Build bill dimension
16. `LAMBDA_BUILD_FACT_TRANSACTIONS` - Build transactions fact table
17. `LAMBDA_BUILD_FACT_FILINGS` - Build filings fact table
18. `LAMBDA_BUILD_FACT_LOBBYING` - Build lobbying fact table
19. `LAMBDA_COMPUTE_TRENDING_STOCKS` - Compute trending stocks
20. `LAMBDA_COMPUTE_MEMBER_STATS` - Compute member statistics
21. `LAMBDA_COMPUTE_BILL_TRADE_CORRELATIONS` - Compute bill-trade correlations
22. `LAMBDA_PUBLISH_METRICS` - Publish CloudWatch metrics

**Input Schema**:
```json
{
  "execution_type": "manual|scheduled|initial_load",
  "mode": "incremental|force_refresh",
  "sources": {
    "house_fd": true,
    "congress_gov": true,
    "lobbying": true
  },
  "parameters": {
    "year": 2024,
    "force_refresh": false,
    "skip_quality_checks": false,
    "rebuild_gold": false
  }
}
```

**Execution Modes**:
- **Incremental** (default): Process new data only
- **Force Refresh**: Re-download and re-process all data
- **Initial Load**: Multi-year processing with 5-year lookback

**Error Handling**:
- **Transient Errors**: Automatic retry with exponential backoff
- **Rate Limits**: 60s interval, up to 10 attempts
- **Timeouts**: SNS alerts + graceful failure
- **Quality Failures**: SNS alert + pipeline halt
- **Partial Failures**: Continue with other sources (resilient design)

---

### Legacy Pipelines (DEPRECATED)

The following pipelines are deprecated and replaced by `congress_data_platform.json`:

#### ❌ `house_fd_pipeline.json`
**Status**: Deprecated  
**Replaced By**: `congress_data_platform.json` (Phase 2-4)  
**Migration Date**: TBD

#### ❌ `congress_pipeline.json`
**Status**: Deprecated  
**Replaced By**: `congress_data_platform.json` (Phase 2-4)  
**Migration Date**: TBD

#### ❌ `lobbying_pipeline.json`
**Status**: Deprecated  
**Replaced By**: `congress_data_platform.json` (Phase 2-4)  
**Migration Date**: TBD

#### ❌ `cross_dataset_correlation.json`
**Status**: Deprecated  
**Replaced By**: `congress_data_platform.json` (Phase 4c: GoldAggregates)  
**Migration Date**: TBD

---

## State Transition Documentation

### Phase 1: Update Detection
**Purpose**: Determine which data sources have new data  
**Parallelism**: 3 concurrent checks  
**Timeout**: 60s per check  
**Retry Strategy**: Exponential backoff (2.0x) with rate limit handling

**Transitions**:
- `ValidateInput` → `CheckForUpdates` (always)
- `CheckForUpdates` → `EvaluateUpdates` (always)
- `EvaluateUpdates` → `BronzeIngestion` (if updates found OR force_refresh mode)
- `EvaluateUpdates` → `NoUpdatesFound` (if no updates and incremental mode)

### Phase 2: Bronze Ingestion
**Purpose**: Download raw data from all sources  
**Parallelism**: 3 concurrent downloads  
**Timeout**: 600-900s per source  
**Retry Strategy**: Exponential backoff (2.0x-3.0x)

**Transitions**:
- `BronzeIngestion` → `SilverTransformation` (always, even with partial failures)

**Resilience**: Individual source failures are caught and logged, but don't halt the entire pipeline.

### Phase 3: Silver Transformation
**Purpose**: Parse and extract structured data  
**Parallelism**: 3 concurrent transformation branches  
**Map States**: MaxConcurrency=10 for distributed processing  
**Timeout**: 300-600s per task

**Transitions**:
- `SilverTransformation` → `ValidateSilverQuality` (always)
- `ValidateSilverQuality` → `GoldDimensions` (if quality checks pass)
- `ValidateSilverQuality` → `NotifyQualityFailure` (if quality checks fail)

**Key Operations**:
- **House FD**: Index parsing → Distributed PDF extraction (10 concurrent)
- **Congress.gov**: Distributed bill processing (10 concurrent)
- **Lobbying**: XML parsing → Parquet writes

### Phase 4a: Gold Dimensions
**Purpose**: Build dimension tables (SCD Type 2)  
**Parallelism**: 3 concurrent dimension builds  
**Timeout**: 300-600s per dimension  

**Transitions**:
- `GoldDimensions` → `GoldFacts` (always)

**Dimensions Built**:
1. `dim_members` - Congressional members (SCD Type 2)
2. `dim_assets` - Stock/asset master data
3. `dim_bills` - Legislative bills

### Phase 4b: Gold Facts
**Purpose**: Build fact tables (references dimensions)  
**Parallelism**: 3 concurrent fact builds  
**Timeout**: 300-600s per fact table  

**Transitions**:
- `GoldFacts` → `GoldAggregates` (always)

**Facts Built**:
1. `fact_transactions` - Trading transactions
2. `fact_filings` - Financial disclosures
3. `fact_lobbying` - Lobbying activities

### Phase 4c: Gold Aggregates
**Purpose**: Compute cross-dataset correlations and metrics  
**Parallelism**: 3 concurrent aggregate computations  
**Timeout**: 300-600s per aggregate  

**Transitions**:
- `GoldAggregates` → `ValidateGoldQuality` (always)

**Aggregates Computed**:
1. Trending stocks (7d, 30d, 90d windows)
2. Member trading statistics
3. Bill-trade correlations

### Phase 5: Quality Checks
**Purpose**: Validate data quality at Silver and Gold layers  
**Parallelism**: Sequential (gates between layers)  
**Timeout**: 300s per check  

**Transitions**:
- `ValidateGoldQuality` → `EvaluateQuality` (always)
- `EvaluateQuality` → `PublishMetrics` (if passed)
- `EvaluateQuality` → `NotifyQualityWarning` (if warned) → `PublishMetrics`
- `EvaluateQuality` → `NotifyQualityFailure` (if failed) → `QualityCheckFailed`

**Quality Levels**:
- **Passed**: All checks passed, continue to publish
- **Warned**: Minor issues detected, send alert but continue
- **Failed**: Critical issues detected, halt pipeline with SNS alert

### Phase 6: Publish
**Purpose**: Publish metrics and update API caches  
**Parallelism**: Sequential  
**Timeout**: 180s  

**Transitions**:
- `PublishMetrics` → `PipelineSuccess` (always, even if metrics publishing fails)

**Graceful Degradation**: Metrics publishing failure is caught and logged, but doesn't fail the pipeline (data is already persisted).

---

## Testing

### Validate JSON Syntax
```bash
python3 -m json.tool state_machines/congress_data_platform.json
```

### Count Lambda References
```bash
grep -o 'LAMBDA_[A-Z_]*' state_machines/congress_data_platform.json | sort -u | wc -l
# Expected: 22
```

### Terraform Plan (Dry Run)
```bash
cd infra/terraform
terraform plan -target=aws_sfn_state_machine.congress_data_platform
```

---

## Deployment

### Prerequisites
1. All 22 Lambda functions deployed
2. SNS topic for alerts created
3. S3 buckets configured
4. IAM roles with proper permissions

### Deploy State Machine
```bash
cd infra/terraform
terraform apply -target=aws_sfn_state_machine.congress_data_platform
```

### Verify Deployment
```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn $(terraform output -raw state_machine_arn) \
  --query 'status'
```

### Test Execution
```bash
# Test with small dataset (2020 only)
aws stepfunctions start-execution \
  --state-machine-arn $(terraform output -raw state_machine_arn) \
  --input '{"execution_type":"manual","mode":"incremental","sources":{"house_fd":true,"congress_gov":true,"lobbying":true},"parameters":{"year":2020}}'
```

---

## Monitoring

### CloudWatch Metrics
- `PipelineExecutions` (Count)
- `PipelineSuccessRate` (Percentage)
- `PipelineDuration` (Milliseconds)
- `QualityCheckFailures` (Count)

### CloudWatch Logs
- Log Group: `/aws/vendedlogs/states/congress-data-platform`
- Log Level: `ALL` (captures all state transitions)
- Retention: 30 days

### X-Ray Tracing
- Enabled for all state machine executions
- Visualizes Lambda invocation chains
- Identifies bottlenecks and error rates

### Alarms
- Pipeline execution failures
- Quality check failures
- Execution duration > 2 hours
- Rate limit errors > 10/hour

---

## Migration Strategy

### Phase 1: Deploy Unified Pipeline (Week 1)
1. Deploy `congress_data_platform.json` state machine
2. Run test executions with 2020 data
3. Validate outputs match legacy pipelines

### Phase 2: Run in Parallel (Week 2)
1. Run both unified and legacy pipelines
2. Compare outputs for consistency
3. Monitor performance and costs

### Phase 3: Switch Over (Week 3)
1. Update EventBridge triggers to use unified pipeline
2. Disable legacy pipeline triggers
3. Keep legacy pipelines for rollback

### Phase 4: Decommission (Week 4)
1. Archive legacy state machine definitions
2. Remove legacy EventBridge triggers
3. Update documentation

---

## Rollback Plan

If the unified pipeline fails:
1. Re-enable EventBridge triggers for legacy pipelines
2. Investigate failure cause in CloudWatch Logs
3. Fix and re-deploy unified pipeline
4. Re-test before switching over again

---

## Cost Estimation

**Step Functions**:
- State transitions: ~60 per execution
- Monthly executions: 30 (daily)
- Monthly transitions: 1,800
- **Cost**: $0 (within free tier: 4,000/month)

**CloudWatch Logs**:
- Per execution: ~5MB
- Monthly: 150MB
- **Cost**: $0 (within free tier: 5GB/month)

**X-Ray Tracing**:
- Per execution: ~60 segments
- Monthly: 1,800 segments
- **Cost**: $0 (within free tier: 100,000/month)

**Total State Machine Cost**: **$0/month** (all within free tier)

---

## Support

**Document Owner**: Engineering Team  
**Status**: Design Complete - Ready for Implementation  
**Last Updated**: 2026-01-04

For questions or issues:
1. Check CloudWatch Logs for execution details
2. Review X-Ray traces for performance issues
3. Create GitHub issue with `state-machine` label
