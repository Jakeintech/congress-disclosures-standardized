# Gold Layer Architecture

The gold layer is the analytics-ready data warehouse layer of the Congressional Disclosures system. It contains curated, enriched, and aggregated data optimized for querying, analysis, and public APIs.

## Overview

### Medallion Architecture

```
Bronze Layer (Raw)     →  Silver Layer (Normalized)  →  Gold Layer (Analytics)
├─ PDFs                   ├─ Extracted text             ├─ Dimension tables
├─ XML indexes            ├─ Metadata tables            ├─ Fact tables
└─ ZIP archives           └─ Structured JSON            ├─ Aggregates
                                                        └─ Quality metrics
```

### Design Principles

1. **Star Schema Design**: Optimized for analytical queries
2. **Enriched Data**: External API integration (Congress.gov, Yahoo Finance)
3. **Pre-computed Aggregates**: Fast dashboard performance
4. **Document Quality Tracking**: Transparency in data processing
5. **Partitioned Storage**: Efficient querying and cost optimization
6. **Columnar Format**: Parquet with Snappy compression

## S3 Folder Structure

```
s3://congress-disclosures-standardized/gold/house/financial/
│
├── dimensions/                          # Dimension tables (SCD Type 2)
│   ├── dim_members/
│   │   └── year=YYYY/
│   │       └── part-0000.parquet
│   ├── dim_assets/
│   │   └── year=YYYY/
│   │       └── part-0000.parquet
│   ├── dim_filing_types/
│   │   └── part-0000.parquet          # Static, no partitions
│   └── dim_date/
│       └── year=YYYY/
│           └── part-0000.parquet
│
├── facts/                               # Fact tables (transaction grain)
│   ├── fact_ptr_transactions/
│   │   └── year=YYYY/month=MM/
│   │       └── part-0000.parquet
│   ├── fact_annual_holdings/           # Future: Annual Report holdings
│   │   └── year=YYYY/
│   │       └── part-0000.parquet
│   └── fact_filings/
│       └── year=YYYY/
│           └── part-0000.parquet
│
├── aggregates/                          # Pre-computed metrics
│   ├── agg_member_portfolio_daily/
│   │   └── year=YYYY/month=MM/
│   │       └── part-0000.parquet
│   ├── agg_member_trading_stats/
│   │   └── year=YYYY/period=YYYYMM/
│   │       └── part-0000.parquet
│   ├── agg_trending_stocks/
│   │   └── year=YYYY/month=MM/
│   │       └── part-0000.parquet
│   ├── agg_sector_activity_monthly/
│   │   └── year_month=YYYYMM/
│   │       └── part-0000.parquet
│   └── agg_document_quality/           # 🔍 Compliance tracking
│       └── year=YYYY/
│           └── part-0000.parquet
│
├── quality/                             # Data quality & audit
│   ├── data_quality_metrics/
│   │   └── metric_date=YYYY-MM-DD/
│   │       └── part-0000.parquet
│   └── extraction_audit_log/
│       └── year=YYYY/month=MM/
│           └── part-0000.parquet
│
└── cache/                               # Enrichment API cache
    ├── congress_api/
    │   └── bioguide_{ID}.json          # Cached member data
    ├── stock_api/
    │   └── ticker_{SYMBOL}.json        # Cached stock data
    └── crypto_api/
        └── asset_{ID}.json             # Cached crypto data
```

## Dimension Tables

### dim_members

Member dimension with Slowly Changing Dimension (SCD) Type 2 for tracking party changes, district redistricting, etc.

**Grain**: One row per member per version

**Partitioning**: `year` (year of effective_from)

**Schema**:
```
member_key: INT                   # Surrogate key
bioguide_id: STRING               # Natural key (e.g., "P000197")
first_name: STRING
last_name: STRING
full_name: STRING
party: STRING                     # D, R, I
state: STRING                     # Two-letter code (CA, TX)
district: INT                     # NULL for state-wide (senators)
state_district: STRING            # "CA-11", "TX-02"
chamber: STRING                   # House, Senate
member_type: STRING               # Member, Officer, Employee
start_date: DATE                  # Term start
end_date: DATE                    # Term end (NULL = current)
is_current: BOOLEAN
effective_from: TIMESTAMP         # SCD version start
effective_to: TIMESTAMP           # SCD version end (NULL = current)
version: INT                      # SCD version number
```

