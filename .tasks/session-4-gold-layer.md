# Session 4: Comprehensive Gold Layer

**Duration**: Week 4 (7 days)
**Goal**: Build complete Gold layer with 6 fact tables, 7 aggregate tables, and master rebuild scripts to enable advanced analytics

---

## Prerequisites

- [x] Session 3 complete (all filing types extractable)
- [ ] Silver layer populated with structured data from all schedules
- [ ] Existing Gold dimensions verified: dim_date, dim_filing_types, dim_members, dim_assets
- [ ] PyArrow, Pandas, DuckDB installed for data processing

---

## Task Checklist

### 1. Fact Table: PTR Transactions (Tasks 1-4)

- [ ] **Task 1.1**: Design fact_ptr_transactions schema
  - **Action**: Create `/ingestion/schemas/gold/fact_ptr_transactions.json`
  - **Fields**: transaction_key (PK), doc_id, year, member_key (FK), asset_key (FK), transaction_date_key (FK), notification_date_key (FK), filing_date_key (FK), transaction_type, owner_code, amount_range, amount_low, amount_high, amount_column, ticker, confidence_score
  - **Deliverable**: JSON schema (80 lines)
  - **Time**: 1 hour

- [ ] **Task 1.2**: Build PTR transactions fact builder
  - **Action**: Write `/scripts/build_fact_ptr_transactions.py`
  - **Logic**: Read Silver structured JSONs (Schedule B) → join dim_members, dim_assets, dim_date → write Parquet
  - **Partitioning**: By year
  - **Deliverable**: Script with incremental mode (250 lines)
  - **Time**: 4 hours

- [ ] **Task 1.3**: Add data quality checks
  - **Action**: Add validation to script
  - **Checks**: No null member_key, valid transaction dates, amount_low ≤ amount_high
  - **Deliverable**: Quality checks in builder
  - **Time**: 1 hour

- [ ] **Task 1.4**: Test on 2025 PTR data
  - **Action**: Run script on 2025 Silver data
  - **Verify**: 3,338+ transactions loaded, all foreign keys valid
  - **Deliverable**: Parquet file in `gold/house/financial/facts/fact_ptr_transactions/year=2025/`
  - **Time**: 1 hour

### 2. Fact Table: Asset Holdings (Tasks 5-8)

- [ ] **Task 2.1**: Design fact_asset_holdings schema
  - **Action**: Create `/ingestion/schemas/gold/fact_asset_holdings.json`
  - **Fields**: holding_key (PK), doc_id, year, member_key (FK), asset_key (FK), filing_date_key (FK), asset_description, asset_category, location_city, location_state, value_code, value_low, value_high, income_type, income_amount_code, income_low, income_high, confidence_score
  - **Deliverable**: JSON schema (100 lines)
  - **Time**: 1 hour

- [ ] **Task 2.2**: Build asset holdings fact builder
  - **Action**: Write `/scripts/build_fact_asset_holdings.py`
  - **Logic**: Read Silver Schedule A JSONs → join dims → deduplicate → write Parquet
  - **Partitioning**: By year
  - **Deliverable**: Script with incremental mode (280 lines)
  - **Time**: 4 hours

- [ ] **Task 2.3**: Add asset categorization logic
  - **Action**: Enhance script with category detection
  - **Categories**: Stock, Bond, Real Estate, Mutual Fund, Partnership, Trust, Retirement Account, Other
  - **Logic**: Keyword matching on asset_description
  - **Deliverable**: Categorization function
  - **Time**: 1.5 hours

- [ ] **Task 2.4**: Test on 2025 Form A data
  - **Action**: Run script on 2025 Silver data
  - **Verify**: All Schedule A assets loaded, categories assigned
  - **Deliverable**: Parquet file in `gold/.../fact_asset_holdings/year=2025/`
  - **Time**: 1 hour

### 3. Fact Table: Liabilities (Tasks 9-11)

- [ ] **Task 3.1**: Design fact_liabilities schema
  - **Action**: Create `/ingestion/schemas/gold/fact_liabilities.json`
  - **Fields**: liability_key (PK), doc_id, year, member_key (FK), filing_date_key (FK), creditor_name, description, month_incurred, year_incurred, value_code, value_low, value_high, interest_rate, confidence_score
  - **Deliverable**: JSON schema (70 lines)
  - **Time**: 45 min

