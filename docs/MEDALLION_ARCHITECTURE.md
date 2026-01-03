# Medallion Architecture - Data Lake Design

## Overview

This document defines the complete medallion architecture (Bronze → Silver → Gold) for the Congress Disclosures data lake, replacing the legacy Makefile-based pipeline with a modern, automated, free-tier AWS architecture.

## Architecture Principles

1. **Separation of Storage and Compute**: Data stored in S3, compute in Lambda/Step Functions
2. **Incremental Processing**: Watermark-based incremental loads, no full rebuilds
3. **Data Quality Gates**: Soda Core validation at each layer transition
4. **Idempotent Transformations**: Re-running produces same results
5. **Cost Optimization**: Free-tier AWS services, DuckDB instead of Athena, ZSTD compression
6. **Scalability**: Designed for 10x data growth within free-tier limits

## Tool Stack

| Component | Tool | Rationale | Cost |
|-----------|------|-----------|------|
| **Orchestration** | AWS Step Functions | Serverless DAGs, 4K free transitions/month | $0 |
| **Transformation** | DuckDB | 10-100x faster than Pandas, S3-native | $0 |
| **Storage Format** | Parquet (→ Iceberg Phase 2) | Columnar, ZSTD compression, schema evolution | $0.023/GB |
| **Data Quality** | Soda Core | SQL-based checks, fail-fast validation | $0 |
| **Metadata** | AWS Glue Data Catalog | 1M objects free, schema registry | $0 |
| **Scheduling** | EventBridge | Cron triggers (daily/weekly, DISABLED until watermarking) | $0 |
| **Monitoring** | CloudWatch + SNS | Dashboards, logs, alerts | $0 (within limits) |
| **Watermarking** | DynamoDB | Track incremental processing state | $0 (25GB free) |

**Total Cost**: ~$0.35/month (S3 storage only)
**Previous Cost**: ~$51.35/month (Athena queries)
**Savings**: $51/month (99.3% reduction)

---

## Bronze Layer (Raw/Immutable)

**Purpose**: Byte-for-byte preservation of source data with audit trail

**Location**: `s3://congress-disclosures-standardized/bronze/`

### Bronze Tables

#### 1. `bronze/house/financial/raw_zip/`
- **Format**: ZIP files (original)
- **Partitioning**: `year=YYYY/YYYYFD.zip`
- **Retention**: 7 years
- **Lifecycle**: Glacier after 1 year
- **Source**: House Clerk website
- **Update Frequency**: Hourly check, ingest on new filings

#### 2. `bronze/house/financial/index/`
- **Format**: XML files
- **Partitioning**: `year=YYYY/YYYYFD.xml`
- **Schema**: Raw XML from House Clerk index
- **Contains**: Filing metadata (doc_id, member, filing_date, filing_type)

#### 3. `bronze/house/financial/pdfs/`
- **Format**: PDF files
- **Partitioning**: `year=YYYY/filing_type={P,A,T,X,D,W}/doc_id={doc_id}.pdf`
- **Metadata Tags**:
  - `extraction-processed: true/false` (prevents duplicate OCR)
  - `sha256_hash: <hash>` (integrity verification)
  - `source_url: <url>` (audit trail)

#### 4. `bronze/congress_gov/bills/`
- **Format**: JSON (Congress.gov API responses)
- **Partitioning**: `congress=119/bill_type={hr,s,hjres,...}/bill_number={num}/metadata.json`
- **Update Frequency**: Daily
- **Retention**: Indefinite (historical legislative data)

#### 5. `bronze/congress_gov/members/`
- **Format**: JSON
- **Partitioning**: `bioguide_id={bioguide_id}/member.json`
- **Update Frequency**: Weekly
- **Contains**: Member biographical data, committee assignments, sponsorships

#### 6. `bronze/lobbying/disclosures/`
- **Format**: XML (Senate LDA database)
- **Partitioning**: `year=YYYY/quarter={Q1,Q2,Q3,Q4}/filing_id={id}.xml`
- **Update Frequency**: Quarterly
- **Source**: Senate Lobbying Disclosure Act database

---

## Silver Layer (Normalized/Queryable)

**Purpose**: Cleaned, normalized, deduplicated data in analytical format

