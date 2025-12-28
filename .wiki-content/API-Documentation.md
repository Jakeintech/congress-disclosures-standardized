# API Documentation

Public API strategy and endpoints for accessing Congress financial disclosure data.

## Table of Contents
- [Overview](#overview)
- [API Access Methods](#api-access-methods)
- [Direct S3 Access](#direct-s3-access)
- [REST API (Planned)](#rest-api-planned)
- [Rate Limiting](#rate-limiting)
- [Authentication](#authentication)

---

## Overview

The Congress Financial Disclosures project provides multiple ways to access data:

1. **Direct S3 Access** (Current) - Read Parquet files directly from S3
2. **REST API** (Planned) - HTTP API for programmatic access
3. **GraphQL API** (Future) - Flexible querying interface

---

## API Access Methods

### Method 1: Direct S3 Access (Current)

**Best for**: Bulk downloads, data scientists, researchers

**Access Pattern**:
```python
import pandas as pd
import s3fs

# Anonymous access to public bucket
s3 = s3fs.S3FileSystem(anon=True)

# Read Parquet directly
df = pd.read_parquet(
    's3://congress-disclosures-public/gold/house/financial/fact_ptr_transactions/year=2025/part-0000.parquet',
    filesystem=s3
)

print(df.head())
```

**Advantages**:
- Zero API infrastructure costs
- Highest performance (direct S3)
- Full dataset access
- No rate limits

**Disadvantages**:
- Requires AWS knowledge
- Difficult for non-technical users
- No built-in filtering

---

## Direct S3 Access

### Available Datasets

**Gold Layer** (recommended for most users):
```
s3://congress-disclosures-public/gold/house/financial/
├── dimensions/
│   ├── dim_members/year=YYYY/part-0000.parquet
│   ├── dim_assets/year=YYYY/part-0000.parquet
│   ├── dim_date/year=YYYY/part-0000.parquet
│   └── dim_filing_types/part-0000.parquet
├── facts/
│   ├── fact_ptr_transactions/year=YYYY/part-0000.parquet
│   └── fact_filings/year=YYYY/part-0000.parquet
└── aggregates/
    ├── agg_trending_stocks/year=YYYY/part-0000.parquet
    ├── agg_member_trading_stats/year=YYYY/part-0000.parquet
    └── agg_document_quality/year=YYYY/part-0000.parquet
```

### Python Examples

**List available years**:
```python
import s3fs
s3 = s3fs.S3FileSystem(anon=True)
files = s3.ls('congress-disclosures-public/gold/house/financial/facts/fact_ptr_transactions/')
years = [f.split('=')[1].split('/')[0] for f in files if 'year=' in f]
print(years)  # ['2020', '2021', '2022', '2023', '2024', '2025']
```

**Download specific dataset**:
```bash
aws s3 cp s3://congress-disclosures-public/gold/house/financial/fact_ptr_transactions/year=2025/part-0000.parquet . --no-sign-request
```

**Query with DuckDB**:
```python
import duckdb

# Query S3 Parquet directly
result = duckdb.sql('''
    SELECT 
        member_last_name, 
        ticker, 
        transaction_type, 
        COUNT(*) as trade_count
    FROM read_parquet('s3://congress-disclosures-public/gold/house/financial/fact_ptr_transactions/year=2025/*.parquet')
    WHERE ticker = 'AAPL'
    GROUP BY member_last_name, ticker, transaction_type
    ORDER BY trade_count DESC
    LIMIT 10
''').df()

print(result)
```

---

## REST API (Planned)

**Base URL**: `https://api.congress-disclosures.org/v1/`

**Status**: Not yet implemented (Phase 2)

### Planned Endpoints

#### GET /filings

List financial disclosure filings.

**Query Parameters**:
- `year` (int): Filing year
- `state` (string): State code (e.g., CA)
- `filing_type` (string): Filing type code
- `limit` (int, default=100, max=1000): Results per page
- `offset` (int): Pagination offset

**Example**:
```bash
curl "https://api.congress-disclosures.org/v1/filings?year=2025&state=CA&limit=10"
```

**Response**:
```json
{
  "data": [
    {
      "doc_id": "8221216",
      "year": 2025,
      "filing_date": "2025-05-15",
      "first_name": "NANCY",
      "last_name": "PELOSI",
      "state_district": "CA11",
      "filing_type": "A"
    }
  ],
  "pagination": {
    "total": 156,
    "limit": 10,
    "offset": 0,
    "next": "/v1/filings?year=2025&state=CA&limit=10&offset=10"
  }
}
```

#### GET /filings/{doc_id}

Get single filing details.

#### GET /transactions

Query PTR transactions.

**Query Parameters**:
- `year` (int)
- `member_bioguide_id` (string)
- `ticker` (string)
- `transaction_type` (string): 'purchase', 'sale', 'exchange'
- `min_amount` (int)
- `limit`, `offset`

---

## Rate Limiting

### Planned Tiers

| Tier | Rate Limit | Use Case | Authentication |
|------|-----------|----------|----------------|
| **Anonymous** | 100 requests/hour | Casual browsing | None |
| **Registered** | 1,000 requests/hour | Research, apps | API key |
| **Research** | 10,000 requests/hour | Academic research | API key + verification |

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1700000000
```

**Response (429 Too Many Requests)**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 45 minutes.",
    "retry_after": 2700
  }
}
```

---

## Authentication

### API Key (Planned)

**Registration Flow**:
1. Visit `https://congress-disclosures.org/api/register`
2. Provide email, name, use case
3. Agree to terms (5 U.S.C. § 13107 compliance)
4. Receive API key via email

**API Key Format**:
```
cd_live_abc123def456ghi789jkl012mno345pqr678
```

**Usage**:
```http
GET /v1/filings?year=2025
Host: api.congress-disclosures.org
X-API-Key: cd_live_abc123def456ghi789jkl012mno345pqr678
```

---

## See Also

- [[Query-Examples]] - Example queries and use cases
- [[Direct-S3-Access]] - Detailed S3 access guide
- [[API-Endpoints-Reference]] - Complete endpoint documentation
- [[Legal-and-Compliance]] - Usage restrictions

---

**Note**: REST API is planned for Phase 2. Currently, only Direct S3 Access is available.
