# Gold Layer Refactor - Comprehensive Architecture Plan

## Executive Summary

This document outlines a complete refactor of the Gold Analytics layer to address critical data accuracy, navigation, infrastructure, and testing issues identified in the current implementation.

## Current Issues Identified

### 1. **Data Accuracy Issues**
- **980 "members"** showing in document quality - these are arbitrary `member_key` IDs (1, 2, 3...), NOT actual Congress members
- **Member source of truth**: Should be Congress API with bioguide IDs, not sequential integers
- **Member matching**: Need to link disclosures to actual Congress members via Congress API
- **All members showing identical stats**: Sample data is being used instead of real aggregated data from silver layer

### 2. **Owner Clarification Issues**
- **PTR Transactions "Owner" dropdown** shows: SP (Spouse), DC (Dependent Child), JT (Joint)
- **Problem**: UI doesn't clearly indicate that the FILER is the Congress member, but the OWNER of the asset may be a relative
- **Field mapping**: `owner_code` in silver = SP/DC/JT, but `filer_full_name` = actual Congress member

### 3. **Navigation Issues**
- **Gold Analytics sidebar buttons don't work** - navigation between views is broken
- **Buttons "look weird"** - styling issues with navigation components

### 4. **Data Quality Issues**
- **Duplicate transaction types in silver**: Need to investigate and clean up
- **PDF links**: Should point to our S3-hosted PDFs, not external House Clerk URLs

### 5. **Infrastructure Issues**
- **No Infrastructure as Code (IaC)**: Entire pipeline should be Terraform-managed
- **Manual deployments**: S3 buckets, Lambda functions, SQS queues all created manually

### 6. **Testing Issues**
- **No test coverage**: Need test-based development with pytest
- **No validation**: Data pipeline outputs are not validated

### 7. **Naming Convention Issues**
- **Inconsistent naming**: Tables, columns, and data structures need standardized naming
- **No schema documentation**: Need clear schema definitions

### 8. **Analytics Gap**
- **No trend analysis**: Need time-series trends (what patterns are emerging over time?)

---

## Architecture Refactor Plan

### Phase 1: Fix Immediate Blocking Issues (Priority: Critical)

#### 1.1 Fix Navigation Buttons
**Problem**: Sidebar navigation doesn't work in Gold Analytics tab
**Root Cause**: CSS `.gold-view` class missing `display: none` for non-active views
**Solution**:
```css
.gold-view {
    display: none;
}
.gold-view.active {
    display: block;
}
```
**Files**: `website/style.css`, `website/gold_analytics.js`
**Test**: Click each sidebar button, verify view switches
**Timeline**: 1 hour

#### 1.2 Fix Member Counting - Integrate Congress API
**Problem**: 980 "members" are just sequential IDs, not real members
**Root Cause**: Using arbitrary `member_key` instead of Congress API bioguide IDs
**Solution**:
1. Build `dim_members` table from Congress API (bioguide ID as primary key)
2. Create mapping: `first_name + last_name + state_district` → `bioguide_id`
3. Update silver layer to include `bioguide_id` on all transactions
4. Rebuild gold aggregates to use `bioguide_id` instead of `member_key`

**Data Flow**:
```
Congress API → dim_members (bioguide_id, full_name, party, state, district, ...)
                     ↓
Silver Transactions (bioguide_id FK)
                     ↓
Gold Aggregates (bioguide_id FK)
```

**Files**:
- `scripts/build_dim_members.py` - needs Congress API key set
- `scripts/build_silver_ptr_transactions.py` - add bioguide_id enrichment
- `scripts/compute_agg_document_quality.py` - group by bioguide_id
- `scripts/compute_agg_member_trading_stats.py` - use real data with bioguide_id

**Timeline**: 4 hours

#### 1.3 Add Owner Clarification in PTR Transactions Tab
**Problem**: Dropdown shows "Owner" but doesn't clarify that Filer = Congress Member
**Solution**:
- Update PTR Transactions tab header to add clarification:
```html
<div class="alert alert-info">
    <strong>Owner Types:</strong>
    • <strong>Filer</strong> = The Congress member who filed the disclosure
    • <strong>SP (Spouse)</strong> = Member's spouse
    • <strong>DC (Dependent Child)</strong> = Member's dependent child
    • <strong>JT (Joint)</strong> = Joint ownership with member
</div>
```
- Rename dropdown from "All Owners" to "Asset Owner Type"
- Add column clarification: "Filer" column shows the Congress member, "Owner" shows who owns the asset