- [ ] **Task 3.2**: Build liabilities fact builder
  - **Action**: Write `/scripts/build_fact_liabilities.py`
  - **Logic**: Read Silver Schedule D JSONs → join dims → parse dates → write Parquet
  - **Partitioning**: By year
  - **Deliverable**: Script with incremental mode (220 lines)
  - **Time**: 3 hours

- [ ] **Task 3.3**: Test on 2025 Form A data
  - **Action**: Run script on 2025 Silver data
  - **Verify**: All Schedule D liabilities loaded
  - **Deliverable**: Parquet file in `gold/.../fact_liabilities/year=2025/`
  - **Time**: 45 min

### 4. Fact Table: Outside Positions (Tasks 12-14)

- [ ] **Task 4.1**: Design fact_positions schema
  - **Action**: Create `/ingestion/schemas/gold/fact_positions.json`
  - **Fields**: position_key (PK), doc_id, year, member_key (FK), filing_date_key (FK), organization_name, organization_city, organization_state, position_title, date_appointed, confidence_score
  - **Deliverable**: JSON schema (65 lines)
  - **Time**: 45 min

- [ ] **Task 4.2**: Build positions fact builder
  - **Action**: Write `/scripts/build_fact_positions.py`
  - **Logic**: Read Silver Schedule E JSONs → join dims → parse dates → write Parquet
  - **Partitioning**: By year
  - **Deliverable**: Script with incremental mode (200 lines)
  - **Time**: 3 hours

- [ ] **Task 4.3**: Test on 2025 Form A data
  - **Action**: Run script on 2025 Silver data
  - **Verify**: All Schedule E positions loaded
  - **Deliverable**: Parquet file in `gold/.../fact_positions/year=2025/`
  - **Time**: 45 min

### 5. Fact Table: Gifts & Travel (Tasks 15-17)

- [ ] **Task 5.1**: Design fact_gifts_travel schema
  - **Action**: Create `/ingestion/schemas/gold/fact_gifts_travel.json`
  - **Fields**: gift_travel_key (PK), doc_id, year, member_key (FK), filing_date_key (FK), type (gift/travel), source_name, description, date_received, departure_date, return_date, destination, estimated_value, reimbursement_amount, confidence_score
  - **Deliverable**: JSON schema (90 lines)
  - **Time**: 1 hour

- [ ] **Task 5.2**: Build gifts & travel fact builder
  - **Action**: Write `/scripts/build_fact_gifts_travel.py`
  - **Logic**: Read Silver Schedule G & H JSONs → combine → join dims → write Parquet
  - **Partitioning**: By year
  - **Deliverable**: Script with incremental mode (260 lines)
  - **Time**: 3.5 hours

- [ ] **Task 5.3**: Test on 2025 data
  - **Action**: Run script on 2025 Silver data
  - **Verify**: All Schedule G & H records loaded
  - **Deliverable**: Parquet file in `gold/.../fact_gifts_travel/year=2025/`
  - **Time**: 45 min

### 6. Update Existing Fact: Filings (Task 18)

- [ ] **Task 6.1**: Enhance fact_filings builder
  - **Action**: Edit `/scripts/build_fact_filings.py`
  - **Add**: Schedule count per filing, total transaction count, total asset count
  - **Enrich**: Join all extracted schedules to count data points
  - **Deliverable**: Enhanced fact_filings
  - **Time**: 2 hours

### 7. Aggregate: Member Trading Stats (Tasks 19-21)

- [ ] **Task 7.1**: Design agg_member_trading_stats schema
  - **Action**: Create `/ingestion/schemas/gold/agg_member_trading_stats.json`
  - **Fields**: member_key (PK), member_name, state_district, total_trades, total_purchases, total_sales, unique_stocks, unique_sectors, total_volume_low, total_volume_high, avg_trade_size_low, avg_trade_size_high, first_trade_date, last_trade_date, most_traded_stock, most_traded_sector, confidence_avg
  - **Deliverable**: JSON schema (120 lines)
  - **Time**: 1 hour

- [ ] **Task 7.2**: Build member trading stats aggregator
  - **Action**: Write `/scripts/build_agg_member_trading_stats.py`
  - **Logic**: Aggregate fact_ptr_transactions by member → calculate stats → join dim_members
  - **Deliverable**: Script (320 lines)
  - **Time**: 4 hours

- [ ] **Task 7.3**: Test and verify
  - **Action**: Run script, verify top traders match expectations
  - **Deliverable**: Parquet file in `gold/.../aggregates/agg_member_trading_stats/`
  - **Time**: 1 hour

