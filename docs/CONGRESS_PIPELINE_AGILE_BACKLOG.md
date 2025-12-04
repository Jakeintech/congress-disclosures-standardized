# Congress.gov Pipeline - Agile Backlog (Fully Groomed)

**Epic**: Implement Congress.gov API Integration with Medallion Architecture

**Epic Goal**: Enable point-in-time analysis of Congressional legislative activity correlated with financial disclosures, using Bronze → Silver → Gold medallion architecture aligned with existing FD pipeline patterns.

**Epic Value**: Researchers, journalists, and transparency advocates can analyze member trading behavior in context of legislative activity (bill sponsorship, voting, committee work) with reproducible, historical accuracy.

**Epic Acceptance Criteria**:
- ✅ Congress 118 data (2023-2025) fully ingested and queryable
- ✅ SCD Type 2 member history tracks party/district changes
- ✅ Gold analytics tables enable FD-to-legislation correlation queries
- ✅ API endpoints return Congress data with <500ms p95 latency
- ✅ Daily incremental sync via GitHub Actions
- ✅ Pipeline integrity validated (Bronze counts match API, no duplicate processing)

---

## FEATURE 1: Infrastructure & Bronze Layer Foundation

**Feature Goal**: Establish AWS infrastructure (Lambdas, SQS, S3 structure) and implement Bronze layer raw data ingestion from Congress.gov API.

**Feature Value**: Provides fault-tolerant, rate-limited API ingestion with raw JSON preservation for audit/replay.

**Feature Dependencies**: None (greenfield)

**Estimated Effort**: 13 story points (8-10 days)

---

### STORY 1.1: S3 Bucket Structure & Terraform Base Configuration

**Story Goal**: Define S3 Hive-partitioned prefixes for Bronze layer and create Terraform configurations for new resources.

**User Story**: As a data engineer, I need a consistent S3 structure for Congress.gov data so that Bronze/Silver/Gold layers follow the same patterns as FD pipeline.

**Acceptance Criteria**:
- ✅ S3 prefix structure documented and created (Bronze: `bronze/congress/{entity_type}/...`)
- ✅ Terraform variables defined for Congress.gov API key (SSM Parameter Store)
- ✅ Terraform module structure mirrors existing FD Lambdas (`infra/terraform/congress_lambdas.tf`)
- ✅ S3 bucket policies allow Lambda read/write to Congress prefixes
- ✅ CloudWatch log groups created for new Lambdas (30-day retention)

**Effort**: 3 story points

---

#### TASK 1.1.1: Design and Document S3 Bronze Structure

**Description**: Create detailed S3 prefix schema with Hive partitioning for all Congress.gov entities.

**DoD**:
- ✅ Markdown file created: `docs/CONGRESS_S3_SCHEMA.md` with complete prefix tree
- ✅ Partitioning strategy documented for each entity type (e.g., `congress=118`, `ingest_date=YYYY-MM-DD`)
- ✅ Example file paths provided for: member, bill, bill_actions, amendment, committee, house_vote
- ✅ Compression format specified (gzip) and file naming convention defined
- ✅ Metadata schema documented (what goes in filename vs object metadata)

**Subtasks**:
1. Research existing FD Bronze structure (`bronze/house/financial/`)
2. Map Congress.gov endpoints to entity types
3. Define partition keys per entity (balance object count vs scan cost)
4. Document in `docs/CONGRESS_S3_SCHEMA.md`
5. Peer review with FD pipeline patterns

**Effort**: 1 story point

---

#### TASK 1.1.2: Create Terraform Variable Definitions

**Description**: Add Terraform variables for Congress.gov API configuration.

**DoD**:
- ✅ File created: `infra/terraform/variables_congress.tf`
- ✅ Variables defined: `congress_api_key_ssm_path`, `congress_api_base_url`, `congress_api_rate_limit`
- ✅ Default values set for dev environment
- ✅ `.env.example` updated with Congress.gov API key placeholder
- ✅ `terraform validate` passes

**Subtasks**:
1. Create `infra/terraform/variables_congress.tf`
2. Add `CONGRESS_API_KEY` to `.env.example`
3. Create SSM parameter manually: `aws ssm put-parameter --name /congress-disclosures/dev/congress-api-key --value YOUR_KEY --type SecureString`
4. Reference in Lambda environment variables
5. Run `terraform validate`

**Effort**: 1 story point

---

#### TASK 1.1.3: Create S3 Prefixes and Bucket Policy Updates

**Description**: Ensure S3 bucket allows Lambda IAM roles to write to Congress prefixes.

**DoD**:
- ✅ Bucket policy updated in `infra/terraform/s3.tf` to allow Congress Lambda writes
- ✅ Test prefixes created manually: `bronze/congress/member/`, `bronze/congress/bill/`
- ✅ IAM policy document allows `s3:PutObject`, `s3:GetObject` on `bronze/congress/*`
- ✅ `terraform plan` shows policy update (no bucket recreation)
- ✅ Test write with AWS CLI succeeds: `aws s3 cp test.json s3://congress-disclosures-standardized/bronze/congress/test.json`

**Subtasks**:
1. Modify `infra/terraform/s3.tf` bucket policy
2. Add IAM policy statement for Congress Lambda role
3. Run `terraform plan` and verify
4. Manually create test prefixes
5. Test write with CLI

**Effort**: 1 story point

---

### STORY 1.2: SQS Queues and Dead Letter Queues

**Story Goal**: Create SQS queues for Congress API ingestion and Silver transformation workflows.

**User Story**: As a data engineer, I need fault-tolerant SQS queues so that API fetch failures retry automatically and Bronze-to-Silver transforms are decoupled.

**Acceptance Criteria**:
- ✅ 2 SQS queues created: `congress-api-fetch-queue`, `congress-bronze-to-silver-queue`
- ✅ 2 DLQs created with 3-retry policy: `congress-api-fetch-dlq`, `congress-bronze-to-silver-dlq`
- ✅ Queue attributes set: `VisibilityTimeout=300s`, `MessageRetentionPeriod=4days`
- ✅ CloudWatch alarms created for DLQ message count > 5
- ✅ IAM policies allow Lambdas to send/receive messages
- ✅ Makefile targets added: `make check-congress-queue`, `make purge-congress-queue`

**Effort**: 2 story points

---

#### TASK 1.2.1: Create SQS Queue Terraform Configuration

**Description**: Define SQS queues in Terraform with proper retry/DLQ configuration.

**DoD**:
- ✅ File created: `infra/terraform/sqs_congress.tf`
- ✅ 4 queue resources defined (2 primary, 2 DLQ)
- ✅ `redrive_policy` configured for 3 retries
- ✅ `visibility_timeout` set to 300s (Lambda timeout + buffer)
- ✅ Tags applied: `Project=congress-disclosures`, `Component=ingestion`
- ✅ `terraform apply` succeeds, queues visible in AWS Console

**Subtasks**:
1. Create `infra/terraform/sqs_congress.tf`
2. Define `aws_sqs_queue` resources for primary queues
3. Define DLQ resources with `message_retention_seconds=1209600` (14 days)
4. Configure redrive policy: `maxReceiveCount=3`
5. Apply and verify in AWS Console

**Effort**: 1 story point

---

#### TASK 1.2.2: Create CloudWatch Alarms for DLQs

**Description**: Set up CloudWatch alarms to alert when messages land in DLQ.

**DoD**:
- ✅ File created: `infra/terraform/cloudwatch_congress.tf`
- ✅ 2 alarms defined: one per DLQ
- ✅ Alarm triggers when `ApproximateNumberOfMessagesVisible > 5` for 5 minutes
- ✅ Alarm actions: log to CloudWatch (email/Slack integration optional)
- ✅ Alarms visible in AWS Console, test triggered manually
- ✅ Documentation added to `docs/MONITORING.md` on how to check DLQs

**Subtasks**:
1. Create `infra/terraform/cloudwatch_congress.tf`
2. Define `aws_cloudwatch_metric_alarm` resources
3. Configure metric: `ApproximateNumberOfMessagesVisible`
4. Set threshold and evaluation period
5. Test alarm by sending message to DLQ
6. Document in `docs/MONITORING.md`

**Effort**: 1 story point

---

### STORY 1.3: Lambda Function - congress_api_fetch_entity

**Story Goal**: Implement Lambda function that fetches individual entities from Congress.gov API with rate limiting and retry logic.

**User Story**: As a data pipeline, I need a Lambda that fetches Congress.gov entities (member, bill, vote) from SQS messages, handles rate limits gracefully, and uploads raw JSON to Bronze.

**Acceptance Criteria**:
- ✅ Lambda function `congress_api_fetch_entity` deployed
- ✅ SQS trigger configured to `congress-api-fetch-queue` with batch size 10
- ✅ Rate limiting implemented: max 1000 req/hr (AWS API Gateway throttling compatible)
- ✅ Exponential backoff on 429 (rate limit) and 5xx errors
- ✅ Raw API JSON uploaded to Bronze with metadata: `ingest_timestamp`, `api_url`, `http_status`
- ✅ Success/failure metrics logged to CloudWatch
- ✅ Integration test passes: fetch 10 members, verify Bronze files exist

**Effort**: 5 story points

---

#### TASK 1.3.1: Create Shared Congress API Client Library

**Description**: Build reusable Python library for Congress.gov API interactions.

**DoD**:
- ✅ File created: `ingestion/lib/congress_api_client.py`
- ✅ Class `CongressAPIClient` with methods: `get_member()`, `get_bill()`, `get_vote()`, `list_bills()`, etc.
- ✅ Rate limiting implemented using `ratelimit` library (1000 req/hr)
- ✅ Retry logic with exponential backoff (max 3 retries, delays: 1s, 2s, 4s)
- ✅ Handles pagination: returns generator for list endpoints
- ✅ Unit tests written: `tests/unit/test_congress_api_client.py`
- ✅ Docstrings (Google style) for all public methods

**Subtasks**:
1. Create `ingestion/lib/congress_api_client.py`
2. Implement `CongressAPIClient.__init__()` with API key from env
3. Implement `_make_request()` with rate limit decorator
4. Implement retry logic using `tenacity` library
5. Implement pagination helper: `_paginate(endpoint, params)`
6. Implement entity-specific methods: `get_member()`, `get_bill()`, etc.
7. Write unit tests with mocked responses
8. Add docstrings

**Effort**: 3 story points

---

#### TASK 1.3.2: Create Lambda Handler for Entity Fetch

**Description**: Implement Lambda handler that processes SQS messages and fetches entities.

**DoD**:
- ✅ File created: `ingestion/lambdas/congress_api_fetch_entity/handler.py`
- ✅ Function `lambda_handler(event, context)` implemented
- ✅ Parses SQS message: `{'entity_type': 'member', 'entity_id': 'A000360', 'endpoint': '/member/A000360'}`
- ✅ Calls `CongressAPIClient` to fetch entity
- ✅ Uploads raw JSON to Bronze S3 with key pattern: `bronze/congress/{entity_type}/ingest_date={date}/{entity_id}.json.gz`
- ✅ Adds S3 object metadata: `ingest-timestamp`, `api-url`, `http-status`
- ✅ Returns SQS partial batch failure for failed items
- ✅ Logs success/failure to CloudWatch with structured JSON

**Subtasks**:
1. Create `ingestion/lambdas/congress_api_fetch_entity/handler.py`
2. Implement `lambda_handler()` with SQS batch processing loop
3. Parse message body JSON
4. Call `CongressAPIClient` method based on `entity_type`
5. Compress JSON with gzip
6. Upload to S3 with metadata using `s3_utils.py`
7. Implement partial batch failure return
8. Add CloudWatch structured logging

**Effort**: 2 story points

---

#### TASK 1.3.3: Package and Deploy Lambda with Dependencies

**Description**: Create Lambda deployment package with dependencies and deploy via Terraform.

**DoD**:
- ✅ File created: `ingestion/lambdas/congress_api_fetch_entity/requirements.txt`
- ✅ Dependencies listed: `requests`, `ratelimit`, `tenacity`, `boto3`
- ✅ Makefile target added: `make package-congress-fetch`
- ✅ Terraform resource defined: `aws_lambda_function.congress_api_fetch_entity`
- ✅ Lambda configuration: Python 3.11, 512 MB memory, 300s timeout
- ✅ Environment variables set: `CONGRESS_API_KEY` (from SSM), `S3_BUCKET_NAME`, `LOG_LEVEL`
- ✅ SQS trigger configured with batch size 10, max concurrency 5
- ✅ `terraform apply` succeeds, Lambda visible in AWS Console