**Location**: `s3://congress-disclosures-standardized/silver/`

### Silver Tables

#### 1. `silver/house/financial/filings/`
- **Format**: Parquet (ZSTD compression)
- **Partitioning**: `year=YYYY/filing_type={P,A,T,X,D,W}/`
- **Schema**:
  ```sql
  CREATE TABLE silver.filings (
    doc_id STRING PRIMARY KEY,
    bioguide_id STRING,
    first_name STRING,
    last_name STRING,
    office STRING,
    state_district STRING,
    filing_type STRING,
    filing_year INT,
    filing_date DATE,
    amended BOOLEAN,
    amendment_number INT,
    filing_status STRING,
    original_source STRING,
    xml_source_url STRING,
    pdf_url STRING,
    sha256_hash STRING,
    ingestion_timestamp TIMESTAMP,
    silver_ingest_ts TIMESTAMP
  );
  ```
- **Indexes**: bioguide_id, filing_date, filing_type
- **Update Pattern**: Upsert on doc_id (deduplicate amendments)

#### 2. `silver/house/financial/documents/`
- **Format**: Parquet
- **Partitioning**: `year=YYYY/`
- **Schema**:
  ```sql
  CREATE TABLE silver.documents (
    doc_id STRING PRIMARY KEY,
    filing_type STRING,
    pdf_path STRING,
    num_pages INT,
    file_size_bytes BIGINT,
    pdf_format STRING, -- 'TEXT', 'IMAGE', 'HYBRID'
    extraction_method STRING, -- 'direct_text', 'ocr', 'failed'
    extraction_status STRING, -- 'success', 'partial', 'failed'
    text_confidence_score FLOAT,
    text_length INT,
    text_path STRING,
    structured_extraction_status STRING,
    structured_objects_path STRING,
    extraction_timestamp TIMESTAMP,
    silver_ingest_ts TIMESTAMP
  );
  ```

#### 3. `silver/house/financial/text/`
- **Format**: Gzipped text files
- **Partitioning**: `extraction_method={direct_text,ocr}/year=YYYY/doc_id={doc_id}.txt.gz`
- **Contents**: Extracted text from PDFs
- **Lifecycle**: Glacier after 2 years (rarely accessed after extraction)

#### 4. `silver/house/financial/transactions/`
- **Format**: Parquet
- **Partitioning**: `year=YYYY/month=MM/`
- **Schema**:
  ```sql
  CREATE TABLE silver.transactions (
    transaction_id STRING PRIMARY KEY, -- Generated: {doc_id}_{row_index}
    doc_id STRING NOT NULL,
    bioguide_id STRING,
    first_name STRING,
    last_name STRING,
    party STRING,
    state STRING,
    transaction_date DATE,
    asset_name STRING,
    asset_type STRING,
    ticker STRING,
    transaction_type STRING, -- 'Purchase', 'Sale', 'Exchange'
    amount_range STRING,
    amount_low DECIMAL(15,2),
    amount_high DECIMAL(15,2),
    notification_date DATE,
    capital_gains_over_200 BOOLEAN,
    comments STRING,
    extraction_method STRING,
    extraction_confidence FLOAT,
    silver_ingest_ts TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES silver.filings(doc_id)
  );
  ```
- **Indexes**: bioguide_id, transaction_date, ticker
- **Data Quality**: Referential integrity to filings, date validation, amount range validation

#### 5. `silver/house/financial/assets/`
- **Format**: Parquet
- **Partitioning**: `year=YYYY/`
- **Schema**:
  ```sql
  CREATE TABLE silver.assets (
    asset_id STRING PRIMARY KEY,
    doc_id STRING NOT NULL,
    bioguide_id STRING,
    asset_name STRING,
    asset_type STRING,
    ticker STRING,
    owner STRING, -- 'Self', 'Spouse', 'Dependent Child', 'Joint'
    value_range STRING,
    value_low DECIMAL(15,2),
    value_high DECIMAL(15,2),
    income_type STRING,
    income_range STRING,
    income_low DECIMAL(15,2),
    income_high DECIMAL(15,2),
    location STRING, -- For real estate
    silver_ingest_ts TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES silver.filings(doc_id)
  );
  ```