### 8. Aggregate: Stock Activity (Tasks 22-24)

- [ ] **Task 8.1**: Design agg_stock_activity schema
  - **Action**: Create `/ingestion/schemas/gold/agg_stock_activity.json`
  - **Fields**: asset_key (PK), ticker, asset_name, total_trades, total_purchases, total_sales, unique_members, total_volume_low, total_volume_high, first_trade_date, last_trade_date, purchase_sale_ratio, top_trader_member_key, confidence_avg
  - **Deliverable**: JSON schema (100 lines)
  - **Time**: 1 hour

- [ ] **Task 8.2**: Build stock activity aggregator
  - **Action**: Write `/scripts/build_agg_stock_activity.py`
  - **Logic**: Aggregate fact_ptr_transactions by asset → calculate stats → rank by volume
  - **Deliverable**: Script (280 lines)
  - **Time**: 3.5 hours

- [ ] **Task 8.3**: Test and verify
  - **Action**: Run script, identify most traded stocks
  - **Deliverable**: Parquet file in `gold/.../aggregates/agg_stock_activity/`
  - **Time**: 1 hour

### 9. Aggregate: Sector Activity (Tasks 25-27)

- [ ] **Task 9.1**: Design agg_sector_activity schema
  - **Action**: Create `/ingestion/schemas/gold/agg_sector_activity.json`
  - **Fields**: sector (PK), year_month, total_trades, total_purchases, total_sales, unique_stocks, unique_members, total_volume_low, total_volume_high
  - **Deliverable**: JSON schema (70 lines)
  - **Time**: 45 min

- [ ] **Task 9.2**: Build sector activity aggregator
  - **Action**: Write `/scripts/build_agg_sector_activity.py`
  - **Logic**: Aggregate fact_ptr_transactions by sector & month → calculate trends
  - **Require**: Sector mapping in dim_assets (enhance dim_assets builder if needed)
  - **Deliverable**: Script (260 lines)
  - **Time**: 3.5 hours

- [ ] **Task 9.3**: Test and verify
  - **Action**: Run script, analyze sector trends over time
  - **Deliverable**: Parquet file in `gold/.../aggregates/agg_sector_activity/`
  - **Time**: 1 hour

### 10. Aggregate: Compliance Metrics (Tasks 28-30)

- [ ] **Task 10.1**: Design agg_compliance_metrics schema
  - **Action**: Create `/ingestion/schemas/gold/agg_compliance_metrics.json`
  - **Fields**: member_key (PK), member_name, state_district, total_filings, total_ptr_filings, total_annual_filings, late_filings_count, amendment_count, avg_days_to_report, max_days_to_report, disclosure_completeness_pct, last_filing_date
  - **Deliverable**: JSON schema (90 lines)
  - **Time**: 1 hour

- [ ] **Task 10.2**: Build compliance metrics aggregator
  - **Action**: Write `/scripts/build_agg_compliance_metrics.py`
  - **Logic**: Calculate days between transaction_date and notification_date → flag late (>45 days) → count amendments
  - **Deliverable**: Script (300 lines)
  - **Time**: 4 hours

- [ ] **Task 10.3**: Test and verify
  - **Action**: Run script, identify members with compliance issues
  - **Deliverable**: Parquet file in `gold/.../aggregates/agg_compliance_metrics/`
  - **Time**: 1 hour

### 11. Aggregate: Portfolio Snapshots (Tasks 31-33)

- [ ] **Task 11.1**: Design agg_portfolio_snapshots schema
  - **Action**: Create `/ingestion/schemas/gold/agg_portfolio_snapshots.json`
  - **Fields**: snapshot_key (PK), member_key (FK), year, total_assets, total_asset_value_low, total_asset_value_high, total_liabilities_value_low, total_liabilities_value_high, net_worth_low, net_worth_high, asset_categories[], top_5_holdings[]
  - **Deliverable**: JSON schema (110 lines)
  - **Time**: 1 hour

- [ ] **Task 11.2**: Build portfolio snapshots aggregator
  - **Action**: Write `/scripts/build_agg_portfolio_snapshots.py`
  - **Logic**: For each member + year → aggregate Schedule A assets → calculate net worth → extract top holdings
  - **Deliverable**: Script (340 lines)
  - **Time**: 4.5 hours

