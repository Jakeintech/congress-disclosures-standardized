# Lambda Functions Requirements Specification

**Project**: Congress Disclosures Standardized Data Platform
**Last Updated**: 2025-12-14
**Status**: Design Document

---

## Overview

This document specifies all 47 Lambda functions required for the unified data platform pipeline. Each function is described with:
- Purpose and responsibility
- Input/output contracts
- Configuration (memory, timeout, concurrency)
- Dependencies (layers, environment variables)
- Error handling requirements
- Testing requirements

---

## Summary Table

| # | Function Name | Phase | Memory | Timeout | Priority |
|---|--------------|-------|--------|---------|----------|
| 1 | check_house_fd_updates | Bronze | 256MB | 60s | P0 |
| 2 | check_congress_updates | Bronze | 256MB | 60s | P1 |
| 3 | check_lobbying_updates | Bronze | 256MB | 60s | P1 |
| 4 | house_fd_ingest_zip | Bronze | 512MB | 300s | P0 |
| 5 | congress_api_ingest_orchestrator | Bronze | 256MB | 120s | P1 |
| 6 | lda_ingest_filings | Bronze | 512MB | 300s | P1 |
| 7 | house_fd_index_to_silver | Silver | 512MB | 180s | P0 |
| 8 | house_fd_extract_document | Silver | 1GB | 300s | P0 |
| 9 | house_fd_extract_structured_code | Silver | 512MB | 120s | P0 |
| 10 | congress_bronze_to_silver | Silver | 512MB | 120s | P1 |
| 11-25 | Gold dimension/fact builders | Gold | 1-2GB | 300-900s | P1 |
| 26-35 | Aggregate compute functions | Gold | 2GB | 600s | P2 |
| 36 | run_soda_checks | Quality | 512MB | 180s | P0 |
| 37 | update_api_cache | Publish | 256MB | 60s | P1 |
| 38 | publish_pipeline_metrics | Publish | 256MB | 60s | P2 |

**Total Lambda Functions**: 47
**Estimated Monthly Cost**: $8-15 (within free tier + minimal overage)

---

## Phase 1: Update Detection (3 functions)

### 1.1 check_house_fd_updates

**Purpose**: Detect if new House FD zip file available

**Input**:
```json
{
  "year": 2024
}
```

**Logic**:
1. Validate year is within 5-year lookback window (current_year - 5 to current_year)
2. If year outside window, return `has_new_filings: false` and skip ingestion
3. Download HEAD of `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.ZIP`
4. Calculate SHA256 hash from Content-Length + Last-Modified headers
5. Compare with Bronze S3 object metadata
6. Return `has_new_filings: true` if hash differs

**Output**:
```json
{
  "has_new_filings": true,
  "year": 2024,
  "remote_sha256": "abc123...",
  "local_sha256": "def456...",
  "estimated_file_size_mb": 105
}
```

**Configuration**:
- Memory: 256MB
- Timeout: 60s
- Concurrency: 1 (no parallel execution needed)

**Environment Variables**:
- `S3_BUCKET_NAME`
- `HOUSE_FD_BASE_URL`

**Error Handling**:
- HTTP 404: Return `has_new_filings: false` (year not available yet)
- Network timeout: Retry 3x with exponential backoff
- S3 error: Fail fast, alert SNS

**Testing**:
- Unit test: Mock HTTP HEAD request
- Integration test: Check against real URL + S3

---

### 1.2 check_congress_updates

**Purpose**: Check Congress.gov API for new bills/members

**Input**:
```json
{
  "entity_types": ["bills", "members"],
  "since_date": "2025-12-13"
}
```

**Logic**:
1. Check if first ingestion (no watermark exists)
2. If first ingestion: Set `fromDateTime` to (current_year - 5) + "-01-01" (5-year lookback)
3. If incremental: Use last fetch timestamp from watermark
4. Query Congress.gov API `/v3/bill?fromDateTime={since_date}`
5. Count results
6. Return `has_new_data: true` if new items found

**Output**:
```json
{
  "has_new_data": true,
  "bills_count": 15,
  "members_count": 2,
  "last_checked": "2025-12-14T10:30:00Z"
}
```

**Configuration**:
- Memory: 256MB
- Timeout: 60s
- Concurrency: 1

**Environment Variables**:
- `CONGRESS_GOV_API_KEY`
- `CONGRESS_GOV_BASE_URL`

