# Congress.gov Pipeline - Development Instructions

## For AI Coding Assistants (Claude, Cursor, etc.)

These instructions allow you to pick up development at any phase of the Congress.gov pipeline implementation.

**Last Updated**: 2025-12-04

## ✅ COMPLETED WORK (Session 2025-12-04)

### STORY 1.1: S3 Bucket Structure & Terraform Base Configuration ✅ COMPLETE
- **TASK 1.1.1** ✅: Created `docs/CONGRESS_S3_SCHEMA.md` with complete Bronze layer structure
- **TASK 1.1.2** ✅: Created `infra/terraform/variables_congress.tf` with all Congress variables
- **TASK 1.1.3** ✅: Created test S3 prefixes, verified bucket policies (no changes needed)

### STORY 1.2: SQS Queues and Dead Letter Queues ✅ COMPLETE
- **TASK 1.2.1** ✅: Created `infra/terraform/sqs_congress.tf` with 4 queues deployed
- **TASK 1.2.2** ✅: Created `infra/terraform/cloudwatch_congress.tf` with 3 alarms + log groups
- **TASK 1.2.2** ✅: Created `docs/MONITORING.md` with comprehensive monitoring guide

### STORY 1.3: Lambda Function - congress_api_fetch_entity (IN PROGRESS)
- **TASK 1.3.1** ✅: Created `ingestion/lib/congress_api_client.py` with full API client + unit tests
- **TASK 1.3.2** 🔄: IN PROGRESS - Creating Lambda handler for entity fetch
- **TASK 1.3.3** ⏳: Pending - Package and deploy Lambda
- **TASK 1.3.4** ⏳: Pending - Write integration test

**Deployed Infrastructure**:
- 4 SQS Queues (fetch + silver, each with DLQ)
- 3 CloudWatch Alarms (2 DLQs + 1 queue age)
- 3 CloudWatch Log Groups (pre-created for Lambdas)
- 9 S3 Bronze prefixes (member, bill, bill_*, house_vote, senate_vote, committee)

**Files Created**:
- `docs/CONGRESS_S3_SCHEMA.md`
- `docs/MONITORING.md`
- `infra/terraform/variables_congress.tf`
- `infra/terraform/sqs_congress.tf`
- `infra/terraform/cloudwatch_congress.tf`
- `ingestion/lib/congress_api_client.py`
- `tests/unit/test_congress_api_client.py`

**Files Modified**:
- `infra/terraform/iam.tf` (added Congress queues to SQS policy)
- `.env.example` (added CONGRESS_API_KEY)

---

## Initial Context Loading

Before starting any phase, read these files in order:

1. **`CLAUDE.md`** - Project overview, FD pipeline architecture, coding standards
2. **`docs/ARCHITECTURE.md`** - Detailed system architecture, medallion pattern
3. **`docs/CONGRESS_PIPELINE_AGILE_BACKLOG.md`** - Complete agile backlog with all features, stories, tasks
4. **`README.md`** - Quick start guide, common commands
5. **`.env.example`** - Environment variables structure
6. **`Makefile`** - Existing build and deployment commands

---

## Phase 1: Infrastructure & Bronze Layer

**Goal**: Establish AWS infrastructure (Lambdas, SQS, S3 structure) and implement Bronze layer raw data ingestion from Congress.gov API.

### Copy-Paste Instruction:
```
Read these files in order:
1. CLAUDE.md
2. docs/ARCHITECTURE.md
3. docs/CONGRESS_PIPELINE_AGILE_BACKLOG.md
4. README.md
5. .env.example
6. Makefile

Now continue with FEATURE 1 (Infrastructure & Bronze Layer Foundation) from the backlog.

Proceed where we left off sequentially through all tasks in Feature 1.

Follow these principles:
- Match the existing FD pipeline patterns (see ingestion/lambdas/house_fd_* for reference)
- Use the same folder structure, naming conventions, and code style
- Reuse existing utilities from ingestion/lib/ where applicable
- Create new Congress-specific utilities in ingestion/lib/ with "congress_" prefix
- Follow the DoD (Definition of Done) checkboxes exactly for each task
- Test each task before moving to the next
- Update documentation as you go

Key reference files to examine:
- ingestion/lambdas/house_fd_ingest_zip/handler.py (for Lambda patterns)
- ingestion/lambdas/house_fd_extract_document/handler.py (for SQS processing)
- ingestion/lib/s3_utils.py (for S3 operations)
- infra/terraform/lambda.tf (for Terraform Lambda patterns)
- infra/terraform/sqs.tf (for SQS queue patterns)

When complete, all Bronze layer infrastructure will be deployed and operational.
```

