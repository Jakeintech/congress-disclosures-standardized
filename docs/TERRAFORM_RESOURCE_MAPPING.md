# Terraform Infrastructure Resource Mapping

## DELETE: Detailed Resource Inventory (5 files, 16 resources)

### 1. api_gateway_assets.tf (DELETE ENTIRELY)
```
aws_apigatewayv2_route.get_filing_assets
aws_apigatewayv2_integration.get_filing_assets
aws_apigatewayv2_route.get_filing_positions
aws_apigatewayv2_integration.get_filing_positions
```
**Already defined in**: api_lambdas.tf local.api_lambdas map
- get_filing_assets → get_filing_transactions, get_filing_assets, get_filing_positions

---

### 2. api_gateway_members.tf (DELETE ENTIRELY)
```
aws_apigatewayv2_route.get_member_filings
aws_apigatewayv2_integration.get_member_filings
aws_apigatewayv2_route.get_member_transactions
aws_apigatewayv2_integration.get_member_transactions
aws_apigatewayv2_route.get_member_assets
aws_apigatewayv2_integration.get_member_assets
```
**Already defined in**: api_lambdas.tf
- get_member_filings
- get_member_transactions
- get_member_assets

---

### 3. api_gateway_transactions.tf (DELETE ENTIRELY)
Inspect file first for actual content. Likely contains single route duplicated in api_lambdas.tf

---

### 4. api_costs_route.tf (DELETE ENTIRELY)
```
aws_apigatewayv2_route.??? (likely related to GET /v1/costs)
aws_apigatewayv2_integration.??? (matching integration)
```
**Already defined in**: api_lambdas.tf
- get_aws_costs → route = "GET /v1/costs"

---

### 5. api_storage_route.tf (DELETE ENTIRELY)
```
aws_apigatewayv2_route.??? (likely GET /v1/storage/{layer})
aws_apigatewayv2_integration.??? (matching integration)
```
**Already defined in**: api_lambdas.tf
- list_s3_objects → route = "GET /v1/storage/{layer}"

---

## REMOVE: Resources within Files (9 resources)

### 1. lambda_stub.tf (DELETE ENTIRE FILE)
```
aws_lambda_function.stub_handler
```

---

### 2. lambdas_analytics.tf (DELETE ENTIRE FILE - 1 function)
```
aws_lambda_function.compute_bill_trade_correlations
  - s3_key: "lambda-deployments/compute_bill_trade_correlations/function.zip" (placeholder)
  - References: aws_lambda_layer_version.congress_pandas_layer (not consistently available)
  - Purpose: Stub analytics, not in modernization plan
```

---

### 3. dynamodb.tf (REMOVE resource, keep file)
```
aws_dynamodb_table.house_fd_documents (REMOVE)
  - name: "house_fd_documents"
  - billing_mode: "PAY_PER_REQUEST"
  - hash_key: "doc_id"
  - range_key: "year"
  - Marked as: "Legacy table (keep for backward compatibility)"
  - Status: Not actively used in modernization plan
  - Impact: Verify no production systems read from this before deletion
```

---

### 4. lambdas_data_quality.tf (DELETE ENTIRE FILE - 6 resources)
```
aws_s3_object.soda_core_layer
aws_lambda_layer_version.soda_core
aws_s3_object.soda_checks
aws_s3_object.soda_configuration
aws_lambda_function.run_soda_checks
aws_cloudwatch_log_group.run_soda_checks_logs
```
**Reason**: Soda quality checks framework not in modernization plan. Use CloudWatch metrics instead.

---

### 5. lambda_congress.tf (REMOVE 1 resource, keep file)
```
aws_lambda_layer_version.congress_pandas_layer (REMOVE)
  - layer_name: "congress-pandas-pyarrow-layer"
  - description: "Custom layer with pandas 2.1.4, pyarrow 14.0.2, numpy 1.26.4 (stripped)"
  - Reason: Duplicate; use AWS-provided AWSSDKPandas layer (arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:24)
  - Referenced by: lambdas_analytics.tf (which is also being deleted)
  - Cleanup: Also update lambda_congress.tf to use AWS layer if referenced there
```

