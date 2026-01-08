# Terraform Infrastructure Audit Report

## Summary
Analyzed 43 Terraform files with 200+ AWS resources. Identified redundancies, deprecated patterns, and missing resources.

## 1. FILES TO DELETE (5 files)

### `api_gateway_assets.tf` (30 lines)
- **Reason**: Routes already defined in `api_lambdas.tf` using for_each loop
- **Conflicting routes**: GET /v1/filings/{doc_id}/assets, GET /v1/filings/{doc_id}/positions
- **Resource names**: 
  - `aws_apigatewayv2_route.get_filing_assets`
  - `aws_apigatewayv2_route.get_filing_positions`
  - `aws_apigatewayv2_integration.get_filing_assets`
  - `aws_apigatewayv2_integration.get_filing_positions`

### `api_gateway_members.tf` (43 lines)
- **Reason**: Routes already defined in `api_lambdas.tf` using for_each loop
- **Conflicting routes**: 
  - GET /v1/members/{name}/filings
  - GET /v1/members/{name}/transactions
  - GET /v1/members/{name}/assets
- **Duplicate resource definitions**

### `api_gateway_transactions.tf` (576 bytes)
- **Reason**: Routes already defined in `api_lambdas.tf`
- **Status**: Likely minimal/redundant content

### `api_costs_route.tf` (499 bytes)
- **Reason**: Single route GET /v1/costs already in api_lambdas.tf (get_aws_costs)
- **Status**: Redundant definition

### `api_storage_route.tf` (533 bytes)
- **Reason**: Single route GET /v1/storage/{layer} already in api_lambdas.tf (list_s3_objects)
- **Status**: Redundant definition

### `api_gateway_congress.tf` (14KB) - CONSOLIDATE (NOT DELETE)
- **Reason**: Contains Congress-specific routes but duplicates those in api_lambdas.tf
- **Action**: Merge Congress endpoint definitions into api_lambdas.tf locals

### `api_gateway_lobbying.tf` (4.4KB) - CONSOLIDATE (NOT DELETE)
- **Reason**: Contains Lobbying-specific routes
- **Action**: Merge into api_lambdas.tf locals

## 2. RESOURCES TO REMOVE (within files)

### `lambda_stub.tf` (47 lines)
- **Resource**: `aws_lambda_function.stub_handler`
- **Reason**: Placeholder function, not part of modernization plan
- **Action**: Delete entire file

### `lambdas_analytics.tf` (58 lines)
- **Resource**: `aws_lambda_function.compute_bill_trade_correlations`
- **Reason**: 
  - Uses placeholder S3 key "lambda-deployments/compute_bill_trade_correlations/function.zip"
  - References undefined layer `aws_lambda_layer_version.congress_pandas_layer` (defined in lambda_congress.tf, not consistently available)
  - This is a stub analytics function not in core plan
- **Action**: Remove this function, consolidate actual analytics into lambdas_gold_transformations.tf

### `dynamodb.tf` (26 lines)
- **Resource**: `aws_dynamodb_table.house_fd_documents`
- **Reason**: Legacy table marked with "Legacy table (keep for backward compatibility)" but not actively used
- **Status**: Consider archiving instead of keeping if no active queries depend on it
- **Recommendation**: Remove after verifying no production systems read from it

### `sqs.tf` - PARTIALLY REMOVE
- **Resource**: `aws_lambda_event_source_mapping.extraction_queue`
- **Issue**: References extraction flow; check if still relevant with Step Functions
- **Action**: Keep if extraction still uses SQS-triggered Lambda; otherwise consolidate into Step Functions

### `lambdas_data_quality.tf` (82 lines) - PARTIALLY REMOVE
- **Resources**:
  - `aws_s3_object.soda_core_layer`
  - `aws_s3_object.soda_checks`
  - `aws_s3_object.soda_configuration`
  - `aws_lambda_layer_version.soda_core`
  - `aws_lambda_function.run_soda_checks`
  - `aws_cloudwatch_log_group.run_soda_checks_logs`