---

## Phase 2: Silver Layer - Normalized Schema & CDC

**Goal**: Transform Bronze raw JSON into queryable Silver Parquet tables with SCD Type 2 history for members and upsert logic for all entities.

### Copy-Paste Instruction:
```
Read these files in order:
1. CLAUDE.md
2. docs/ARCHITECTURE.md
3. docs/CONGRESS_PIPELINE_AGILE_BACKLOG.md
4. docs/CONGRESS_S3_SCHEMA.md (if it exists from Phase 1)
5. README.md

Now continue with FEATURE 2 (Silver Layer - Normalized Schema & CDC) from the backlog.

Start with STORY 2.1, TASK 2.1.1 and proceed sequentially through all tasks in Feature 2.

Key reference files to examine:
- ingestion/lib/parquet_writer.py (for Parquet upsert patterns)
- ingestion/lambdas/house_fd_index_to_silver/handler.py (for Silver transform patterns)
- Any existing schema documentation in docs/

Focus areas:
- SCD Type 2 implementation for member history (party changes, district changes)
- Parquet upsert logic with source_last_modified CDC
- Schema mapping from Congress.gov API JSON to normalized Silver tables
- Proper partition key selection for query performance

When complete, Silver layer will have queryable Parquet tables for members, bills, votes, and committees.
```

---

## Phase 3: Silver Layer - Bill Subresources

**Goal**: Ingest and transform bill subresources (actions, cosponsors, committees, subjects, titles) from Bronze to Silver.

### Copy-Paste Instruction:
```
Read these files in order:
1. CLAUDE.md
2. docs/CONGRESS_PIPELINE_AGILE_BACKLOG.md
3. docs/CONGRESS_SILVER_SCHEMA.md (created in Phase 2)
4. ingestion/lib/congress_schema_mappers.py (created in Phase 2)

Now continue with FEATURE 3 (Silver Layer - Bill Subresources) from the backlog.

Start with STORY 3.1, TASK 3.1.1 and proceed sequentially through all tasks in Feature 3.

Key reference files:
- Previous Lambda and schema mapper implementations from Phase 2
- Congress.gov API documentation for subresource endpoints

Focus areas:
- Extend fetch Lambda to queue subresource jobs after bill fetch
- Handle array/nested JSON structures (actions, cosponsors)
- Flatten arrays to individual rows in Silver tables
- Maintain referential integrity (bill_id foreign keys)

When complete, Silver layer will have complete bill data including actions, cosponsors, committees, subjects, and titles.
```

---

## Phase 4: Gold Layer - Dimensions & Facts

**Goal**: Build denormalized Gold dimensions and fact tables for API consumption and analytics.

### Copy-Paste Instruction:
```
Read these files in order:
1. CLAUDE.md
2. docs/CONGRESS_PIPELINE_AGILE_BACKLOG.md
3. docs/CONGRESS_SILVER_SCHEMA.md
4. scripts/build_dim_members_simple.py (existing FD Gold script for reference)
5. scripts/build_fact_filings.py (existing FD Gold script for reference)

Now continue with FEATURE 4 (Gold Layer - Dimensions & Facts) from the backlog.

Start with STORY 4.1, TASK 4.1.1 and proceed sequentially through all tasks in Feature 4.

Key reference files:
- Existing Gold layer scripts in scripts/ (build_dim_*, build_fact_*)
- Silver Parquet tables from Phase 2 & 3

Focus areas:
- Denormalization: join Silver tables to create enriched Gold dimensions
- Aggregations: count bills, votes, disclosures per member
- Fact table grain: ensure one row per atomic event (member-vote, member-bill)
- Partition strategy: balance query performance vs object count
- Script-based approach (not Lambda) for CPU-intensive Pandas operations

When complete, Gold layer will have API-ready dimensions (member, bill) and fact tables (member_bill_role, member_vote).
```

---

## Phase 5: Gold Analytics - FD-to-Congress Correlation

**Goal**: Build Gold analytics tables that join FD transactions with Congressional activity (bills, votes) to enable correlation analysis.

