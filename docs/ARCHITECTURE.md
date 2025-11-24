# Architecture Documentation

## Overview

This pipeline implements a **medallion architecture** data lake for U.S. House financial disclosure reports, using AWS-native services for scalable, cost-effective processing.

### Design Principles

1. **Fidelity first**: Bronze layer preserves original data byte-for-byte
2. **Auditability**: Every transformation tracks provenance and version
3. **Reproducibility**: Any output can be regenerated from bronze + code version
4. **Cost efficiency**: Optimize for AWS free tier; minimize Lambda execution time
5. **Transparency**: Open source, documented, legally compliant

---

## Medallion Architecture

### Bronze Layer (Raw)

**Purpose**: Immutable archive of source data exactly as provided by House Clerk

**Storage**: S3 with versioning enabled

**Contents**:
- Original zip files (`2025FD.zip`)
- Index files (XML and TXT)
- PDF files (one per filing)

**Metadata** (S3 object tags or metadata):
- `source_url`: Where it was downloaded from
- `download_timestamp`: When ingestion occurred
- `http_etag`, `http_last_modified`: HTTP headers for caching
- `ingest_version`: Pipeline version (for reproducibility)

### Silver Layer (Normalized)

**Purpose**: Cleaned, typed, queryable data in analytics-ready format

**Storage**: Parquet files with Snappy compression

**Tables**:
1. `house_fd_filings`: One row per filing (from XML index)
2. `house_fd_documents`: PDF metadata and extraction status
3. `house_fd_text`: Extracted text per document/page

**Partitioning**: By `year` for query efficiency

**Schema enforcement**: JSON Schema validation before write

### Gold Layer (Query-Facing)

**Purpose**: Denormalized, business-logic-enriched tables for end users

**Status**: Phase 2 (not yet implemented)

**Planned tables**:
- `fd_filings_flat`: Clean, user-friendly filing metadata
- `holdings`: Parsed asset holdings with tickers
- `transactions`: Parsed buy/sell transactions
- `member_rollups`: Aggregated views by member/ticker/sector

---

## S3 Bucket Layout

```
s3://congress-disclosures/
│
├── bronze/
│   └── house/
│       └── financial/
│           ├── year=2008/
│           ├── year=2009/
│           ├── ...
│           └── year=2025/
│               ├── raw_zip/
│               │   └── 2025FD.zip
│               ├── index/
│               │   ├── 2025FD.xml
│               │   └── 2025FD.txt
│               └── pdfs/
│                   └── 2025/
│                       ├── 8221216.pdf
│                       ├── 8221217.pdf
│                       └── ...
│
├── silver/
│   └── house/
│       └── financial/
│           ├── filings/
│           │   ├── year=2025/
│           │   │   ├── part-0000.parquet
│           │   │   └── ...
│           │   └── ...
│           ├── documents/
│           │   └── year=2025/
│           │       ├── part-0000.parquet
│           │       └── ...
│           └── text/
│               └── year=2025/
│                   ├── doc_id=8221216/
│                   │   └── raw_text.txt.gz
│                   └── ...
│
└── gold/                           # Phase 2
    └── house/
        └── financial/
            ├── filings_flat/
            ├── holdings/
            └── transactions/
```

### Path Determinism

All S3 keys are **deterministic** and computable from `(year, DocID)`:

```python
# Bronze PDF
f"bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf"

# Silver text
f"silver/house/financial/text/year={year}/doc_id={doc_id}/raw_text.txt.gz"

# Silver filings (one Parquet per year)
f"silver/house/financial/filings/year={year}/part-0000.parquet"
```

This enables idempotent re-processing and easy data validation.

---

## Data Flow

### Phase 1: Ingestion & Extraction