- **Reason**: Soda quality checks not mentioned in modernization plan; use CloudWatch instead
- **Action**: Remove entire file (8 resources)

### `lambda_congress.tf` (298 lines) - PARTIALLY REMOVE
- **Resource**: `aws_lambda_layer_version.congress_pandas_layer` (lines 196-202)
- **Reason**: Duplicate layer definition; should use AWS-provided AWSSDKPandas layer
- **Other congress lambdas**: Keep (part of Congress pipeline)

## 3. RESOURCES TO CONSOLIDATE

### API Gateway Routes (api_*.tf files) - CONSOLIDATE INTO ONE
Current structure (11 API-related files):
- api_gateway.tf (main HTTP API + member/trading/analytics routes)
- api_gateway_assets.tf (filing asset routes)
- api_gateway_congress.tf (Congress.gov proxy routes)
- api_gateway_lobbying.tf (Lobbying routes)
- api_gateway_members.tf (member detail routes)
- api_gateway_transactions.tf (transaction routes)
- api_costs_route.tf (cost tracking route)
- api_storage_route.tf (S3 storage route)

**Recommended Structure**:
```
api_gateway_core.tf          # API, stage, CloudWatch logs
api_gateway_routes.tf         # All routes defined via api_lambdas.tf locals
api_lambdas.tf               # Lambdas + unified locals for all endpoints
```

**Action Items**:
1. Keep `api_gateway.tf` (HTTP API, stage, logging)
2. Keep `api_lambdas.tf` (unified Lambda creation + route definitions via locals)
3. Delete: `api_gateway_assets.tf`, `api_gateway_members.tf`, `api_gateway_transactions.tf`, `api_costs_route.tf`, `api_storage_route.tf`
4. Consolidate `api_gateway_congress.tf` routes into `api_lambdas.tf` locals (already partially done)
5. Consolidate `api_gateway_lobbying.tf` routes into `api_lambdas.tf` locals

### Lambda Functions Across Files - GROUP BY LAYER
Current spread (highly scattered):

**Bronze Layer (Ingestion)**:
- `lambda.tf`: ingest_zip, index_to_silver, extract_document
- `lambda_congress.tf`: congress_fetch_entity, congress_orchestrator, congress_bronze_to_silver
- `lambda_lobbying.tf`: lda_ingest_filings

**Recommendation**: Create `lambda_bronze_layer.tf`

**Silver Layer (Extraction)**:
- `structured_extraction.tf`: structured_extraction (isolated, incomplete)
- `structured_code_extraction.tf`: (needs review)

**Recommendation**: Create `lambda_silver_layer.tf`

**Gold Layer (Transformations)**:
- `lambdas_gold_transformations.tf`: build_dim_members, build_dim_assets, build_dim_bills, etc.

**Recommendation**: Keep as-is, expand with new lambdas

**API Layer**:
- `api_lambdas.tf`: All API endpoint handlers (good structure)

**Shared/Utility**:
- `step_functions.tf`: Has 3 Lambda functions (publish_pipeline_metrics, check_house_fd_updates, check_lobbying_updates, check_congress_updates)

**Recommendation**: Move Step Functions check/publish lambdas to separate `lambda_orchestration.tf`

### Lambda Files to Consolidate
- `lambda_congress.tf` + `lambda.tf` → `lambda_bronze_layer.tf`
- `lambda_lobbying.tf` → `lambda_bronze_layer.tf` (or separate if complex)
- `lambda_stub.tf` → DELETE
- `structured_extraction.tf` + `structured_code_extraction.tf` → `lambda_silver_layer.tf`

### SQS Queues - CONSOLIDATE
Current spread:
- `sqs.tf`: extraction_queue, extraction_dlq
- `sqs_congress.tf`: congress_fetch_queue, congress_fetch_dlq, congress_silver_queue, congress_silver_dlq
- `sqs_lobbying.tf`: lda_bill_extraction_queue, lda_bill_extraction_dlq
- `structured_extraction.tf`: structured_extraction_queue (inline)

