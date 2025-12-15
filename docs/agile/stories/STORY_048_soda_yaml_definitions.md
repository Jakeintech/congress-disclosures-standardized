# STORY-048: Create Soda Quality Check YAML Definitions

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 5 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** data quality engineer
**I want** comprehensive quality check definitions for all pipeline layers
**So that** data quality issues are automatically detected before reaching production

## Acceptance Criteria
- **GIVEN** Bronze, Silver, and Gold data layers
- **WHEN** Soda checks execute
- **THEN** 15+ quality checks defined across all layers
- **AND** Checks cover: completeness, freshness, schema, referential integrity
- **AND** Critical checks fail pipeline execution
- **AND** Warning checks log but don't fail
- **AND** All checks documented with business rationale

## Technical Tasks
- [ ] Create `soda/checks/` directory structure
- [ ] Define Bronze layer checks (5 checks)
- [ ] Define Silver layer checks (6 checks)
- [ ] Define Gold layer checks (6 checks)
- [ ] Configure check severity levels (critical/warning)
- [ ] Document each check's business purpose
- [ ] Test checks locally with sample data
- [ ] Integrate with STORY-033 (run_soda_checks Lambda)

## Directory Structure
```
soda/checks/
├── bronze_house_fd.yml
├── silver_filings.yml
├── silver_documents.yml
├── silver_text.yml
├── gold_dim_members.yml
├── gold_fact_transactions.yml
├── gold_aggregates.yml
└── README.md
```

## Implementation

### 1. Bronze Layer Checks (bronze_house_fd.yml)
```yaml
# soda/checks/bronze_house_fd.yml
# Purpose: Ensure Bronze layer has complete, immutable source data

table_name: bronze_house_fd_pdfs
dataset: s3://congress-disclosures-standardized/bronze/house/financial/

checks for bronze_house_fd_pdfs:
  # Completeness Check
  - row_count > 0:
      name: Bronze has PDFs
      severity: critical
      description: Bronze layer must contain at least one PDF per year

  # Freshness Check
  - max(upload_timestamp) > now() - interval '48 hours':
      name: Bronze data is fresh
      severity: warning
      description: Bronze data should be updated within last 48 hours

  # SHA256 Integrity Check
  - missing_count(sha256) == 0:
      name: All PDFs have SHA256 checksums
      severity: critical
      description: Every PDF must have SHA256 for integrity validation

  # No Duplicates Check
  - duplicate_count(doc_id) == 0:
      name: No duplicate documents in Bronze
      severity: critical
      description: Each doc_id should appear only once per year

  # File Size Validation
  - min(file_size_bytes) > 1000:
      name: PDFs are not empty
      severity: critical
      description: All PDFs must be at least 1KB (not corrupted/empty)
```

### 2. Silver Layer Checks (silver_filings.yml)
```yaml
# soda/checks/silver_filings.yml
# Purpose: Ensure Silver layer has valid, normalized data

table_name: silver_filings
dataset: s3://congress-disclosures-standardized/silver/house/financial/filings/

checks for silver_filings:
  # Schema Validation
  - schema:
      name: Filings table has correct schema
      severity: critical
      fail: when required column missing or type mismatch
      columns:
        - name: doc_id
          type: string
          required: true
        - name: filing_type
          type: string
          required: true
        - name: filing_date
          type: date
          required: true

  # Data Quality - No Nulls
  - missing_count(doc_id) == 0:
      name: No missing doc_id
      severity: critical

  # Data Quality - Valid Filing Types
  - invalid_count(filing_type, valid_values: ['P', 'A', 'T', 'X', 'D', 'W']) == 0:
      name: All filing types are valid
      severity: critical

  # Data Quality - Date Range
  - invalid_percent(filing_date) < 1%:
      name: Filing dates are within valid range
      severity: warning
      valid when filing_date between '2020-01-01' and now() + interval '30 days'

  # Referential Integrity - Bronze to Silver
  - row_count == (select count(*) from bronze_house_fd_pdfs):
      name: Silver has all Bronze records
      severity: critical
      description: Every Bronze PDF should have a Silver filing record

  # Transformation Success Rate
  - fraction_where(extraction_status = 'success') > 0.95:
      name: 95%+ extraction success rate
      severity: warning
      description: At least 95% of PDFs should extract successfully
```