#### 6. `silver/congress_gov/bills/`
- **Format**: Parquet
- **Partitioning**: `congress=119/bill_type={hr,s,...}/`
- **Schema**:
  ```sql
  CREATE TABLE silver.bills (
    bill_id STRING PRIMARY KEY, -- '119-hr-1234'
    congress INT,
    bill_type STRING,
    bill_number INT,
    title STRING,
    title_short STRING,
    introduced_date DATE,
    latest_action_date DATE,
    latest_action_text STRING,
    sponsor_bioguide_id STRING,
    sponsor_name STRING,
    sponsor_party STRING,
    sponsor_state STRING,
    num_cosponsors INT,
    num_committees INT,
    policy_area STRING,
    subjects ARRAY<STRING>,
    bill_status STRING, -- 'Introduced', 'Passed House', 'Passed Senate', 'Enacted', etc.
    law_number STRING,
    bill_text_url STRING,
    congress_gov_url STRING,
    silver_ingest_ts TIMESTAMP
  );
  ```

#### 7. `silver/congress_gov/cosponsors/`
- **Format**: Parquet
- **Partitioning**: `congress=119/`
- **Schema**:
  ```sql
  CREATE TABLE silver.cosponsors (
    cosponsor_id STRING PRIMARY KEY,
    bill_id STRING NOT NULL,
    bioguide_id STRING,
    full_name STRING,
    party STRING,
    state STRING,
    district STRING,
    date_cosponsored DATE,
    is_original_cosponsor BOOLEAN,
    withdrawn_date DATE,
    silver_ingest_ts TIMESTAMP,
    FOREIGN KEY (bill_id) REFERENCES silver.bills(bill_id)
  );
  ```

#### 8. `silver/lobbying/disclosures/`
- **Format**: Parquet
- **Partitioning**: `year=YYYY/quarter={Q1,Q2,Q3,Q4}/`
- **Schema**:
  ```sql
  CREATE TABLE silver.lobbying_disclosures (
    filing_id STRING PRIMARY KEY,
    filing_type STRING,
    filing_year INT,
    filing_period STRING,
    registrant_name STRING,
    registrant_id STRING,
    client_name STRING,
    client_id STRING,
    client_state STRING,
    client_country STRING,
    amount DECIMAL(15,2),
    income DECIMAL(15,2),
    expense DECIMAL(15,2),
    termination_date DATE,
    issues ARRAY<STRING>,
    lobbying_activities STRING,
    silver_ingest_ts TIMESTAMP
  );
  ```

#### 9. `silver/lobbying/lobbyists/`
- **Format**: Parquet
- **Schema**:
  ```sql
  CREATE TABLE silver.lobbyists (
    lobbyist_id STRING PRIMARY KEY,
    filing_id STRING,
    lobbyist_name STRING,
    covered_position STRING, -- Former government position
    new_lobbyist BOOLEAN,
    silver_ingest_ts TIMESTAMP,
    FOREIGN KEY (filing_id) REFERENCES silver.lobbying_disclosures(filing_id)
  );
  ```

---

## Gold Layer (Query-Facing/Aggregated)

**Purpose**: Optimized star schema for analytics, pre-computed aggregates, API cache

**Location**: `s3://congress-disclosures-standardized/gold/`

### Gold Dimensions (SCD Type 2)

#### 1. `gold/dimensions/dim_member/`
- **Format**: Parquet
- **SCD Type**: 2 (track historical changes)
- **Schema**:
  ```sql
  CREATE TABLE gold.dim_member (
    member_key BIGINT PRIMARY KEY, -- Surrogate key
    bioguide_id STRING NOT NULL,
    full_name STRING,
    first_name STRING,
    last_name STRING,
    party STRING,
    state STRING,
    district STRING,
    chamber STRING, -- 'House', 'Senate'
    office STRING,
    phone STRING,
    twitter_handle STRING,
    official_website STRING,
    leadership_role STRING,
    committees ARRAY<STRING>,
    subcommittees ARRAY<STRING>,
    valid_from DATE,
    valid_to DATE,
    is_current BOOLEAN,
    gold_ingest_ts TIMESTAMP
  );
  ```
- **Update Pattern**: Detect changes in party, district, committees → Insert new row with updated valid_from