**Subtasks**:
1. Create `requirements.txt` with dependencies
2. Create Makefile target `package-congress-fetch` (pattern: existing `package-extract`)
3. Create Terraform resource in `infra/terraform/lambda_congress.tf`
4. Configure environment variables with SSM parameter lookup
5. Configure SQS event source mapping
6. Run `make package-congress-fetch && terraform apply`
7. Verify in AWS Console

**Effort**: 1 story point (reuse existing patterns)

---

#### TASK 1.3.4: Write Integration Test for Entity Fetch

**Description**: Test end-to-end fetch workflow with real API (dev environment only).

**DoD**:
- ✅ File created: `tests/integration/test_congress_fetch.py`
- ✅ Test function: `test_fetch_member_to_bronze()` that:
  - Sends SQS message with member entity
  - Waits for Lambda processing (polls S3)
  - Verifies Bronze JSON exists and is valid
  - Verifies S3 metadata is correct
- ✅ Test marked with `@pytest.mark.integration`
- ✅ Test passes in CI (GitHub Actions with AWS credentials)
- ✅ Test includes cleanup (deletes test S3 objects)

**Subtasks**:
1. Create `tests/integration/test_congress_fetch.py`
2. Write helper: `send_fetch_message(entity_type, entity_id)`
3. Write helper: `wait_for_bronze_file(s3_key, timeout=60)`
4. Implement test: send message → wait → verify
5. Add cleanup in `pytest` fixture
6. Run test locally: `pytest tests/integration/test_congress_fetch.py -v`
7. Verify in CI

**Effort**: 1 story point

---

### STORY 1.4: Lambda Function - congress_api_ingest_orchestrator

**Story Goal**: Implement orchestrator Lambda that enumerates entities to fetch and queues them to SQS.

**User Story**: As a data pipeline operator, I need a Lambda that orchestrates bulk ingestion (e.g., "fetch all Congress 118 bills") by queuing individual fetch jobs to SQS.

**Acceptance Criteria**:
- ✅ Lambda function `congress_api_ingest_orchestrator` deployed
- ✅ Accepts payload: `{"entity_type": "bill", "congress": 118, "mode": "full"}`
- ✅ Queries Congress.gov list endpoint (e.g., `/bill?congress=118`) with pagination
- ✅ Queues individual fetch jobs to `congress-api-fetch-queue` in batches of 10
- ✅ Handles pagination (max 250 items/page): continues until all pages processed
- ✅ Logs progress: "Queued 1500/5000 bills to fetch queue"
- ✅ Manual invocation test: `make ingest-congress-bills CONGRESS=118` triggers Lambda

**Effort**: 3 story points

---

#### TASK 1.4.1: Implement Orchestrator Lambda Handler

**Description**: Create Lambda that paginates through list endpoints and queues fetch jobs.

**DoD**:
- ✅ File created: `ingestion/lambdas/congress_api_ingest_orchestrator/handler.py`
- ✅ Function `lambda_handler(event, context)` parses: `entity_type`, `congress`, `mode`
- ✅ Calls `CongressAPIClient.list_bills(congress=118)` with pagination
- ✅ Queues messages to SQS in batches of 10 using `boto3.client('sqs').send_message_batch()`
- ✅ Logs progress every 100 items: "Queued 300/5000 bills"
- ✅ Returns summary: `{"queued_count": 5000, "duration_seconds": 45}`
- ✅ Handles `mode=incremental`: fetches only items updated since last run (uses DynamoDB state table or S3 marker file)

**Subtasks**:
1. Create handler file
2. Implement pagination loop using `CongressAPIClient`
3. Implement SQS batch queuing helper: `queue_fetch_jobs(items, queue_url)`
4. Add progress logging
5. Implement incremental mode: read last ingest timestamp from S3 marker file
6. Return summary JSON
7. Add error handling for pagination failures

**Effort**: 2 story points

---

#### TASK 1.4.2: Create State Management for Incremental Mode

**Description**: Implement mechanism to track last successful ingest timestamp per entity type.

**DoD**:
- ✅ S3 marker files used: `bronze/congress/_state/{entity_type}_last_ingest.json`
- ✅ Marker file format: `{"last_ingest_date": "2025-12-04T10:30:00Z", "last_item_count": 5000}`
- ✅ Orchestrator reads marker before querying API
- ✅ Orchestrator writes marker after successful ingest
- ✅ Handles missing marker (first run): uses default start date (2023-01-01 for Congress 118)
- ✅ Unit test: `test_state_read_write()` verifies read/write logic

**Subtasks**:
1. Create helper: `read_last_ingest_state(entity_type) -> dict`
2. Create helper: `write_last_ingest_state(entity_type, timestamp, count)`
3. Integrate into orchestrator handler
4. Handle missing marker (first run)
5. Write unit test
6. Test manually: invoke orchestrator twice, verify incremental works

**Effort**: 1 story point

---

#### TASK 1.4.3: Add Makefile Target and Manual Invocation Script

**Description**: Make it easy to trigger bulk ingestion manually.

**DoD**:
- ✅ Makefile target added: `make ingest-congress-bills CONGRESS=118`
- ✅ Target invokes Lambda with payload: `{"entity_type": "bill", "congress": 118, "mode": "full"}`
- ✅ Script created: `scripts/invoke_congress_orchestrator.py` for programmatic invocation
- ✅ Script accepts CLI args: `--entity-type`, `--congress`, `--mode`
- ✅ Script prints progress and summary from Lambda response
- ✅ Documentation added to `README.md` under "Congress.gov Ingestion" section

**Subtasks**:
1. Add Makefile target using `aws lambda invoke`
2. Create `scripts/invoke_congress_orchestrator.py`
3. Add argparse CLI: `--entity-type`, `--congress`, `--mode`
4. Call `boto3.client('lambda').invoke()` with payload
5. Print Lambda response JSON
6. Document in `README.md`
7. Test manually: `make ingest-congress-bills CONGRESS=118`

**Effort**: 1 story point

---

---

## FEATURE 2: Silver Layer - Normalized Schema & CDC

**Feature Goal**: Transform Bronze raw JSON into queryable Silver Parquet tables with SCD Type 2 history for members and upsert logic for all entities.

**Feature Value**: Enables fast SQL-like queries on Congress data with point-in-time accuracy (track member party changes, bill status updates).

**Feature Dependencies**: Feature 1 (Bronze layer must be populated)

**Estimated Effort**: 13 story points (8-10 days)

---

### STORY 2.1: Define Silver Schema and Create Parquet Writer Utility

**Story Goal**: Document Silver table schemas and create reusable Parquet upsert utilities.

**User Story**: As a data engineer, I need clear Silver table schemas (columns, types, partitions) and utilities to upsert Parquet files so that Bronze → Silver transforms are consistent.

**Acceptance Criteria**:
- ✅ Documentation created: `docs/CONGRESS_SILVER_SCHEMA.md` with all table schemas
- ✅ Utility created: `ingestion/lib/congress_parquet_writer.py` with `upsert_parquet()` function
- ✅ Schemas defined for: `dim_member`, `dim_bill`, `bill_actions`, `bill_cosponsors`, `house_vote_members`, etc.
- ✅ Partition keys documented per table (e.g., `congress`, `bill_type`, `chamber`)
- ✅ Unit tests verify upsert logic: dedupe on PK, update if `source_last_modified` differs

**Effort**: 3 story points

---

#### TASK 2.1.1: Document Silver Schema in Markdown

**Description**: Create comprehensive schema documentation for all Silver tables.

**DoD**:
- ✅ File created: `docs/CONGRESS_SILVER_SCHEMA.md`
- ✅ Schemas documented for 10+ tables with:
  - Table name and description
  - Primary key columns
  - All columns with data types (Parquet types: `int64`, `string`, `timestamp`, `boolean`)
  - Partition keys
  - Example row (JSON format)
- ✅ SCD Type 2 schema explained for `dim_member` with `effective_date`, `end_date`, `is_current` columns
- ✅ Index of tables included (linked list)

**Subtasks**:
1. Create `docs/CONGRESS_SILVER_SCHEMA.md`
2. Document `dim_member` schema (SCD Type 2)
3. Document `dim_bill` schema
4. Document fact/detail tables: `bill_actions`, `bill_cosponsors`, `bill_committees`, `bill_subjects`, `bill_titles`
5. Document `house_vote_members` schema
6. Document `dim_committee`, `dim_amendment` schemas
7. Add example rows for each table
8. Peer review for completeness

**Effort**: 2 story points

---

#### TASK 2.1.2: Create Parquet Upsert Utility

**Description**: Build reusable library for upserting Parquet files with CDC logic.

**DoD**:
- ✅ File created: `ingestion/lib/congress_parquet_writer.py`
- ✅ Function `upsert_parquet(bucket, s3_key, new_df, pk_columns, update_column='source_last_modified')` implemented
- ✅ Logic:
  1. Read existing Parquet (if exists) into DataFrame
  2. Remove old rows where PK matches new rows
  3. Concat old + new DataFrames
  4. Write back to S3 (atomic replace)
- ✅ Handles schema evolution: adds missing columns with nulls
- ✅ Validates types match before concat
- ✅ Unit test: `test_upsert_parquet_new_records()`, `test_upsert_parquet_updates()`
- ✅ Docstring with usage examples

**Subtasks**:
1. Create `ingestion/lib/congress_parquet_writer.py`
2. Implement `upsert_parquet()` function
3. Handle case: S3 key doesn't exist (first write)
4. Handle case: existing Parquet, dedupe on PK
5. Handle schema evolution: align columns
6. Add type validation
7. Write unit tests with pytest fixtures
8. Add docstring with examples

**Effort**: 2 story points

---

#### TASK 2.1.3: Create SCD Type 2 Handler for dim_member

**Description**: Implement specialized logic for tracking member history with effective dates.

**DoD**:
- ✅ File created: `ingestion/lib/congress_cdc_handler.py`
- ✅ Function `apply_scd_type2(bucket, s3_key, new_member_df, pk='bioguide_id')` implemented
- ✅ Logic:
  1. Read existing member history
  2. For each new member record, check if attributes changed (party, district, etc.)
  3. If changed: close old record (`end_date=today`, `is_current=False`), insert new record
  4. If no change: skip
  5. If new member: insert with `effective_date=today`, `is_current=True`
- ✅ Generates surrogate key: `member_sk` (UUID or sequential int)
- ✅ Unit test: `test_scd_type2_party_change()` verifies party switch creates 2 records
- ✅ Docstring explains SCD Type 2 pattern

**Subtasks**:
1. Create `ingestion/lib/congress_cdc_handler.py`
2. Implement `apply_scd_type2()` function
3. Implement change detection logic (compare all tracked columns)
4. Implement close-and-insert logic
5. Generate surrogate keys with `uuid.uuid4()`
6. Write unit tests for party change, district change, new member scenarios
7. Add docstring

**Effort**: 2 story points

---

### STORY 2.2: Lambda Function - congress_bronze_to_silver (Members)

**Story Goal**: Transform Bronze member JSON to Silver `dim_member` Parquet with SCD Type 2 history.

**User Story**: As a data pipeline, I need a Lambda that reads Bronze member JSON, flattens it, applies SCD Type 2 logic, and writes to Silver Parquet so that member history is queryable.

**Acceptance Criteria**:
- ✅ Lambda function `congress_bronze_to_silver` deployed (supports multiple entity types via message routing)
- ✅ S3 trigger or SQS trigger from Bronze writes
- ✅ For entity_type=member: parses JSON, extracts fields (bioguide_id, name, party, state, district, term dates)
- ✅ Applies SCD Type 2 logic using `congress_cdc_handler.py`
- ✅ Writes to `silver/congress/dim_member/chamber={chamber}/is_current={true|false}/part-{uuid}.parquet`
- ✅ Logs success/failure with member count
- ✅ Integration test: upload member JSON to Bronze → Lambda processes → verify Silver Parquet exists

**Effort**: 5 story points

---

#### TASK 2.2.1: Create Schema Mapper for Member JSON

**Description**: Build utility to map Congress.gov member API response to Silver schema.

**DoD**:
- ✅ File created: `ingestion/lib/congress_schema_mappers.py`
- ✅ Function `map_member_to_silver(bronze_json: dict) -> dict` implemented
- ✅ Extracts fields: `bioguide_id`, `first_name`, `last_name`, `party`, `state`, `district`, `chamber`, `terms` (nested)
- ✅ Flattens current term: extracts `start_year`, `end_year` from latest term
- ✅ Handles missing fields gracefully (defaults to None)
- ✅ Returns dict matching `dim_member` Silver schema
- ✅ Unit test: `test_map_member_json()` with real API response fixture