### 3. Silver Text Extraction Checks (silver_text.yml)
```yaml
# soda/checks/silver_text.yml
# Purpose: Ensure text extraction quality

table_name: silver_text_extractions
dataset: s3://congress-disclosures-standardized/silver/house/financial/text/

checks for silver_text_extractions:
  # Completeness
  - row_count > 0:
      name: Text extractions exist
      severity: critical

  # Extraction Method Distribution
  - value_distribution(extraction_method):
      name: Extraction method breakdown
      severity: info
      expected:
        direct_text: > 70%
        ocr: < 30%
      description: Most PDFs should extract via direct_text (not OCR)

  # Confidence Scores
  - avg(confidence_score) > 0.80:
      name: Average confidence above 80%
      severity: warning
      description: Text extraction confidence should be high

  # Text Length Validation
  - invalid_count(text_length, valid_when: text_length > 100) == 0:
      name: All extractions have meaningful text
      severity: warning
      description: Extracted text should be at least 100 characters
```

### 4. Gold Dimension Checks (gold_dim_members.yml)
```yaml
# soda/checks/gold_dim_members.yml
# Purpose: Ensure dimension tables are complete and consistent

table_name: gold_dim_members
dataset: s3://congress-disclosures-standardized/gold/house/financial/dimensions/members/

checks for gold_dim_members:
  # Primary Key Uniqueness
  - duplicate_count(member_key) == 0:
      name: Member keys are unique
      severity: critical
      description: Each member should have a unique surrogate key

  # SCD Type 2 Validation
  - invalid_count(effective_date) == 0:
      name: All members have effective dates
      severity: critical
      description: SCD Type 2 requires effective_date for all records

  # Current Flag Validation
  - duplicate_count(bioguide_id) where is_current = true == 0:
      name: Only one current record per member
      severity: critical
      description: Each bioguide_id should have only one is_current=true record

  # Referential Integrity
  - missing_count(bioguide_id) == 0:
      name: All members have bioguide_id
      severity: critical
      description: bioguide_id is required for lookups

  # Data Quality
  - invalid_count(party, valid_values: ['D', 'R', 'I']) < 1%:
      name: Party codes are valid
      severity: warning
```

### 5. Gold Fact Checks (gold_fact_transactions.yml)
```yaml
# soda/checks/gold_fact_transactions.yml
# Purpose: Ensure fact tables have referential integrity

table_name: gold_fact_transactions
dataset: s3://congress-disclosures-standardized/gold/house/financial/facts/transactions/

checks for gold_fact_transactions:
  # Foreign Key - Member Dimension
  - referential_integrity(member_key):
      name: All transactions have valid members
      severity: critical
      references: gold_dim_members.member_key
      description: Every transaction must reference a valid member

  # Foreign Key - Asset Dimension
  - referential_integrity(asset_key):
      name: All transactions have valid assets
      severity: critical
      references: gold_dim_assets.asset_key

  # Foreign Key - Date Dimension
  - referential_integrity(transaction_date_key):
      name: All transactions have valid dates
      severity: critical
      references: gold_dim_dates.date_key

  # Business Logic - Amount Ranges
  - invalid_count(amount_low, valid_when: amount_low >= 0) == 0:
      name: Amount low is non-negative
      severity: critical

  - invalid_count(amount_high, valid_when: amount_high >= amount_low) == 0:
      name: Amount high >= amount low
      severity: critical

  # Transaction Type Validation
  - invalid_count(transaction_type, valid_values: ['Purchase', 'Sale', 'Exchange']) == 0:
      name: Transaction types are valid
      severity: critical
```