**Files**: `website/index.html`, `website/ptr_transactions.js`
**Timeline**: 2 hours

---

### Phase 2: Data Pipeline Cleanup (Priority: High)

#### 2.1 Clean Duplicate Transaction Types in Silver
**Investigation Needed**:
```sql
SELECT transaction_type, COUNT(*) as cnt
FROM silver.ptr_transactions
GROUP BY transaction_type
ORDER BY cnt DESC
```

Expected types: Purchase, Sale, Partial Sale, Exchange
**Action**: Investigate if there are variations (e.g., "Sale (Partial)", "P" vs "Purchase")
**Solution**: Normalize transaction types in silver layer ingestion
**Files**: `ingestion/lib/extraction/*.py`
**Timeline**: 3 hours

#### 2.2 Fix PDF Links to Point to S3
**Problem**: Silver layer has `pdf_url` pointing to House Clerk external URLs
**Solution**:
- Add `pdf_s3_key` column to silver tables
- Update manifest generator to use S3 URLs:
```python
pdf_url = f"https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/bronze/house/financial/ptr-pdfs/{year}/{doc_id}.pdf"
```
**Files**:
- `scripts/build_silver_*.py` - add pdf_s3_key column
- `scripts/generate_ptr_manifest.py` - use S3 URLs
**Timeline**: 2 hours

#### 2.3 Establish Naming Conventions
**Standard**: Use lowercase with underscores, prefix by layer
**Examples**:
- **Bronze**: `bronze_house_ptr_documents`, `bronze_house_ptr_pdfs`
- **Silver**: `silver_ptr_filings`, `silver_ptr_transactions`, `silver_dim_members`, `silver_dim_assets`
- **Gold**: `gold_agg_document_quality`, `gold_agg_member_trading_stats`, `gold_agg_trending_stocks`

**Schema Documentation**:
- Create `docs/SCHEMA.md` with all tables, columns, types, descriptions
- Add inline schema validation in scripts

**Timeline**: 4 hours

---

### Phase 3: Replace Sample Data with Real Data (Priority: High)

#### 3.1 Rebuild Gold Aggregates with Real Silver Data
**Current Problem**: Using fake sample data instead of real silver aggregations
**Solution**:
1. **gold_agg_member_trading_stats**: Read from `silver_ptr_transactions`, group by bioguide_id
2. **gold_agg_trending_stocks**: Read from `silver_ptr_transactions`, group by asset ticker, rank by trade_count
3. **gold_agg_sector_analysis**: Read from `silver_ptr_transactions` joined with asset sector mapping
4. **gold_agg_document_quality**: Already using real data but needs bioguide_id fix

**Data Sources**:
```python
# Member Trading Stats
silver_ptr_transactions
    .groupby('bioguide_id')
    .agg({
        'transaction_id': 'count',  # total_trades
        'amount_midpoint': ['sum', 'mean'],  # total_volume, avg_size
        ...
    })

# Trending Stocks
silver_ptr_transactions
    .groupby('ticker')
    .agg({
        'transaction_id': 'count',  # trade_count
        ...
    })
    .sort_values('trade_count', ascending=False)
    .head(50)
```

**Timeline**: 6 hours

---

### Phase 4: Infrastructure as Code (Priority: Medium)

#### 4.1 Convert to Terraform
**Scope**: All AWS resources managed via Terraform
- S3 buckets (bronze, silver, gold, website)
- Lambda functions (extraction, processing)
- SQS queues (ptr-docs-queue, dlq)
- IAM roles and policies
- CloudWatch log groups
- EventBridge rules (daily triggers)

**Structure**:
```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── modules/
│   ├── s3/
│   ├── lambda/
│   ├── sqs/
│   ├── iam/
│   └── eventbridge/
└── environments/
    ├── dev/
    └── prod/
```

**Benefits**:
- Version-controlled infrastructure
- Reproducible deployments
- Easy disaster recovery
- Multi-environment support (dev/prod)

**Timeline**: 16 hours

---

### Phase 5: Add Trend Analytics (Priority: Medium)

#### 5.1 Time-Series Trend Analysis
**New Aggregates**:
1. **gold_agg_trading_trends_monthly**: Trading volume by month
2. **gold_agg_sector_trends_monthly**: Sector activity over time
3. **gold_agg_document_quality_trends**: Quality scores over time

**Visualizations**:
- Line charts showing trading volume trends
- Sector allocation changes over time
- Document quality score trends

**Files**:
- `scripts/compute_agg_trading_trends.py`
- `website/gold_analytics_trends.js` (new)
- `website/index.html` - add "Trends" tab to sidebar