**Recommendation**: Create `sqs_queues.tf`
```
- Main extraction queues (primary + DLQ)
- Congress pipeline queues (fetch + silver, each with DLQ)
- Lobbying extraction queues (primary + DLQ)
- Structured extraction queue
```

### CloudWatch Log Groups - CONSOLIDATE
Currently defined across multiple files (lambdas, step_functions, api_gateway).

**Recommendation**: Create `cloudwatch_logs.tf`
- Group by component: ingestion, extraction, api, orchestration, monitoring
- Standardize retention policies
- Add missing log groups

## 4. MISSING RESOURCES (from modernization plan)

### 1. Lambda Authorizer for API Authentication
- **Type**: `aws_apigatewayv2_authorizer` (missing)
- **Purpose**: JWT validation for API key authentication
- **Location**: Create in new file `api_authorizer.tf`
- **Configuration needed**:
  - Reference to api_keys DynamoDB table
  - JWT validation from api_keys.api_key_hash
  - Cache authorization for 300s

### 2. EventBridge Rules (if replacing SQS triggers)
- **Status**: Partially present in `eventbridge.tf`
- **Current rules**:
  - house_fd_daily (trigger state machine)
  - congress_daily (trigger state machine)
  - lobbying_weekly (trigger state machine)
  - manual_trigger
- **Missing**: Rules for direct Lambda invocation (if needed)
- **Action**: Review and finalize EventBridge strategy vs SQS

### 3. CloudWatch Dashboards
- **Missing**: Main operational dashboard
- **Location**: Create `cloudwatch_dashboards.tf`
- **Metrics to track**:
  - Pipeline execution status (Step Functions)
  - Lambda invocation counts + durations + errors
  - SQS queue depth + messages processed
  - S3 data volume (Bronze/Silver/Gold layers)
  - API Gateway request rate + errors + latency
  - DynamoDB reads/writes
  - Extraction success rate
  - Data quality metrics

### 4. Glue Data Catalog
- **Status**: Already added in `glue_catalog.tf`
- **Status**: GOOD - Keep as-is

### 5. SNS Topics
- **Status**: Present in `sns.tf`
- **Resources**:
  - pipeline_alerts (+ email/SMS subscriptions)
  - data_quality_alerts (+ email subscription)
- **Missing**: Cross-dataset-correlation alerts topic
- **Recommendation**: Add new topic in sns.tf for correlation failures

### 6. IAM Role for Lambda Authorizer
- **Missing**: Dedicated IAM role for authorizer Lambda
- **Current**: Uses shared `aws_iam_role.lambda_execution`
- **Recommendation**: Create specific role with minimal DynamoDB access to api_keys table

## 5. DEPRECATED/PROBLEMATIC PATTERNS

### Pattern 1: Multiple API Gateway definitions
- Files: api_gateway_*.tf
- **Problem**: Routes defined in multiple files, hard to maintain consistency
- **Better**: Single source of truth in api_lambdas.tf locals (already doing this)

### Pattern 2: Raw S3 object uploads in Terraform
- Files: lambdas_data_quality.tf (aws_s3_object for soda configs)
- **Problem**: Not best practice, files should be in source control
- **Better**: Use data source or CI/CD pipeline to upload

### Pattern 3: Inline Lambda code with filebase64sha256()
- Files: Most lambda definitions
- **Problem**: Source hash ignored in lifecycle rules
- **Better**: Use source_code_hash with proper packaging (already doing this)

### Pattern 4: Hardcoded ARNs
- Files: api_lambdas.tf (hardcoded layer ARNs)
- **Problem**: Breaks on version updates, region changes
- **Better**: Reference aws_lambda_layer_version.* resources or variables

