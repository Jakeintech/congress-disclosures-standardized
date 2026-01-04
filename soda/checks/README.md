# Soda Quality Checks

## Overview

This directory contains Soda Core quality check definitions for the Congress Disclosures data pipeline. These checks validate data quality across Bronze (raw), Silver (normalized), and Gold (analytics-ready) layers of the medallion architecture.

## Check Severity Levels

The pipeline uses three severity levels to control behavior:

- **Critical**: Fails pipeline execution, requires immediate attention
  - Used for: Schema violations, missing primary keys, referential integrity failures
  - Action: Pipeline stops, SNS alert sent, manual intervention required
  
- **Warning**: Logs issue but pipeline continues, investigate during next sprint
  - Used for: Low success rates, anomaly detection, freshness issues
  - Action: CloudWatch log entry, investigate in weekly review
  
- **Info**: Monitoring only, no action required
  - Used for: Trend analysis, distribution monitoring, performance metrics
  - Action: Logged for observability, informational only

## Check Categories

Quality checks are organized into five categories:

### 1. Completeness
- **Purpose**: Ensure required data is present
- **Examples**: Row count > 0, missing_count(column) = 0
- **Business Impact**: Incomplete data breaks downstream analytics

### 2. Freshness
- **Purpose**: Validate data recency
- **Examples**: freshness(timestamp) < 24h
- **Business Impact**: Stale data misleads users about current activity

### 3. Schema
- **Purpose**: Enforce expected structure
- **Examples**: Column type validation, required fields
- **Business Impact**: Schema drift breaks queries and downstream systems

### 4. Referential Integrity
- **Purpose**: Validate foreign key relationships
- **Examples**: values in (fk) must exist in dimension (pk)
- **Business Impact**: Orphaned records create incorrect aggregations

### 5. Business Logic
- **Purpose**: Enforce domain rules
- **Examples**: amount_low <= amount_high, valid value sets
- **Business Impact**: Invalid data produces incorrect analytics

## Check Files

### Bronze Layer (Raw/Immutable)
**File**: `bronze_house_fd.yml` (12 checks)
- Completeness: Bronze has PDFs, sufficient volume
- Freshness: Data updated within 48 hours
- Integrity: SHA256 checksums present and valid
- Uniqueness: No duplicate doc_ids or file hashes
- Validation: File sizes realistic (1KB-50MB)

**Business Rationale**: Bronze is the source of truth. If Bronze is corrupted or incomplete, all downstream layers are compromised.

### Silver Layer (Normalized/Queryable)

**File**: `silver_filings.yml` (9 checks)
- Schema: Required columns, correct types
- Uniqueness: doc_id is unique
- Valid values: Filing types in ['P', 'A', 'T', 'X', 'D', 'W']
- Date ranges: 2008-2026 (e-filing era)
- Freshness: Updated within 24 hours

**Business Rationale**: Filings are the core entity. Invalid filing metadata breaks all member/transaction lookups.

---

**File**: `silver_documents.yml` (12 checks)
- Schema: Extraction metadata present
- Extraction status: 90%+ success rate
- Method distribution: 70%+ direct_text (quality indicator)
- Page counts: 1-500 pages (realistic range)
- Referential integrity: Links to Bronze PDFs

**Business Rationale**: Document extraction quality directly impacts data completeness. Low success rates indicate PDF format changes or extraction bugs.

---

**File**: `silver_text.yml` (16 checks)
- Schema: Text extraction structure
- Confidence scores: 0.0-1.0 range, average > 0.80
- Text length: Meaningful content (50+ chars)
- Method distribution: Track OCR vs direct_text trends
- Referential integrity: Links to silver_documents

**Business Rationale**: Text extraction is the foundation for structured data extraction. Low confidence scores indicate poor OCR quality or format issues.

---

**File**: `silver_transactions.yml` (13 checks)
- Schema: Transaction structure
- Date ranges: Valid transaction dates
- Amount validation: amount_low <= amount_high
- Transaction types: Valid values (Purchase/Sale/Exchange)
- Ticker presence: 70%+ have tickers

**Business Rationale**: Transactions are the most queried data. Invalid amounts or types break financial analytics.

---