### Copy-Paste Instruction:
```
Read these files in order:
1. CLAUDE.md
2. docs/CONGRESS_PIPELINE_AGILE_BACKLOG.md
3. docs/CONGRESS_GOLD_SCHEMA.md (created in Phase 4)
4. gold/house/financial/fact_ptr_transactions/ (existing FD transaction data)
5. scripts/compute_agg_member_trading_stats.py (existing FD analytics for reference)

Now continue with FEATURE 5 (Gold Analytics - FD-to-Congress Correlation Tables) from the backlog.

Start with STORY 5.1, TASK 5.1.1 and proceed sequentially through all tasks in Feature 5.

Key reference files:
- Gold Congress tables from Phase 4
- Gold FD tables (fact_ptr_transactions, dim_member)
- Congress.gov policy area values (query Silver dim_bill to see examples)

Focus areas:
- Sector mapping: Create mapping table from Congress.gov policy areas/subjects to financial sectors (Technology, Healthcare, Energy, etc.)
- Time window joins: Match FD transactions to bill actions within +/- 30 days
- Sector filtering: Only include trades in sectors affected by the bill
- Performance: Use partition pruning to avoid full table scans
- Complex aggregations: Count transactions, sum amounts, list tickers per window

This is the CORE VALUE of the entire project: correlating member trading with legislative activity.

When complete, you can answer: "Did this member trade stocks in sectors affected by bills they sponsored/voted on?"
```

---

## Phase 6: Pipeline Orchestration & Incremental Sync

**Goal**: Create master orchestration script and daily incremental sync workflow.

### Copy-Paste Instruction:
```
Read these files in order:
1. CLAUDE.md
2. docs/CONGRESS_PIPELINE_AGILE_BACKLOG.md
3. scripts/run_smart_pipeline.py (existing FD pipeline orchestrator for reference)
4. .github/workflows/daily_incremental.yml (existing FD automation for reference)

Now continue with FEATURE 6 (Pipeline Orchestration & Incremental Sync) from the backlog.

Start with STORY 6.1, TASK 6.1.1 and proceed sequentially through all tasks in Feature 6.

Key reference files:
- Existing pipeline orchestration script (run_smart_pipeline.py)
- All Lambda functions and scripts created in Phases 1-5

Focus areas:
- Orchestration modes: full (backfill), incremental (daily updates), aggregate (Gold only)
- Queue polling: Wait for SQS queues to drain before proceeding to next step
- Error handling: Retry failed steps, log to CloudWatch
- State management: Track last ingest timestamp for incremental mode
- GitHub Actions: Automated daily sync via cron

When complete, you'll have a single command to run the entire pipeline and automated daily updates.
```

---

## Phase 7: API Endpoints for Congress Data

**Goal**: Create API Lambda functions to expose Congress data via REST endpoints.

### Copy-Paste Instruction:
```
Read these files in order:
1. CLAUDE.md
2. docs/CONGRESS_PIPELINE_AGILE_BACKLOG.md
3. docs/API_STRATEGY.md
4. api/lambdas/get_members/handler.py (existing FD API for reference)
5. api/lambdas/get_member/handler.py (existing FD API for reference)
6. infra/terraform/api_gateway.tf (existing API Gateway config)

Now continue with FEATURE 7 (API Endpoints for Congress Data) from the backlog.

Start with STORY 7.1, TASK 7.1.1 and proceed sequentially through all tasks in Feature 7.

Key reference files:
- Existing API Lambda functions in api/lambdas/
- Gold Parquet tables from Phases 4 & 5
- API Gateway Terraform configuration

Focus areas:
- Read from Gold layer (not Silver) for fast queries
- Use pyarrow filters for partition pruning
- Pagination: limit, offset parameters
- Response format: Consistent JSON structure with existing FD APIs
- CORS headers: Enable for website access
- Error handling: 404 for not found, 400 for bad requests, 500 for server errors
- Performance: <500ms p95 latency target

When complete, REST API will expose Congress data (bills, votes, members) and FD-Congress correlation analytics.
```

---

## Phase 8: Website Integration & Visualization

**Goal**: Update website to display Congress data and FD-Congress correlations.

### Copy-Paste Instruction:
```
Read these files in order:
1. CLAUDE.md
2. docs/CONGRESS_PIPELINE_AGILE_BACKLOG.md
3. website/index.html (existing website structure)
4. website/member.html or website/js/member.js (existing member profile page)
5. website/stock.html or website/js/stock.js (existing stock detail page)

Now continue with FEATURE 8 (Website Integration & Visualization) from the backlog.

Start with STORY 8.1, TASK 8.1.1 and proceed sequentially through all tasks in Feature 8.

Key reference files:
- Existing website components/pages in website/
- API endpoints created in Phase 7
- CSS/styling framework used in existing website

Focus areas:
- Member profile: Add "Legislative Activity" tab with bills, votes, committee memberships
- Stock detail: Add "Legislative Exposure" section with related bills and member trades
- New dashboard: "Bill-Trade Correlation" showing suspicious trading patterns
- Responsive design: Mobile-friendly layouts
- Data fetching: Call API endpoints created in Phase 7
- Loading states: Show spinners while fetching data
- Error handling: Display user-friendly error messages

When complete, website will display Congress data integrated with FD disclosures for comprehensive transparency.
```