- [ ] **Task 11.3**: Test and verify
  - **Action**: Run script, review member portfolios
  - **Deliverable**: Parquet file in `gold/.../aggregates/agg_portfolio_snapshots/`
  - **Time**: 1 hour

### 12. Aggregate: Trading Timeline (Tasks 34-36)

- [ ] **Task 12.1**: Design agg_trading_timeline_daily schema
  - **Action**: Create `/ingestion/schemas/gold/agg_trading_timeline_daily.json`
  - **Fields**: trade_date (PK), total_trades, total_purchases, total_sales, unique_members, unique_stocks, total_volume_low, total_volume_high
  - **Deliverable**: JSON schema (60 lines)
  - **Time**: 45 min

- [ ] **Task 12.2**: Build trading timeline aggregator
  - **Action**: Write `/scripts/build_agg_trading_timeline_daily.py`
  - **Logic**: Aggregate fact_ptr_transactions by transaction_date → calculate daily totals
  - **Deliverable**: Script (220 lines)
  - **Time**: 3 hours

- [ ] **Task 12.3**: Test and verify
  - **Action**: Run script, plot daily trading volume over time
  - **Deliverable**: Parquet file in `gold/.../aggregates/agg_trading_timeline_daily/`
  - **Time**: 1 hour

### 13. Master Gold Rebuild Script (Tasks 37-39)

- [ ] **Task 13.1**: Create master rebuild script
  - **Action**: Write `/scripts/rebuild_gold_complete.py`
  - **Logic**: Run all fact builders → run all aggregate builders → upload to S3 → generate manifests
  - **Modes**: full (rebuild all), incremental (only new data), year (specific year)
  - **Deliverable**: Master script (400 lines)
  - **Time**: 5 hours

- [ ] **Task 13.2**: Add progress tracking and logging
  - **Action**: Enhance script with progress bars, CloudWatch logging
  - **Use**: tqdm for progress, boto3 CloudWatch for metrics
  - **Deliverable**: Enhanced script with monitoring
  - **Time**: 2 hours

- [ ] **Task 13.3**: Test full rebuild
  - **Action**: Run `python scripts/rebuild_gold_complete.py --mode full`
  - **Verify**: All 6 fact tables + 7 aggregates built, uploaded to S3
  - **Deliverable**: Complete Gold layer
  - **Time**: 2 hours (runtime)

### 14. Documentation & Testing (Tasks 40-42)

- [ ] **Task 14.1**: Create Gold layer data dictionary
  - **Action**: Write `/docs/GOLD_DATA_DICTIONARY.md`
  - **Include**: All fact tables, all aggregates, field descriptions, join keys, ERD diagram
  - **Deliverable**: Comprehensive data dictionary (200+ lines)
  - **Time**: 3 hours

- [ ] **Task 14.2**: Write integration tests for Gold builders
  - **Action**: Create `/tests/integration/test_gold_builders.py`
  - **Tests**: Each fact builder, each aggregate builder, master rebuild script
  - **Deliverable**: 15+ integration tests
  - **Time**: 3 hours

- [ ] **Task 14.3**: Generate sample queries documentation
  - **Action**: Write `/docs/GOLD_SAMPLE_QUERIES.md`
  - **Include**: 20+ SQL/DuckDB queries for common analytics (top traders, trending stocks, compliance issues, etc.)
  - **Deliverable**: Query cookbook
  - **Time**: 2 hours

---

## Files Created/Modified

### Created (32 files)
- **Schemas (7)**: fact_ptr_transactions, fact_asset_holdings, fact_liabilities, fact_positions, fact_gifts_travel, agg_member_trading_stats, agg_stock_activity, agg_sector_activity, agg_compliance_metrics, agg_portfolio_snapshots, agg_trading_timeline_daily
- **Builders (11)**: 6 fact builders + 5 aggregate builders
- **Master Script**: rebuild_gold_complete.py
- **Tests**: test_gold_builders.py
- **Docs (3)**: GOLD_DATA_DICTIONARY.md, GOLD_SAMPLE_QUERIES.md

### Modified (1 file)
- `/scripts/build_fact_filings.py` - Enhanced with schedule counts

---

## Acceptance Criteria

✅ **Fact Tables Built**
- 6 fact tables: PTR transactions, asset holdings, liabilities, positions, gifts/travel, filings (enhanced)
- All facts partitioned by year
- All foreign keys validated