**Subtasks**:
1. Create `ingestion/lib/congress_schema_mappers.py`
2. Download sample member JSON from Congress.gov API
3. Implement `map_member_to_silver()` function
4. Extract fields with safe dict access (`.get()`)
5. Flatten nested `terms` array (get latest term)
6. Write unit test with JSON fixture in `tests/fixtures/member_response.json`
7. Run test

**Effort**: 2 story points

---

#### TASK 2.2.2: Implement Lambda Handler for Member Transform

**Description**: Create Lambda handler that processes Bronze member JSON and writes Silver Parquet.

**DoD**:
- ✅ File created: `ingestion/lambdas/congress_bronze_to_silver/handler.py`
- ✅ Function `lambda_handler(event, context)` handles SQS messages with: `{"entity_type": "member", "bronze_s3_key": "bronze/congress/member/..."}`
- ✅ Downloads Bronze JSON from S3
- ✅ Calls `map_member_to_silver()` to flatten
- ✅ Converts to Pandas DataFrame
- ✅ Calls `apply_scd_type2()` to write Silver Parquet with history
- ✅ Logs: "Processed 1 member, 2 history records written"
- ✅ Handles batch of 10 messages (SQS batch)
- ✅ Returns partial batch failure for errors

**Subtasks**:
1. Create handler file
2. Implement message parsing
3. Download Bronze JSON using `s3_utils.py`
4. Call schema mapper
5. Convert to DataFrame
6. Call SCD Type 2 handler
7. Add structured logging
8. Implement partial batch failure
9. Add error handling (invalid JSON, S3 errors)

**Effort**: 2 story points

---

#### TASK 2.2.3: Package and Deploy Lambda

**Description**: Deploy congress_bronze_to_silver Lambda with dependencies.

**DoD**:
- ✅ File created: `ingestion/lambdas/congress_bronze_to_silver/requirements.txt`
- ✅ Dependencies: `pandas`, `pyarrow`, `boto3`
- ✅ Makefile target: `make package-congress-silver`
- ✅ Terraform resource: `aws_lambda_function.congress_bronze_to_silver`
- ✅ Lambda config: Python 3.11, 1024 MB memory, 300s timeout
- ✅ SQS trigger: `congress-bronze-to-silver-queue`, batch size 10
- ✅ Environment variables: `S3_BUCKET_NAME`, `LOG_LEVEL`
- ✅ Deployed via `terraform apply`

**Subtasks**:
1. Create requirements.txt
2. Create Makefile target (reuse pattern)
3. Create Terraform resource in `lambda_congress.tf`
4. Configure SQS event source mapping
5. Run `make package-congress-silver && terraform apply`
6. Verify in AWS Console

**Effort**: 1 story point

---

#### TASK 2.2.4: Write Integration Test for Member Transform

**Description**: Test end-to-end Bronze → Silver transform for members.

**DoD**:
- ✅ File created: `tests/integration/test_congress_silver_member.py`
- ✅ Test uploads sample member JSON to Bronze
- ✅ Sends SQS message to trigger Lambda
- ✅ Polls Silver S3 for Parquet file (timeout 60s)
- ✅ Reads Parquet and verifies: bioguide_id, party, is_current=True
- ✅ Test scenario 2: upload updated member JSON (party change), verify 2 records in history
- ✅ Test marked with `@pytest.mark.integration`
- ✅ Cleanup in fixture

**Subtasks**:
1. Create test file
2. Create fixture: sample member JSON
3. Write test: upload → trigger → verify
4. Write test: party change scenario
5. Add cleanup
6. Run locally and in CI

**Effort**: 1 story point

---

### STORY 2.3: Lambda Handler Extensions for Bills, Votes, Committees

**Story Goal**: Extend `congress_bronze_to_silver` Lambda to handle bill, vote, and committee entity types.

**User Story**: As a data pipeline, I need Bronze → Silver transforms for bills, votes, and committees so that all core Congress entities are queryable in Silver.

**Acceptance Criteria**:
- ✅ Schema mappers implemented: `map_bill_to_silver()`, `map_vote_to_silver()`, `map_committee_to_silver()`
- ✅ Lambda handler routes entity_type to correct mapper
- ✅ Silver Parquet tables created: `dim_bill`, `house_vote_members`, `dim_committee`
- ✅ Upsert logic applied (no SCD Type 2, just update if `source_last_modified` differs)
- ✅ Integration tests pass for each entity type
- ✅ Documentation updated: `docs/CONGRESS_SILVER_SCHEMA.md` includes examples

**Effort**: 5 story points

---

#### TASK 2.3.1: Implement Schema Mappers for Bills

**Description**: Create mapper for bill JSON to Silver `dim_bill` schema.

**DoD**:
- ✅ Function added to `congress_schema_mappers.py`: `map_bill_to_silver(bronze_json: dict) -> dict`
- ✅ Extracts: `congress`, `bill_type`, `bill_number`, `title`, `introduced_date`, `sponsor_bioguide_id`, `policy_area`, `latest_action_date`, `latest_action_text`
- ✅ Generates composite key: `bill_id = f"{congress}-{bill_type}-{bill_number}"`
- ✅ Handles nested fields: `latestAction`, `policyArea`, `sponsors`
- ✅ Unit test with fixture: `tests/fixtures/bill_response.json`

**Subtasks**:
1. Download sample bill JSON from API
2. Implement `map_bill_to_silver()`
3. Extract fields with nested access
4. Generate `bill_id` composite key
5. Write unit test
6. Run test

**Effort**: 2 story points

---

#### TASK 2.3.2: Extend Lambda Handler to Route Entity Types

**Description**: Add routing logic to Lambda handler to call correct schema mapper.

**DoD**:
- ✅ Handler updated: `if entity_type == 'member': map_member_to_silver() elif entity_type == 'bill': map_bill_to_silver()`
- ✅ Router function: `get_schema_mapper(entity_type) -> Callable`
- ✅ Router function: `get_silver_table_path(entity_type) -> str` returns S3 key pattern
- ✅ Handler calls mapper, then upserts to correct Silver table
- ✅ Unit test: `test_entity_routing()` verifies correct mapper called

**Subtasks**:
1. Refactor handler to use router functions
2. Implement `get_schema_mapper(entity_type)`
3. Implement `get_silver_table_path(entity_type)` with partition logic
4. Update handler main loop
5. Write unit test
6. Deploy updated Lambda

**Effort**: 1 story point

---

#### TASK 2.3.3: Implement Schema Mappers for Votes and Committees

**Description**: Create mappers for house_vote and committee entities.

**DoD**:
- ✅ Function: `map_vote_to_silver(bronze_json: dict) -> dict` extracts: `vote_id`, `congress`, `session`, `vote_number`, `question`, `result`, `vote_date`, `bill_id`
- ✅ Function: `map_committee_to_silver(bronze_json: dict) -> dict` extracts: `committee_code`, `name`, `chamber`, `is_subcommittee`, `parent_committee_code`
- ✅ Unit tests for both mappers with fixtures
- ✅ Silver S3 paths defined: `silver/congress/house_vote_members/congress={congress}/session={session}/`, `silver/congress/dim_committee/chamber={chamber}/`

**Subtasks**:
1. Download sample vote and committee JSON
2. Implement `map_vote_to_silver()`
3. Implement `map_committee_to_silver()`
4. Add fixtures
5. Write unit tests
6. Update router to include vote and committee

**Effort**: 2 story points

---

#### TASK 2.3.4: Write Integration Tests for Bills, Votes, Committees

**Description**: Test Bronze → Silver transform for each entity type.

**DoD**:
- ✅ Tests created: `test_congress_silver_bill.py`, `test_congress_silver_vote.py`, `test_congress_silver_committee.py`
- ✅ Each test: upload Bronze JSON → trigger Lambda → verify Silver Parquet
- ✅ Each test verifies: correct partition, correct schema, correct values
- ✅ All tests pass in CI

**Subtasks**:
1. Create test files
2. Write test for bill transform
3. Write test for vote transform
4. Write test for committee transform
5. Run locally
6. Run in CI

**Effort**: 1 story point

---

---

## FEATURE 3: Silver Layer - Bill Subresources (Actions, Cosponsors, Subjects)

**Feature Goal**: Ingest and transform bill subresources (actions, cosponsors, committees, subjects, titles) from Bronze to Silver.

**Feature Value**: Enables detailed bill analysis (action timeline, cosponsor network, subject tagging).

**Feature Dependencies**: Feature 1 (Bronze must include bill subresources), Feature 2 (Silver `dim_bill` must exist)

**Estimated Effort**: 8 story points (5-7 days)

---

### STORY 3.1: Ingest Bill Subresources to Bronze

**Story Goal**: Extend orchestrator and fetch Lambda to fetch bill subresources after bill is fetched.

**User Story**: As a data pipeline, I need bill subresources (actions, cosponsors) fetched automatically after a bill is fetched so that Silver layer has complete data.

**Acceptance Criteria**:
- ✅ After fetching a bill, fetch Lambda queues subresource fetch jobs: `/bill/{congress}/{type}/{number}/actions`, `/bill/.../cosponsors`, etc.
- ✅ Subresources uploaded to Bronze: `bronze/congress/bill_actions/congress={congress}/bill_id={id}/ingest_date={date}/actions.json.gz`
- ✅ Integration test: fetch bill → verify 5 subresource files in Bronze

**Effort**: 3 story points

---

#### TASK 3.1.1: Extend Fetch Lambda to Queue Subresource Jobs

**Description**: After fetching a bill, queue subresource fetch jobs.

**DoD**:
- ✅ `congress_api_fetch_entity` handler updated
- ✅ After successful bill fetch, queues 5-7 subresource messages to `congress-api-fetch-queue`:
  - `{"entity_type": "bill_actions", "parent_bill_id": "118-hr-1", "endpoint": "/bill/118/hr/1/actions"}`
  - Similar for: cosponsors, committees, subjects, titles, summaries, relatedBills
- ✅ Subresource messages batched (send_message_batch)
- ✅ Logged: "Queued 6 subresource jobs for bill 118-hr-1"

**Subtasks**:
1. Update fetch Lambda handler
2. Add logic: `if entity_type == 'bill' and success: queue_subresources()`
3. Implement `queue_subresources(bill_id, queue_url)` function
4. Build subresource message list
5. Call `sqs.send_message_batch()`
6. Add logging
7. Deploy updated Lambda

**Effort**: 2 story points

---

#### TASK 3.1.2: Handle Subresource Fetch in Lambda

**Description**: Extend fetch Lambda to handle subresource entity types.

**DoD**:
- ✅ Fetch Lambda recognizes entity types: `bill_actions`, `bill_cosponsors`, `bill_committees`, `bill_subjects`, `bill_titles`, `bill_summaries`, `bill_related_bills`
- ✅ Calls appropriate `CongressAPIClient` method (e.g., `client.get_bill_actions(congress, bill_type, bill_number)`)
- ✅ Uploads to Bronze with partition: `bronze/congress/bill_actions/congress={congress}/bill_id={id}/ingest_date={date}/actions.json.gz`
- ✅ S3 metadata includes: `parent-bill-id`, `api-url`
- ✅ Integration test verifies all subresource types

**Subtasks**:
1. Add subresource methods to `CongressAPIClient`: `get_bill_actions()`, `get_bill_cosponsors()`, etc.
2. Update fetch Lambda router to handle subresource entity types
3. Update S3 key builder to partition by `congress` and `bill_id`
4. Test manually: queue subresource message, verify Bronze file
5. Write integration test

**Effort**: 2 story points

---

#### TASK 3.1.3: Write Integration Test for Bill with Subresources

**Description**: Test full bill ingestion including subresources.

**DoD**:
- ✅ Test file: `tests/integration/test_congress_bill_with_subresources.py`
- ✅ Test queues bill fetch message
- ✅ Waits for bill Bronze file
- ✅ Waits for 6 subresource Bronze files (actions, cosponsors, etc.)
- ✅ Verifies each file exists and is valid JSON
- ✅ Test passes in CI

**Subtasks**:
1. Create test file
2. Write test: queue bill → wait for bill + subresources
3. Add polling helper: `wait_for_files(s3_keys, timeout=120)`
4. Verify JSON validity
5. Run locally and in CI

**Effort**: 1 story point

---

### STORY 3.2: Transform Bill Subresources to Silver