#### 2. `gold/dimensions/dim_asset/`
- **Format**: Parquet
- **Schema**:
  ```sql
  CREATE TABLE gold.dim_asset (
    asset_key BIGINT PRIMARY KEY,
    ticker STRING,
    asset_name STRING,
    asset_type STRING, -- 'Stock', 'Bond', 'Mutual Fund', 'Real Estate', etc.
    industry STRING,
    sector STRING,
    exchange STRING,
    cusip STRING,
    first_traded_date DATE,
    last_traded_date DATE,
    total_trade_count INT,
    total_trade_volume DECIMAL(15,2),
    gold_ingest_ts TIMESTAMP
  );
  ```

#### 3. `gold/dimensions/dim_date/`
- **Format**: Parquet
- **Schema**:
  ```sql
  CREATE TABLE gold.dim_date (
    date_key INT PRIMARY KEY, -- YYYYMMDD
    date DATE,
    year INT,
    quarter INT,
    month INT,
    day INT,
    day_of_week INT,
    day_name STRING,
    week_of_year INT,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN,
    holiday_name STRING,
    fiscal_year INT,
    fiscal_quarter INT,
    congress_session INT
  );
  ```
- **Preloaded**: 2008-2035 (all possible dates)

#### 4. `gold/dimensions/dim_bill/`
- **Format**: Parquet
- **Partitioning**: `congress=119/`
- **Schema**:
  ```sql
  CREATE TABLE gold.dim_bill (
    bill_key BIGINT PRIMARY KEY,
    bill_id STRING NOT NULL,
    congress INT,
    bill_type STRING,
    bill_number INT,
    title STRING,
    title_short STRING,
    sponsor_bioguide_id STRING,
    sponsor_name STRING,
    policy_area STRING,
    subjects ARRAY<STRING>,
    introduced_date DATE,
    enacted_date DATE,
    bill_status STRING,
    law_number STRING,
    is_enacted BOOLEAN,
    gold_ingest_ts TIMESTAMP
  );
  ```

### Gold Facts

#### 1. `gold/facts/fact_ptr_transactions/`
- **Format**: Parquet
- **Partitioning**: `year=YYYY/month=MM/`
- **Schema**:
  ```sql
  CREATE TABLE gold.fact_ptr_transactions (
    transaction_key BIGINT PRIMARY KEY,
    transaction_id STRING NOT NULL,
    doc_id STRING,
    member_key BIGINT,
    asset_key BIGINT,
    transaction_date_key INT,
    notification_date_key INT,
    bioguide_id STRING,
    ticker STRING,
    transaction_type STRING,
    amount_low DECIMAL(15,2),
    amount_high DECIMAL(15,2),
    amount_midpoint DECIMAL(15,2),
    capital_gains_over_200 BOOLEAN,
    days_to_notification INT,
    extraction_confidence FLOAT,
    gold_ingest_ts TIMESTAMP,
    FOREIGN KEY (member_key) REFERENCES gold.dim_member(member_key),
    FOREIGN KEY (asset_key) REFERENCES gold.dim_asset(asset_key),
    FOREIGN KEY (transaction_date_key) REFERENCES gold.dim_date(date_key)
  );
  ```
- **Indexes**: member_key, asset_key, transaction_date_key, ticker
- **Partitioning**: By transaction_date (year/month) for time-range queries

#### 2. `gold/facts/fact_filings/`
- **Format**: Parquet
- **Partitioning**: `year=YYYY/`
- **Schema**:
  ```sql
  CREATE TABLE gold.fact_filings (
    filing_key BIGINT PRIMARY KEY,
    doc_id STRING NOT NULL,
    member_key BIGINT,
    filing_date_key INT,
    bioguide_id STRING,
    filing_type STRING,
    filing_year INT,
    is_amendment BOOLEAN,
    amendment_number INT,
    num_pages INT,
    extraction_method STRING,
    text_confidence_score FLOAT,
    num_transactions INT,
    total_transaction_volume DECIMAL(15,2),
    num_assets INT,
    total_asset_value DECIMAL(15,2),
    filing_quality_score FLOAT,
    days_late INT, -- Compliance metric
    gold_ingest_ts TIMESTAMP,
    FOREIGN KEY (member_key) REFERENCES gold.dim_member(member_key)
  );
  ```