```
┌─────────────────────────────────────────────────────────────────┐
│                      Manual Trigger / EventBridge               │
│                          { "year": 2025 }                       │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                ┌───────────────────────────────┐
                │  Lambda: house_fd_ingest_zip  │
                │                               │
                │  1. Download YEARFD.zip       │
                │  2. Upload to bronze/raw_zip  │
                │  3. Extract & upload index    │
                │  4. Extract & upload PDFs     │
                │  5. Emit SQS messages         │
                └───────┬───────────────────┬───┘
                        │                   │
                        ▼                   ▼
        ┌───────────────────────┐   ┌─────────────────────┐
        │ Invoke:               │   │ SQS Queue:          │
        │ house_fd_index_to_    │   │ house-fd-extract-   │
        │ silver (sync)         │   │ queue               │
        └───────┬───────────────┘   └──────┬──────────────┘
                │                           │
                ▼                           │
    ┌────────────────────────────┐         │
    │ Silver: house_fd_filings   │         │
    │ (Parquet table)            │         │
    └────────────────────────────┘         │
                                            ▼
                            ┌──────────────────────────────┐
                            │  Lambda:                     │
                            │  house_fd_extract_document   │
                            │                              │
                            │  1. Download PDF from S3     │
                            │  2. Detect text layer        │
                            │  3. Extract via pypdf or     │
                            │     AWS Textract             │
                            │  4. Upload text to silver    │
                            │  5. Update documents table   │
                            └──────────────┬───────────────┘
                                           │
                                           ▼
                            ┌────────────────────────────┐
                            │ Silver: house_fd_documents │
                            │ Silver: house_fd_text      │
                            └────────────────────────────┘
```

### Trigger Mechanisms

**Current (Phase 1)**:
- Manual invocation: `aws lambda invoke --function-name house-fd-ingest-zip --payload '{"year": 2025}'`
- Ad-hoc re-processing of specific years

**Planned (Phase 2)**:
- **EventBridge cron**: Nightly at 2 AM UTC, check for new filings in current year
- **Step Functions orchestration**: Coordinate multi-year backfills, retry logic, monitoring

---

## AWS Services

### Lambda Functions

| Function                       | Trigger       | Memory | Timeout | Concurrency |
| ------------------------------ | ------------- | ------ | ------- | ----------- |
| `house-fd-ingest-zip`          | Manual / EB   | 1024MB | 5 min   | 1           |
| `house-fd-index-to-silver`     | Synchronous   | 512MB  | 2 min   | 1           |
| `house-fd-extract-document`    | SQS (batched) | 2048MB | 5 min   | 10          |

**Runtime**: Python 3.11

**Packaging**: Zip with dependencies (via `pip install -t` or Lambda Layers)

### SQS Queue

**Name**: `house-fd-extract-queue`

**Type**: Standard (FIFO optional for strict ordering, but not required)

**Configuration**:
- **Visibility timeout**: 6 minutes (Lambda timeout + buffer)
- **Message retention**: 4 days
- **Dead letter queue**: `house-fd-extract-dlq` after 3 retries
- **Batching**: Lambda receives up to 10 messages per invocation

### S3 Bucket

**Name**: `congress-disclosures` (configurable via Terraform)

**Features**:
- **Versioning**: Enabled on bronze layer
- **Lifecycle policies**:
  - Bronze: Never expire (immutable archive)
  - Silver: Transition to Glacier after 1 year (optional)
- **Encryption**: SSE-S3 (AES-256)
- **Public access**: Blocked (use CloudFront or presigned URLs for public serving)

### IAM Roles

**Lambda execution role**: `house-fd-lambda-role`

Permissions:
- `s3:GetObject`, `s3:PutObject` on `congress-disclosures/*`
- `sqs:ReceiveMessage`, `sqs:DeleteMessage` on extract queue
- `textract:DetectDocumentText` (for image-based PDFs)
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### CloudWatch

**Log groups**:
- `/aws/lambda/house-fd-ingest-zip`
- `/aws/lambda/house-fd-index-to-silver`
- `/aws/lambda/house-fd-extract-document`

**Retention**: 30 days (configurable)

**Metrics** (custom):
- `PdfExtraction.Success` (count)
- `PdfExtraction.Failed` (count)
- `PdfExtraction.Duration` (ms, per doc)