**File**: `silver_lobbying.yml` (10 checks)
- Schema: LDA disclosure structure
- Financial validation: Non-negative amounts
- Quarter validation: Q1/Q2/Q3/Q4 only
- Uniqueness: No duplicate filing_id
- Freshness: Updated within 48 hours

**Business Rationale**: Lobbying data supports cross-dataset correlation with member trading. Incomplete quarterly data breaks trend analysis.

### Gold Layer (Analytics-Ready)

**File**: `gold_dim_member.yml` (11 checks)
- Schema: SCD Type 2 structure (valid_from, valid_to, is_current)
- Primary key: member_key is unique
- SCD validation: Only one is_current=true per bioguide_id
- Party codes: Valid values (D/R/I)
- State codes: 2-letter format

**Business Rationale**: Member dimension is the primary lookup for all user queries. SCD violations cause duplicate member records in dashboards.

---

**File**: `gold_fact_transactions.yml` (12 checks)
- Referential integrity: Valid member/asset/date keys
- Amount validation: Midpoint correctly calculated
- Business rules: amount_low >= 0, amount_high >= amount_low
- Row count: 100K+ total transactions
- Freshness: Updated within 12 hours

**Business Rationale**: Fact table is the most queried table. Orphaned dimension keys cause missing data in reports.

---

**File**: `gold_fact_lobbying.yml` (12 checks)
- Referential integrity: Valid client/registrant/date keys
- Financial validation: Non-negative income/expense
- Calculation: net_amount = income - expense
- Row count: 10K+ records per year
- Freshness: Updated within 12 hours

**Business Rationale**: Lobbying facts support correlation analysis with member trading. Invalid financial amounts break expense analysis.

---

**File**: `gold_agg_trending_stocks.yml` (10 checks)
- Schema: Aggregation structure
- Time windows: Valid values (7d/30d/90d)
- Calculation: total_volume = buy_volume + sell_volume
- Sentiment: Score between -1.0 and 1.0
- Freshness: Updated within 24 hours

**Business Rationale**: Trending stocks are the most visible user feature. Invalid calculations break the entire trending stocks widget.

## Running Checks

### Locally (Development)

```bash
# Install Soda Core
pip install soda-core-duckdb

# Run all checks
soda scan -d congress_s3 -c soda/configuration.yml soda/checks/*.yml

# Run specific layer
soda scan -d congress_s3 -c soda/configuration.yml soda/checks/silver_*.yml

# Run single file
soda scan -d congress_s3 -c soda/configuration.yml soda/checks/gold_fact_transactions.yml
```

### In Lambda (Production)

Quality checks are executed via the `run_soda_checks` Lambda function, which is invoked by Step Functions at each layer transition:

1. **Bronze → Silver**: Validates Bronze completeness before extraction
2. **Silver → Gold**: Validates Silver schema/integrity before transformation
3. **Gold → Publish**: Validates Gold calculations before website deployment

**Lambda Event**:
```json
{
  "checks_path": "soda/checks/silver_filings.yml"
}
```

**Lambda Response**:
```json
{
  "status": "success|failed",
  "checks_run": 12,
  "checks_passed": 11,
  "checks_failed": 1,
  "failures": [
    {
      "check": "90%+ extraction success rate",
      "severity": "warning",
      "message": "Actual: 85%, Expected: > 90%"
    }
  ]
}
```

### In Step Functions

Quality gates are implemented as Step Function states:

```json
{
  "ValidateSilver": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...:function:run_soda_checks",
    "Parameters": {
      "checks_path": "soda/checks/silver_filings.yml"
    },
    "Catch": [
      {
        "ErrorEquals": ["States.ALL"],
        "ResultPath": "$.error",
        "Next": "NotifyDataQualityFailure"
      }
    ],
    "Next": "ExtractDocuments"
  }
}
```

## Adding New Checks

To add a new quality check:

### 1. Create YAML file

```bash
touch soda/checks/silver_new_table.yml
```

### 2. Define checks with clear names

```yaml
checks for silver_new_table:
  # COMPLETENESS
  - row_count > 0:
      name: Table has data
      severity: critical
      description: Explain business impact of empty table
  
  # SCHEMA
  - schema:
      fail when required column missing:
        - primary_key
        - required_field
      name: Table has correct schema
      severity: critical
```