**Example**:
```
member_key | bioguide_id | full_name    | party | state_district | effective_from | effective_to | version
-----------+-------------+--------------+-------+----------------+----------------+--------------+--------
1          | P000197     | Nancy Pelosi | D     | CA-11          | 2023-01-01     | NULL         | 1
```

**Source**:
- Bronze: Filing XML (first_name, last_name, state, district)
- Congress.gov API: bioguide_id, party, chamber, term dates

**Update frequency**: Daily enrichment job

---

### dim_assets

Asset master table with ticker extraction and sector classification.

**Grain**: One row per unique asset

**Partitioning**: None (relatively small, ~50K unique assets)

**Schema**:
```
asset_key: INT                    # Surrogate key
asset_name: STRING                # Full name from PTR
normalized_asset_name: STRING     # Cleaned/standardized name
ticker_symbol: STRING             # Extracted ticker (GOOGL, AAPL)
company_name: STRING              # Official company name
asset_type: STRING                # Stock, Bond, Property, Crypto, Fund, Other
sector: STRING                    # Technology, Healthcare, Finance, etc.
industry: STRING                  # Software, Pharmaceuticals, Banking, etc.
market_cap_category: STRING       # Large (>$10B), Mid ($2-10B), Small (<$2B)
is_publicly_traded: BOOLEAN
is_crypto: BOOLEAN
exchange: STRING                  # NYSE, NASDAQ, CRYPTO
cusip: STRING                     # 9-character identifier (if available)
first_seen_date: DATE             # First appearance in disclosures
last_seen_date: DATE              # Most recent appearance
occurrence_count: INT             # How many times traded by members
created_at: TIMESTAMP
updated_at: TIMESTAMP
```

**Example**:
```
asset_key | asset_name                                  | ticker | sector       | market_cap_category | occurrence_count
----------+---------------------------------------------+--------+--------------+---------------------+-----------------
1         | Alphabet Inc. - Class A Common Stock        | GOOGL  | Technology   | Large               | 47
2         | Bitcoin                                     | BTC    | Cryptocurrency | Large             | 12
3         | Vanguard Total Stock Market Index Fund      | VTI    | Finance      | N/A                 | 89
```

**Source**:
- Silver: PTR structured JSON (asset_name)
- Yahoo Finance API: ticker, sector, industry, market_cap
- Coinbase API: crypto asset classification
- Regex patterns: Ticker extraction from asset_name

**Update frequency**: Nightly batch (new assets only)

---

### dim_filing_types

Static lookup table for filing type codes.

**Grain**: One row per filing type

**Partitioning**: None (static, ~12 rows)

**Schema**:
```
filing_type_key: INT
filing_type_code: STRING          # P, A, C, T, X, etc.
filing_type_name: STRING          # "Periodic Transaction Report"
form_type: STRING                 # Form A, Form B, PTR
description: STRING
frequency: STRING                 # Annual, As-needed, etc.
is_transaction_report: BOOLEAN
requires_structured_extraction: BOOLEAN
typical_page_count_low: INT
typical_page_count_high: INT
```

**Example**:
```
filing_type_key | filing_type_code | filing_type_name             | form_type | is_transaction_report
----------------+------------------+------------------------------+-----------+----------------------
1               | P                | Periodic Transaction Report  | PTR       | true
2               | A                | Annual Report                | Form A    | false
3               | C                | Candidate Report             | Form B    | false
```

**Source**: Static seed data

**Update frequency**: Manual (only when House Clerk adds new types)

---

### dim_date

Standard date dimension for time-series analysis.

**Grain**: One row per date

**Partitioning**: `year`