---

## Silver Table Schemas

### `house_fd_filings`

**Grain**: One row per filing (DocID)

| Column             | Type      | Description                                  |
| ------------------ | --------- | -------------------------------------------- |
| `doc_id`           | STRING    | Unique document identifier                   |
| `year`             | INT       | Filing year                                  |
| `filing_date`      | DATE      | Date filing was submitted                    |
| `filing_type`      | STRING    | Code (e.g., 'A' = Annual, 'N' = New Member) |
| `prefix`           | STRING    | Title (Hon., Dr., etc.)                      |
| `first_name`       | STRING    | Filer first name                             |
| `last_name`        | STRING    | Filer last name                              |
| `suffix`           | STRING    | Name suffix (Jr., III, etc.)                 |
| `state_district`   | STRING    | e.g., 'CA-11'                                |
| `raw_xml_path`     | STRING    | S3 key to source XML                         |
| `raw_txt_path`     | STRING    | S3 key to source TXT                         |
| `pdf_s3_key`       | STRING    | S3 key to PDF in bronze                      |
| `bronze_ingest_ts` | TIMESTAMP | When zip was ingested                        |
| `silver_ingest_ts` | TIMESTAMP | When this row was created                    |
| `source_system`    | STRING    | Always 'house_fd'                            |

**Partitioning**: `year` (Hive-style)

**Format**: Parquet, Snappy compression

### `house_fd_documents`

**Grain**: One row per PDF (DocID)

| Column                  | Type      | Description                                   |
| ----------------------- | --------- | --------------------------------------------- |
| `doc_id`                | STRING    | Document ID                                   |
| `year`                  | INT       | Filing year                                   |
| `pdf_s3_key`            | STRING    | Bronze PDF location                           |
| `pdf_sha256`            | STRING    | Content hash (for deduplication)              |
| `pdf_file_size_bytes`   | BIGINT    | File size                                     |
| `pages`                 | INT       | Number of pages                               |
| `has_embedded_text`     | BOOLEAN   | True if PDF has text layer                    |
| `extraction_method`     | STRING    | 'pypdf', 'textract-detect', 'failed', 'none'  |
| `extraction_status`     | STRING    | 'pending', 'success', 'failed'                |
| `extraction_version`    | STRING    | Code version (semantic or git hash)           |
| `extraction_timestamp`  | TIMESTAMP | Last extraction attempt                       |
| `extraction_error`      | STRING    | Error message if failed                       |
| `text_s3_key`           | STRING    | Silver text location (if success)             |
| `json_s3_key`           | STRING    | Structured JSON location (Phase 2)            |

**Partitioning**: `year`

**Update pattern**: Upsert by `(year, doc_id)` after each extraction run

### `house_fd_text`

**Grain**: One row per document (or per page, if needed)

| Column        | Type   | Description                 |
| ------------- | ------ | --------------------------- |
| `doc_id`      | STRING | Document ID                 |
| `year`        | INT    | Filing year                 |
| `page_number` | INT    | Page number (1-indexed)     |
| `text`        | STRING | Extracted text for the page |

**Alternative**: Store as gzipped text files in S3 instead of Parquet (current approach)

---

## PDF Extraction Logic

### Decision Tree

```
1. Download PDF from S3
2. Inspect PDF:
   a. Count pages (pypdf.PdfReader.pages)
   b. Sample first 2 pages for text content
   c. If total extracted chars > 100: has_embedded_text = True

3. Branch:

   IF has_embedded_text == True:
       ├─> Use pypdf.PdfReader
       ├─> Extract text per page
       ├─> Concatenate to single string
       └─> extraction_method = 'pypdf'

   ELSE (image-based PDF):
       ├─> Convert to images (pdf2image or pypdfium2)
       ├─> Call AWS Textract DetectDocumentText
       │   ├─> Async if > 10 pages
       │   └─> Sync if <= 10 pages
       ├─> Parse Textract JSON response
       └─> extraction_method = 'textract-detect'

4. Upload text to silver:
   ├─> Gzip compress text
   └─> Upload to silver/house/financial/text/year={year}/doc_id={doc_id}/raw_text.txt.gz

5. Update house_fd_documents Parquet:
   └─> Upsert row with extraction metadata
```