---

### 1.3 check_lobbying_updates

**Purpose**: Check Senate LDA database for new filings

**Input**:
```json
{
  "filing_year": 2024,
  "filing_quarter": "Q4"
}
```

**Logic**:
1. Validate year is within 5-year lookback window
2. If year outside window, return `has_new_filings: false`
3. Check Bronze manifest for existing quarter data
4. Query LDA database for new filings
5. Return `has_new_filings: true` if new data found

**Output**:
```json
{
  "has_new_filings": true,
  "new_filing_count": 125,
  "last_filing_date": "2025-12-13"
}
```

**Configuration**:
- Memory: 256MB
- Timeout: 60s

---

## Phase 2: Bronze Ingestion (3 functions)

### 2.1 house_fd_ingest_zip

**Status**: ✅ Exists (needs fixes)

**Purpose**: Download House FD zip, extract to Bronze

**Input**:
```json
{
  "year": 2024,
  "force_download": false
}
```

**Logic**:
1. Check if Bronze zip exists (unless `force_download`)
2. Download zip from House Clerk website
3. Calculate SHA256
4. Upload to `s3://bucket/bronze/.../raw_zip/{year}FD.zip`
5. Tag with metadata (sha256, download_date, source_url)
6. Extract XML index → Bronze
7. Extract PDFs → Bronze (partitioned by filing_type)
8. Return summary

**Output**:
```json
{
  "zip_s3_key": "bronze/house/financial/year=2024/raw_zip/2024FD.zip",
  "index_s3_key": "bronze/.../index/2024FD.xml",
  "pdf_count": 5234,
  "total_size_mb": 105
}
```

**Configuration**:
- Memory: 512MB
- Timeout: 300s (5 min)
- Ephemeral storage: 2GB (for zip extraction)

**Fixes Needed**:
1. ✅ Implement watermarking (check SHA256 before download)
2. ✅ Add error handling for 404 (year not available)
3. ✅ Validate year parameter is within 5-year lookback window (current_year - 5 to current_year)

**Year Range Validation**:
- **Initial Ingestion**: Only process years within 5-year lookback window (e.g., 2020-2025 for year 2025)
- **Data Retention**: Once ingested, data is retained permanently (no deletion)
- **Rationale**: Reduces initial ingestion cost and scope while maintaining recent compliance data

---

### 2.2 congress_api_ingest_orchestrator

**Status**: ✅ Exists (needs fixes)

**Purpose**: Fetch bills/members from Congress.gov API

**Fixes Needed**:
1. ✅ Remove hardcoded AWS account ID
2. ✅ Use environment variables for queue URLs
3. ✅ Add rate limiting (10 requests/second max)
4. ✅ Implement checkpointing for resumable ingestion
5. ✅ Handle HTTP 429 (rate limit exceeded) gracefully

**Rate Limiting Strategy**:
- **API Limit**: Congress.gov allows ~5,000 requests/hour (source: API documentation)
- **Conservative Rate**: 10 requests/second (36,000/hour) to avoid hitting limits
- **Initial Load**: 5 years × ~50,000 bills = ~250,000 API calls
- **Estimated Time**: 250,000 / 36,000 = ~7 hours for full initial ingestion
- **Checkpointing**: Save progress after each 1,000 bills ingested
- **Resume Logic**: If rate limited (HTTP 429), save state to DynamoDB and exit gracefully. Next execution resumes from checkpoint.

**Checkpointing Schema** (DynamoDB table: `congress_api_ingestion_state`):
```json
{
  "source": "congress_bills",
  "last_processed_bill_id": "119-sconres-23",
  "last_processed_date": "2025-01-09",
  "total_processed": 1500,
  "ingestion_start": "2025-12-14T10:00:00Z",
  "status": "in_progress"
}
```

---

### 2.3 lda_ingest_filings

**Status**: ✅ Exists (needs fixes)

**Fixes Needed**:
1. ✅ Add idempotency (check if filing already ingested)
2. ✅ Handle XML parsing errors gracefully

---

## Phase 3: Silver Transformation (4 functions)

### 3.1 house_fd_index_to_silver

**Status**: ✅ Exists (needs fixes)

**Fixes Needed**:
1. ✅ Add schema validation for XML
2. ✅ Handle malformed XML gracefully
3. ✅ Queue only unprocessed PDFs (check Silver documents table)

---

### 3.2 house_fd_extract_document