**Schema**:
```
date_key: INT                     # YYYYMMDD (e.g., 20250115)
full_date: DATE                   # 2025-01-15
year: INT
quarter: INT                      # 1-4
month: INT                        # 1-12
week_of_year: INT                 # 1-53
day_of_year: INT                  # 1-366
day_of_month: INT                 # 1-31
day_of_week: INT                  # 1-7 (Monday=1)
day_name: STRING                  # Monday, Tuesday, etc.
month_name: STRING                # January, February, etc.
is_weekend: BOOLEAN
is_holiday: BOOLEAN               # Federal holidays
fiscal_year: INT                  # Government fiscal year (Oct 1 start)
fiscal_quarter: INT
congressional_session: INT        # 118th, 119th, etc.
congressional_session_year: INT   # 1 or 2 (within 2-year session)
```

**Example**:
```
date_key | full_date  | year | quarter | month | day_name | is_weekend | fiscal_year | congressional_session
---------+------------+------+---------+-------+----------+------------+-------------+----------------------
20250115 | 2025-01-15 | 2025 | 1       | 1     | Wednesday| false      | 2025        | 119
```

**Source**: Generated script

**Update frequency**: One-time generation (2008-2030 range)

---

## Fact Tables

### fact_ptr_transactions

Transaction-level fact table for Periodic Transaction Reports.

**Grain**: One row per transaction per filing

**Partitioning**: `year(transaction_date), month(transaction_date)`

**Clustering**: `member_key, asset_key`

**Schema**:
```
transaction_key: BIGINT           # Surrogate key

-- Dimension foreign keys
member_key: INT                   # → dim_members
asset_key: INT                    # → dim_assets
filing_type_key: INT              # → dim_filing_types
transaction_date_key: INT         # → dim_date
notification_date_key: INT        # → dim_date
filing_date_key: INT              # → dim_date

-- Transaction attributes
doc_id: STRING                    # Source document ID
transaction_id: INT               # Sequence within filing (1, 2, 3...)
transaction_type: STRING          # Purchase, Sale, Partial Sale, Exchange
owner_code: STRING                # SP, DC, JT, null
amount_column: STRING             # A-K
amount_range: STRING              # "$1,001 - $15,000"
amount_low: BIGINT                # Numeric low bound
amount_high: BIGINT               # Numeric high bound
amount_midpoint: BIGINT           # Calculated: (low + high) / 2

-- Derived metrics
transaction_size_category: STRING # Small (<$15K), Medium ($15K-$50K),
                                  # Large ($50K-$500K), Mega (>$500K)
days_to_notification: INT         # transaction_date → notification_date
days_to_filing: INT               # transaction_date → filing_date
is_late_filing: BOOLEAN           # Filed after 45-day deadline
is_same_day_notification: BOOLEAN
is_spouse_transaction: BOOLEAN    # owner_code = 'SP'
is_dependent_child_transaction: BOOLEAN # owner_code = 'DC'

-- Extraction metadata
extraction_confidence: FLOAT      # 0.0-1.0
extraction_method: STRING         # pypdf, textract_ocr
pdf_type: STRING                  # text, image, hybrid
data_completeness_pct: FLOAT
requires_manual_review: BOOLEAN

-- Audit
created_at: TIMESTAMP
updated_at: TIMESTAMP
source_version: STRING            # e.g., "1.0.0"
```

**Example**:
```
transaction_key | member_key | asset_key | transaction_date | transaction_type | amount_low | amount_high | days_to_filing | is_late_filing
----------------+------------+-----------+------------------+------------------+------------+-------------+----------------+---------------
1               | 1          | 42        | 2025-01-14       | Purchase         | 250001     | 500000      | 12             | false
```

**Source**: `silver/structured/year=YYYY/doc_id=*/structured.json`

**Update frequency**: Real-time (S3 event-triggered)

---

### fact_filings

Filing-level fact table (metadata about each disclosure filing).

**Grain**: One row per filing

**Partitioning**: `year`