### Error Handling

- **HTTP errors** (zip download): Retry 3x with exponential backoff
- **Textract throttling**: Catch `ProvisionedThroughputExceededException`, re-queue with delay
- **Corrupt PDFs**: Mark `extraction_status='failed'`, log error, continue
- **Lambda timeout**: SQS message returns to queue automatically (visibility timeout)

### Cost Optimization

**Textract free tier**: 1,000 pages/month for DetectDocumentText

For 2025 FD filings:
- Assume ~10,000 filings
- If 20% are image-based (~2,000)
- Average 5 pages each = **10,000 pages total**

Cost:
- First 1,000 pages: Free
- Next 9,000 pages: $1.50 per 1,000 = **$13.50/month**

**Fallback**: Can use Tesseract OCR to eliminate Textract cost (tradeoff: slower, less accurate)

---

## Monitoring & Observability

### CloudWatch Logs

All Lambda functions emit structured logs:

```json
{
  "timestamp": "2025-11-24T20:00:00Z",
  "level": "INFO",
  "function": "house_fd_extract_document",
  "doc_id": "8221216",
  "year": 2025,
  "extraction_method": "pypdf",
  "duration_ms": 1234,
  "pages": 12,
  "message": "Extraction successful"
}
```

### Custom Metrics

**Namespace**: `CongressDisclosures`

Metrics:
- `Ingestion.FilingsProcessed` (count, dimension: year)
- `Extraction.Success` (count, dimension: method)
- `Extraction.Failed` (count, dimension: error_type)
- `Extraction.Duration` (ms, dimension: method, has_text_layer)

**Alarms**:
- Extraction failure rate > 5% (SNS alert)
- Lambda errors > 10 in 5 minutes (SNS alert)
- SQS DLQ message count > 0 (SNS alert)

---

## Data Quality & Validation

### Bronze Layer

**Validation**:
- ZIP file integrity (CRC check)
- XML well-formedness (parse with `xml.etree.ElementTree`)
- PDF file header (`%PDF-` magic bytes)

**Checksums**:
- Store SHA256 hash in S3 metadata
- On re-ingestion, compare hash to detect changes

### Silver Layer

**Schema validation**:
- JSON Schema enforcement before Parquet write
- Type coercion (e.g., parse `filing_date` string to DATE)
- Null handling (explicit in schema)

**Deduplication**:
- Upsert by `(year, doc_id)` to handle re-runs
- Track `silver_ingest_ts` to identify latest version

**Referential integrity**:
- Every `pdf_s3_key` in `house_fd_filings` must exist in bronze
- Every `doc_id` in `house_fd_documents` must exist in `house_fd_filings`

### Audit Trail

For every record:
- **Lineage**: `bronze_pdf_s3_key` → `extraction_method` → `extraction_version`
- **Reproducibility**: Re-run extraction with same version → same output
- **Versioning**: If extraction logic changes, increment `extraction_version`, re-process

---

## Security & Access Control

### IAM Policies

**Principle of least privilege**:
- Lambdas can only read/write to `congress-disclosures/*`
- Lambdas cannot delete S3 objects (use lifecycle policies instead)
- No cross-account access (single AWS account)

### Data Sensitivity

Financial disclosure reports are **public records**, but:
- No personally identifiable information (PII) beyond what's in public filings
- No Social Security Numbers, account numbers, or home addresses
- Still subject to 5 U.S.C. § 13107 usage restrictions

### Public Access

**Phase 1**: Bucket is private

**Phase 2** (planned):
- CloudFront distribution with signed URLs
- Or: Public read access to `gold/*` prefix only
- Rate limiting to prevent abuse

---

## Performance & Scalability

### Throughput Estimates