### Pattern 5: Unused layer definitions
- Files: lambda_congress.tf defines congress_pandas_layer but not used consistently
- **Better**: Remove and use AWS-provided AWSSDKPandas layer

## 6. ORGANIZATION RECOMMENDATION

### Final Directory Structure
```
infra/terraform/
├── core/
│   ├── main.tf                    (locals, provider, data sources)
│   ├── variables.tf               (all variables)
│   ├── outputs.tf                 (all outputs)
│   └── backend.tf                 (state management)
│
├── storage/
│   ├── s3.tf                      (data lake bucket + policies)
│   └── glue_catalog.tf            (Glue Data Catalog)
│
├── queues/
│   └── sqs_queues.tf              (all SQS queues + DLQs)
│
├── database/
│   ├── dynamodb.tf                (pipeline state tables)
│   └── dynamodb_api.tf            (API layer tables)
│
├── security/
│   ├── iam.tf                     (IAM roles + policies)
│   └── api_authorizer.tf          (Lambda authorizer)
│
├── lambdas/
│   ├── lambda_bronze_layer.tf     (ingestion: ingest, index_to_silver, extract, congress, lobbying)
│   ├── lambda_silver_layer.tf     (extraction: structured extraction)
│   ├── lambdas_gold_transformations.tf (dimension/fact builders)
│   ├── api_lambdas.tf             (API endpoint handlers)
│   └── lambda_orchestration.tf    (Step Functions check/publish lambdas)
│
├── api/
│   ├── api_gateway.tf             (HTTP API, stage, logging)
│   └── api_gateway_routes.tf      (routes auto-generated from api_lambdas.tf)
│
├── orchestration/
│   ├── step_functions.tf          (state machines)
│   ├── eventbridge.tf             (scheduled rules)
│   └── sns.tf                     (alerting topics)
│
├── monitoring/
│   ├── cloudwatch_logs.tf         (log groups)
│   └── cloudwatch_dashboards.tf   (operational dashboards)
│
└── config/
    ├── terraform.tfvars           (environment-specific values)
    └── terraform.tfvars.example   (template)
```

### Refactored File Count
- Before: 43 files (highly scattered)
- After: ~25 files (organized, logical grouping)
- Deleted: 5 files
- Consolidated: 8 files
- Created: 3 new files

## 7. MIGRATION CHECKLIST

- [ ] Delete api_gateway_assets.tf, api_gateway_members.tf, api_gateway_transactions.tf, api_costs_route.tf, api_storage_route.tf
- [ ] Delete lambda_stub.tf
- [ ] Delete lambdas_analytics.tf
- [ ] Delete lambdas_data_quality.tf
- [ ] Remove aws_dynamodb_table.house_fd_documents from dynamodb.tf (legacy)
- [ ] Remove congress_pandas_layer from lambda_congress.tf
- [ ] Consolidate api_gateway_congress.tf routes into api_lambdas.tf locals
- [ ] Consolidate api_gateway_lobbying.tf routes into api_lambdas.tf locals
- [ ] Create lambda_bronze_layer.tf (consolidate lambda.tf + lambda_congress.tf + lambda_lobbying.tf)
- [ ] Create lambda_silver_layer.tf (consolidate structured_extraction.tf + structured_code_extraction.tf)
- [ ] Create lambda_orchestration.tf (move Step Functions check lambdas)
- [ ] Create sqs_queues.tf (consolidate from sqs.tf, sqs_congress.tf, sqs_lobbying.tf, structured_extraction.tf)
- [ ] Create api_authorizer.tf (Lambda authorizer + role)
- [ ] Create cloudwatch_logs.tf (consolidate log groups)
- [ ] Create cloudwatch_dashboards.tf (operational dashboards)
- [ ] Add cross-dataset-correlation SNS topic to sns.tf
- [ ] Update variables.tf with any new configurations
- [ ] Update outputs.tf with consolidated outputs
- [ ] Verify terraform plan shows no unintended changes
- [ ] Test infrastructure deployment