### 3. Set appropriate severity

- **Critical**: Data is unusable (schema errors, missing PKs, invalid FKs)
- **Warning**: Data is degraded (low success rates, freshness issues)
- **Info**: Monitoring only (trend analysis, performance metrics)

### 4. Document business purpose

Every check must have a `description` field explaining:
- What data quality issue this prevents
- Business impact if this check fails
- Typical remediation steps

### 5. Add to configuration.yml

```yaml
tables:
  silver_new_table:
    path: 's3://bucket/silver/new_table/*.parquet'
```

### 6. Test locally

```bash
soda scan -d congress_s3 -c soda/configuration.yml soda/checks/silver_new_table.yml
```

### 7. Update this README

Add entry to "Check Files" section with:
- File name and check count
- Key validations performed
- Business rationale

### 8. Deploy to Lambda

The `run_soda_checks` Lambda automatically picks up new checks from the `soda/checks/` directory when the layer is rebuilt.

## Troubleshooting

### Check Syntax Errors

**Symptom**: Soda scan fails with YAML parse error

**Solution**: Validate YAML syntax
```bash
yamllint soda/checks/silver_filings.yml
```

### DuckDB Connection Errors

**Symptom**: "Unable to connect to S3"

**Solution**: Ensure AWS credentials are configured
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### Missing Table/Column Errors

**Symptom**: "Table 'xyz' not found" or "Column 'abc' does not exist"

**Solution**: 
1. Verify S3 path in `configuration.yml` is correct
2. Ensure Parquet files exist at that path
3. Check column names match Parquet schema (case-sensitive)

### Referential Integrity Failures

**Symptom**: "values in (fk) must exist in dimension (pk)" fails

**Solution**:
1. Check if dimension table was built before fact table
2. Verify foreign key values are not -1 or NULL
3. Ensure dimension table has all expected records

### Freshness Check Failures

**Symptom**: "freshness(timestamp) < 24h" fails

**Solution**:
1. Check if upstream pipeline ran successfully
2. Verify timestamp column exists and has recent values
3. Consider increasing threshold for less-frequent updates

## Check Statistics

**Total Checks**: 115+
- **Bronze Layer**: 12 checks
- **Silver Layer**: 60 checks (9+12+16+13+10)
- **Gold Layer**: 45 checks (11+12+12+10)

**Severity Distribution**:
- **Critical**: ~75 checks (65%)
- **Warning**: ~35 checks (30%)
- **Info**: ~5 checks (5%)

**Category Distribution**:
- **Schema Validation**: ~20 checks
- **Completeness**: ~25 checks
- **Referential Integrity**: ~15 checks
- **Business Logic**: ~30 checks
- **Freshness**: ~10 checks
- **Anomaly Detection**: ~5 checks

## Monitoring & Alerts

### CloudWatch Metrics

The `run_soda_checks` Lambda publishes custom metrics:
- `SodaChecksRun`: Total checks executed
- `SodaChecksFailed`: Critical failures
- `SodaChecksWarning`: Warning-level issues

### SNS Alerts

Critical failures trigger SNS topic: `congress-disclosures-quality-alerts`

**Subscribers**:
- Email: data-quality@example.com
- Slack: #data-quality-alerts

### Dashboard

CloudWatch dashboard: `Congress-Disclosures-Quality`

**Widgets**:
- Check success rate by layer (Bronze/Silver/Gold)
- Freshness violations over time
- Schema drift detection
- Referential integrity failure trends

## Release Notes

### v1.0.0 (January 2026)
- Initial implementation with 115+ checks
- Bronze, Silver, Gold layer coverage
- Integration with Step Functions quality gates
- CloudWatch alerting configured

## References

- **Soda Core Docs**: https://docs.soda.io/soda-core/overview.html
- **DuckDB S3 Integration**: https://duckdb.org/docs/guides/import/s3_import.html
- **Step Functions Quality Gates**: `/docs/STATE_MACHINE_FLOW.md`
- **Pipeline Architecture**: `/docs/ARCHITECTURE.md`

## Support

For questions or issues:
1. Check this README and troubleshooting section
2. Review CloudWatch logs for detailed error messages
3. Open GitHub issue with tag `data-quality`
4. Contact data engineering team in #data-quality Slack channel