---

## Phase 9: Documentation & Testing

**Goal**: Comprehensive documentation and test coverage for Congress pipeline.

### Copy-Paste Instruction:
```
Read these files in order:
1. CLAUDE.md
2. docs/CONGRESS_PIPELINE_AGILE_BACKLOG.md
3. CONTRIBUTING.md (contribution guidelines, commit conventions)
4. tests/integration/test_congress_*.py (any tests created so far)
5. All implementation files from Phases 1-8

Now continue with FEATURE 9 (Documentation & Testing) from the backlog.

Start with STORY 9.1, TASK 9.1.1 and proceed sequentially through all tasks in Feature 9.

Key reference files:
- Existing documentation in docs/
- Existing integration tests in tests/integration/
- All code implemented in Phases 1-8

Focus areas:
- Documentation: Comprehensive guides for architecture, usage, troubleshooting
- Architecture diagrams: Use Mermaid or ASCII diagrams for data flow
- API documentation: Update OpenAPI spec (docs/openapi.yaml)
- Integration tests: End-to-end tests validating Bronze → Silver → Gold → API
- Test coverage: >80% for new code
- Validation tests: SCD Type 2 correctness, trade window logic, sector mapping

When complete, the project will be fully documented and tested, ready for production deployment and open-source contributions.
```

---

## Quick Reference: Phase Dependencies

```
Phase 1 (Infrastructure & Bronze)
  ↓
Phase 2 (Silver - Core Entities)
  ↓
Phase 3 (Silver - Bill Subresources)
  ↓
Phase 4 (Gold - Dimensions & Facts)
  ↓
Phase 5 (Gold - FD Correlation) ← CORE VALUE
  ↓
Phase 6 (Orchestration)
  ↓
Phase 7 (API Endpoints)
  ↓
Phase 8 (Website)
  ↓
Phase 9 (Documentation & Testing)
```

---

## General Guidelines for All Phases

### Code Style
- Follow existing patterns in `ingestion/lambdas/house_fd_*` for Lambda structure
- Use Python 3.11, type hints, Google-style docstrings
- Format with Black (88 char line length)
- Lint with flake8
- Prefix Congress-specific utilities with `congress_` to distinguish from FD utilities

### Testing
- Write unit tests for utilities (`tests/unit/test_congress_*.py`)
- Write integration tests for Lambda functions (`tests/integration/test_congress_*.py`)
- Test locally before deploying: `pytest tests/unit/test_congress_api_client.py -v`
- Run integration tests in CI: `pytest tests/integration/ -v --aws`

### Terraform
- Add Congress resources to new files: `infra/terraform/lambda_congress.tf`, `sqs_congress.tf`, etc.
- Follow existing naming: `congress-disclosures-{environment}-{resource-name}`
- Use Hive partitioning for S3: `key=value` format (e.g., `congress=118`, `bill_type=hr`)
- Tag all resources: `Project=congress-disclosures`, `Component=ingestion|silver|gold|api`

### Deployment
- Package Lambdas: `make package-congress-fetch`
- Deploy infrastructure: `cd infra/terraform && terraform apply`
- Deploy website: `make deploy-website`
- Monitor logs: `make logs-congress-fetch` (add Makefile target if needed)

### Debugging
- Check SQS queue status: `make check-congress-queue` (add Makefile target)
- Check DLQ: `make check-congress-dlq` (add Makefile target)
- View Lambda logs: `aws logs tail /aws/lambda/congress-disclosures-development-fetch-entity --follow`
- Validate pipeline: Run integration tests after each phase

---

## Getting Help

If you encounter ambiguity or need clarification:
1. Check the backlog DoD (Definition of Done) for the specific task
2. Examine reference files listed in each phase instruction
3. Review existing FD pipeline code for patterns
4. Check `docs/ARCHITECTURE.md` for high-level design decisions
5. Ask the user for clarification if DoD is unclear or requirements conflict

---

## Success Criteria (All Phases Complete)

✅ Congress 118 data fully ingested to Bronze (5000+ bills, 500+ members, 1000+ votes)
✅ Silver Parquet tables queryable with SCD Type 2 member history
✅ Gold analytics tables enable FD-to-legislation correlation queries
✅ API endpoints return <500ms p95 latency
✅ Website displays Congress data integrated with FD disclosures
✅ Daily incremental sync runs via GitHub Actions
✅ All integration tests pass in CI
✅ Documentation complete and peer-reviewed

**You will have built a world-class Congressional transparency platform.**