**Story Goal**: Create Silver tables for bill subresources with proper flattening and denormalization.

**User Story**: As a data analyst, I need bill actions, cosponsors, and subjects queryable in Silver so I can analyze bill timelines and cosponsor networks.

**Acceptance Criteria**:
- ✅ Silver tables created: `bill_actions`, `bill_cosponsors`, `bill_committees`, `bill_subjects`, `bill_titles`
- ✅ Schema mappers implemented for each subresource
- ✅ Lambda handler extended to process subresource entity types
- ✅ Integration tests verify Bronze subresource → Silver transform
- ✅ Parquet partitioned by `congress` and `bill_type`

**Effort**: 5 story points

---

#### TASK 3.2.1: Define Silver Schemas for Subresources

**Description**: Document schemas for all bill subresource tables.

**DoD**:
- ✅ `docs/CONGRESS_SILVER_SCHEMA.md` updated with schemas for:
  - `silver/congress/bill_actions/` (grain: one row per action)
  - `silver/congress/bill_cosponsors/` (grain: one row per bill-cosponsor)
  - `silver/congress/bill_committees/` (grain: one row per bill-committee)
  - `silver/congress/bill_subjects/` (grain: one row per bill-subject)
  - `silver/congress/bill_titles/` (grain: one row per bill-title)
- ✅ Primary keys, partition keys, data types documented
- ✅ Example rows provided

**Subtasks**:
1. Update `docs/CONGRESS_SILVER_SCHEMA.md`
2. Document `bill_actions` schema (columns: `bill_id`, `action_date`, `action_code`, `action_text`, `source_last_modified`)
3. Document `bill_cosponsors` schema
4. Document other subresource schemas
5. Add example rows
6. Peer review

**Effort**: 1 story point

---

#### TASK 3.2.2: Implement Schema Mappers for Subresources

**Description**: Create mappers to flatten Bronze subresource JSON to Silver rows.

**DoD**:
- ✅ Functions added to `congress_schema_mappers.py`:
  - `map_bill_actions_to_silver(bronze_json: dict, bill_id: str) -> List[dict]` - flattens actions array
  - `map_bill_cosponsors_to_silver(bronze_json: dict, bill_id: str) -> List[dict]` - flattens cosponsors array
  - Similar for committees, subjects, titles
- ✅ Each mapper extracts parent `bill_id` from Bronze file path or metadata
- ✅ Each mapper returns list of dicts (one per row)
- ✅ Unit tests with fixtures for each mapper

**Subtasks**:
1. Implement `map_bill_actions_to_silver()`
2. Implement `map_bill_cosponsors_to_silver()`
3. Implement `map_bill_committees_to_silver()`
4. Implement `map_bill_subjects_to_silver()`
5. Implement `map_bill_titles_to_silver()`
6. Write unit tests with JSON fixtures
7. Run tests

**Effort**: 3 story points

---

#### TASK 3.2.3: Extend Lambda Handler for Subresource Transforms

**Description**: Update congress_bronze_to_silver Lambda to handle subresource entity types.

**DoD**:
- ✅ Lambda handler recognizes entity types: `bill_actions`, `bill_cosponsors`, etc.
- ✅ Calls appropriate mapper, converts to DataFrame
- ✅ Calls `upsert_parquet()` to write to Silver
- ✅ Logs: "Processed bill_actions for bill 118-hr-1: 15 actions written"
- ✅ Integration test for each subresource type

**Subtasks**:
1. Update handler router to include subresource entity types
2. Integrate subresource mappers
3. Ensure `bill_id` extracted from message or S3 key
4. Add logging
5. Deploy updated Lambda
6. Test manually

**Effort**: 1 story point

---

#### TASK 3.2.4: Write Integration Tests for Subresource Transforms

**Description**: Test Bronze → Silver for each subresource type.

**DoD**:
- ✅ Tests created: `test_congress_silver_bill_actions.py`, `test_congress_silver_bill_cosponsors.py`, etc.
- ✅ Each test uploads Bronze subresource JSON → triggers Lambda → verifies Silver Parquet
- ✅ Each test verifies: row count matches, PK columns correct, partition correct
- ✅ All tests pass in CI

**Subtasks**:
1. Create test files for each subresource
2. Write test for bill_actions
3. Write test for bill_cosponsors
4. Write tests for committees, subjects, titles
5. Run locally and in CI

**Effort**: 1 story point

---

---

## FEATURE 4: Gold Layer - Dimensions & Facts

**Feature Goal**: Build denormalized Gold dimensions and fact tables for API consumption and analytics.

**Feature Value**: Enables fast API queries and FD-to-legislation correlation analysis without scanning Silver.

**Feature Dependencies**: Feature 2 & 3 (Silver must be populated)

**Estimated Effort**: 13 story points (8-10 days)

---

### STORY 4.1: Gold Dimension - dim_member (Enriched)

**Story Goal**: Build Gold member dimension with enrichment (bill counts, vote counts, FD disclosure counts).

**User Story**: As an API consumer, I need a denormalized member dimension so that member profiles load fast with summary stats.

**Acceptance Criteria**:
- ✅ Gold table: `gold/congress/dim_member/chamber={chamber}/part-{uuid}.parquet`
- ✅ Columns: all from Silver + `total_bills_sponsored`, `total_bills_cosponsored`, `total_votes_cast`, `fd_disclosure_count`, `last_fd_disclosure_date`
- ✅ Only current members (is_current=True) from Silver SCD2
- ✅ Script: `scripts/congress_build_dim_member.py` builds table
- ✅ Makefile target: `make build-congress-gold-member`
- ✅ Integration test verifies enrichment fields

**Effort**: 3 story points

---

#### TASK 4.1.1: Create Script to Build Gold Member Dimension

**Description**: Implement script that reads Silver, aggregates metrics, writes Gold.

**DoD**:
- ✅ File created: `scripts/congress_build_dim_member.py`
- ✅ Script reads: `silver/congress/dim_member/` (filter `is_current=True`)
- ✅ Script joins with `silver/congress/dim_bill/` to count bills sponsored/cosponsored
- ✅ Script joins with `silver/congress/house_vote_members/` to count votes
- ✅ Script joins with `gold/house/financial/fact_filings/` to count FD disclosures
- ✅ Script writes to: `gold/congress/dim_member/chamber={chamber}/`
- ✅ Script logs: "Built dim_member: 535 members written"
- ✅ CLI args: `--congress` (default: all), `--output-path`

**Subtasks**:
1. Create script file
2. Read Silver dim_member with pyarrow
3. Aggregate bill counts (group by sponsor_bioguide_id)
4. Aggregate vote counts
5. Join with FD fact_filings (on bioguide_id)
6. Merge all metrics into DataFrame
7. Write to Gold with partition by chamber
8. Add argparse CLI
9. Add logging
10. Test manually: `python scripts/congress_build_dim_member.py`

**Effort**: 2 story points

---

#### TASK 4.1.2: Add Makefile Target and Documentation

**Description**: Make script easy to invoke and document in README.

**DoD**:
- ✅ Makefile target: `make build-congress-gold-member`
- ✅ Target runs: `python3 scripts/congress_build_dim_member.py`
- ✅ `README.md` updated with Gold layer build instructions
- ✅ `docs/CONGRESS_GOLD_SCHEMA.md` created with dim_member schema

**Subtasks**:
1. Add Makefile target
2. Create `docs/CONGRESS_GOLD_SCHEMA.md`
3. Document dim_member schema (columns, partition, example)
4. Update `README.md` with usage instructions

**Effort**: 1 story point

---

#### TASK 4.1.3: Write Integration Test for Gold Member Build

**Description**: Test script output correctness.

**DoD**:
- ✅ Test file: `tests/integration/test_congress_gold_member.py`
- ✅ Test populates Silver with sample members, bills, votes
- ✅ Test runs `congress_build_dim_member.py`
- ✅ Test reads Gold Parquet and verifies:
  - Member count matches Silver current members
  - Enrichment fields are populated (not null)
  - Specific member has correct bill_sponsored_count
- ✅ Test passes in CI

**Subtasks**:
1. Create test file
2. Create fixtures: sample Silver data
3. Run script in test
4. Read Gold output
5. Assert correctness
6. Add cleanup

**Effort**: 1 story point

---

### STORY 4.2: Gold Dimension - dim_bill (Denormalized)

**Story Goal**: Build Gold bill dimension with denormalized sponsor name, subject list, cosponsor count.

**User Story**: As an API consumer, I need a denormalized bill dimension so that bill list queries don't require joins.

**Acceptance Criteria**:
- ✅ Gold table: `gold/congress/dim_bill/congress={congress}/bill_type={type}/`
- ✅ Columns: all from Silver + `sponsor_name`, `subject_list` (array), `cosponsor_count`, `action_count`, `latest_action_date`
- ✅ Script: `scripts/congress_build_dim_bill.py`
- ✅ Makefile target: `make build-congress-gold-bill`
- ✅ Integration test verifies denormalization

**Effort**: 3 story points

---

#### TASK 4.2.1: Create Script to Build Gold Bill Dimension

**Description**: Implement script that denormalizes bill data from Silver subresources.

**DoD**:
- ✅ File created: `scripts/congress_build_dim_bill.py`
- ✅ Script reads: `silver/congress/dim_bill/`, `bill_cosponsors/`, `bill_subjects/`, `bill_actions/`
- ✅ Script joins bill with dim_member to get sponsor_name
- ✅ Script aggregates: cosponsor_count, action_count
- ✅ Script arrays: subject_list (list of subjects)
- ✅ Script extracts: latest_action_date (max action_date from bill_actions)
- ✅ Script writes to: `gold/congress/dim_bill/congress={congress}/bill_type={type}/`
- ✅ CLI args: `--congress`, `--output-path`

**Subtasks**:
1. Create script
2. Read Silver dim_bill
3. Join with dim_member on sponsor_bioguide_id
4. Join with bill_cosponsors (count)
5. Join with bill_subjects (collect into array)
6. Join with bill_actions (count, max date)
7. Merge into denormalized DataFrame
8. Write to Gold
9. Add CLI and logging

**Effort**: 2 story points

---

#### TASK 4.2.2: Add Makefile Target and Documentation

**Description**: Integrate script into workflow.

**DoD**:
- ✅ Makefile target: `make build-congress-gold-bill`
- ✅ `docs/CONGRESS_GOLD_SCHEMA.md` updated with dim_bill schema
- ✅ README.md updated

**Subtasks**:
1. Add Makefile target
2. Document schema
3. Update README

**Effort**: 1 story point

---

#### TASK 4.2.3: Write Integration Test

**Description**: Verify denormalization correctness.

**DoD**:
- ✅ Test file: `tests/integration/test_congress_gold_bill.py`
- ✅ Test populates Silver with sample bills + subresources
- ✅ Test runs script
- ✅ Test verifies: sponsor_name populated, cosponsor_count correct, subject_list is array
- ✅ Test passes

**Subtasks**:
1. Create test
2. Create fixtures
3. Run script
4. Assert correctness

**Effort**: 1 story point

---

### STORY 4.3: Gold Fact - fact_member_bill_role

**Story Goal**: Build fact table capturing member-bill relationships (sponsor, cosponsor, committee member).

**User Story**: As a data analyst, I need a table that shows which members touched which bills so I can query "bills this member influenced."

**Acceptance Criteria**:
- ✅ Gold table: `gold/congress/fact_member_bill_role/congress={congress}/bill_type={type}/`
- ✅ Grain: one row per member-bill combination
- ✅ Columns: `member_id`, `bioguide_id`, `bill_id`, `is_sponsor`, `is_cosponsor`, `is_committee_member`, `sponsored_date`, `cosponsored_date`
- ✅ Script: `scripts/congress_build_fact_member_bill_role.py`
- ✅ Makefile target: `make build-congress-gold-fact-role`
- ✅ Integration test

**Effort**: 3 story points

---

#### TASK 4.3.1: Create Script to Build Fact Table

**Description**: Aggregate member-bill relationships from Silver.

**DoD**:
- ✅ File created: `scripts/congress_build_fact_member_bill_role.py`
- ✅ Script reads: `silver/congress/dim_bill/` (for sponsors), `bill_cosponsors/`, `bill_committees/` + `dim_member/`
- ✅ Script creates rows for:
  - Each sponsor-bill (is_sponsor=True)
  - Each cosponsor-bill (is_cosponsor=True)
  - Each committee_member-bill (is_committee_member=True, requires joining committee memberships)
- ✅ Script dedupes: one row per member-bill with flags
- ✅ Script writes to Gold
- ✅ CLI args, logging