**Schema**:
```
filing_key: BIGINT                # Surrogate key

-- Dimensions
member_key: INT                   # → dim_members
filing_type_key: INT              # → dim_filing_types
filing_date_key: INT              # → dim_date

-- Filing attributes
doc_id: STRING                    # Unique document ID
year: INT
pdf_url: STRING
pdf_pages: INT
pdf_file_size_bytes: BIGINT
pdf_sha256: STRING

-- Counts (from structured extraction)
transaction_count: INT            # For PTRs
asset_count: INT                  # For Annual Reports
liability_count: INT
position_count: INT
agreement_count: INT

-- Filing timeliness
expected_deadline_date: DATE
days_late: INT
is_timely_filed: BOOLEAN
is_amendment: BOOLEAN
original_filing_doc_id: STRING    # If amendment

-- Extraction metadata
extraction_method: STRING         # pypdf, textract
extraction_status: STRING         # success, failed, pending
pdf_type: STRING                  # text, image, hybrid
overall_confidence: FLOAT
has_extracted_data: BOOLEAN
has_structured_data: BOOLEAN
requires_manual_review: BOOLEAN
textract_pages_used: INT          # For budget tracking

-- Audit
created_at: TIMESTAMP
updated_at: TIMESTAMP
```

**Example**:
```
filing_key | member_key | doc_id   | filing_date | transaction_count | pdf_type | overall_confidence | is_timely_filed
-----------+------------+----------+-------------+-------------------+----------+--------------------+----------------
1          | 1          | 20026590 | 2025-01-26  | 9                 | text     | 0.93               | true
```

**Source**:
- `silver/filings/year=YYYY/*.parquet`
- `silver/documents/year=YYYY/*.parquet`
- `silver/structured/year=YYYY/doc_id=*/structured.json`

**Update frequency**: Real-time (S3 event-triggered)

---

## Aggregate Tables

### agg_member_portfolio_daily

Daily portfolio snapshots showing cumulative positions.

**Grain**: One row per member per asset per day

**Partitioning**: `year, month`

**Schema**:
```
member_key: INT
asset_key: INT
date_key: INT

-- Aggregated metrics
total_transactions: INT
total_purchases: INT
total_sales: INT
purchase_volume_low: BIGINT
purchase_volume_high: BIGINT
sale_volume_low: BIGINT
sale_volume_high: BIGINT
net_position_change_low: BIGINT   # purchases - sales
net_position_change_high: BIGINT

-- Calculated position
estimated_current_position_low: BIGINT
estimated_current_position_high: BIGINT
last_transaction_date: DATE
last_transaction_type: STRING

PRIMARY KEY (member_key, asset_key, date_key)
```

**Use case**: "Show Nancy Pelosi's tech stock portfolio over time"

**Update frequency**: Daily (incremental)

---

### agg_member_trading_stats

Member-level trading effectiveness and compliance metrics.

**Grain**: One row per member per period (monthly)

**Partitioning**: `year, period (YYYYMM)`

**Schema**:
```
member_key: INT
period_start_date: DATE
period_end_date: DATE

-- Trading volume
total_transactions: INT
total_purchase_count: INT
total_sale_count: INT
total_exchange_count: INT
estimated_total_volume_low: BIGINT
estimated_total_volume_high: BIGINT

-- Diversification
unique_assets_traded: INT
unique_sectors_traded: INT
concentration_score: FLOAT        # Herfindahl index (0-1, 0=diversified)
top_sector: STRING
top_sector_pct: FLOAT

-- Timeliness & compliance
avg_days_to_filing: FLOAT
median_days_to_filing: INT
late_filing_count: INT
late_filing_pct: FLOAT
same_day_notification_count: INT

-- Document quality metrics 🔍
avg_extraction_confidence: FLOAT
image_pdf_count: INT
image_pdf_pct: FLOAT
manual_review_count: INT

-- Patterns
most_traded_asset_key: INT        # → dim_assets
most_traded_asset_name: STRING
largest_transaction_amount_high: BIGINT
```

**Use case**: "Most active traders in 2025", "Members with late filing patterns"

**Update frequency**: Nightly (incremental)

---

### agg_trending_stocks

Rolling window analysis of stock trading activity.

**Grain**: One row per asset per day

**Partitioning**: `year, month`

