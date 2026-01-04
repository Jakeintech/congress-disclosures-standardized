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

## Step Functions Architecture (STORY-015)

### State Machine Orchestration

The pipeline uses **AWS Step Functions** to orchestrate complex workflows with parallel processing, error handling, and quality gates.

**State Machines**:
- `house_fd_pipeline` - House Financial Disclosures pipeline
- `congress_pipeline` - Congress.gov API data pipeline  
- `lobbying_pipeline` - Senate LDA lobbying disclosures
- `cross_dataset_correlation` - Cross-dataset analytics

**Key Features**:
- **Parallel Processing**: Map states with `MaxConcurrency: 10` for PDF extraction
- **Error Handling**: Exponential backoff retries, DLQ integration, SNS alerts
- **Quality Gates**: Soda quality checks between Bronze→Silver→Gold
- **Watermarking**: Prevents duplicate processing via SHA256 hashing + DynamoDB

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
        update_watermark(data_type, datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), count)
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

### Execution Patterns

**Scheduled Execution** (EventBridge):
```json
{
  "execution_type": "scheduled",
  "year": 2025
}
```

**Manual Execution** (GitHub Actions):
```bash
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --name "manual-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"manual","year":2024}'
```

**Multi-Year Initial Load** (STORY-046):
```json
{
  "execution_type": "initial_load",
  "parameters": {
    "years": [2020, 2021, 2022, 2023, 2024, 2025]
  }
}
```

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

- **X-Ray Tracing**: Distributed tracing enabled for all state machines

**Step Functions Console**: Visual execution history with state-by-state timing

See `docs/STATE_MACHINE_FLOW.md` for detailed diagrams.


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

- **`reprocess_filings`** (`ingestion/lambdas/reprocess_filings/handler.py`) **[NEW - STORY-055]**
  - Selective reprocessing of filings when extraction logic improves
  - Targets specific filing types and year ranges
  - Generates before/after quality comparison reports
  - Stores multiple extraction versions side-by-side (no data loss)
  - Supports version promotion/rollback for safe iteration
  - See `ingestion/lambdas/reprocess_filings/README.md` for usage

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

The master orchestrator is `scripts/run_smart_pipeline.py`. It supports 4 modes:

1. **Full Reset**: `python3 scripts/run_smart_pipeline.py --mode full --year 2025`
   - Purges queue → Ingests (overwrite) → Waits for extraction → Aggregates

2. **Incremental**: `python3 scripts/run_smart_pipeline.py --mode incremental`
   - Ingests (skip existing) → Waits for extraction → Aggregates
   - Used for daily updates (GitHub Actions cron)

3. **Reprocess**: `python3 scripts/run_smart_pipeline.py --mode reprocess`
   - Re-triggers index-to-silver → Waits → Aggregates

4. **Aggregate Only**: `python3 scripts/run_smart_pipeline.py --mode aggregate`
   - Skips ingestion, just runs Gold scripts

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
- **`version_utils.py`**: Version comparison, registry management (STORY-055)
- **`version_comparison.py`**: Quality metrics calculation, comparison reports (STORY-055)

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
# 1. Setup
make setup
# Edit .env with your AWS credentials

# 2. Deploy infrastructure
make init
make deploy

# 3. Run pipeline
make run-pipeline
```

### Daily Incremental Update
Automated via GitHub Actions (`.github/workflows/daily_incremental.yml`):
```bash
python3 scripts/run_smart_pipeline.py --mode incremental
```

### Manual Re-processing
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