---

### 6. structured_extraction.tf (REVIEW - Currently Problematic)
```
aws_sqs_queue.structured_extraction_queue
  - name: "congress-disclosures-development-structured-extraction-queue-v2"
  - Status: Hardcoded name, should use local.name_prefix
  
aws_lambda_function.structured_extraction
  - function_name: "congress-disclosures-development-structured-extraction"
  - Status: Hardcoded name
  - Issue: Runtime = "python3.12" (inconsistent with others using python3.11)
  - Issue: Uses local filename instead of S3 deployment
  
aws_lambda_event_source_mapping.sqs_to_lambda
  - Orphaned mapping, missing proper error handling configuration
```
**Action**: Consolidate into lambda_silver_layer.tf with proper naming

---

### 7. sqs.tf (REVIEW - Potentially Remove if Step Functions Primary)
```
aws_sqs_queue.extraction_queue
  - May be used by extraction Lambda or Step Functions
  - If moving to Event-driven (Step Functions → Lambda), may not need SQS trigger
  - Status: Keep for now, review after Step Functions consolidation

aws_lambda_event_source_mapping.extraction_queue
  - Status: Potentially redundant if orchestrated via Step Functions
  - Action: Keep if Lambda still needs SQS trigger, else remove
```

---

## CONSOLIDATE: Files to Merge

### API Gateway Files (5 files → 2 files)

#### Keep: api_gateway.tf
- aws_apigatewayv2_api.congress_api (HTTP API definition)
- aws_apigatewayv2_stage.default (production stage)
- aws_cloudwatch_log_group.api_gateway (API logs)
- Status: KEEP - Core API configuration

#### Keep: api_lambdas.tf
- aws_lambda_function.api (for_each loop for all API Lambdas)
- aws_lambda_permission.api_gateway (permissions for all API Lambdas)
- aws_lambda_layer_version.api_duckdb_layer
- Local: api_lambda_config (shared configuration)
- Local: api_lambdas (map of all endpoint definitions)
- Status: KEEP - Unified Lambda creation + route definitions via locals

#### Consolidate INTO api_lambdas.tf: api_gateway_congress.tf
```
// Add to local.api_lambdas map:
"get_congress_bills"        = { route = "GET /v1/congress/bills" }
"get_congress_bill"         = { route = "GET /v1/congress/bills/{bill_id}" }
"get_bill_actions"          = { route = "GET /v1/congress/bills/{bill_id}/actions" }
"get_bill_text"             = { route = "GET /v1/congress/bills/{bill_id}/text" }
"get_bill_committees"       = { route = "GET /v1/congress/bills/{bill_id}/committees" }
"get_bill_cosponsors"       = { route = "GET /v1/congress/bills/{bill_id}/cosponsors" }
"get_bill_subjects"         = { route = "GET /v1/congress/bills/{bill_id}/subjects" }
"get_bill_summaries"        = { route = "GET /v1/congress/bills/{bill_id}/summaries" }
"get_bill_titles"           = { route = "GET /v1/congress/bills/{bill_id}/titles" }
"get_bill_amendments"       = { route = "GET /v1/congress/bills/{bill_id}/amendments" }
"get_bill_related"          = { route = "GET /v1/congress/bills/{bill_id}/related" }
"get_congress_members"      = { route = "GET /v1/congress/members" }
"get_congress_member"       = { route = "GET /v1/congress/members/{bioguide_id}" }
"get_congress_committees"   = { route = "GET /v1/congress/committees" }
"get_congress_committee"    = { route = "GET /v1/congress/committees/{chamber}/{code}" }
"get_committee_bills"       = { route = "GET /v1/congress/committees/{chamber}/{code}/bills" }
"get_committee_members"     = { route = "GET /v1/congress/committees/{chamber}/{code}/members" }
"get_committee_reports"     = { route = "GET /v1/congress/committees/{chamber}/{code}/reports" }
```