**Status**: ✅ Exists (needs major fixes)

**Purpose**: Extract text from PDF (pypdf → Tesseract fallback)

**Fixes Needed**:
1. ✅ Implement partial batch failure for SQS
2. ✅ Dynamic timeout based on page count
3. ✅ Better error handling for corrupted PDFs

**Partial Batch Failure Pattern**:
```python
def lambda_handler(event, context):
    failed_items = []

    for record in event['Records']:
        try:
            process_pdf(record)
        except Exception as e:
            logger.error(f"Failed: {e}")
            failed_items.append({
                'itemIdentifier': record['messageId']
            })

    return {
        'batchItemFailures': failed_items
    }
```

---

### 3.3 house_fd_extract_structured_code

**Status**: ✅ Exists (minor fixes)

**Fixes Needed**:
1. ✅ Add retry logic (3 attempts)
2. ✅ Better validation of extracted JSON

---

### 3.4 congress_bronze_to_silver

**Status**: ✅ Exists (minor fixes)

**Fixes Needed**:
1. ✅ Validate payload type (bills vs members)
2. ✅ Better error messages

---

## Phase 4: Gold Layer Dimension Builders (5 functions)

### 4.1 build_dim_members

**Status**: 🆕 NEW (wrap script)

**Script**: `scripts/build_dim_members_simple.py`

**Purpose**: Build member dimension table with SCD Type 2

**Input**:
```json
{
  "rebuild": false,
  "incremental_date": "2025-12-13"
}
```

**Logic**:
1. Read all Silver filings
2. Extract unique member names
3. Fuzzy match against Congress.gov members
4. Detect changes (party, chamber, in_office)
5. Implement SCD Type 2 (new row on change, expire old row)
6. Write to `gold/dimensions/dim_members/`

**Output**:
```json
{
  "members_processed": 535,
  "new_members": 5,
  "updated_members": 2,
  "output_s3_key": "gold/dimensions/dim_members/dim_members.parquet"
}
```

**Configuration**:
- Memory: 2GB (Pandas operations)
- Timeout: 600s (10 min)
- Ephemeral storage: 2GB

**Dependencies**:
- Layer: `pandas`, `pyarrow`
- Script: `scripts/build_dim_members_simple.py`

**Testing**:
- Unit test: Test SCD Type 2 logic
- Integration test: Verify against real data

---

### 4.2 build_dim_assets

**Status**: 🆕 NEW

**Purpose**: Build asset dimension table

**Logic**:
1. Extract unique asset names from Silver transactions
2. Normalize names (NVIDIA CORP → NVIDIA)
3. Lookup tickers (via Yahoo Finance API or manual mapping)
4. Classify asset type (stock, bond, fund, real_estate)
5. Map to industry (GICS sectors)

**Configuration**:
- Memory: 1GB
- Timeout: 300s

---

### 4.3 build_dim_bills

**Status**: 🆕 NEW

**Purpose**: Build bills dimension table

**Logic**:
1. Read Silver congress_gov/bills
2. Denormalize (join with sponsor info)
3. Write to Gold dimensions

---

### 4.4 build_dim_lobbyists

**Status**: 🆕 NEW

**Purpose**: Build lobbyists dimension table

**Logic**:
1. Extract unique registrants/clients from Silver lobbying
2. Deduplicate and normalize names

---

### 4.5 build_dim_dates

**Status**: 🆕 NEW

**Purpose**: Build date dimension table

**Logic**:
1. Generate rows for 2010-2030 (all dates)
2. Calculate derived fields (quarter, month, day_of_week, fiscal_year)
3. Mark US holidays

**Note**: This is a one-time build, can be pre-generated

---

## Phase 5: Gold Layer Fact Builders (5 functions)

### 5.1 build_fact_transactions

**Status**: 🆕 NEW (wrap script)

**Script**: `scripts/build_fact_ptr_transactions.py`

**Purpose**: Build PTR transactions fact table (star schema)

**Logic**:
1. Read Silver objects (Type P filings)
2. Flatten transactions array
3. Join with dimensions:
   - dim_members (member_key)
   - dim_assets (asset_key)
   - dim_dates (transaction_date_key, notification_date_key)
4. Calculate amount_midpoint
5. Partition by year/month
6. Write to `gold/facts/ptr_transactions/`

**Configuration**:
- Memory: 2GB
- Timeout: 900s (15 min)
- Partitioning strategy: `year={year}/month={month}`