### 6. Gold Aggregate Checks (gold_aggregates.yml)
```yaml
# soda/checks/gold_aggregates.yml
# Purpose: Ensure aggregate calculations are correct

table_name: gold_agg_trending_stocks
dataset: s3://congress-disclosures-standardized/gold/house/financial/aggregates/trending_stocks/

checks for gold_agg_trending_stocks:
  # Calculation Validation
  - row_count > 0:
      name: Trending stocks calculated
      severity: critical

  # Ranking Validation
  - duplicate_count(rank) == 0:
      name: Stock ranks are unique
      severity: critical
      description: Each stock should have a unique rank

  # Activity Count Validation
  - invalid_count(purchase_count, valid_when: purchase_count >= 0) == 0:
      name: Purchase counts are non-negative
      severity: critical

  - invalid_count(sale_count, valid_when: sale_count >= 0) == 0:
      name: Sale counts are non-negative
      severity: critical

  # Freshness
  - max(calculation_date) > now() - interval '48 hours':
      name: Trending stocks are fresh
      severity: warning
      description: Aggregates should be recalculated within last 48 hours
```

### 7. Soda Configuration (soda.yml)
```yaml
# soda/soda.yml
# Soda Cloud configuration (optional, for monitoring UI)

data_source s3_data_lake:
  type: spark
  connection:
    type: s3
    bucket: congress-disclosures-standardized
    region: us-east-1

severity_levels:
  critical:
    action: fail_pipeline
    notify: email
  warning:
    action: log_only
    notify: slack
  info:
    action: log_only
```

## Testing Strategy

### Local Testing (Dev Environment)
```bash
# Install Soda Core
pip install soda-core-spark

# Run checks against dev data
soda scan -d s3_data_lake -c soda/soda.yml soda/checks/silver_filings.yml

# Expected output:
# ✓ All checks passed (12/12)
# ✗ 2 critical failures, 1 warning
```

### Integration with run_soda_checks Lambda (STORY-033)
```python
# Lambda will invoke:
from soda.scan import Scan

scan = Scan()
scan.add_configuration_yaml_file('soda/soda.yml')
scan.add_sodacl_yaml_file('soda/checks/silver_filings.yml')
scan.execute()

if scan.has_check_fails():
    raise Exception(f"Quality checks failed: {scan.get_checks_fail_text()}")
```

## Documentation (README.md)
```markdown
# Soda Quality Checks

## Overview
This directory contains Soda quality check definitions for the Congress Disclosures data pipeline.

## Check Severity Levels
- **Critical**: Fails pipeline execution, requires immediate attention
- **Warning**: Logs issue but pipeline continues, investigate during next sprint
- **Info**: Monitoring only, no action required

## Check Categories
1. **Completeness**: Row counts, missing values
2. **Freshness**: Data recency (< 48 hours)
3. **Schema**: Column types, required fields
4. **Referential Integrity**: Foreign key relationships
5. **Business Logic**: Amount ranges, valid values

## Running Checks Locally
```bash
soda scan -d s3_data_lake -c soda/soda.yml soda/checks/*.yml
```

## Adding New Checks
1. Create YAML file in `soda/checks/`
2. Define checks with clear names and descriptions
3. Set appropriate severity level
4. Test locally before deploying
5. Update this README with check description
```

## Estimated Effort: 5 hours
- 2 hours: Create 7 YAML files (15+ checks)
- 1 hour: Document each check's purpose
- 1 hour: Local testing with sample data
- 1 hour: Integration with STORY-033 Lambda

## AI Development Notes
**Baseline**: Research Soda Core documentation + examples
**Pattern**: YAML-based declarative quality checks
**Files to Create**:
- soda/checks/bronze_house_fd.yml (5 checks)
- soda/checks/silver_filings.yml (6 checks)
- soda/checks/silver_text.yml (4 checks)
- soda/checks/gold_dim_members.yml (5 checks)
- soda/checks/gold_fact_transactions.yml (6 checks)
- soda/checks/gold_aggregates.yml (5 checks)
- soda/soda.yml (configuration)
- soda/checks/README.md (documentation)

**Token Budget**: 3,500 tokens (7 YAML files + README)

**Dependencies**:
- STORY-033 (run_soda_checks Lambda) must be ready to consume these files
- Sample data in dev environment for local testing

**Acceptance Criteria Verification**:
1. ✅ 15+ checks defined across Bronze/Silver/Gold
2. ✅ Critical checks fail pipeline when violated
3. ✅ Warning checks log but don't fail
4. ✅ All checks have clear business rationale
5. ✅ Local testing passes with sample data

**Target**: Sprint 3, Day 3 (January 1, 2026)