#### Consolidate INTO api_lambdas.tf: api_gateway_lobbying.tf
```
// Add to local.api_lambdas map:
"get_lobbying_filings"      = { route = "GET /v1/lobbying/filings" }
"get_lobbying_client"       = { route = "GET /v1/lobbying/clients/{client_id}" }
"get_lobbying_network"      = { route = "GET /v1/lobbying/network" }
"get_bill_lob_activity"     = { route = "GET /v1/congress/bills/{bill_id}/lobbying" }
"get_member_lob_connects"   = { route = "GET /v1/members/{bioguide_id}/lobbying" }
"get_triple_correlations"   = { route = "GET /v1/correlations/triple" }
```

#### DELETE: These 5 files
- api_gateway_assets.tf
- api_gateway_members.tf
- api_gateway_transactions.tf
- api_costs_route.tf
- api_storage_route.tf

#### MERGE & DELETE: These 2 files
- api_gateway_congress.tf (merge into api_lambdas.tf, then delete)
- api_gateway_lobbying.tf (merge into api_lambdas.tf, then delete)

---

### Lambda Files (scattered → organized)

#### Current Lambda Functions by Layer

**Bronze Layer (Ingestion)** - Currently scattered across 3 files:
```
lambda.tf (13KB):
  - aws_lambda_function.ingest_zip
  - aws_lambda_function.index_to_silver
  - aws_lambda_function.extract_document
  - aws_lambda_permission (2x for SQS/manual invoke)
  - aws_lambda_function.gold_seed
  - aws_lambda_function.gold_seed_members
  - aws_lambda_function.data_quality_validator

lambda_congress.tf (10.5KB):
  - aws_lambda_layer_version.congress_pandas_layer (DELETE)
  - aws_lambda_function.congress_fetch_entity
  - aws_lambda_event_source_mapping.congress_fetch_queue
  - aws_lambda_function.congress_orchestrator
  - aws_lambda_function.congress_bronze_to_silver
  - aws_lambda_event_source_mapping.congress_silver_queue

lambda_lobbying.tf (3KB):
  - aws_cloudwatch_log_group.lda_ingest_filings
  - aws_lambda_function.lda_ingest_filings
  - aws_lambda_permission.allow_manual_invoke_lda_ingest
```

**Action**: Create `lambda_bronze_layer.tf` and move:
- ingest_zip
- index_to_silver
- extract_document
- congress_fetch_entity
- congress_orchestrator
- congress_bronze_to_silver
- lda_ingest_filings
- Plus their associated permissions, log groups, and event source mappings

---

**Silver Layer (Extraction)** - Scattered across 2 files:
```
structured_extraction.tf (38 lines):
  - aws_sqs_queue.structured_extraction_queue
  - aws_lambda_function.structured_extraction
  - aws_lambda_event_source_mapping.sqs_to_lambda
  
structured_code_extraction.tf (5.4KB):
  - Needs inspection for actual content
```

**Action**: Create `lambda_silver_layer.tf` and consolidate both

---

**Gold Layer (Transformations)** - Already organized:
```
lambdas_gold_transformations.tf (14.5KB):
  - aws_lambda_function.build_dim_members
  - aws_cloudwatch_log_group.build_dim_members_v2_logs
  - aws_lambda_function.build_dim_assets
  - aws_cloudwatch_log_group.build_dim_assets_logs
  - aws_lambda_function.build_dim_bills
  - (+ more below line 150, truncated in read)
```

**Action**: Keep as-is, rename to `lambdas_gold_layer.tf` for consistency

---

**API Layer** - Already organized:
```
api_lambdas.tf (213 lines):
  - aws_lambda_layer_version.api_duckdb_layer
  - aws_lambda_function.api (for_each over 40+ endpoints)
  - aws_lambda_permission.api_gateway (for_each)
```

**Action**: KEEP as-is

---