**Subtasks**:
1. Create script
2. Extract sponsor relationships
3. Extract cosponsor relationships
4. Extract committee relationships (may require committee-member mapping)
5. Merge with flags
6. Dedupe on (member_id, bill_id)
7. Write to Gold
8. Add CLI

**Effort**: 2 story points

---

#### TASK 4.3.2: Add Makefile Target and Documentation

**DoD**:
- ✅ Makefile target added
- ✅ Schema documented
- ✅ README updated

**Subtasks**:
1. Add target
2. Document schema
3. Update README

**Effort**: 1 story point

---

#### TASK 4.3.3: Write Integration Test

**DoD**:
- ✅ Test populates Silver with bills, cosponsors, committees
- ✅ Test runs script
- ✅ Test verifies: sponsor flag correct, cosponsor flag correct, row count correct

**Subtasks**:
1. Create test
2. Create fixtures
3. Run script
4. Assert

**Effort**: 1 story point

---

### STORY 4.4: Gold Fact - fact_member_vote

**Story Goal**: Build fact table for member voting records.

**User Story**: As a data analyst, I need member vote records so I can analyze voting patterns and correlate with FD trades.

**Acceptance Criteria**:
- ✅ Gold table: `gold/congress/fact_member_vote/congress={congress}/vote_year={year}/vote_month={month}/`
- ✅ Grain: one row per member-vote
- ✅ Columns: `member_id`, `bioguide_id`, `vote_id`, `vote_position`, `vote_date`, `bill_id`, `party_at_vote_time`
- ✅ Script: `scripts/congress_build_fact_member_vote.py`
- ✅ Enriched with party_at_vote_time from Silver SCD2
- ✅ Integration test

**Effort**: 3 story points

---

#### TASK 4.4.1: Create Script to Build Vote Fact Table

**Description**: Flatten Silver house_vote_members to Gold with enrichment.

**DoD**:
- ✅ File created: `scripts/congress_build_fact_member_vote.py`
- ✅ Script reads: `silver/congress/house_vote_members/`, `silver/congress/dim_member/` (SCD2 history)
- ✅ Script joins member votes with member history to get `party_at_vote_time` (uses vote_date to find correct SCD2 record)
- ✅ Script extracts `bill_id` from vote metadata if available
- ✅ Script writes to: `gold/congress/fact_member_vote/congress={congress}/vote_year={year}/vote_month={month}/`
- ✅ CLI args, logging

**Subtasks**:
1. Create script
2. Read house_vote_members
3. Join with dim_member SCD2 (filter by effective_date <= vote_date <= end_date)
4. Extract party_at_vote_time
5. Partition by vote_year, vote_month
6. Write to Gold
7. Add CLI

**Effort**: 2 story points

---

#### TASK 4.4.2: Add Makefile Target and Documentation

**DoD**:
- ✅ Makefile target added
- ✅ Schema documented
- ✅ README updated

**Subtasks**:
1. Add target
2. Document schema
3. Update README

**Effort**: 1 story point

---

#### TASK 4.4.3: Write Integration Test

**DoD**:
- ✅ Test populates Silver votes + member history with party change
- ✅ Test runs script
- ✅ Test verifies: party_at_vote_time correct for vote before and after party change

**Subtasks**:
1. Create test
2. Create fixtures (party change scenario)
3. Run script
4. Assert party_at_vote_time

**Effort**: 1 story point

---

---

## FEATURE 5: Gold Analytics - FD-to-Congress Correlation Tables

**Feature Goal**: Build Gold analytics tables that join FD transactions with Congressional activity (bills, votes) to enable correlation analysis.

**Feature Value**: Core value proposition: "Did this member trade stocks in sectors affected by bills they sponsored/voted on?"

**Feature Dependencies**: Feature 4 (Gold Congress tables), existing FD Gold tables

**Estimated Effort**: 13 story points (8-10 days)

---

### STORY 5.1: Create Sector Mapping Utility

**Story Goal**: Map bill subjects/policy areas to financial sectors so we can link bills to stocks.

**User Story**: As a data analyst, I need bill subjects mapped to financial sectors (Technology, Healthcare, Energy) so I can correlate legislation with FD stock trades.

**Acceptance Criteria**:
- ✅ Utility created: `ingestion/lib/congress_sector_mapper.py`
- ✅ Function: `map_policy_area_to_sector(policy_area: str) -> str` returns sector (e.g., "Healthcare")
- ✅ Function: `map_subject_to_sector(subject: str) -> str`
- ✅ Mapping table documented in `docs/CONGRESS_SECTOR_MAPPING.md`
- ✅ Unit tests verify mappings
- ✅ Handles unmapped subjects → "General"

**Effort**: 3 story points

---

#### TASK 5.1.1: Research and Document Sector Mapping

**Description**: Create mapping table from Congress.gov policy areas to financial sectors.

**DoD**:
- ✅ File created: `docs/CONGRESS_SECTOR_MAPPING.md`
- ✅ Mapping table documented with examples:
  - "Health" → "Healthcare"
  - "Finance and Financial Sector" → "Financials"
  - "Energy" → "Energy"
  - "Science, Technology, Communications" → "Technology"
  - "Armed Forces and National Security" → "Defense"
  - etc. (20+ mappings)
- ✅ Mapping includes both policy_area (single value) and subjects (multi-value)
- ✅ Peer reviewed for accuracy

**Subtasks**:
1. Research Congress.gov policy area values (query Silver dim_bill)
2. Research GICS sectors (or use simplified 11-sector model)
3. Create mapping table
4. Document in Markdown
5. Peer review

**Effort**: 1 story point

---

#### TASK 5.1.2: Implement Sector Mapper Utility

**Description**: Create Python library for sector mapping.

**DoD**:
- ✅ File created: `ingestion/lib/congress_sector_mapper.py`
- ✅ Hardcoded dict: `POLICY_AREA_TO_SECTOR = {"Health": "Healthcare", ...}`
- ✅ Function: `map_policy_area_to_sector(policy_area: str) -> str`
- ✅ Function: `map_subjects_to_sectors(subjects: List[str]) -> List[str]` (handles multi-subject, returns unique sectors)
- ✅ Handles case-insensitive matching
- ✅ Returns "General" for unmapped values
- ✅ Unit test: `test_map_policy_area()`, `test_map_subjects()`

**Subtasks**:
1. Create file
2. Define POLICY_AREA_TO_SECTOR dict
3. Implement map_policy_area_to_sector()
4. Implement map_subjects_to_sectors()
5. Add case-insensitive logic
6. Add fallback "General"
7. Write unit tests

**Effort**: 2 story points

---

### STORY 5.2: Gold Table - fact_member_bill_trade_window

**Story Goal**: Build fact table capturing member FD trades in time windows before/after bill actions.

**User Story**: As a data analyst, I need a table showing member trades in 30-day windows around bill actions so I can detect suspicious timing.

**Acceptance Criteria**:
- ✅ Gold table: `gold/analytics/fact_member_bill_trade_window/congress={congress}/window_year={year}/`
- ✅ Grain: one row per member-bill-window_type
- ✅ Columns: `member_id`, `bioguide_id`, `bill_id`, `window_type` (before_action_30d, after_action_30d), `action_date`, `action_type`, `transaction_count`, `total_disclosed_amount_low`, `total_disclosed_amount_high`, `distinct_tickers_traded`, `sectors_affected`
- ✅ Script: `scripts/congress_build_analytics_trade_windows.py`
- ✅ Joins: bill_actions + FD fact_ptr_transactions + sector mapping
- ✅ Makefile target: `make build-congress-analytics-trade-windows`
- ✅ Integration test

**Effort**: 5 story points

---

#### TASK 5.2.1: Create Script to Build Trade Window Fact Table

**Description**: Implement complex join logic between bill actions and FD transactions.

**DoD**:
- ✅ File created: `scripts/congress_build_analytics_trade_windows.py`
- ✅ Script reads:
  - `silver/congress/bill_actions/` (for action dates)
  - `gold/house/financial/fact_ptr_transactions/` (for trades)
  - `silver/congress/fact_member_bill_role/` (to link members to bills)
  - `gold/congress/dim_bill/` (for bill subjects → sectors)
- ✅ Script logic:
  1. For each bill-member pair (where member sponsored/cosponsored)
  2. For each significant action (introduced, committee action, floor action, passed)
  3. Find FD transactions by that member within 30 days before/after action
  4. Filter transactions to sectors affected by bill
  5. Aggregate: count, sum amounts, list tickers
  6. Create row per window_type
- ✅ Script writes to: `gold/analytics/fact_member_bill_trade_window/`
- ✅ CLI args: `--congress`, `--window-days` (default 30)

**Subtasks**:
1. Create script
2. Read bill_actions, filter to significant types
3. Read fact_member_bill_role
4. Read fact_ptr_transactions
5. Read dim_bill, map subjects to sectors using sector_mapper
6. Implement time window join: action_date -30 to +30
7. Filter trades to matching sectors
8. Aggregate metrics per window
9. Write to Gold
10. Add CLI and logging

**Effort**: 3 story points

---

#### TASK 5.2.2: Optimize Query Performance with Partition Pruning

**Description**: Ensure script uses partition pruning to avoid full table scans.

**DoD**:
- ✅ Script uses pyarrow filters: `filters=[('transaction_year', '>=', 2023)]` when reading FD transactions
- ✅ Script only reads relevant congress partitions from bill_actions
- ✅ Benchmark: script completes Congress 118 in <10 minutes
- ✅ Logs show: "Read 50K transactions (filtered from 1M total)"

**Subtasks**:
1. Add pyarrow partition filters
2. Benchmark script runtime
3. Profile memory usage
4. Optimize if needed

**Effort**: 1 story point

---

#### TASK 5.2.3: Add Makefile Target and Documentation

**DoD**:
- ✅ Makefile target: `make build-congress-analytics-trade-windows`
- ✅ Schema documented in `docs/CONGRESS_GOLD_SCHEMA.md`
- ✅ README updated with analytics workflow

**Subtasks**:
1. Add target
2. Document schema
3. Update README

**Effort**: 1 story point

---

#### TASK 5.2.4: Write Integration Test

**Description**: Verify trade window logic correctness.

**DoD**:
- ✅ Test file: `tests/integration/test_congress_analytics_trade_windows.py`
- ✅ Test populates:
  - Silver: member, bill with action on 2024-01-15
  - Gold: FD transaction on 2024-01-05 (10 days before) in matching sector
  - Gold: FD transaction on 2024-02-10 (outside window) in matching sector
- ✅ Test runs script
- ✅ Test verifies:
  - `before_action_30d` window includes 2024-01-05 trade
  - `before_action_30d` window excludes 2024-02-10 trade
  - Sector filtering works (non-matching sector trades excluded)
- ✅ Test passes

**Subtasks**:
1. Create test
2. Create complex fixture (bill, action, trades in/out of window)
3. Run script
4. Assert window logic
5. Assert sector filtering

**Effort**: 1 story point

---

### STORY 5.3: Gold Table - fact_stock_congress_activity

**Story Goal**: Build fact table aggregating Congressional activity (bills, trades) per stock per month.

**User Story**: As an API consumer, I need stock-level summaries of Congressional activity so I can display "legislative exposure" on stock detail pages.

**Acceptance Criteria**:
- ✅ Gold table: `gold/analytics/fact_stock_congress_activity/year={year}/month={month}/`
- ✅ Grain: one row per ticker-month
- ✅ Columns: `ticker`, `year`, `month`, `members_trading_count`, `bills_mentioning_count`, `committee_hearings_count`, `total_transaction_volume_disclosed`, `sectors`
- ✅ Script: `scripts/congress_build_analytics_stock_activity.py`
- ✅ Makefile target: `make build-congress-analytics-stock-activity`
- ✅ Integration test

**Effort**: 3 story points

---

#### TASK 5.3.1: Create Script to Build Stock Activity Table

**Description**: Aggregate bill and trade activity by stock.

**DoD**:
- ✅ File created: `scripts/congress_build_analytics_stock_activity.py`
- ✅ Script reads:
  - `gold/house/financial/fact_ptr_transactions/` (for trades by ticker)
  - `gold/congress/dim_bill/` (for bills, map subjects to sectors → tickers)
  - (Optional) `gold/congress/dim_hearing/` if available
- ✅ Script logic:
  1. Group FD transactions by (ticker, year, month): count members, sum amounts
  2. Group bills by sector → map to tickers in sector
  3. Join and aggregate
- ✅ Script writes to Gold
- ✅ CLI args: `--year`, `--month`