**Timeline**: 8 hours

---

### Phase 6: Test-Based Development (Priority: High)

#### 6.1 Add Pytest Test Suite
**Test Coverage**:
1. **Unit Tests**:
   - Extraction logic (`ingestion/lib/extraction/`)
   - Transformation logic (`scripts/build_silver_*.py`)
   - Aggregation logic (`scripts/compute_agg_*.py`)

2. **Integration Tests**:
   - End-to-end pipeline test with sample data
   - S3 read/write operations
   - Congress API integration

3. **Data Quality Tests**:
   - Schema validation (column types, required fields)
   - Referential integrity (FKs exist)
   - Data completeness checks

**Structure**:
```
tests/
├── unit/
│   ├── test_extraction.py
│   ├── test_silver_transforms.py
│   └── test_gold_aggregates.py
├── integration/
│   ├── test_pipeline_e2e.py
│   └── test_congress_api.py
└── fixtures/
    ├── sample_pdfs/
    └── sample_data/
```

**CI/CD Integration**:
- Run tests on every PR
- Block merges if tests fail
- Add test coverage reporting

**Timeline**: 12 hours

---

## Implementation Timeline

| Phase | Description | Hours | Priority |
|-------|-------------|-------|----------|
| 1.1 | Fix navigation buttons | 1 | Critical |
| 1.2 | Fix member counting (Congress API) | 4 | Critical |
| 1.3 | Add owner clarification | 2 | Critical |
| **Phase 1 Total** | **Immediate fixes** | **7** | **Critical** |
| 2.1 | Clean duplicate transaction types | 3 | High |
| 2.2 | Fix PDF links to S3 | 2 | High |
| 2.3 | Establish naming conventions | 4 | High |
| **Phase 2 Total** | **Data pipeline cleanup** | **9** | **High** |
| 3.1 | Rebuild gold with real data | 6 | High |
| **Phase 3 Total** | **Real data implementation** | **6** | **High** |
| 4.1 | Convert to Terraform | 16 | Medium |
| **Phase 4 Total** | **Infrastructure as Code** | **16** | **Medium** |
| 5.1 | Add trend analytics | 8 | Medium |
| **Phase 5 Total** | **Trend analysis** | **8** | **Medium** |
| 6.1 | Add pytest test suite | 12 | High |
| **Phase 6 Total** | **Test coverage** | **12** | **High** |
| **GRAND TOTAL** | | **58 hours** | |

---

## Success Criteria

### Phase 1 (Critical)
- [ ] Navigation buttons work - can switch between all 4 views
- [ ] Member count shows actual Congress members (38 members for 2025 data)
- [ ] Document quality shows real member names from Congress API
- [ ] PTR Transactions tab clearly explains Owner vs Filer

### Phase 2 (High)
- [ ] No duplicate transaction types in silver
- [ ] All PDF links point to S3-hosted files
- [ ] Schema documentation exists and is accurate
- [ ] Naming conventions documented and enforced

### Phase 3 (High)
- [ ] Member Trading Stats uses real silver transaction data
- [ ] Trending Stocks shows actual top traded stocks from silver
- [ ] Sector Analysis uses real asset sector data
- [ ] No sample/fake data anywhere in gold layer

### Phase 4 (Medium)
- [ ] All AWS resources defined in Terraform
- [ ] Can deploy entire stack with `terraform apply`
- [ ] Dev and prod environments isolated

### Phase 5 (Medium)
- [ ] Trend analytics tab shows time-series data
- [ ] Trading volume trends chart working
- [ ] Sector allocation trends chart working

### Phase 6 (High)
- [ ] Test coverage > 80%
- [ ] All tests passing in CI/CD
- [ ] Data quality tests validate schema

---

## Next Steps

1. **Review this plan with stakeholders** - Get alignment on priorities
2. **Start with Phase 1** - Fix critical navigation and member counting issues
3. **Iterate through phases** - Complete one phase before moving to next
4. **Document as we go** - Update docs with each change
5. **Test everything** - Don't merge without tests

---

## Questions to Resolve

1. **Congress API rate limits**: Do we need caching strategy?
2. **Member matching logic**: How to handle name variations (Jr., III, etc.)?
3. **Terraform state**: Where to store state file (S3 backend)?
4. **Testing data**: What sample PDFs to use for test fixtures?
5. **Trend window**: How far back should trend analytics go?

---

**Document Version**: 1.0
**Created**: 2025-11-25
**Author**: Claude Code
**Status**: Draft - Pending Review