**Orchestration** - Lambda functions for Step Functions:
```
step_functions.tf (Contains mixed concerns):
  - aws_iam_role.step_functions_role
  - aws_iam_role_policy.step_functions_policy
  - aws_sfn_state_machine.house_fd_pipeline
  - aws_sfn_state_machine.congress_pipeline
  - aws_sfn_state_machine.lobbying_pipeline
  - aws_sfn_state_machine.cross_dataset_correlation
  - aws_sfn_state_machine.congress_data_platform
  - aws_cloudwatch_log_group.step_functions_logs
  - aws_cloudwatch_log_group.publish_pipeline_metrics
  - aws_lambda_function.publish_pipeline_metrics ← MOVE
  - aws_lambda_function.check_house_fd_updates ← MOVE
  - aws_lambda_function.check_lobbying_updates ← MOVE
  - aws_lambda_function.check_congress_updates ← MOVE
  - aws_cloudwatch_log_group.check_house_fd_updates_logs ← MOVE
  - aws_cloudwatch_log_group.check_lobbying_updates_logs ← MOVE
  - aws_cloudwatch_log_group.check_congress_updates_logs ← MOVE
```

**Action**: Create `lambda_orchestration.tf` and move the 4 Lambda functions + their log groups

---

### SQS Queues (scattered → consolidated)

**Current distribution**:
```
sqs.tf (107 lines):
  - aws_sqs_queue.extraction_dlq
  - aws_sqs_queue.extraction_queue
  - aws_lambda_event_source_mapping.extraction_queue
  - aws_cloudwatch_metric_alarm.dlq_messages

sqs_congress.tf (141 lines):
  - aws_sqs_queue.congress_fetch_dlq
  - aws_sqs_queue.congress_fetch_queue
  - aws_lambda_event_source_mapping.congress_fetch_queue
  - aws_sqs_queue.congress_silver_dlq
  - aws_sqs_queue.congress_silver_queue
  - aws_lambda_event_source_mapping.congress_silver_queue

sqs_lobbying.tf (48 lines):
  - aws_sqs_queue.lda_bill_extraction_queue
  - aws_sqs_queue.lda_bill_extraction_dlq

structured_extraction.tf (7 lines - inline):
  - aws_sqs_queue.structured_extraction_queue (inline)
```

**Action**: Create `sqs_queues.tf` with consolidated definitions:
```
# Extraction Pipeline
aws_sqs_queue.extraction_queue
aws_sqs_queue.extraction_dlq
aws_lambda_event_source_mapping.extraction_queue
aws_cloudwatch_metric_alarm.dlq_messages

# Congress Pipeline
aws_sqs_queue.congress_fetch_queue
aws_sqs_queue.congress_fetch_dlq
aws_lambda_event_source_mapping.congress_fetch_queue

aws_sqs_queue.congress_silver_queue
aws_sqs_queue.congress_silver_dlq
aws_lambda_event_source_mapping.congress_silver_queue

# Lobbying Pipeline
aws_sqs_queue.lda_bill_extraction_queue
aws_sqs_queue.lda_bill_extraction_dlq

# Structured Extraction
aws_sqs_queue.structured_extraction_queue
```

---

## CREATE: Missing Resources

### 1. api_authorizer.tf (NEW FILE)
```
# Lambda Authorizer for API Gateway
aws_iam_role.api_authorizer_role
aws_iam_role_policy.api_authorizer_policy
aws_lambda_function.api_authorizer
aws_cloudwatch_log_group.api_authorizer_logs
aws_apigatewayv2_authorizer.api_jwt_authorizer

# Purpose: JWT validation from api_keys DynamoDB table
# Integration: Check token against api_keys.api_key_hash
# Cache: 300 seconds
```

---

### 2. cloudwatch_logs.tf (NEW FILE)
Consolidate log groups from:
- api_gateway.tf: aws_cloudwatch_log_group.api_gateway
- lambda.tf: aws_cloudwatch_log_group.ingest_zip, index_to_silver, extract_document, gold_seed, gold_seed_members, data_quality_validator
- lambda_congress.tf: aws_cloudwatch_log_group.congress_fetch_lambda, congress_orchestrator_lambda, congress_silver_lambda
- lambda_lobbying.tf: aws_cloudwatch_log_group.lda_ingest_filings
- lambdas_gold_transformations.tf: build_dim_members_v2_logs, build_dim_assets_logs, etc.
- step_functions.tf: step_functions_logs, publish_pipeline_metrics, check_house_fd_updates_logs, etc.
- structured_extraction.tf: (if any)
- structured_code_extraction.tf: (if any)