**Schema**:
```
date_key: INT
asset_key: INT

-- 7-day rolling metrics
transactions_last_7d: INT
purchases_last_7d: INT
sales_last_7d: INT
unique_members_last_7d: INT
net_buy_pressure_7d: INT          # purchases - sales

-- 30-day rolling metrics
transactions_last_30d: INT
purchases_last_30d: INT
sales_last_30d: INT
unique_members_last_30d: INT

-- Trends
transaction_velocity_7d: FLOAT    # % change from prior 7-day period
buy_sell_ratio: FLOAT             # purchases / sales
momentum_score: FLOAT             # Weighted by recency
is_trending_buy: BOOLEAN          # Momentum > threshold
is_trending_sell: BOOLEAN

PRIMARY KEY (date_key, asset_key)
```

**Use case**: "Top 10 most-purchased stocks this month", "What's being sold off?"

**Update frequency**: Daily (incremental)

---

### agg_sector_activity_monthly

Sector-level trading patterns.

**Grain**: One row per sector per month

**Partitioning**: `year (derived from year_month)`

**Schema**:
```
year_month: INT                   # YYYYMM
sector: STRING

-- Aggregates
unique_members: INT
total_transactions: INT
purchase_count: INT
sale_count: INT
purchase_volume_low: BIGINT
purchase_volume_high: BIGINT
sale_volume_low: BIGINT
sale_volume_high: BIGINT
net_buy_pressure_low: BIGINT
net_buy_pressure_high: BIGINT

-- Top assets in sector
top_5_assets: ARRAY<STRUCT<
  asset_key: INT,
  asset_name: STRING,
  transaction_count: INT
>>

PRIMARY KEY (year_month, sector)
```

**Use case**: "Which sectors are Congress buying into?", "Sector rotation analysis"

**Update frequency**: Nightly (incremental, only current month)

---

### agg_document_quality 🔍

**NEW**: Member-level document quality and compliance tracking.

**Grain**: One row per member per period (monthly)

**Partitioning**: `year`

**Schema**:
```
member_key: INT
period_start_date: DATE
period_end_date: DATE

-- Filing counts
total_filings: INT
ptr_filings: INT
annual_filings: INT

-- Document format breakdown
text_pdf_count: INT
image_pdf_count: INT
hybrid_pdf_count: INT
image_pdf_pct: FLOAT              # % image-based (key metric!)

-- Extraction quality
avg_confidence_score: FLOAT
min_confidence_score: FLOAT
low_confidence_count: INT         # Below MIN_CONFIDENCE_SCORE threshold
manual_review_count: INT
extraction_failure_count: INT

-- Completeness
avg_data_completeness_pct: FLOAT
zero_transaction_filing_count: INT # PTRs with 0 transactions extracted

-- Document quality score (0-100)
quality_score: FLOAT              # Weighted composite score
quality_category: STRING          # Excellent, Good, Fair, Poor

-- Flags
is_hard_to_process: BOOLEAN       # image_pdf_pct > IMAGE_PDF_WARNING_THRESHOLD
quality_trend: STRING             # Improving, Stable, Declining
days_since_last_filing: INT

-- Textract budget usage
textract_pages_used: INT

PRIMARY KEY (member_key, period_start_date)
```

**Quality Score Calculation**:
```
quality_score = (
    avg_confidence_score * QUALITY_WEIGHT_CONFIDENCE +
    (1 - image_pdf_pct) * QUALITY_WEIGHT_FORMAT +
    avg_data_completeness_pct * QUALITY_WEIGHT_COMPLETENESS
) * 100
```

**Use case**: "Which members submit hard-to-process PDFs?", "Document quality leaderboard"

**Update frequency**: Nightly (incremental)

---

## Quality & Audit Tables

### data_quality_metrics

Aggregated data quality metrics across the entire system.

**Grain**: One row per filing type per extraction method per date

**Partitioning**: `metric_date`

**Schema**:
```
metric_date: DATE
filing_type_code: STRING
extraction_method: STRING

-- Quality metrics
total_filings: INT
successful_extractions: INT
failed_extractions: INT
success_rate: FLOAT
avg_confidence_score: FLOAT
avg_completeness_pct: FLOAT
manual_review_count: INT

-- By issue
zero_transaction_count: INT
low_confidence_count: INT
suspicious_pattern_count: INT
timeout_count: INT

-- Performance
avg_extraction_duration_seconds: FLOAT
textract_pages_used: INT

PRIMARY KEY (metric_date, filing_type_code, extraction_method)
```

