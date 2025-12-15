# Data Contracts

**Project**: Congress Disclosures Standardized Data Platform
**Last Updated**: 2025-12-14
**Purpose**: Define data formats, schemas, and contracts between pipeline layers

---

## Overview

This document defines the **data contracts** between Bronze → Silver → Gold layers. Each contract specifies:
- Input/output formats
- Required fields
- Data types
- Validation rules
- SLA (latency, freshness)

**Data Ingestion Scope**:
- **Initial Load**: Only ingest data from last 5 years (e.g., 2020-2025 for current year 2025)
- **Data Retention**: Once ingested, data is retained permanently (no deletion policy)
- **Incremental Updates**: After initial load, daily incremental updates fetch latest data only
- **Rationale**: Reduces initial ingestion cost/time while maintaining recent compliance data

---

## Table of Contents

1. [Bronze Layer Contracts](#bronze-contracts)
2. [Silver Layer Contracts](#silver-contracts)
3. [Gold Layer Contracts](#gold-contracts)
4. [API Response Contracts](#api-contracts)
5. [Event/Message Contracts](#event-contracts)

---

<a name="bronze-contracts"></a>
## 1. Bronze Layer Contracts

### 1.1 House Financial Disclosure Zip File

**Location**: `s3://bucket/bronze/house/financial/year={YYYY}/raw_zip/{YYYY}FD.zip`

**Format**: ZIP archive
**Source**: https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{YYYY}FD.ZIP

**Metadata** (S3 Object Tags):
```json
{
  "sha256": "abc123...",           // File checksum
  "download_date": "2025-12-14",   // When downloaded
  "source_url": "https://...",     // Original URL
  "file_size_bytes": "104857600"   // 100MB
}
```

**Contract**:
- ✅ Immutable (never modified after upload)
- ✅ Append-only (new years added, old years kept permanently)
- ✅ Byte-for-byte identical to source
- ✅ **Ingestion Scope**: Initial load only processes years within 5-year lookback window (e.g., 2020-2025)
- ✅ **Retention**: Once ingested, files are retained indefinitely (no deletion)

### 1.2 House FD XML Index

**Location**: `s3://bucket/bronze/house/financial/year={YYYY}/index/{YYYY}FD.xml`

**Format**: XML (defusedxml-safe)

**Schema**:
```xml
<FilingList>
  <Filing>
    <DocID>10063228</DocID>
    <LastName>PELOSI</LastName>
    <FirstName>NANCY</FirstName>
    <FilingType>P</FilingType>
    <FilingYear>2024</FilingYear>
    <FilingDate>2024-08-14</FilingDate>
    <PdfLink>2024/10063228.pdf</PdfLink>
  </Filing>
</FilingList>
```

**Required Fields**:
- `DocID` (string, unique)
- `FilingType` (P, A, T, X, D, W)
- `FilingDate` (ISO 8601 date)
- `PdfLink` (relative path)

**Validation**:
- DocID must be numeric string
- FilingType must be in allowed set
- FilingDate must be valid date
- **Year Range** (initial ingestion): Only process filings from last 5 years

### 1.3 House FD PDF Files

**Location**: `s3://bucket/bronze/house/financial/year={YYYY}/filing_type={type}/pdfs/{doc_id}.pdf`

**Format**: PDF/A or standard PDF

**Metadata** (S3 Object Tags):
```json
{
  "doc_id": "10063228",
  "filing_type": "P",
  "extraction-processed": "true",     // Set after Silver extraction
  "extraction-method": "direct_text",  // or "ocr"
  "extraction-date": "2025-12-14",
  "sha256": "def456..."
}
```

**Contract**:
- ✅ Immutable (never modified)
- ✅ Metadata tags track processing state
- ✅ Used as source of truth for re-extraction

### 1.4 Congress.gov Bronze Data

**Location**: `s3://bucket/bronze/congress_gov/{entity_type}/`

**Entity Types**:
- `bills/` - Bill text and metadata
- `members/` - Member information
- `amendments/` - Amendment data
- `summaries/` - Bill summaries

**Format**: JSON (raw API responses)

**Example** (`bills/119-sconres-23.json`):
```json
{
  "bill_id": "119-sconres-23",
  "bill_type": "sconres",
  "congress": 119,
  "number": "23",
  "title": "A concurrent resolution...",
  "sponsor": {
    "bioguide_id": "C001047",
    "name": "Capito, Shelley Moore"
  },
  "introduced_date": "2025-01-09",
  "api_response_date": "2025-12-14"
}
```

### 1.5 Lobbying (LDA) Bronze Data

**Location**: `s3://bucket/bronze/lobbying/lda/year={YYYY}/filings/{filing_id}.xml`

**Format**: XML from Senate LDA database

**Schema**:
```xml
<LOBBYINGDISCLOSURE1>
  <filingID>12345ABC</filingID>
  <filingType>Q1</filingType>
  <filingYear>2024</filingYear>
  <registrant>
    <registrantName>Acme Lobbying LLC</registrantName>
  </registrant>
  <client>
    <clientName>BigCorp Inc</clientName>
  </client>
  <lobbying Activities>...</lobbyingActivities>
</LOBBYINGDISCLOSURE1>
```

---

<a name="silver-contracts"></a>
## 2. Silver Layer Contracts

### 2.1 House FD Filings Table

**Location**: `s3://bucket/silver/house/financial/filings/filings.parquet`

**Format**: Parquet (partitioned by year)

**Schema**:
```python
{
  'doc_id': 'string',              # Primary key
  'last_name': 'string',
  'first_name': 'string',
  'middle_name': 'string',         # Nullable
  'suffix': 'string',              # Nullable
  'filing_type': 'string',         # P, A, T, X, D, W
  'filing_year': 'int64',
  'filing_date': 'date32',         # ISO 8601
  'pdf_link': 'string',
  'bronze_s3_key': 'string',       # Link back to Bronze
  'created_at': 'timestamp',
  'updated_at': 'timestamp'
}
```

**Uniqueness**: `doc_id` (primary key)
**Partitioning**: `year={filing_year}`
**Compression**: Snappy

**Validation Rules**:
- `doc_id` NOT NULL, unique
- `filing_type` IN ('P', 'A', 'T', 'X', 'D', 'W')
- `filing_date` >= (current_year - 5) + "-01-01" (5-year lookback for initial ingestion)
- `filing_date` <= current_date + 30 days
- **Note**: After initial load, all dates retained permanently. Validation only applies during ingestion.

### 2.2 House FD Documents Table

**Location**: `s3://bucket/silver/house/financial/documents/documents.parquet`

**Schema**:
```python
{
  'doc_id': 'string',              # Foreign key to filings
  'extraction_status': 'string',   # 'pending', 'success', 'failed'
  'extraction_method': 'string',   # 'direct_text', 'ocr', 'failed'
  'extraction_date': 'timestamp',
  'text_s3_key': 'string',        # Location of extracted text
  'objects_s3_key': 'string',     # Location of structured JSON
  'page_count': 'int32',
  'file_size_bytes': 'int64',
  'confidence_score': 'float32',  # 0.0 - 1.0
  'quality_issues': 'string',     # JSON array of issues
  'processing_time_seconds': 'float32',
  'created_at': 'timestamp',
  'updated_at': 'timestamp'
}
```

**Uniqueness**: `doc_id`
**Validation**:
- `confidence_score` BETWEEN 0.0 AND 1.0
- `extraction_status` IN ('pending', 'success', 'failed')

### 2.3 House FD Extracted Text

**Location**: `s3://bucket/silver/house/financial/text/extraction_method={method}/year={year}/{doc_id}.txt.gz`

**Format**: Gzipped plain text (UTF-8)

**Structure**:
```
[Page 1]
<extracted text content>

[Page 2]
<extracted text content>

---
Extraction Metadata:
  Method: direct_text
  Confidence: 0.95
  Processing Time: 2.3s
  Timestamp: 2025-12-14T10:30:00Z
```

**Contract**:
- ✅ Compressed with gzip (reduce S3 costs)
- ✅ UTF-8 encoding
- ✅ Metadata footer (separated by `---`)

### 2.4 House FD Structured Objects

**Location**: `s3://bucket/silver/house/financial/objects/filing_type=type_{p,a,t}/year={year}/{doc_id}.json`

**Format**: JSON (structured extraction output)

**Schema** (Type P - PTR):
```json
{
  "doc_id": "10063228",
  "filing_type": "P",
  "filing_date": "2024-08-14",
  "filer": {
    "name": "Hon. Nancy Pelosi",
    "office": "U.S. House of Representatives",
    "district": "CA-11"
  },
  "transactions": [
    {
      "transaction_id": "10063228-001",
      "asset_name": "NVIDIA CORP",
      "ticker": "NVDA",
      "transaction_type": "Purchase",
      "transaction_date": "2024-08-01",
      "notification_date": "2024-08-14",
      "amount_range": "$100,001 - $250,000",
      "amount_low": 100001,
      "amount_high": 250000
    }
  ],
  "extraction_metadata": {
    "extracted_at": "2025-12-14T10:30:00Z",
    "extractor_version": "v2.1.0",
    "confidence": 0.95
  }
}
```

**Validation**:
- `transactions` must be array (can be empty)
- `amount_low` < `amount_high`
- `transaction_date` <= `notification_date`

**Schema** (Type A - Annual):
```json
{
  "doc_id": "10050123",
  "filing_type": "A",
  "schedules": {
    "schedule_a_assets": [...],
    "schedule_b_income": [...],
    "schedule_c_liabilities": [...]
  }
}
```

### 2.5 Congress.gov Silver Tables

**Locations**:
- `silver/congress_gov/bills/bills.parquet`
- `silver/congress_gov/members/members.parquet`
- `silver/congress_gov/cosponsors/cosponsors.parquet`

**Bills Schema**:
```python
{
  'bill_id': 'string',             # Primary key
  'congress': 'int32',
  'bill_type': 'string',
  'number': 'int32',
  'title': 'string',
  'sponsor_bioguide_id': 'string',
  'introduced_date': 'date32',
  'policy_area': 'string',
  'summary': 'string',
  'bronze_s3_key': 'string',
  'created_at': 'timestamp'
}
```

### 2.6 Lobbying Silver Tables

**Location**: `silver/lobbying/lda/filings.parquet`

**Schema**:
```python
{
  'filing_id': 'string',           # Primary key
  'filing_type': 'string',         # Q1, Q2, Q3, Q4, YEAR_END
  'filing_year': 'int32',
  'registrant_name': 'string',
  'client_name': 'string',
  'lobbying_amount': 'int64',      # In dollars
  'issues_lobbied': 'string',      # Comma-separated
  'bills_lobbied': 'string',       # Comma-separated bill IDs
  'bronze_s3_key': 'string',
  'created_at': 'timestamp'
}
```

---

<a name="gold-contracts"></a>
## 3. Gold Layer Contracts

### 3.1 Dimension Tables

#### dim_members

**Location**: `gold/dimensions/dim_members/dim_members.parquet`

**Schema** (SCD Type 2 - Slowly Changing Dimension):
```python
{
  'member_key': 'int64',           # Surrogate key
  'bioguide_id': 'string',         # Business key
  'full_name': 'string',
  'party': 'string',               # D, R, I
  'chamber': 'string',             # House, Senate
  'state': 'string',               # Two-letter code
  'district': 'string',            # House only
  'in_office': 'bool',
  'effective_date': 'date32',      # SCD start date
  'expiration_date': 'date32',     # SCD end date (9999-12-31 if current)
  'is_current': 'bool',
  'created_at': 'timestamp'
}
```

**SCD Type 2 Pattern**:
- When party/chamber changes, insert new row with new `effective_date`
- Set previous row's `expiration_date` to day before change
- Only current row has `is_current = true`

#### dim_assets

**Location**: `gold/dimensions/dim_assets/dim_assets.parquet`

**Schema**:
```python
{
  'asset_key': 'int64',            # Surrogate key
  'asset_name': 'string',          # Normalized name
  'ticker': 'string',              # Stock ticker (nullable)
  'asset_type': 'string',          # stock, bond, fund, real_estate, etc.
  'industry': 'string',            # GICS sector (nullable)
  'created_at': 'timestamp'
}
```

#### dim_bills

**Location**: `gold/dimensions/dim_bills/dim_bills.parquet`

**Schema**:
```python
{
  'bill_key': 'int64',
  'bill_id': 'string',             # Business key (119-sconres-23)
  'congress': 'int32',
  'bill_type': 'string',
  'number': 'int32',
  'title': 'string',
  'policy_area': 'string',
  'sponsor_member_key': 'int64',   # FK to dim_members
  'introduced_date': 'date32',
  'created_at': 'timestamp'
}
```

#### dim_dates

**Location**: `gold/dimensions/dim_dates/dim_dates.parquet`

**Schema** (Date dimension for star schema):
```python
{
  'date_key': 'int32',             # YYYYMMDD (e.g., 20251214)
  'full_date': 'date32',
  'year': 'int32',
  'quarter': 'int32',              # 1-4
  'month': 'int32',                # 1-12
  'month_name': 'string',
  'day_of_month': 'int32',
  'day_of_week': 'int32',          # 1=Monday, 7=Sunday
  'day_name': 'string',
  'is_weekend': 'bool',
  'is_holiday': 'bool',
  'fiscal_year': 'int32',          # US fiscal year
  'fiscal_quarter': 'int32'
}
```

### 3.2 Fact Tables

#### fact_ptr_transactions

**Location**: `gold/facts/ptr_transactions/year={year}/month={month}/transactions.parquet`

**Schema** (Star Schema):
```python
{
  'transaction_key': 'int64',      # Surrogate key
  'transaction_id': 'string',      # Business key
  'member_key': 'int64',           # FK to dim_members
  'asset_key': 'int64',            # FK to dim_assets
  'transaction_date_key': 'int32', # FK to dim_dates
  'notification_date_key': 'int32',# FK to dim_dates
  'transaction_type': 'string',    # Purchase, Sale, Exchange
  'amount_low': 'int64',
  'amount_high': 'int64',
  'amount_midpoint': 'int64',      # Calculated (low + high) / 2
  'doc_id': 'string',              # Link to Silver
  'filing_date': 'date32',
  'created_at': 'timestamp'
}
```

**Partitioning**: `year={year}/month={month}` (based on transaction_date)
**Indexing**: Partition pruning on year/month

#### fact_filings

**Location**: `gold/facts/filings/year={year}/filings.parquet`

**Schema**:
```python
{
  'filing_key': 'int64',
  'doc_id': 'string',              # Business key
  'member_key': 'int64',           # FK to dim_members
  'filing_date_key': 'int32',      # FK to dim_dates
  'filing_type': 'string',
  'filing_year': 'int32',
  'transaction_count': 'int32',    # Count from fact_ptr_transactions
  'total_value_midpoint': 'int64', # Sum of amount_midpoint
  'quality_score': 'float32',      # 0.0 - 1.0
  'created_at': 'timestamp'
}
```

#### fact_lobbying

**Location**: `gold/facts/lobbying/year={year}/lobbying.parquet`

**Schema**:
```python
{
  'lobbying_key': 'int64',
  'filing_id': 'string',
  'filing_date_key': 'int32',
  'registrant_name': 'string',
  'client_name': 'string',
  'lobbying_amount': 'int64',
  'issue_count': 'int32',
  'bill_count': 'int32',
  'created_at': 'timestamp'
}
```

### 3.3 Aggregate Tables

#### agg_trending_stocks

**Location**: `gold/aggregates/trending_stocks/trending_stocks.parquet`

**Schema**:
```python
{
  'ticker': 'string',
  'asset_name': 'string',
  'window_days': 'int32',          # 7, 30, 90
  'window_end_date': 'date32',
  'purchase_count': 'int32',
  'sale_count': 'int32',
  'net_activity': 'int32',         # purchase_count - sale_count
  'total_value_midpoint': 'int64',
  'member_count': 'int32',         # Unique members trading
  'trend_direction': 'string',     # 'buying', 'selling', 'mixed'
  'rank': 'int32',                 # By total_value_midpoint
  'created_at': 'timestamp'
}
```

**Update Frequency**: Daily (incremental)

#### agg_member_trading_stats

**Location**: `gold/aggregates/member_stats/member_stats.parquet`

**Schema**:
```python
{
  'member_key': 'int64',
  'year': 'int32',
  'total_transactions': 'int32',
  'purchase_count': 'int32',
  'sale_count': 'int32',
  'total_value_midpoint': 'int64',
  'avg_transaction_size': 'int64',
  'unique_assets_traded': 'int32',
  'filing_count': 'int32',
  'late_filing_count': 'int32',    # Filed > 45 days after transaction
  'compliance_score': 'float32',   # 0.0 - 1.0
  'created_at': 'timestamp'
}
```

#### agg_document_quality

**Location**: `gold/aggregates/document_quality/quality.parquet`

**Schema**:
```python
{
  'member_key': 'int64',
  'total_filings': 'int32',
  'avg_confidence_score': 'float32',
  'ocr_required_count': 'int32',   # Count where method = 'ocr'
  'extraction_failed_count': 'int32',
  'avg_page_count': 'float32',
  'avg_processing_time': 'float32',
  'quality_grade': 'string',       # A, B, C, D, F
  'created_at': 'timestamp'
}
```

#### agg_network_graph

**Location**: `gold/aggregates/network_graph/network.json`

**Format**: JSON (for D3.js visualization)

**Schema**:
```json
{
  "nodes": [
    {
      "id": "member-123",
      "name": "Hon. John Doe",
      "type": "member",
      "party": "D",
      "total_value": 5000000
    },
    {
      "id": "asset-456",
      "name": "NVIDIA",
      "ticker": "NVDA",
      "type": "asset",
      "industry": "Technology"
    }
  ],
  "edges": [
    {
      "source": "member-123",
      "target": "asset-456",
      "weight": 10,               // Transaction count
      "total_value": 2500000
    }
  ],
  "metadata": {
    "generated_at": "2025-12-14T10:30:00Z",
    "node_count": 1500,
    "edge_count": 8000
  }
}
```

---

<a name="api-contracts"></a>
## 4. API Response Contracts

### 4.1 GET /members

**Response**:
```json
{
  "data": [
    {
      "bioguide_id": "P000197",
      "full_name": "Nancy Pelosi",
      "party": "D",
      "chamber": "House",
      "state": "CA",
      "district": "11",
      "in_office": false,
      "stats": {
        "total_transactions": 150,
        "total_value_midpoint": 50000000,
        "compliance_score": 0.95
      }
    }
  ],
  "pagination": {
    "total": 535,
    "page": 1,
    "per_page": 50
  },
  "metadata": {
    "generated_at": "2025-12-14T10:30:00Z",
    "data_current_as_of": "2025-12-14",
    "cache_expires_at": "2025-12-14T10:35:00Z"
  }
}
```

### 4.2 GET /transactions

**Response**:
```json
{
  "data": [
    {
      "transaction_id": "10063228-001",
      "member": {
        "bioguide_id": "P000197",
        "full_name": "Nancy Pelosi"
      },
      "asset": {
        "name": "NVIDIA CORP",
        "ticker": "NVDA"
      },
      "transaction_type": "Purchase",
      "transaction_date": "2024-08-01",
      "amount": {
        "range": "$100,001 - $250,000",
        "low": 100001,
        "high": 250000,
        "midpoint": 175001
      }
    }
  ],
  "filters_applied": {
    "member": "P000197",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  },
  "pagination": {...},
  "metadata": {...}
}
```

### 4.3 GET /trending-stocks

**Response**:
```json
{
  "data": [
    {
      "rank": 1,
      "ticker": "NVDA",
      "asset_name": "NVIDIA CORP",
      "window_days": 30,
      "activity": {
        "purchase_count": 45,
        "sale_count": 10,
        "net_activity": 35,
        "total_value_midpoint": 25000000,
        "member_count": 28
      },
      "trend_direction": "buying"
    }
  ],
  "window": {
    "days": 30,
    "start_date": "2024-11-14",
    "end_date": "2024-12-14"
  },
  "metadata": {...}
}
```

---

<a name="event-contracts"></a>
## 5. Event/Message Contracts

### 5.1 SQS Extraction Queue Message

**Queue**: `congress-disclosures-{env}-house-fd-extraction-queue`

**Message Body**:
```json
{
  "doc_id": "10063228",
  "filing_type": "P",
  "filing_year": 2024,
  "pdf_s3_key": "bronze/house/financial/year=2024/filing_type=P/pdfs/10063228.pdf",
  "index_s3_key": "bronze/house/financial/year=2024/index/2024FD.xml",
  "execution_id": "arn:aws:states:...:execution/...",
  "retry_count": 0
}
```

**Message Attributes**:
- `doc_id` (String)
- `filing_type` (String)
- `priority` (Number): 1-10 (10 = highest)

**Visibility Timeout**: 300 seconds (5 minutes)
**Retry Policy**: 3 retries with exponential backoff
**DLQ**: After 3 failures → DLQ

### 5.2 Step Functions State Machine Input

**Input** (for manual execution):
```json
{
  "execution_type": "manual",
  "mode": "incremental",           // or "full_refresh"
  "sources": {
    "house_fd": true,
    "congress_gov": true,
    "lobbying": true
  },
  "year": 2024,                    // Optional (for year-specific run)
  "skip_quality_checks": false     // Emergency override
}
```

**Input** (for scheduled execution):
```json
{
  "execution_type": "scheduled",
  "mode": "incremental",
  "sources": {
    "house_fd": true,
    "congress_gov": true,
    "lobbying": true
  }
}
```

### 5.3 SNS Alert Messages

**Topic**: `congress-disclosures-{env}-pipeline-alerts`

**Message Format**:
```json
{
  "alert_type": "pipeline_failure",
  "severity": "critical",          // critical, high, medium, low
  "execution_id": "arn:aws:states:...",
  "error": {
    "phase": "Silver Transformation",
    "step": "ExtractDocuments",
    "error_type": "Lambda.Timeout",
    "message": "Task timed out after 300.00 seconds"
  },
  "timestamp": "2025-12-14T10:30:00Z",
  "recovery_actions": [
    "Check Lambda timeout configuration",
    "Review CloudWatch logs for doc_id",
    "Consider increasing timeout or memory"
  ]
}
```

---

## Data Quality Rules

### Bronze Layer
- ✅ **Completeness**: All files from source preserved
- ✅ **Accuracy**: SHA256 checksums match source
- ✅ **Immutability**: Never modified after upload

### Silver Layer
- ✅ **Completeness**: Every Bronze PDF has Silver record
- ✅ **Consistency**: Referential integrity (doc_id exists in filings table)
- ✅ **Validity**: All fields pass type and range checks
- ✅ **Uniqueness**: No duplicate doc_ids

### Gold Layer
- ✅ **Completeness**: All Silver records aggregated
- ✅ **Consistency**: Fact table foreign keys valid
- ✅ **Accuracy**: Aggregate counts match source counts
- ✅ **Timeliness**: Updated within 24 hours of Silver changes

---

## SLA (Service Level Agreement)

| Layer | Update Frequency | Max Staleness | Availability | Notes |
|-------|-----------------|---------------|--------------|-------|
| Bronze | Daily (6AM UTC) | 24 hours | 99.0% | Initial load: 5-year lookback only |
| Silver | Daily (after Bronze) | 36 hours | 99.0% | - |
| Gold | Daily (after Silver) | 48 hours | 99.5% | - |
| API | On-demand | 5 minutes (cache) | 99.9% | - |

**Initial Ingestion Timeline**:
- **House FD**: ~2 hours (5 years × ~5,000 PDFs/year)
- **Congress.gov**: ~1.5 hours (5 years × ~50,000 bills, rate-limited to 10 req/sec)
- **Lobbying**: ~1 hour (5 years × 4 quarters/year)
- **Total Initial Pipeline**: ~4-5 hours (includes Silver extraction + Gold aggregation)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-14 | Initial data contracts | Engineering Team |
| 1.1 | 2025-12-14 | Added 5-year ingestion scope, API rate limiting, checkpointing | Engineering Team |

---

**Document Owner**: Data Engineering Team
**Review Cycle**: Quarterly or when schema changes
**Approval**: Requires tech lead + data owner sign-off