Organize into logical sections:
```
### Ingestion Layer
### Extraction Layer
### Gold Layer
### API Layer
### Step Functions & Orchestration
```

---

### 3. cloudwatch_dashboards.tf (NEW FILE)
```
aws_cloudwatch_dashboard.main_pipeline_dashboard
  - Pipeline execution status (Step Functions metrics)
  - Lambda invocation counts, durations, errors
  - SQS queue depth + messages processed
  - S3 data volume by layer (Bronze/Silver/Gold)
  - API Gateway request rate, errors, latency
  - DynamoDB reads/writes
  - Extraction success rate
  - Data quality metrics

aws_cloudwatch_dashboard.api_performance
  - API endpoint latency (by route)
  - API error rates (4xx, 5xx)
  - Authentication successes/failures
  - Cache hit/miss ratios
  - Top slowest endpoints
```

---

## REVIEW: Potentially Conditional Resources

### Lambda Packaging
**File**: lambda_packaging.tf (799 lines)
- Status: Contains null_resource.package_lambdas
- Purpose: Package Lambda deployment zips
- Should trigger: Before Lambda functions
- Status: Keep, needed for CI/CD

### Variables
**File**: variables.tf (7.9 KB) + variables_congress.tf (7.6 KB)
**Action**: Consolidate into single variables.tf, remove variables_congress.tf
- Congress-specific variables should be in main variables.tf with conditional logic

### Budget Alerts
**File**: budgets.tf (8.2 KB)
**Status**: Cost monitoring, keep as-is

### IAM
**File**: iam.tf (6.9 KB)
**Status**: Shared Lambda execution role + policies, keep as-is
**Note**: Create separate role for api_authorizer in api_authorizer.tf

### Miscellaneous
- github_oidc.tf: GitHub Actions OIDC, keep
- bucket_policy.tf: S3 bucket policy, keep
- seeds.tf: Seed data, keep
- state_backend.tf: Terraform state backend, keep
- backend.tf: Backend configuration, keep
- cloudwatch_congress.tf: Congress-specific metrics, consolidate into cloudwatch_logs.tf

---

## SUMMARY TABLE

| Action | Count | Files |
|--------|-------|-------|
| **DELETE** | 5 | api_gateway_assets.tf, api_gateway_members.tf, api_gateway_transactions.tf, api_costs_route.tf, api_storage_route.tf |
| **DELETE** | 3 | lambda_stub.tf, lambdas_analytics.tf, lambdas_data_quality.tf |
| **MERGE & DELETE** | 2 | api_gateway_congress.tf, api_gateway_lobbying.tf → api_lambdas.tf |
| **CONSOLIDATE** | 1 | lambda.tf + lambda_congress.tf + lambda_lobbying.tf → lambda_bronze_layer.tf |
| **CONSOLIDATE** | 1 | structured_extraction.tf + structured_code_extraction.tf → lambda_silver_layer.tf |
| **CONSOLIDATE** | 1 | sqs.tf + sqs_congress.tf + sqs_lobbying.tf + structured_extraction.tf → sqs_queues.tf |
| **CONSOLIDATE** | 1 | step_functions.tf lambdas → lambda_orchestration.tf |
| **CREATE** | 3 | api_authorizer.tf, cloudwatch_logs.tf, cloudwatch_dashboards.tf |
| **CONSOLIDATE** | 2 | variables.tf + variables_congress.tf |
| **CONSOLIDATE** | 1 | cloudwatch.tf + cloudwatch_congress.tf → cloudwatch_logs.tf |

**Total changes**: ~19 files refactored
**Final file count**: ~24 files (from 43)