**Single year ingestion** (2025):
- Download zip: ~5-10 seconds (100-500 MB)
- Upload to bronze: ~5-10 seconds
- Parse XML: <1 second
- Write silver/filings: ~2 seconds
- **Total: ~20-30 seconds**

**PDF extraction** (per document):
- Text-based (pypdf): ~0.5-2 seconds
- Image-based (Textract): ~5-15 seconds (sync), ~30-60 seconds (async)
- SQS concurrency: 10 Lambdas = **~100-200 docs/minute**

**Full year** (10,000 filings):
- Ingestion: 30 seconds
- Extraction: 50-100 minutes (assuming 20% image-based)

### Scaling Limits

- **Lambda concurrency**: Default 1,000 per account (can request increase)
- **SQS throughput**: Nearly unlimited (standard queue)
- **Textract quota**: 10 transactions/second (can request increase)
- **S3**: No practical limit for this use case

### Cost Estimates (Monthly)

**Assumptions**: Process 2025 data once, store long-term

| Service          | Usage                     | Cost           |
| ---------------- | ------------------------- | -------------- |
| S3 storage       | 20 GB (bronze + silver)   | $0.46          |
| Lambda (compute) | 5,000 GB-seconds          | $0.08          |
| Lambda (requests)| 10,000 invocations        | $0.002         |
| Textract         | 9,000 pages (after free)  | $13.50         |
| SQS              | 10,000 messages           | $0.004         |
| CloudWatch Logs  | 1 GB ingestion            | $0.50          |
| **Total**        |                           | **~$14.50**    |

**Annual** (processing 2008-2025): ~$250-300 (mostly Textract)

---

## Future Enhancements (Phase 2+)

### Gold Layer
- Denormalized tables for BI tools (Tableau, Metabase)
- Pre-aggregated rollups (member-level, ticker-level)

### Structured Extraction
- OpenAI GPT-4 with JSON Schema for parsing assets/transactions
- Training set for fine-tuning on FD report structure
- Confidence scoring for extracted fields

### Member ID Crosswalk
- Map `(first_name, last_name, state_district)` → Congress.gov bioguide ID
- Handle name changes, district redistricting

### Public API
- REST API (FastAPI or API Gateway)
- GraphQL endpoint
- Rate limiting, API keys

### Automation
- EventBridge cron for nightly checks
- Step Functions for multi-year orchestration
- Slack/email alerts on ingestion failures

### Data Versioning
- Track schema evolution (V1, V2, ...)
- Support concurrent versions (e.g., re-extract with new parser, compare)

---

## Disaster Recovery

### Backup Strategy

**Bronze layer**: S3 versioning enabled
- Point-in-time recovery
- Can revert to any previous version of zip/PDF

**Silver layer**: Reproducible from bronze
- If lost, re-run ingestion → extraction pipeline
- No additional backup needed (cost optimization)

**Terraform state**: Stored in S3 with versioning
- Can recover from accidental infrastructure changes

### Recovery Procedures

**Scenario**: Entire S3 bucket deleted
1. Restore from S3 versioning (if enabled)
2. Or: Re-run ingestion for all years (2008-2025)
3. Estimated recovery time: ~2-3 hours (Lambda concurrency)

**Scenario**: Corrupted silver Parquet files
1. Delete affected partitions
2. Re-run `house_fd_index_to_silver` and `house_fd_extract_document` for affected years
3. Verify row counts match original

**Scenario**: Lambda function fails to deploy
1. Revert Terraform to last known good state
2. Investigate failure (check CloudWatch logs, IAM permissions)
3. Fix and re-deploy

---

## References

- **Source data**: [House Financial Disclosures](https://disclosures-clerk.house.gov/FinancialDisclosure)
- **Legal framework**: [5 U.S.C. § 13107](https://www.law.cornell.edu/uscode/text/5/13107)
- **AWS Textract**: [Documentation](https://docs.aws.amazon.com/textract/)
- **Medallion architecture**: [Databricks pattern](https://www.databricks.com/glossary/medallion-architecture)

---

**Last Updated**: November 24, 2025