#### 3. `gold/facts/fact_bill_cosponsors/`
- **Format**: Parquet
- **Partitioning**: `congress=119/`
- **Schema**:
  ```sql
  CREATE TABLE gold.fact_bill_cosponsors (
    cosponsor_key BIGINT PRIMARY KEY,
    bill_key BIGINT,
    member_key BIGINT,
    date_cosponsored_key INT,
    bioguide_id STRING,
    bill_id STRING,
    is_original_cosponsor BOOLEAN,
    is_withdrawn BOOLEAN,
    days_to_cosponsor INT,
    gold_ingest_ts TIMESTAMP,
    FOREIGN KEY (bill_key) REFERENCES gold.dim_bill(bill_key),
    FOREIGN KEY (member_key) REFERENCES gold.dim_member(member_key)
  );
  ```

#### 4. `gold/facts/fact_lobbying_activity/`
- **Format**: Parquet
- **Partitioning**: `year=YYYY/quarter={Q1,Q2,Q3,Q4}/`
- **Schema**:
  ```sql
  CREATE TABLE gold.fact_lobbying_activity (
    activity_key BIGINT PRIMARY KEY,
    filing_id STRING,
    filing_date_key INT,
    registrant_name STRING,
    client_name STRING,
    amount DECIMAL(15,2),
    income DECIMAL(15,2),
    expense DECIMAL(15,2),
    issues ARRAY<STRING>,
    num_lobbyists INT,
    num_former_officials INT,
    gold_ingest_ts TIMESTAMP
  );
  ```

### Gold Aggregates (Pre-computed Metrics)

#### 1. `gold/aggregates/agg_trending_stocks/`
- **Format**: Parquet
- **Update Frequency**: Hourly (after new transactions)
- **Schema**:
  ```sql
  CREATE TABLE gold.agg_trending_stocks (
    ticker STRING,
    time_window STRING, -- '7d', '30d', '90d'
    total_transactions INT,
    total_volume DECIMAL(15,2),
    num_buyers INT,
    num_sellers INT,
    buy_volume DECIMAL(15,2),
    sell_volume DECIMAL(15,2),
    net_volume DECIMAL(15,2),
    dem_transactions INT,
    rep_transactions INT,
    sentiment_score FLOAT, -- Net volume / Total volume
    first_trade_date DATE,
    last_trade_date DATE,
    computed_at TIMESTAMP,
    PRIMARY KEY (ticker, time_window)
  );
  ```

#### 2. `gold/aggregates/agg_member_trading_stats/`
- **Format**: Parquet
- **Update Frequency**: Daily
- **Schema**:
  ```sql
  CREATE TABLE gold.agg_member_trading_stats (
    bioguide_id STRING PRIMARY KEY,
    full_name STRING,
    party STRING,
    state STRING,
    time_window STRING, -- 'ytd', '1y', 'all_time'
    total_transactions INT,
    total_volume DECIMAL(15,2),
    num_unique_assets INT,
    buy_count INT,
    sell_count INT,
    buy_volume DECIMAL(15,2),
    sell_volume DECIMAL(15,2),
    avg_trade_size DECIMAL(15,2),
    largest_trade DECIMAL(15,2),
    most_traded_ticker STRING,
    last_trade_date DATE,
    avg_days_to_notification FLOAT,
    late_filings_count INT,
    filing_quality_score FLOAT,
    computed_at TIMESTAMP
  );
  ```

#### 3. `gold/aggregates/agg_document_quality/`
- **Format**: Parquet
- **Schema**:
  ```sql
  CREATE TABLE gold.agg_document_quality (
    bioguide_id STRING PRIMARY KEY,
    full_name STRING,
    total_filings INT,
    text_filings_count INT,
    image_filings_count INT,
    hybrid_filings_count INT,
    avg_confidence_score FLOAT,
    avg_pages INT,
    total_extraction_failures INT,
    quality_score FLOAT, -- Composite score
    last_filing_date DATE,
    computed_at TIMESTAMP
  );
  ```