**Subtasks**:
1. Create script
2. Read fact_ptr_transactions
3. Group by ticker, year, month
4. Read dim_bill, map subjects to sectors
5. Map sectors to tickers (requires ticker-sector lookup, may use existing dim_stock)
6. Count bills per ticker
7. Join and merge
8. Write to Gold

**Effort**: 2 story points

---

#### TASK 5.3.2: Add Makefile Target and Documentation

**DoD**:
- ✅ Makefile target added
- ✅ Schema documented
- ✅ README updated

**Subtasks**:
1. Add target
2. Document schema
3. Update README

**Effort**: 1 story point

---

#### TASK 5.3.3: Write Integration Test

**DoD**:
- ✅ Test populates trades and bills for AAPL
- ✅ Test runs script
- ✅ Test verifies: AAPL row exists, counts correct

**Subtasks**:
1. Create test
2. Create fixtures
3. Run script
4. Assert

**Effort**: 1 story point

---

### STORY 5.4: Gold Aggregates - Member and Bill Summaries

**Story Goal**: Pre-compute aggregates for API endpoints (member legislative stats, bill trade overlap stats).

**User Story**: As an API, I need pre-computed aggregates so that /members endpoint returns fast without scanning fact tables.

**Acceptance Criteria**:
- ✅ Aggregates created: `member_legislative_stats`, `member_sector_exposure`, `bill_trade_overlap_stats`
- ✅ Scripts: `scripts/congress_compute_agg_member_stats.py`, `scripts/congress_compute_agg_bill_trade_overlap.py`
- ✅ Makefile target: `make build-congress-aggregates`
- ✅ Integration tests

**Effort**: 3 story points

---

#### TASK 5.4.1: Create Member Legislative Stats Aggregate

**Description**: Compute member-level stats (bills sponsored, votes cast, FD disclosures).

**DoD**:
- ✅ File created: `scripts/congress_compute_agg_member_stats.py`
- ✅ Script reads: Gold `dim_member`, `fact_member_bill_role`, `fact_member_vote`, FD `fact_filings`
- ✅ Script aggregates per member: bills_sponsored, bills_cosponsored, votes_cast, votes_missed, fd_disclosure_count
- ✅ Script writes to: `gold/congress/aggregates/member_legislative_stats/`
- ✅ CLI args, logging

**Subtasks**:
1. Create script
2. Read Gold tables
3. Group by member_id, aggregate
4. Write to Gold

**Effort**: 1 story point

---

#### TASK 5.4.2: Create Bill Trade Overlap Stats Aggregate

**Description**: Compute bill-level stats (how many cosponsors traded affected sectors).

**DoD**:
- ✅ File created: `scripts/congress_compute_agg_bill_trade_overlap.py`
- ✅ Script reads: `fact_member_bill_trade_window`
- ✅ Script aggregates per bill: cosponsors_who_traded_count, days_avg_between_action_and_trade, total_trade_volume
- ✅ Script writes to: `gold/congress/aggregates/bill_trade_overlap_stats/`

**Subtasks**:
1. Create script
2. Read fact_member_bill_trade_window
3. Group by bill_id, aggregate
4. Write to Gold

**Effort**: 1 story point

---

#### TASK 5.4.3: Add Makefile Target and Tests

**DoD**:
- ✅ Makefile target: `make build-congress-aggregates` runs both scripts
- ✅ Integration tests verify aggregate correctness

**Subtasks**:
1. Add Makefile target
2. Write integration tests

**Effort**: 1 story point

---

---

## FEATURE 6: Pipeline Orchestration & Incremental Sync

**Feature Goal**: Create master orchestration script and daily incremental sync workflow.

**Feature Value**: Automates end-to-end Congress pipeline with modes (full, incremental, aggregate-only).

**Feature Dependencies**: Features 1-5 (all layers implemented)

**Estimated Effort**: 8 story points (5-7 days)

---

### STORY 6.1: Master Orchestration Script - run_congress_pipeline.py

**Story Goal**: Create unified script to orchestrate Bronze → Silver → Gold pipeline.

**User Story**: As a pipeline operator, I need a single command to run the entire Congress pipeline so I don't have to manually sequence steps.

**Acceptance Criteria**:
- ✅ Script created: `scripts/run_congress_pipeline.py`
- ✅ Modes supported: `--mode full`, `--mode incremental`, `--mode aggregate`
- ✅ Full mode: orchestrates ingest → wait for extraction → build Silver → build Gold
- ✅ Incremental mode: fetches updates since last run → same flow
- ✅ Aggregate mode: skips ingestion, rebuilds Gold only
- ✅ Progress logging: "Bronze ingestion: 1500/5000 bills fetched"
- ✅ Error handling: retries failed steps, logs to CloudWatch
- ✅ Makefile target: `make run-congress-pipeline MODE=full CONGRESS=118`

**Effort**: 5 story points

---

#### TASK 6.1.1: Create Orchestration Script Framework

**Description**: Build script skeleton with CLI, logging, mode routing.

**DoD**:
- ✅ File created: `scripts/run_congress_pipeline.py`
- ✅ CLI args: `--mode`, `--congress`, `--wait-for-completion` (bool)
- ✅ Logging configured: structured JSON to stdout + CloudWatch
- ✅ Mode router: `if mode == 'full': run_full_pipeline() elif mode == 'incremental': run_incremental_pipeline()`
- ✅ Each mode function defined (empty stubs)

**Subtasks**:
1. Create script file
2. Add argparse CLI
3. Configure logging (structlog or stdlib)
4. Define mode router
5. Define stub functions for each mode

**Effort**: 1 story point

---

#### TASK 6.1.2: Implement Full Mode Orchestration

**Description**: Sequence Bronze ingestion → Silver transform → Gold build for full backfill.

**DoD**:
- ✅ `run_full_pipeline(congress)` function implemented
- ✅ Step 1: Invoke `congress_api_ingest_orchestrator` Lambda for each entity type (member, bill, amendment, committee, vote)
- ✅ Step 2: Poll SQS queues (`congress-api-fetch-queue`, `congress-bronze-to-silver-queue`) until empty (with timeout)
- ✅ Step 3: Invoke Silver build scripts if needed (or rely on Lambda triggers)
- ✅ Step 4: Invoke Gold build scripts sequentially:
  - `congress_build_dim_member.py`
  - `congress_build_dim_bill.py`
  - `congress_build_fact_member_bill_role.py`
  - `congress_build_fact_member_vote.py`
  - `congress_build_analytics_trade_windows.py`
  - `congress_build_analytics_stock_activity.py`
  - `congress_compute_agg_member_stats.py`
  - `congress_compute_agg_bill_trade_overlap.py`
- ✅ Logs progress at each step
- ✅ Exits with error code if any step fails

**Subtasks**:
1. Implement `run_full_pipeline()` function
2. Invoke orchestrator Lambda for each entity type using boto3
3. Implement queue polling helper: `wait_for_queue_empty(queue_url, timeout=3600)`
4. Invoke Gold scripts using subprocess
5. Add error handling and logging
6. Test manually: `python scripts/run_congress_pipeline.py --mode full --congress 118`

**Effort**: 3 story points

---

#### TASK 6.1.3: Implement Incremental Mode

**Description**: Fetch only updates since last run.

**DoD**:
- ✅ `run_incremental_pipeline()` function implemented
- ✅ Reads last ingest state from S3 marker files
- ✅ Invokes orchestrator with `mode=incremental`
- ✅ Waits for processing, then runs Gold scripts
- ✅ Updates marker files with new timestamp

**Subtasks**:
1. Implement `run_incremental_pipeline()`
2. Read last ingest state
3. Invoke orchestrator with incremental mode
4. Wait for processing
5. Run Gold scripts
6. Update state markers

**Effort**: 1 story point

---

#### TASK 6.1.4: Add Makefile Target and Documentation

**DoD**:
- ✅ Makefile target: `make run-congress-pipeline MODE=full CONGRESS=118`
- ✅ Target invokes: `python3 scripts/run_congress_pipeline.py --mode $(MODE) --congress $(CONGRESS)`
- ✅ README.md updated with Congress pipeline usage
- ✅ `docs/CONGRESS_PIPELINE.md` created with detailed orchestration flow

**Subtasks**:
1. Add Makefile target
2. Create `docs/CONGRESS_PIPELINE.md`
3. Document each mode
4. Update README

**Effort**: 1 story point

---

### STORY 6.2: Daily Incremental Sync via GitHub Actions

**Story Goal**: Automate daily incremental updates via GitHub Actions cron.

**User Story**: As a project maintainer, I need daily automated updates so that Congress data stays current without manual intervention.

**Acceptance Criteria**:
- ✅ GitHub Actions workflow: `.github/workflows/congress_incremental.yml`
- ✅ Cron schedule: daily at 3 AM UTC
- ✅ Workflow runs: `python scripts/run_congress_pipeline.py --mode incremental`
- ✅ Workflow uploads logs to S3: `logs/congress_pipeline/{date}.log`
- ✅ Workflow sends notification on failure (optional: Slack, email)
- ✅ Workflow tested manually via workflow_dispatch

**Effort**: 3 story points

---

#### TASK 6.2.1: Create GitHub Actions Workflow

**Description**: Define workflow YAML for automated incremental sync.

**DoD**:
- ✅ File created: `.github/workflows/congress_incremental.yml`
- ✅ Trigger: `schedule.cron: '0 3 * * *'` (daily 3 AM UTC)
- ✅ Trigger: `workflow_dispatch` (manual)
- ✅ Steps:
  1. Checkout repo
  2. Setup Python 3.11
  3. Install dependencies: `pip install -r requirements.txt`
  4. Configure AWS credentials (GitHub secrets)
  5. Run: `python scripts/run_congress_pipeline.py --mode incremental`
  6. Upload logs to S3
- ✅ Logs uploaded to: `s3://congress-disclosures-standardized/logs/congress_pipeline/{date}.log`
- ✅ Workflow tested via manual dispatch

**Subtasks**:
1. Create workflow file
2. Define cron trigger
3. Add checkout and setup steps
4. Add AWS credentials configuration (use OIDC or IAM keys in secrets)
5. Add run command
6. Add log upload step
7. Test via workflow_dispatch
8. Verify logs in S3

**Effort**: 2 story points

---

#### TASK 6.2.2: Add Notification on Failure (Optional)

**Description**: Send alert if workflow fails.

**DoD**:
- ✅ Workflow step added: `if: failure()` sends notification
- ✅ Notification method: Slack webhook or GitHub issue creation
- ✅ Configured via GitHub secret: `SLACK_WEBHOOK_URL`
- ✅ Test manually: force workflow failure, verify notification

**Subtasks**:
1. Add Slack notification step (using action: slackapi/slack-github-action)
2. Configure secret
3. Test failure scenario

**Effort**: 1 story point

---

---

## FEATURE 7: API Endpoints for Congress Data

**Feature Goal**: Create API Lambda functions to expose Congress data via REST endpoints.

**Feature Value**: Enables website and external consumers to query Congress data with fast response times.

**Feature Dependencies**: Feature 4 & 5 (Gold layer populated)

**Estimated Effort**: 13 story points (8-10 days)

---

### STORY 7.1: Congress-Specific API Endpoints

**Story Goal**: Implement Lambda functions for core Congress queries (bills, votes, members).

**User Story**: As an API consumer, I need REST endpoints to query bills, votes, and members so I can build UIs.

**Acceptance Criteria**:
- ✅ Endpoints implemented:
  - `GET /api/v1/congress/bills?congress=118&limit=50`
  - `GET /api/v1/congress/bills/{bill_id}`
  - `GET /api/v1/congress/votes?congress=118`
  - `GET /api/v1/congress/votes/{vote_id}`
  - `GET /api/v1/congress/members?chamber=House`
  - `GET /api/v1/congress/members/{bioguide_id}`
- ✅ Lambda functions created in `api/lambdas/congress/`
- ✅ API Gateway routes configured in Terraform
- ✅ Responses cached with CloudFront (5 min TTL)
- ✅ p95 latency <500ms
- ✅ Integration tests verify each endpoint

**Effort**: 8 story points

---

#### TASK 7.1.1: Create Lambda Function - get_bills

**Description**: Implement list bills endpoint with pagination and filters.

**DoD**:
- ✅ File created: `api/lambdas/congress/get_bills/handler.py`
- ✅ Function reads: `gold/congress/dim_bill/`
- ✅ Query params: `congress`, `bill_type`, `sponsor`, `limit`, `offset`
- ✅ Returns JSON: `{"bills": [...], "total_count": 5000, "next_offset": 50}`
- ✅ Uses pyarrow filters for partition pruning
- ✅ Response time: <300ms for 50 bills
- ✅ Unit test, integration test