✅ **Aggregate Tables Built**
- 7 aggregates: member trading stats, stock activity, sector activity, compliance metrics, portfolio snapshots, trading timeline, document quality (existing)
- All aggregates calculated correctly

✅ **Master Rebuild Script**
- Single script rebuilds entire Gold layer
- Incremental mode for efficient updates
- Progress tracking and logging

✅ **Data Quality**
- No null foreign keys
- All dates validated
- All amounts consistent (low ≤ high)

✅ **Documentation**
- Data dictionary complete
- Sample queries provided
- ERD diagram created

✅ **Testing**
- 15+ integration tests passing
- Full rebuild successful

---

## Testing Checklist

### Integration Tests
- [ ] fact_ptr_transactions builder
- [ ] fact_asset_holdings builder
- [ ] fact_liabilities builder
- [ ] fact_positions builder
- [ ] fact_gifts_travel builder
- [ ] agg_member_trading_stats builder
- [ ] agg_stock_activity builder
- [ ] agg_sector_activity builder
- [ ] agg_compliance_metrics builder
- [ ] agg_portfolio_snapshots builder
- [ ] agg_trading_timeline_daily builder
- [ ] Master rebuild script (full mode)
- [ ] Master rebuild script (incremental mode)
- [ ] Run: `pytest tests/integration/test_gold_builders.py -v`

### Manual Verification
- [ ] Query fact_ptr_transactions, verify transaction count
- [ ] Query agg_member_trading_stats, identify top trader
- [ ] Query agg_stock_activity, identify most traded stock
- [ ] Query agg_compliance_metrics, find late filers
- [ ] Verify all Parquet files in S3 Gold layer

---

## Deployment Steps

1. **Local Development**
   ```bash
   # Test individual builders
   python scripts/build_fact_ptr_transactions.py --year 2025
   python scripts/build_agg_member_trading_stats.py

   # Test master rebuild
   python scripts/rebuild_gold_complete.py --mode full --dry-run
   ```

2. **Run Full Rebuild**
   ```bash
   python scripts/rebuild_gold_complete.py --mode full
   ```

3. **Upload to S3**
   ```bash
   aws s3 sync data/gold/ s3://congress-disclosures-standardized/gold/ --delete
   ```

4. **Verify in S3**
   ```bash
   aws s3 ls s3://congress-disclosures-standardized/gold/house/financial/facts/ --recursive
   aws s3 ls s3://congress-disclosures-standardized/gold/house/financial/aggregates/ --recursive
   ```

5. **Update Website Manifests**
   ```bash
   python scripts/generate_gold_manifests.py
   aws s3 cp data/gold/manifest.json s3://congress-disclosures-standardized/gold/manifest.json
   ```

---

## Rollback Plan

If Gold layer build fails:

1. **Preserve Old Data**: Backup existing Gold layer before rebuild
   ```bash
   aws s3 sync s3://congress-disclosures-standardized/gold/ s3://congress-disclosures-standardized/gold-backup-$(date +%Y%m%d)/
   ```

2. **Restore**: Copy backup back if needed
   ```bash
   aws s3 sync s3://congress-disclosures-standardized/gold-backup-YYYYMMDD/ s3://congress-disclosures-standardized/gold/
   ```

3. **Incremental Fix**: If only one table fails, rebuild just that table
   ```bash
   python scripts/build_fact_ptr_transactions.py --year 2025 --force
   ```

---

## Next Session Handoff

**Prerequisites for Session 5 (API Gateway)**:
- ✅ Complete Gold layer with 6 facts + 7 aggregates
- ✅ All tables in S3 and queryable
- ✅ Sample queries tested and working
- ✅ Data dictionary complete

**Data Needed**:
- Gold Parquet files accessible from Lambda
- Fast query library (DuckDB or PyArrow)
- Sample API responses for testing

**Code Dependencies**:
- Gold tables stable and tested
- Query patterns documented

---

## Session 4 Success Metrics

- **Fact tables**: 6 tables built and tested
- **Aggregate tables**: 7 tables built and tested
- **Scripts**: 11 builders + 1 master script
- **Test coverage**: 15+ integration tests passing
- **Data volume**: Millions of transactions, thousands of members
- **Code volume**: ~3,500 lines (builders + schemas + tests + docs)
- **Documentation**: Data dictionary + sample queries
- **Time**: Completed in 7 days (Week 4)

**Status**: ⏸️ NOT STARTED | 🔄 IN PROGRESS | ✅ COMPLETE