#### 4. `gold/aggregates/agg_network_graph/`
- **Format**: JSON (D3.js ready)
- **Update Frequency**: Daily
- **Schema**:
  ```json
  {
    "nodes": [
      {
        "id": "bioguide_id",
        "name": "Member Name",
        "group": "member",
        "party": "Democrat",
        "state": "CA",
        "value": 5000000,
        "transaction_count": 45
      },
      {
        "id": "AAPL",
        "name": "Apple Inc.",
        "group": "asset",
        "value": 8000000,
        "transaction_count": 85,
        "degree": 12
      }
    ],
    "links": [
      {
        "source": "bioguide_id",
        "target": "AAPL",
        "value": 500000,
        "count": 5,
        "type": "purchase"
      }
    ],
    "aggregated_nodes": [
      {
        "id": "Democrat",
        "group": "party_agg",
        "value": 7500000,
        "transaction_count": 73
      }
    ],
    "aggregated_links": [],
    "computed_at": "2025-01-11T12:00:00Z"
  }
  ```

#### 5. `gold/aggregates/agg_bill_trading_correlations/`
- **Format**: Parquet
- **Update Frequency**: Weekly
- **Schema**:
  ```sql
  CREATE TABLE gold.agg_bill_trading_correlations (
    correlation_key BIGINT PRIMARY KEY,
    bill_id STRING,
    ticker STRING,
    bioguide_id STRING,
    bill_introduced_date DATE,
    first_trade_date DATE,
    days_between INT,
    transaction_type STRING,
    transaction_volume DECIMAL(15,2),
    bill_status STRING,
    is_sponsor BOOLEAN,
    is_cosponsor BOOLEAN,
    is_committee_member BOOLEAN,
    correlation_score FLOAT,
    computed_at TIMESTAMP
  );
  ```

### Gold API Cache (JSON Files)

These are pre-computed JSON responses for common API queries to eliminate Lambda/DuckDB overhead:

#### 1. `gold/api_cache/trending_stocks_7d.json`
```json
{
  "data": [...],
  "generated_at": "2025-01-11T12:00:00Z",
  "ttl": 3600
}
```

#### 2. `gold/api_cache/top_traders_ytd.json`
#### 3. `gold/api_cache/recent_transactions.json`
#### 4. `gold/api_cache/dashboard_stats.json`

**Update Pattern**: CloudWatch Events trigger Lambda every hour to regenerate cache files

---

## Incremental Processing Strategy

### Watermark Table (DynamoDB)

```python
# Table: pipeline_watermarks
{
  "table_name": "gold.fact_ptr_transactions",  # Partition key
  "watermark_type": "max_doc_id",  # Sort key
  "last_processed_value": "20026590",
  "last_processed_timestamp": "2025-01-11T10:30:00Z",
  "last_run_status": "success",
  "rows_processed": 1250
}
```

### Incremental Load Pattern

```sql
-- Get watermark
SELECT last_processed_value FROM watermarks
WHERE table_name = 'gold.fact_ptr_transactions';

-- Incremental load (DuckDB)
INSERT INTO gold.fact_ptr_transactions
SELECT
  ROW_NUMBER() OVER () + (SELECT MAX(transaction_key) FROM gold.fact_ptr_transactions) AS transaction_key,
  t.*,
  m.member_key,
  a.asset_key,
  CAST(REPLACE(CAST(t.transaction_date AS STRING), '-', '') AS INT) AS transaction_date_key,
  CURRENT_TIMESTAMP AS gold_ingest_ts
FROM 's3://bucket/silver/house/financial/transactions/*.parquet' t
LEFT JOIN 's3://bucket/gold/dimensions/dim_member/*.parquet' m
  ON t.bioguide_id = m.bioguide_id AND m.is_current = true
LEFT JOIN 's3://bucket/gold/dimensions/dim_asset/*.parquet' a
  ON t.ticker = a.ticker
WHERE t.doc_id > '${last_processed_value}'  -- INCREMENTAL!
  AND t.transaction_date >= CURRENT_DATE - INTERVAL '2 years';

-- Update watermark
UPDATE watermarks
SET last_processed_value = (SELECT MAX(doc_id) FROM silver.transactions),
    last_processed_timestamp = CURRENT_TIMESTAMP,
    rows_processed = ${rows_inserted};
```

---

## Data Quality Framework (Soda Core)

### Quality Check Categories