**Subtasks**:
1. Create handler file
2. Read Gold dim_bill with pyarrow
3. Apply filters from query params
4. Implement pagination (limit, offset)
5. Convert to JSON
6. Add response headers (CORS)
7. Write tests
8. Deploy Lambda

**Effort**: 2 story points

---

#### TASK 7.1.2: Create Lambda Function - get_bill

**Description**: Implement single bill detail endpoint.

**DoD**:
- ✅ File created: `api/lambdas/congress/get_bill/handler.py`
- ✅ Function reads: `gold/congress/dim_bill/` filtered by `bill_id`
- ✅ Path param: `bill_id` (e.g., "118-hr-1")
- ✅ Returns JSON with full bill details: title, sponsor_name, cosponsor_count, action_count, subject_list, latest_action
- ✅ Returns 404 if bill not found
- ✅ Response time: <200ms
- ✅ Tests

**Subtasks**:
1. Create handler
2. Parse bill_id from path
3. Read Gold, filter by bill_id
4. Return JSON or 404
5. Write tests
6. Deploy

**Effort**: 1 story point

---

#### TASK 7.1.3: Create Lambda Functions - get_votes, get_vote

**Description**: Implement vote list and detail endpoints.

**DoD**:
- ✅ Files created: `api/lambdas/congress/get_votes/handler.py`, `get_vote/handler.py`
- ✅ `get_votes` reads: `gold/congress/fact_member_vote/` (grouped by vote_id)
- ✅ `get_vote` reads: single vote + member positions
- ✅ Query params for list: `congress`, `session`, `limit`
- ✅ Path param for detail: `vote_id`
- ✅ Tests

**Subtasks**:
1. Create handlers
2. Implement list endpoint
3. Implement detail endpoint
4. Write tests
5. Deploy

**Effort**: 2 story points

---

#### TASK 7.1.4: Create Lambda Functions - get_members, get_member

**Description**: Implement member list and detail endpoints.

**DoD**:
- ✅ Files created: `api/lambdas/congress/get_members/handler.py`, `get_member/handler.py`
- ✅ `get_members` reads: `gold/congress/dim_member/`
- ✅ `get_member` reads: single member + enrichment stats
- ✅ Query params for list: `chamber`, `state`, `party`, `limit`
- ✅ Path param for detail: `bioguide_id`
- ✅ Tests

**Subtasks**:
1. Create handlers
2. Implement list endpoint with filters
3. Implement detail endpoint
4. Write tests
5. Deploy

**Effort**: 2 story points

---

#### TASK 7.1.5: Configure API Gateway Routes in Terraform

**Description**: Add routes to API Gateway for Congress endpoints.

**DoD**:
- ✅ File updated: `infra/terraform/api_gateway_congress.tf`
- ✅ Routes configured:
  - `/congress/bills` → `get_bills` Lambda
  - `/congress/bills/{bill_id}` → `get_bill` Lambda
  - `/congress/votes` → `get_votes` Lambda
  - `/congress/votes/{vote_id}` → `get_vote` Lambda
  - `/congress/members` → `get_members` Lambda
  - `/congress/members/{bioguide_id}` → `get_member` Lambda
- ✅ CORS configured
- ✅ CloudFront distribution updated to cache `/congress/*` paths (5 min TTL)
- ✅ `terraform apply` succeeds
- ✅ Endpoints tested with curl

**Subtasks**:
1. Create `api_gateway_congress.tf`
2. Define routes for each endpoint
3. Link to Lambda integrations
4. Configure CORS
5. Update CloudFront distribution
6. Apply and test
7. Document in `docs/API_STRATEGY.md`

**Effort**: 1 story point

---

### STORY 7.2: Cross-Domain Analytics API Endpoints

**Story Goal**: Implement API endpoints for FD-Congress correlation queries.

**User Story**: As an API consumer, I need endpoints that join FD and Congress data so I can query "member legislation vs trades" without client-side joins.

**Acceptance Criteria**:
- ✅ Endpoints implemented:
  - `GET /api/v1/analytics/members/{bioguide_id}/legislation-trades` - member's bills + trades in windows
  - `GET /api/v1/analytics/stocks/{ticker}/legislative-exposure` - bills + trades for a stock
  - `GET /api/v1/analytics/sectors/{sector}/congress-activity` - sector-level bill + trade stats
- ✅ Lambda functions created
- ✅ API Gateway routes configured
- ✅ Integration tests verify joins correct
- ✅ p95 latency <500ms

**Effort**: 5 story points

---

#### TASK 7.2.1: Create Lambda - get_member_legislation_trades

**Description**: Endpoint showing member's bills and correlated trades.

