# System Architecture

Comprehensive technical architecture documentation for the Congress Financial Disclosures pipeline.

## Table of Contents
- [Overview](#overview)
- [Design Principles](#design-principles)
- [Medallion Architecture](#medallion-architecture)
- [S3 Bucket Layout](#s3-bucket-layout)
- [Data Flow](#data-flow)
- [AWS Services](#aws-services)
- [Silver Table Schemas](#silver-table-schemas)
- [PDF Extraction Logic](#pdf-extraction-logic)
- [Monitoring & Observability](#monitoring--observability)
- [Data Quality & Validation](#data-quality--validation)
- [Security & Access Control](#security--access-control)
- [Performance & Scalability](#performance--scalability)

---

## Overview

This pipeline implements a **medallion architecture** data lake for U.S. House financial disclosure reports, using AWS-native services for scalable, cost-effective processing.

**Core Technology Stack**:
- **Compute**: AWS Lambda (Python 3.11)
- **Storage**: Amazon S3 (Parquet + gzipped text)
- **Orchestration**: AWS Step Functions
- **Queuing**: Amazon SQS
- **Monitoring**: Amazon CloudWatch
- **Infrastructure**: Terraform

---

## Design Principles

1. **Fidelity first**: Bronze layer preserves original data byte-for-byte
2. **Auditability**: Every transformation tracks provenance and version
3. **Reproducibility**: Any output can be regenerated from bronze + code version
4. **Cost efficiency**: Optimize for AWS free tier; minimize Lambda execution time
5. **Transparency**: Open source, documented, legally compliant

---

## Medallion Architecture

### Bronze Layer (Raw/Immutable)

**Purpose**: Byte-for-byte preservation of source data exactly as provided by House Clerk

**Storage**: `s3://congress-disclosures-standardized/bronze/house/financial/`

**Contents**:
- `year=YYYY/raw_zip/YYYYFD.zip` - Original zip from House Clerk
- `year=YYYY/index/YYYYFD.xml` - Filing metadata index
- `year=YYYY/filing_type={P,A,T,...}/pdfs/{doc_id}.pdf` - Individual PDFs

**Metadata** (S3 object tags):
- `source_url`: Where it was downloaded from
- `download_timestamp`: When ingestion occurred
- `http_etag`, `http_last_modified`: HTTP headers for caching
- `ingest_version`: Pipeline version (for reproducibility)
- `extraction-processed`: Tracks extraction state to prevent duplicates

**Important**: S3 object metadata tagging prevents duplicate processing across pipeline re-runs. Each PDF tagged with `extraction-processed: true` after processing.

### Silver Layer (Normalized/Queryable)

**Purpose**: Cleaned, typed, queryable data in analytics-ready format

**Storage**: `s3://congress-disclosures-standardized/silver/house/financial/`

**Format**: Parquet files with Snappy compression + gzipped text

**Tables**:
1. **filings/** - Filing metadata from XML index (one row per filing)
2. **documents/** - PDF metadata + extraction status
3. **text/extraction_method={direct_text,ocr}/** - Extracted text (gzipped)
4. **objects/filing_type=type_{p,a,t}/** - Structured extraction JSON

**Partitioning**: By `year` for query efficiency

**Schema enforcement**: Pydantic models validate before write

### Gold Layer (Query-Facing/Aggregated)

**Purpose**: Denormalized, business-logic-enriched tables for end users

**Storage**: `s3://congress-disclosures-standardized/gold/house/financial/`

**Structure**:
- **dimensions/** - Member, asset, date dimensions (SCD Type 2)
  - `dim_members/` - Member names, bioguide IDs, party affiliation
  - `dim_assets/` - Asset names, tickers, descriptions
  - `dim_date/` - Date dimension for time-series analysis
  - `dim_filing_types/` - Filing type reference data
- **facts/** - Transactions, filings (star schema, partitioned by year/month)
  - `fact_ptr_transactions/` - All PTR transactions
  - `fact_filings/` - All filings metadata
- **aggregates/** - Pre-computed metrics
  - `agg_trending_stocks/` - Rolling window stock activity (7d, 30d, 90d)
  - `agg_member_trading_stats/` - Trading volume, compliance metrics
  - `agg_document_quality/` - Member-level PDF quality scores
  - `agg_network_graph/` - Member-asset network analysis

---

## S3 Bucket Layout

```
s3://congress-disclosures-standardized/
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
│           ├── text/
│           │   └── extraction_method=direct_text/
│           │       └── year=2025/
│           │           ├── doc_id=8221216/
│           │           │   └── raw_text.txt.gz
│           │           └── ...
│           └── objects/
│               └── filing_type=type_p/
│                   └── year=2025/
│                       └── doc_id=20033421.json
│
└── gold/
    └── house/
        └── financial/
            ├── dimensions/
            │   ├── dim_members/
            │   ├── dim_assets/
            │   ├── dim_date/
            │   └── dim_filing_types/
            ├── facts/
            │   ├── fact_ptr_transactions/
            │   └── fact_filings/
            └── aggregates/
                ├── agg_trending_stocks/
                ├── agg_member_trading_stats/
                ├── agg_document_quality/
                └── agg_network_graph/
```

### Path Determinism

All S3 keys are **deterministic** and computable from `(year, DocID)`:

```python
# Bronze PDF
f"bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf"

# Silver text
f"silver/house/financial/text/extraction_method=direct_text/year={year}/doc_id={doc_id}/raw_text.txt.gz"

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
                            │  3. Extract via pypdf or OCR │
                            │  4. Upload text to silver    │
                            │  5. Update documents table   │
                            │  6. Queue structured extract │
                            └──────────────┬───────────────┘
                                           │
                                           ▼
                            ┌──────────────────────────────┐
                            │  Lambda:                     │
                            │  house_fd_extract_structured │
                            │                              │
                            │  1. Route to filing-type     │
                            │     specific extractor       │
                            │  2. Code-based extraction    │
                            │  3. Output JSON to Silver    │
                            └──────────────┬───────────────┘
                                           │
                                           ▼
                            ┌────────────────────────────┐
                            │ Silver: objects/           │
                            │ (Structured JSON)          │
                            └────────────────────────────┘
```

### Trigger Mechanisms

**Current**:
- Manual invocation: `aws lambda invoke --function-name house-fd-ingest-zip --payload '{"year": 2025}'`
- Make commands: `make ingest-year YEAR=2025`
- Pipeline scripts: `python3 scripts/run_smart_pipeline.py --mode full --year 2025`

**Planned (Phase 2)**:
- **EventBridge cron**: Nightly at 2 AM UTC, check for new filings in current year
- **Step Functions orchestration**: Coordinate multi-year backfills, retry logic, monitoring
- **Watermarking**: SHA256 hash comparison prevents duplicate processing

---

## AWS Services

### Lambda Functions

| Function                       | Trigger       | Memory | Timeout | Concurrency |
| ------------------------------ | ------------- | ------ | ------- | ----------- |
| `house-fd-ingest-zip`          | Manual / EB   | 1024MB | 5 min   | 1           |
| `house-fd-index-to-silver`     | Synchronous   | 512MB  | 2 min   | 1           |
| `house-fd-extract-document`    | SQS (batched) | 2048MB | 5 min   | 10          |
| `house-fd-extract-structured`  | SQS (batched) | 1024MB | 3 min   | 10          |

**Runtime**: Python 3.11

**Packaging**: Zip with dependencies (via `pip install -t` or Lambda Layers)

### SQS Queues

**Extract Queue**: `house-fd-extract-queue`
- Type: Standard
- Visibility timeout: 6 minutes (Lambda timeout + buffer)
- Message retention: 4 days
- Dead letter queue: `house-fd-extract-dlq` after 3 retries
- Batching: Lambda receives up to 10 messages per invocation

**Structured Extract Queue**: `house-fd-extract-structured-queue`
- Type: Standard
- Visibility timeout: 4 minutes
- Message retention: 4 days
- Dead letter queue: `house-fd-extract-structured-dlq`

### S3 Bucket

**Name**: `congress-disclosures-standardized` (configurable via Terraform)

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
- `sqs:ReceiveMessage`, `sqs:DeleteMessage` on extract queues
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### CloudWatch

**Log groups**:
- `/aws/lambda/house-fd-ingest-zip`
- `/aws/lambda/house-fd-index-to-silver`
- `/aws/lambda/house-fd-extract-document`
- `/aws/lambda/house-fd-extract-structured`

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
| `filing_type`      | STRING    | Code (e.g., 'A' = Annual, 'P' = PTR)        |
| `prefix`           | STRING    | Title (Hon., Dr., etc.)                      |
| `first_name`       | STRING    | Filer first name                             |
| `last_name`        | STRING    | Filer last name                              |
| `suffix`           | STRING    | Name suffix (Jr., III, etc.)                 |
| `state_district`   | STRING    | e.g., 'CA-11'                                |
| `pdf_s3_key`       | STRING    | S3 key to PDF in bronze                      |
| `bronze_ingest_ts` | TIMESTAMP | When zip was ingested                        |
| `silver_ingest_ts` | TIMESTAMP | When this row was created                    |

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
| `extraction_method`     | STRING    | 'pypdf', 'tesseract-ocr', 'failed', 'none'   |
| `extraction_status`     | STRING    | 'pending', 'success', 'failed'                |
| `extraction_version`    | STRING    | Code version (semantic or git hash)           |
| `extraction_timestamp`  | TIMESTAMP | Last extraction attempt                       |
| `extraction_error`      | STRING    | Error message if failed                       |
| `text_s3_key`           | STRING    | Silver text location (if success)             |
| `json_s3_key`           | STRING    | Structured JSON location                      |

**Partitioning**: `year`

**Update pattern**: Upsert by `(year, doc_id)` after each extraction run

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
       ├─> Convert to images (pdf2image)
       ├─> Apply image preprocessing
       │   ├─> Grayscale conversion
       │   ├─> Noise reduction (cv2.fastNlMeansDenoising)
       │   ├─> Binarization (Otsu's method)
       │   ├─> Deskew correction
       │   ├─> Border removal
       │   └─> Contrast enhancement
       ├─> Run Tesseract OCR
       └─> extraction_method = 'tesseract-ocr'

4. Upload text to silver:
   ├─> Gzip compress text
   └─> Upload to silver/house/financial/text/year={year}/doc_id={doc_id}/raw_text.txt.gz

5. Update house_fd_documents Parquet:
   └─> Upsert row with extraction metadata
```

### Error Handling

- **HTTP errors** (zip download): Retry 3x with exponential backoff
- **Corrupt PDFs**: Mark `extraction_status='failed'`, log error, continue
- **Lambda timeout**: SQS message returns to queue automatically (visibility timeout)
- **OCR failures**: Mark as failed, log error, send to DLQ after 3 retries

### Cost Optimization

**Free-tier approach**: pypdf + Tesseract OCR = $0/month

For 2025 FD filings:
- Assume ~2,000 filings
- If 20% are image-based (~400)
- Average 5 pages each = **2,000 pages total**
- Cost: **$0** (Tesseract is free)

**Alternative (paid)**: AWS Textract
- First 1,000 pages: Free
- Next 1,000 pages: $1.50
- Total: **~$1.50/month**

See [[Extraction-Architecture]] for detailed extraction pipeline documentation.

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

See [[Monitoring-Guide]] for detailed monitoring setup.

---

## Data Quality & Validation

### Bronze Layer

**Validation**:
- ZIP file integrity (CRC check)
- XML well-formedness (parse with `defusedxml`)
- PDF file header (`%PDF-` magic bytes)

**Checksums**:
- Store SHA256 hash in S3 metadata
- On re-ingestion, compare hash to detect changes

### Silver Layer

**Schema validation**:
- Pydantic model enforcement before Parquet write
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
- Image-based (Tesseract OCR): ~3-10 seconds
- SQS concurrency: 10 Lambdas = **~100-200 docs/minute**

**Full year** (2,000 filings):
- Ingestion: 30 seconds
- Extraction: 10-20 minutes (assuming 20% image-based)

### Scaling Limits

- **Lambda concurrency**: Default 1,000 per account (can request increase)
- **SQS throughput**: Nearly unlimited (standard queue)
- **S3**: No practical limit for this use case

### Cost Estimates (Monthly)

**Assumptions**: Process 2025 data once, store long-term

| Service          | Usage                     | Cost           |
| ---------------- | ------------------------- | -------------- |
| S3 storage       | 20 GB (bronze + silver)   | $0.46          |
| Lambda (compute) | 5,000 GB-seconds          | $0.08          |
| Lambda (requests)| 10,000 invocations        | $0.002         |
| SQS              | 10,000 messages           | $0.004         |
| CloudWatch Logs  | 1 GB ingestion            | $0.50          |
| **Total**        |                           | **~$1.00**     |

**Annual** (processing 2008-2025): ~$15-20/year

See [[Cost-Management]] for optimization strategies.

---

## See Also

- [[Medallion-Architecture]] - Deep dive into data layers
- [[Data-Layers]] - Detailed Bronze/Silver/Gold specifications
- [[Extraction-Architecture]] - PDF extraction pipeline
- [[State-Machines]] - Step Functions orchestration
- [[Monitoring-Guide]] - Monitoring and alerting setup
- [[Performance-Testing]] - Load testing and benchmarks

---

**Last Updated**: December 28, 2025