1. **Schema Validation**: Column existence, data types
2. **Referential Integrity**: Foreign key checks
3. **Data Freshness**: Ensure recent data exists
4. **Anomaly Detection**: Row count, value distribution changes
5. **Business Rules**: Valid date ranges, amount ranges, enum values

### Example Checks

**`soda/checks/silver_transactions.yml`**:
```yaml
checks for silver.transactions:
  - schema:
      fail when required column missing:
        - doc_id
        - transaction_date
        - asset_name
        - transaction_type
        - amount_low

  - values in (doc_id) must exist in silver.filings (doc_id):
      name: Referential integrity to filings

  - invalid_count(transaction_date) = 0:
      valid min: 2008-01-01
      valid max: ${TODAY}
      name: Valid transaction dates

  - invalid_count(transaction_type) = 0:
      valid values: ['Purchase', 'Sale', 'Exchange']

  - freshness(silver_ingest_ts) < 2h:
      name: Silver data is fresh

  - anomaly score for row_count < 3:
      name: Row count matches historical pattern

  - avg(amount_low) between 10000 and 500000:
      name: Average trade size is reasonable
```

**`soda/checks/gold_fact_transactions.yml`**:
```yaml
checks for gold.fact_ptr_transactions:
  - row_count > 100000:
      name: Minimum expected transactions

  - missing_count(member_key) = 0:
      name: All transactions have member dimension

  - duplicate_count(transaction_id) = 0:
      name: No duplicate transactions

  - values in (bioguide_id) must exist in gold.dim_member (bioguide_id):
      name: Referential integrity to member dimension

  - freshness(gold_ingest_ts) < 24h:
      name: Gold layer updated daily
```

### Quality Gate Integration

Step Functions integrate quality checks as fail-fast gates:

```json
{
  "TransformToGold": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:::function:build-fact-transactions",
    "Next": "ValidateGoldQuality"
  },
  "ValidateGoldQuality": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:::function:run-soda-checks",
    "Parameters": {
      "checks_path": "soda/checks/gold_fact_transactions.yml"
    },
    "Catch": [{
      "ErrorEquals": ["DataQualityFailure"],
      "Next": "SendQualityAlert"
    }],
    "Next": "PublishGoldMetrics"
  }
}
```

---

## Orchestration Architecture

### Pipeline DAGs

1. **House FD Pipeline** (Hourly)
   - Check for new filings → Ingest ZIP → Index to Silver → Extract Documents → Transform to Gold → Quality Checks → Update API Cache

2. **Congress.gov Pipeline** (Daily)
   - Fetch new bills → Fetch bill details → Fetch cosponsors → Transform to Silver → Build dim_bill → Update correlations

3. **Lobbying Pipeline** (Weekly)
   - Check for new filings → Download XML → Parse to Silver → Transform to Gold

4. **Cross-Dataset Correlation Pipeline** (Event-triggered after House FD completes)
   - Build bill-trading correlations → Build member-asset network → Update aggregates

### Monitoring & Alerts

**CloudWatch Dashboards**:
- Pipeline execution metrics (success rate, duration)
- Data volume metrics (rows processed, storage size)
- Data quality metrics (check pass rate, anomaly counts)
- API performance (cache hit rate, query latency)

**SNS Alerts**:
- Pipeline failures
- Data quality check failures
- Ingestion delays (no new data for 48+ hours)
- Cost anomalies (unexpected charges)

---

## Migration Checklist

- [ ] Week 1: Step Functions infrastructure, EventBridge triggers
- [ ] Week 2: DuckDB Lambda layer, rewrite 3 Gold scripts
- [ ] Week 3: Soda Core integration, 30+ quality checks
- [ ] Week 4: API handler migration (eliminate Athena)
- [ ] Week 5-6: Parallel validation (old vs new pipeline)
- [ ] Week 7: Final cutover, decommission Makefile scripts

---

## Future Enhancements (Phase 2)

1. **Apache Iceberg Tables**: ACID transactions, schema evolution, time travel queries
2. **Social Media Ingestion**: Twitter/X mentions, sentiment analysis
3. **Real-time Stream Processing**: Kinesis Data Streams for live updates
4. **Machine Learning**: Trade prediction models, anomaly detection
5. **Data Marketplace**: OpenAPI monetization, usage-based billing
6. **Multi-Region Replication**: DR and global distribution