**DoD**:
- ✅ File created: `api/lambdas/analytics/get_member_legislation_trades/handler.py`
- ✅ Path param: `bioguide_id`
- ✅ Function reads:
  - `gold/congress/fact_member_bill_role/` (member's bills)
  - `gold/analytics/fact_member_bill_trade_window/` (trade windows)
- ✅ Returns JSON: `{"member": {...}, "bills": [{"bill_id": "118-hr-1", "role": "sponsor", "trade_windows": [{"window_type": "before_action_30d", "transaction_count": 3}]}]}`
- ✅ Tests

**Subtasks**:
1. Create handler
2. Read member's bills
3. Join with trade windows
4. Format response
5. Write tests
6. Deploy

**Effort**: 2 story points

---

#### TASK 7.2.2: Create Lambda - get_stock_legislative_exposure

**Description**: Endpoint showing bills and trades for a stock.

**DoD**:
- ✅ File created: `api/lambdas/analytics/get_stock_legislative_exposure/handler.py`
- ✅ Path param: `ticker`
- ✅ Function reads:
  - `gold/analytics/fact_stock_congress_activity/` (stock-level stats)
  - `gold/congress/dim_bill/` (bills in stock's sectors)
  - `gold/house/financial/fact_ptr_transactions/` (trades of this ticker)
- ✅ Returns JSON: `{"ticker": "AAPL", "legislative_activity": {...}, "trading_activity": {...}}`
- ✅ Tests

**Subtasks**:
1. Create handler
2. Read stock congress activity
3. Read bills in sectors
4. Read trades
5. Format response
6. Write tests
7. Deploy

**Effort**: 2 story points

---

#### TASK 7.2.3: Configure API Gateway Routes for Analytics

**Description**: Add routes for analytics endpoints.

**DoD**:
- ✅ Routes configured in Terraform
- ✅ Endpoints tested
- ✅ Documented in API docs

**Subtasks**:
1. Update `api_gateway_congress.tf` with analytics routes
2. Apply Terraform
3. Test endpoints
4. Update `docs/openapi.yaml` with new endpoints

**Effort**: 1 story point

---

---

## FEATURE 8: Website Integration & Visualization

**Feature Goal**: Update website to display Congress data and FD-Congress correlations.

**Feature Value**: Makes Congress data accessible via user-friendly UI.

**Feature Dependencies**: Feature 7 (API endpoints)

**Estimated Effort**: 13 story points (8-10 days)

---

### STORY 8.1: Member Profile Page - Add Legislative Activity Tab

**Story Goal**: Extend member profile page to show bills sponsored, votes cast, committee memberships.

**User Story**: As a website user, I want to see a member's legislative activity on their profile page so I understand their policy focus.

**Acceptance Criteria**:
- ✅ Member profile page updated: `website/member.html` (or component)
- ✅ New tab: "Legislative Activity" (alongside existing "Transactions", "Holdings")
- ✅ Tab displays:
  - Bills sponsored (list with titles, click to bill detail)
  - Votes cast (recent votes with bill context)
  - Committee memberships (list)
  - Stats: total_bills_sponsored, total_votes_cast
- ✅ Data fetched from: `/api/v1/analytics/members/{bioguide_id}/legislation-trades`
- ✅ UI responsive (mobile-friendly)
- ✅ Tested in browser

**Effort**: 5 story points

---

#### TASK 8.1.1: Design UI Mockup for Legislative Activity Tab

**Description**: Create wireframe/mockup for new tab.

**DoD**:
- ✅ Mockup created (Figma, sketch, or HTML prototype)
- ✅ Shows layout: tabs, bill list, vote list, stats cards
- ✅ Responsive design (desktop + mobile)
- ✅ Peer reviewed for UX

**Subtasks**:
1. Sketch mockup
2. Decide on layout (cards vs table)
3. Peer review

**Effort**: 1 story point

---

#### TASK 8.1.2: Implement Frontend Component - Legislative Activity Tab

**Description**: Build React/Vue/vanilla JS component for tab.

**DoD**:
- ✅ Component file created (or HTML/JS updated)
- ✅ Component fetches: `/api/v1/analytics/members/{bioguide_id}/legislation-trades`
- ✅ Component renders:
  - Stats cards: bills_sponsored, votes_cast
  - Bill list: titles, bill_id, role (sponsor/cosponsor), click → bill detail page
  - Vote list: vote_date, question, position
- ✅ Loading state, error handling
- ✅ Styled with existing CSS framework
- ✅ Tested in browser (Chrome, Safari, Firefox)

**Subtasks**:
1. Create component file
2. Add API fetch logic
3. Render stats cards
4. Render bill list
5. Render vote list
6. Add loading/error states
7. Style with CSS
8. Test in browsers

**Effort**: 3 story points

---

#### TASK 8.1.3: Deploy and Test Website Update

**Description**: Deploy updated website to S3, test end-to-end.

**DoD**:
- ✅ Website deployed: `make deploy-website`
- ✅ Member profile page loads with new tab
- ✅ Tab shows correct data for test member (e.g., Nancy Pelosi)
- ✅ Links to bill detail pages work
- ✅ Mobile responsive verified

**Subtasks**:
1. Deploy website
2. Test member profile page
3. Verify data correctness
4. Test links
5. Test on mobile

**Effort**: 1 story point

---

### STORY 8.2: Stock Detail Page - Add Legislative Exposure Section

**Story Goal**: Add section to stock detail page showing bills and trades related to the stock.

**User Story**: As a website user, I want to see legislative activity related to a stock so I understand regulatory risks.

**Acceptance Criteria**:
- ✅ Stock detail page updated: `website/stock.html`
- ✅ New section: "Legislative Exposure"
- ✅ Section displays:
  - Bills potentially impacting stock (from sector mapping)
  - Member trades of this stock (count, volume)
  - Heat score: "High/Medium/Low legislative activity"
- ✅ Data fetched from: `/api/v1/analytics/stocks/{ticker}/legislative-exposure`
- ✅ UI responsive
- ✅ Tested in browser

**Effort**: 3 story points

---

#### TASK 8.2.1: Implement Frontend Component - Legislative Exposure

**Description**: Build component for legislative exposure section.

**DoD**:
- ✅ Component created
- ✅ Fetches: `/api/v1/analytics/stocks/{ticker}/legislative-exposure`
- ✅ Renders:
  - Heat badge: "High", "Medium", "Low" with color
  - Bill list: titles, bill_id, click → bill detail
  - Trade stats: members_trading_count, total_volume
- ✅ Loading/error states
- ✅ Styled
- ✅ Tested

**Subtasks**:
1. Create component
2. Add API fetch
3. Render heat badge
4. Render bill list
5. Render trade stats
6. Add loading/error states
7. Style
8. Test

**Effort**: 2 story points

---

#### TASK 8.2.2: Deploy and Test

**DoD**:
- ✅ Deployed
- ✅ Stock detail page shows legislative exposure
- ✅ Data correct for test stock (e.g., AAPL)
- ✅ Links work
- ✅ Mobile responsive

**Subtasks**:
1. Deploy
2. Test stock detail page
3. Verify data
4. Test links
5. Test mobile

**Effort**: 1 story point

---

### STORY 8.3: New Dashboard - Bill-Trade Correlation

**Story Goal**: Create new dashboard showing bills with suspicious trading patterns.

**User Story**: As a website user, I want to see bills where cosponsors traded affected sectors so I can identify potential conflicts.

**Acceptance Criteria**:
- ✅ New page created: `website/bill-trade-correlation.html`
- ✅ Page displays:
  - Top bills ranked by "trade overlap score" (cosponsors trading affected sectors)
  - Table: bill_id, title, cosponsor_count, members_who_traded_count, sectors_affected
  - Click bill → bill detail page
  - Click member → member profile page
- ✅ Data fetched from: `gold/congress/aggregates/bill_trade_overlap_stats/` (via new API endpoint or direct S3 read)
- ✅ UI responsive
- ✅ Tested

**Effort**: 5 story points

---

#### TASK 8.3.1: Create API Endpoint - get_bill_trade_correlation

**Description**: Expose bill trade overlap stats via API.

**DoD**:
- ✅ Lambda created: `api/lambdas/analytics/get_bill_trade_correlation/handler.py`
- ✅ Endpoint: `GET /api/v1/analytics/bill-trade-correlation?limit=50`
- ✅ Returns: ranked list of bills with trade overlap stats
- ✅ Terraform route configured
- ✅ Tested

**Subtasks**:
1. Create Lambda handler
2. Read `gold/congress/aggregates/bill_trade_overlap_stats/`
3. Sort by trade overlap score descending
4. Return JSON
5. Configure route in Terraform
6. Test

**Effort**: 2 story points

---

#### TASK 8.3.2: Implement Frontend Page - Bill-Trade Correlation Dashboard

**Description**: Build dashboard page with table and filters.

**DoD**:
- ✅ Page created: `website/bill-trade-correlation.html`
- ✅ Fetches: `/api/v1/analytics/bill-trade-correlation`
- ✅ Renders table with columns: bill_id, title, members_who_traded, sectors
- ✅ Sortable, filterable (by congress, sector)
- ✅ Links to bill and member detail pages
- ✅ Styled
- ✅ Tested

**Subtasks**:
1. Create HTML page
2. Add API fetch
3. Render table
4. Add sorting/filtering
5. Add links
6. Style
7. Test

**Effort**: 2 story points

---

#### TASK 8.3.3: Add Navigation Link and Deploy

**Description**: Link new dashboard from main nav, deploy.

**DoD**:
- ✅ Navigation menu updated: "Bill-Trade Correlation" link added
- ✅ Website deployed
- ✅ Dashboard accessible
- ✅ Tested end-to-end

**Subtasks**:
1. Update nav menu HTML/component
2. Deploy website
3. Test navigation
4. Test dashboard

**Effort**: 1 story point

---

---

## FEATURE 9: Documentation & Testing

**Feature Goal**: Comprehensive documentation and test coverage for Congress pipeline.

**Feature Value**: Ensures maintainability and onboarding ease for future contributors.

**Feature Dependencies**: All features (documentation of implemented features)

**Estimated Effort**: 8 story points (5-7 days)

---

### STORY 9.1: Create Congress Pipeline Documentation

**Story Goal**: Write comprehensive documentation for Congress pipeline architecture, usage, and troubleshooting.

**User Story**: As a new contributor, I need clear documentation so I can understand and contribute to the Congress pipeline.

**Acceptance Criteria**:
- ✅ Documentation files created:
  - `docs/CONGRESS_PIPELINE.md` - Pipeline overview, architecture, data flow
  - `docs/CONGRESS_S3_SCHEMA.md` - Bronze/Silver/Gold S3 structure
  - `docs/CONGRESS_SILVER_SCHEMA.md` - Silver table schemas
  - `docs/CONGRESS_GOLD_SCHEMA.md` - Gold table schemas
  - `docs/CONGRESS_API.md` - API endpoint documentation (or update `docs/openapi.yaml`)
  - `docs/CONGRESS_SECTOR_MAPPING.md` - Sector mapping table
- ✅ `README.md` updated with Congress section
- ✅ `CLAUDE.md` updated with Congress architecture
- ✅ Documentation peer reviewed

**Effort**: 3 story points

---

#### TASK 9.1.1: Write CONGRESS_PIPELINE.md

**Description**: Document pipeline architecture and orchestration.

**DoD**:
- ✅ File created: `docs/CONGRESS_PIPELINE.md`
- ✅ Sections:
  - Overview (goals, scope)
  - Architecture diagram (Bronze → Silver → Gold)
  - Data flow (ingestion → extraction → transformation)
  - Lambda functions (purpose, triggers, configs)
  - Scripts (Gold layer build scripts)
  - Orchestration (run_congress_pipeline.py modes)
  - Troubleshooting (common issues, debugging tips)
- ✅ Examples: commands to run pipeline, check queue status
- ✅ Peer reviewed

**Subtasks**:
1. Create file
2. Write overview
3. Add architecture diagram (Mermaid or ASCII)
4. Document data flow
5. Document Lambda functions
6. Document scripts
7. Document orchestration
8. Add troubleshooting section
9. Peer review

**Effort**: 2 story points

---

#### TASK 9.1.2: Update README.md and CLAUDE.md

**Description**: Add Congress sections to main docs.

**DoD**:
- ✅ `README.md` updated with:
  - "Congress.gov Pipeline" section
  - Quick start: `make run-congress-pipeline MODE=full CONGRESS=118`
  - API endpoints listed
- ✅ `CLAUDE.md` updated with:
  - Congress architecture summary
  - Key commands
  - Important patterns (SCD Type 2, sector mapping)
- ✅ Peer reviewed

**Subtasks**:
1. Update README.md
2. Update CLAUDE.md
3. Peer review

**Effort**: 1 story point

---

### STORY 9.2: Write Integration Tests for End-to-End Pipeline

**Story Goal**: Create integration tests that validate full Bronze → Silver → Gold flow.

**User Story**: As a developer, I need end-to-end integration tests so I can verify the pipeline works after code changes.

**Acceptance Criteria**:
- ✅ Test suite created: `tests/integration/test_congress_pipeline_e2e.py`
- ✅ Test scenarios:
  - Full pipeline: ingest → Silver → Gold → API query
  - Incremental pipeline: update → Silver upsert → Gold refresh
  - SCD Type 2: member party change propagates to Gold
  - Trade window correlation: trade within window detected
- ✅ Tests run in CI (GitHub Actions)
- ✅ Tests include cleanup (delete test data)
- ✅ All tests pass

**Effort**: 5 story points

---

#### TASK 9.2.1: Write Test - Full Pipeline E2E

**Description**: Test complete pipeline from ingestion to API query.

**DoD**:
- ✅ Test file: `tests/integration/test_congress_pipeline_e2e.py`
- ✅ Test function: `test_full_pipeline_e2e()`
- ✅ Test steps:
  1. Queue sample member, bill, vote to Bronze (via orchestrator or direct upload)
  2. Trigger Silver Lambda (or wait for SQS processing)
  3. Run Gold scripts
  4. Query API: `GET /api/v1/congress/members/{bioguide_id}`
  5. Assert: member data correct, bills listed, votes listed
- ✅ Test includes cleanup
- ✅ Test passes in CI

**Subtasks**:
1. Create test file
2. Create fixtures: sample member, bill, vote JSON
3. Write test: upload → process → query
4. Assert correctness at each stage
5. Add cleanup
6. Run locally
7. Run in CI

**Effort**: 3 story points

---

#### TASK 9.2.2: Write Test - Incremental Pipeline and CDC

**Description**: Test incremental updates and SCD Type 2.

**DoD**:
- ✅ Test function: `test_incremental_update_with_party_change()`
- ✅ Test steps:
  1. Ingest member with party="D"
  2. Process to Silver, verify is_current=True
  3. Ingest updated member with party="R"
  4. Process to Silver, verify 2 records (old closed, new current)
  5. Run Gold scripts
  6. Query API, verify current party="R"
  7. Query fact_member_vote with historical vote, verify party_at_vote_time correct
- ✅ Test passes

**Subtasks**:
1. Write test
2. Create fixtures: member v1 and v2
3. Upload and process v1
4. Upload and process v2
5. Verify SCD Type 2 in Silver
6. Verify Gold propagation
7. Assert API response

**Effort**: 2 story points

---

#### TASK 9.2.3: Write Test - Trade Window Correlation

**Description**: Test FD-Congress correlation logic.

**DoD**:
- ✅ Test function: `test_trade_window_correlation()`
- ✅ Test steps:
  1. Populate Silver: member, bill with action on 2024-01-15, sector="Technology"
  2. Populate Gold FD: transaction by member on 2024-01-05 (10 days before), ticker in Technology sector
  3. Run `congress_build_analytics_trade_windows.py`
  4. Query: `fact_member_bill_trade_window`
  5. Assert: window_type="before_action_30d" has transaction_count=1, sectors_affected includes "Technology"
- ✅ Test passes

**Subtasks**:
1. Write test
2. Create fixtures: bill action, FD transaction
3. Populate Silver and Gold FD
4. Run analytics script
5. Read fact_member_bill_trade_window
6. Assert window logic

**Effort**: 2 story points

---

---

## Summary: Epic Breakdown

| Feature | Stories | Total Story Points | Estimated Days |
|---------|---------|-------------------|----------------|
| 1. Infrastructure & Bronze | 4 | 13 | 8-10 |
| 2. Silver Layer - Schema & CDC | 3 | 13 | 8-10 |
| 3. Silver Layer - Bill Subresources | 2 | 8 | 5-7 |
| 4. Gold Layer - Dimensions & Facts | 4 | 13 | 8-10 |
| 5. Gold Analytics - FD Correlation | 4 | 13 | 8-10 |
| 6. Pipeline Orchestration | 2 | 8 | 5-7 |
| 7. API Endpoints | 2 | 13 | 8-10 |
| 8. Website Integration | 3 | 13 | 8-10 |
| 9. Documentation & Testing | 2 | 8 | 5-7 |
| **TOTAL** | **26 Stories** | **102 Story Points** | **~63-81 days** |

**Adjusted for Parallel Work**: ~50-60 calendar days (assuming some tasks can be parallelized)

**Recommended Sprint Cadence**: 2-week sprints, ~13 story points per sprint, ~8 sprints total

---

## Sprint Planning Recommendation

### Sprint 1-2: Foundation (Features 1-2)
- Focus: Bronze ingestion, Silver schema, member/bill transforms
- Deliverable: Bronze populated, Silver dim_member + dim_bill queryable

### Sprint 3-4: Silver Expansion (Feature 3)
- Focus: Bill subresources, votes, committees
- Deliverable: All Silver tables populated

### Sprint 5-6: Gold Layer (Features 4-5)
- Focus: Gold dimensions, facts, analytics tables
- Deliverable: Gold layer queryable, FD-Congress joins working

### Sprint 7: Orchestration & API (Features 6-7)
- Focus: Pipeline automation, API endpoints
- Deliverable: Daily sync running, APIs live

### Sprint 8: Website & Docs (Features 8-9)
- Focus: UI updates, documentation, testing
- Deliverable: Website shows Congress data, docs complete

---

## Success Metrics (DoD for Epic)

✅ **Bronze Layer**
- Congress 118 data fully ingested: 5000+ bills, 500+ members, 1000+ votes
- Bronze S3 keys follow Hive partition pattern
- SQS queues drain to zero (no stuck messages)

✅ **Silver Layer**
- All Silver tables queryable with pyarrow
- SCD Type 2 member history validated (party changes tracked)
- Upsert logic prevents duplicates

✅ **Gold Layer**
- All Gold dimensions, facts, aggregates built
- `fact_member_bill_trade_window` populated with 1000+ rows
- Trade window logic validated with sample data

✅ **API**
- All endpoints return <500ms p95 latency
- API Gateway routes configured
- CORS enabled, CloudFront caching works

✅ **Website**
- Member profiles show legislative activity tab
- Stock pages show legislative exposure
- Bill-trade correlation dashboard accessible

✅ **Pipeline**
- Daily incremental sync runs via GitHub Actions
- Full pipeline completes in <2 hours for Congress 118
- Error rate <1% (DLQ messages / total messages)

✅ **Documentation**
- All docs/*.md files created and peer reviewed
- README.md and CLAUDE.md updated
- API documentation (OpenAPI spec) updated

✅ **Testing**
- All integration tests pass in CI
- End-to-end pipeline test validates full flow
- Test coverage >80% for new code

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Congress.gov API rate limits | High | Medium | Implement rate limiting, queue-based backoff, spread ingestion over time |
| Large data volume (slow processing) | Medium | High | Use partition pruning, optimize Parquet schemas, increase Lambda concurrency |
| Schema evolution (API changes) | Medium | Medium | Version schemas, add migration scripts, monitor API changelog |
| Sector mapping inaccuracy | Low | Medium | Peer review mapping table, allow manual overrides, track unmapped subjects |
| SCD Type 2 complexity | Medium | Low | Thorough unit tests, validate with historical data |

---

**This backlog is now fully groomed and ready for development. Each task has clear DoD, subtasks, and effort estimates. Proceed with sprint planning and execution.**