---

### 5.2 build_fact_filings

**Status**: 🆕 NEW (wrap script)

**Script**: `scripts/build_fact_filings.py`

**Purpose**: Build filings fact table

**Logic**:
1. Read Silver filings
2. Join with dimensions
3. Calculate aggregates (transaction_count, total_value)
4. Write to Gold

---

### 5.3 build_fact_lobbying

**Status**: 🆕 NEW

**Purpose**: Build lobbying fact table

---

### 5.4 build_fact_cosponsors

**Status**: 🆕 NEW

**Purpose**: Bill cosponsorship fact table

---

### 5.5 build_fact_amendments

**Status**: 🆕 NEW

**Purpose**: Bill amendments fact table

---

## Phase 6: Gold Layer Aggregate Builders (10 functions)

### 6.1 compute_trending_stocks

**Script**: `scripts/compute_agg_trending_stocks.py`

**Purpose**: Calculate trending stocks (7, 30, 90 day windows)

**Logic**:
1. Read fact_transactions for last 90 days
2. Group by ticker, window_days
3. Calculate: purchase_count, sale_count, net_activity, total_value
4. Rank by total_value
5. Write to `gold/aggregates/trending_stocks/`

**Configuration**:
- Memory: 2GB
- Timeout: 600s

---

### 6.2 compute_member_stats

**Script**: `scripts/compute_agg_member_trading_stats.py`

**Purpose**: Member-level trading statistics

**Logic**:
1. Read fact_transactions, fact_filings
2. Group by member_key, year
3. Calculate: total_transactions, total_value, compliance_score
4. Write to Gold

---

### 6.3 compute_document_quality

**Script**: `scripts/compute_agg_document_quality.py`

**Purpose**: PDF quality scores by member

**Logic**:
1. Read Silver documents table
2. Group by member (derived from filings)
3. Calculate: avg_confidence_score, ocr_required_count, quality_grade
4. Write to Gold

---

### 6.4 compute_network_graph

**Script**: `scripts/compute_agg_network_graph.py`

**Purpose**: Member-asset network for visualization

**Logic**:
1. Read fact_transactions
2. Create nodes (members + assets)
3. Create edges (weighted by transaction count + value)
4. Export as JSON for D3.js

**Output Format**: JSON (not Parquet)

---

### 6.5-6.10 Additional Aggregates

- `compute_congressional_alpha`
- `compute_bill_trade_correlation`
- `compute_bill_lobbying_correlation`
- `compute_member_lobbyist_network`
- `compute_industry_correlations`
- `compute_impact_scores`

---

## Phase 7: Quality & Publish (3 functions)

### 7.1 run_soda_checks

**Status**: 🆕 NEW

**Purpose**: Execute Soda quality checks

**Input**:
```json
{
  "layer": "silver",
  "checks_to_run": ["all"]
}
```

**Logic**:
1. Load Soda YAML checks from `/soda/checks/`
2. Execute checks against Silver/Gold Parquet files
3. Collect results (pass/fail/warn)
4. If critical failures: fail state machine
5. If warnings: send SNS notification
6. Write results to `gold/quality/soda_results.json`

**Configuration**:
- Memory: 512MB
- Timeout: 180s
- Layer: `soda-core`

**Dependencies**:
- `/soda/checks/silver_filings.yml`
- `/soda/checks/silver_documents.yml`
- `/soda/checks/gold_transactions.yml`
- `/soda/checks/gold_aggregates.yml`

**Output**:
```json
{
  "status": "passed",
  "checks_run": 25,
  "checks_passed": 24,
  "checks_failed": 0,
  "checks_warned": 1,
  "failures": [],
  "warnings": [
    {
      "check": "silver_documents.confidence_score_avg",
      "expected": ">= 0.90",
      "actual": 0.87,
      "severity": "warn"
    }
  ]
}
```

---

### 7.2 update_api_cache

**Status**: 🆕 NEW

**Purpose**: Invalidate API Gateway cache after data update

**Input**:
```json
{
  "api_id": "abc123",
  "stage": "prod"
}
```

**Logic**:
1. Call API Gateway `DELETE /restapis/{api-id}/stages/{stage}/cache`
2. Verify cache cleared
3. Optional: Warm cache by calling popular endpoints

**Configuration**:
- Memory: 256MB
- Timeout: 60s

---