**Use case**: "System-wide data quality monitoring", "Extraction pipeline health"

**Update frequency**: Daily

---

### extraction_audit_log

Complete audit trail of all extraction operations.

**Grain**: One row per extraction attempt per document

**Partitioning**: `year, month`

**Schema**:
```
audit_key: BIGINT
doc_id: STRING
extraction_timestamp: TIMESTAMP
extraction_version: STRING
extraction_method: STRING
pdf_type: STRING
pdf_file_size_bytes: BIGINT
pdf_page_count: INT

-- Results
extraction_duration_seconds: FLOAT
records_extracted: INT
confidence_score: FLOAT
completeness_pct: FLOAT
extraction_status: STRING

-- Issues
suspicious_patterns: ARRAY<STRING>
validation_warnings: ARRAY<STRING>
error_message: STRING

-- Lineage
bronze_s3_key: STRING
silver_text_s3_key: STRING
silver_structured_s3_key: STRING
gold_load_timestamp: TIMESTAMP
```

**Use case**: "Full lineage tracking", "Debugging failed extractions", "Reprocessing candidates"

**Update frequency**: Real-time (every extraction)

---

## Data Flow & ETL

### Transformation Pipeline

```
Silver Layer                Gold Layer ETL               Gold Layer

structured.json    →   gold_transform_ptr     →   fact_ptr_transactions
    ↓                        ↓                        ↓
    ↓                  enrich_members         →   dim_members (bioguide)
    ↓                        ↓                        ↓
    ↓                  enrich_assets          →   dim_assets (tickers)
    ↓                        ↓                        ↓
    ↓                  compute_aggregates     →   agg_* tables
    ↓                        ↓                        ↓
    ↓                  track_quality          →   agg_document_quality
    └──────────────────────────────────────────→   extraction_audit_log
```

### Lambda Functions

#### gold_transform_ptr_transactions
- **Trigger**: S3 event (`silver/structured/*.json` created)
- **Actions**:
  1. Load structured.json
  2. Lookup member_key (dim_members)
  3. Lookup/create asset_key (dim_assets)
  4. Calculate derived metrics
  5. Write to `fact_ptr_transactions`
  6. Trigger aggregate updates

#### gold_enrich_members
- **Trigger**: EventBridge cron (daily 2 AM UTC)
- **Actions**:
  1. Query distinct members from silver filings
  2. Fuzzy match against existing dim_members
  3. For new/changed members: Call Congress.gov API
  4. Update dim_members with SCD Type 2 logic

#### gold_enrich_assets
- **Trigger**: EventBridge cron (daily 3 AM UTC)
- **Actions**:
  1. Query distinct assets from PTR transactions
  2. Extract ticker symbols (regex patterns)
  3. Call Yahoo Finance API for sector/industry
  4. Call Coinbase API for crypto assets
  5. Update dim_assets

#### gold_update_aggregates
- **Trigger**: EventBridge cron (daily 4 AM UTC)
- **Actions**:
  1. Identify changed partitions (incremental)
  2. Recompute affected aggregates
  3. Write to agg_* tables

#### gold_track_document_quality
- **Trigger**: EventBridge cron (daily 5 AM UTC)
- **Actions**:
  1. Join fact_filings + documents metadata
  2. Calculate per-member quality metrics
  3. Compute quality scores
  4. Write to agg_document_quality

### Deduplication & CDC

**Strategy**: Upsert by natural key

```python
def upsert_fact_table(new_data, partition):
    # Read existing partition
    existing = read_parquet(f"gold/.../year={partition}/")

    # Remove old records for same doc_id (or transaction_key)
    existing_clean = existing[
        ~existing['doc_id'].isin(new_data['doc_id'].unique())
    ]

    # Append new records
    combined = pd.concat([existing_clean, new_data])

    # Write back (overwrite partition)
    combined.to_parquet(
        f"gold/.../year={partition}/",
        partition_cols=['year', 'month'],
        compression='snappy'
    )
```