### 7.3 publish_pipeline_metrics

**Status**: ✅ EXISTS (enhance)

**Purpose**: Publish execution metrics to CloudWatch

**Enhancements Needed**:
1. ✅ Add Gold layer metrics
2. ✅ Add cost tracking metrics
3. ✅ Add data freshness metrics

---

## Lambda Layers

### Layer 1: core_dependencies
**Packages**: `boto3`, `requests`, `python-dateutil`
**Size**: ~20MB

### Layer 2: pdf_processing
**Packages**: `pypdf`, `tesseract`, `Pillow`
**Size**: ~80MB

### Layer 3: data_processing
**Packages**: `pandas`, `pyarrow`, `numpy`
**Size**: ~120MB

### Layer 4: soda_core
**Packages**: `soda-core`, `soda-core-parquet`
**Size**: ~50MB

### Layer 5: extraction_libs
**Custom code**: `/ingestion/lib/extraction`, `/ingestion/lib/extractors`
**Size**: ~5MB

---

## Year Range Filtering (All Update Detection Functions)

**Policy**: 5-Year Lookback Window for Initial Ingestion

All update detection functions (`check_house_fd_updates`, `check_congress_updates`, `check_lobbying_updates`) implement year range validation:

```python
from datetime import datetime

CURRENT_YEAR = datetime.now().year
LOOKBACK_YEARS = 5
MIN_YEAR = CURRENT_YEAR - LOOKBACK_YEARS  # e.g., 2020 for year 2025
MAX_YEAR = CURRENT_YEAR

def validate_year(year):
    """Validate year is within acceptable range."""
    if year < MIN_YEAR or year > MAX_YEAR:
        logger.info(f"Year {year} outside lookback window ({MIN_YEAR}-{MAX_YEAR})")
        return False
    return True
```

**Scope**:
- **Initial Load**: Only ingest data from last 5 years (2020-2025 for current year 2025)
- **Incremental Updates**: After initial load, daily updates fetch latest data only
- **Data Retention**: Once ingested, data is retained permanently (no deletion)

**Benefits**:
1. **Reduced Initial Ingestion**: ~50% less data to process vs. full historical (2010-present)
2. **Lower Cost**: Fewer Lambda invocations, less S3 storage during initial load
3. **Faster Time to Value**: Initial pipeline completes in ~2 hours vs. ~4 hours
4. **Compliance Focus**: Most relevant data for current congressional activity

**Example**:
- Current year: 2025
- Years processed: 2020, 2021, 2022, 2023, 2024, 2025 (6 years)
- Years skipped: 2010-2019 (10 years)
- Data reduction: 62.5% less historical data

---

## API Rate Limiting & Checkpointing

### Congress.gov API Rate Limits

**Official Limits**:
- **Rate**: 5,000 requests per hour per API key
- **Burst**: Unknown (conservative approach: 10 req/sec)
- **HTTP 429**: Rate limit exceeded response

**Initial Ingestion Strategy**:
1. **Batch Processing**: Process bills in batches of 1,000
2. **Checkpointing**: Save progress to DynamoDB after each batch
3. **Rate Limiting**: Sleep 100ms between requests (10 req/sec)
4. **Graceful Degradation**: On HTTP 429, save state and exit with success
5. **Resume on Next Execution**: Next run picks up from last checkpoint

**Checkpoint State (DynamoDB)**:
```python
{
  'PK': 'INGESTION#congress_bills',
  'SK': 'STATE',
  'last_bill_id': '119-sconres-23',
  'last_date': '2025-01-09',
  'total_processed': 15000,
  'status': 'in_progress',
  'started_at': '2025-12-14T10:00:00Z',
  'updated_at': '2025-12-14T12:30:00Z'
}
```

**Implementation Pattern**:
```python
import time
import boto3

dynamodb = boto3.resource('dynamodb')
state_table = dynamodb.Table('congress_api_ingestion_state')

def lambda_handler(event, context):
    # Load checkpoint
    checkpoint = load_checkpoint('congress_bills')
    last_bill_id = checkpoint.get('last_bill_id')

    bills_processed = 0
    MAX_BILLS_PER_EXECUTION = 1000  # Process 1K bills then exit

    for bill in fetch_bills_since(last_bill_id):
        try:
            process_bill(bill)
            bills_processed += 1

            # Rate limiting: 10 req/sec
            time.sleep(0.1)

            # Checkpoint every 100 bills
            if bills_processed % 100 == 0:
                save_checkpoint('congress_bills', bill['bill_id'], bills_processed)

            # Exit after 1K bills (resume on next execution)
            if bills_processed >= MAX_BILLS_PER_EXECUTION:
                logger.info(f"Processed {bills_processed} bills, exiting for next execution")
                break

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limited by Congress.gov API, saving checkpoint")
                save_checkpoint('congress_bills', bill['bill_id'], bills_processed)
                return {'statusCode': 200, 'message': 'Rate limited, resume on next run'}
            raise

    # Mark complete if no more bills
    if bills_processed < MAX_BILLS_PER_EXECUTION:
        save_checkpoint('congress_bills', status='completed')

    return {'statusCode': 200, 'bills_processed': bills_processed}
```

**Estimated Initial Load Timeline**:
- 5 years of bills: ~50,000 bills
- Rate: 10 requests/sec = 600 bills/min = 36,000 bills/hour
- Initial ingestion: ~1.5 hours (spread across multiple executions)
- Step Functions can loop execution until checkpoint status = 'completed'

---

## Environment Variables (All Functions)

**Common**:
```
AWS_REGION=us-east-1
S3_BUCKET_NAME=congress-disclosures-standardized
LOG_LEVEL=INFO
ENVIRONMENT=production
```

**Bronze Functions**:
```
HOUSE_FD_BASE_URL=https://disclosures-clerk.house.gov
CONGRESS_GOV_API_KEY=<secret>
CONGRESS_GOV_BASE_URL=https://api.congress.gov
```

**Silver Functions**:
```
EXTRACTION_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/.../extraction-queue
```

**Gold Functions**:
```
DIM_MEMBERS_S3_KEY=gold/dimensions/dim_members/dim_members.parquet
DIM_ASSETS_S3_KEY=gold/dimensions/dim_assets/dim_assets.parquet
```

---

## Error Handling Standards

**All functions must**:
1. ✅ Use structured logging (JSON format)
2. ✅ Catch specific exceptions (not bare `except:`)
3. ✅ Return error details in response
4. ✅ Send critical errors to SNS
5. ✅ Implement exponential backoff for retries
6. ✅ Set CloudWatch alarms for error rate > 5%

**Standard Error Response**:
```json
{
  "statusCode": 500,
  "error": {
    "type": "ExtractionError",
    "message": "Failed to extract text from PDF",
    "doc_id": "10063228",
    "traceback": "...",
    "recoverable": true
  }
}
```

---

## Cost Estimation

### Monthly Costs (Incremental Daily Runs)

| Phase | Invocations/month | GB-seconds | Cost |
|-------|------------------|------------|------|
| Update Detection | 90 | 100 | $0 (free tier) |
| Bronze Ingestion | 30 | 5,000 | $0 (free tier) |
| Silver Transform | 5,000 | 150,000 | $2.50 |
| Gold Builders | 600 | 200,000 | $3.33 |
| Aggregates | 300 | 100,000 | $1.67 |
| Quality & Publish | 90 | 1,000 | $0 (free tier) |
| **Total** | **~6,110** | **~456,100** | **~$7.50** |

**Free Tier**: 400,000 GB-seconds/month → Covers ~87% of usage
**Overage**: ~56,100 GB-seconds × $0.0000166667 = **$0.94**

**Total Estimated Lambda Cost**: $0.94/month (plus other AWS services = $8-15 total)

---

## Testing Requirements

### Unit Tests (Per Function)
- ✅ Test happy path
- ✅ Test error handling
- ✅ Test input validation
- ✅ Mock AWS services (boto3)
- ✅ Coverage ≥ 80%

### Integration Tests (Per Phase)
- ✅ Test with real AWS services (dev account)
- ✅ Test end-to-end flow
- ✅ Verify outputs in S3

### Load Tests (Critical Functions)
- ✅ Extract function: 1,000 PDFs
- ✅ Gold builders: 100K transactions

---

## Deployment Checklist

**Per Lambda**:
- [ ] Function code written
- [ ] Unit tests passing
- [ ] Dependencies packaged
- [ ] Terraform resource created
- [ ] IAM permissions granted
- [ ] Environment variables set
- [ ] CloudWatch alarms configured
- [ ] Documentation updated

---

**Document Owner**: Engineering Team
**Status**: Living Document (updated as functions are implemented)