**For dimensions (SCD Type 2)**:
```python
def upsert_dim_member(new_member):
    # Close current version (if exists)
    existing = query_current_version(bioguide_id=new_member['bioguide_id'])
    if existing and has_changes(existing, new_member):
        existing['effective_to'] = now()
        existing['is_current'] = False
        update_record(existing)

    # Insert new version
    new_member['effective_from'] = now()
    new_member['effective_to'] = None
    new_member['is_current'] = True
    new_member['version'] = (existing.version or 0) + 1
    insert_record(new_member)
```

---

## Query Patterns

### Common Queries

**Member portfolio over time:**
```sql
SELECT
    d.full_date,
    m.full_name,
    a.company_name,
    a.ticker_symbol,
    p.total_purchases,
    p.total_sales,
    p.estimated_current_position_high as position
FROM agg_member_portfolio_daily p
JOIN dim_members m ON p.member_key = m.member_key AND m.is_current = true
JOIN dim_assets a ON p.asset_key = a.asset_key
JOIN dim_date d ON p.date_key = d.date_key
WHERE m.last_name = 'PELOSI'
  AND a.sector = 'Technology'
  AND d.year = 2025
ORDER BY d.full_date, a.company_name
```

**Document quality leaderboard:**
```sql
SELECT
    m.full_name,
    m.party,
    m.state_district,
    q.total_filings,
    q.image_pdf_count,
    ROUND(q.image_pdf_pct * 100, 1) as image_pdf_pct,
    ROUND(q.avg_confidence_score, 3) as avg_confidence,
    ROUND(q.quality_score, 1) as quality_score,
    q.quality_category,
    q.is_hard_to_process
FROM agg_document_quality q
JOIN dim_members m ON q.member_key = m.member_key AND m.is_current = true
WHERE q.period_start_date >= '2025-01-01'
ORDER BY q.image_pdf_pct DESC
LIMIT 20
```

**Trending stocks:**
```sql
SELECT
    a.company_name,
    a.ticker_symbol,
    a.sector,
    t.purchases_last_30d,
    t.sales_last_30d,
    t.unique_members_last_30d,
    t.buy_sell_ratio,
    t.momentum_score
FROM agg_trending_stocks t
JOIN dim_assets a ON t.asset_key = a.asset_key
JOIN dim_date d ON t.date_key = d.date_key
WHERE d.full_date = CURRENT_DATE
  AND t.is_trending_buy = true
ORDER BY t.momentum_score DESC
LIMIT 10
```

---

## Performance Optimization

### File Sizing
- Target: 128-256 MB per Parquet file
- Use `repartition()` in Spark/Pandas before writing
- Consolidate small files weekly

### Partitioning Strategy
- **High cardinality**: Partition by `year, month`
- **Low cardinality**: No partitions or `year` only
- Never partition on low-cardinality columns (party, state)

### Clustering (For Iceberg/Delta Lake)
- Cluster by frequently filtered columns: `member_key, asset_key`
- Improves query performance without partition explosion

### Compression
- Use Snappy (default) for balance of compression + speed
- Consider Zstd for infrequently accessed archives

### Columnar Encoding
- Dictionary encoding for categorical columns (state, party, filing_type)
- RLE encoding for sorted columns (date_key)
- Delta encoding for numeric sequences

---

## Cost Estimates

### Storage (S3)
- Dimension tables: ~50 MB
- Fact tables: ~500 MB/year
- Aggregates: ~200 MB/year
- **Total**: ~750 MB/year × 5 years = **3.75 GB** (well within 5 GB free tier)

### Compute (Lambda)
- Transformation: 5K invocations/month × 512 MB × 30s = $0.42/month
- Enrichment: 500 invocations/month × 512 MB × 10s = $0.04/month
- Aggregates: 100 invocations/month × 1024 MB × 60s = $0.21/month
- **Total**: **$0.67/month** (well within 1M free tier invocations)

### Queries (Athena)
- 10 GB scanned/month = $0.05/month

**Grand total: ~$0.72/month** 🎉

---

## Related Documentation

- [API Key Setup](API_KEY_SETUP.md)
- [Extraction Methods](EXTRACTION_METHODS.md)
- [Free Tier Optimization](FREE_TIER_OPTIMIZATION.md)
- [API Strategy](API_STRATEGY.md)
