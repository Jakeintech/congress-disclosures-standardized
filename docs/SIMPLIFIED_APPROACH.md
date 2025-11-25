# Simplified Gold Analytics Approach

## Key Insight from User Feedback

Instead of forcing complex Congress API matching for all 985+ filers, **present the data as it is**:

```
1,616 TOTAL FILINGS
├─ 38 Current Members (with PTR transactions)
├─ 947 Candidates / Other Filers
└─ Breakdown by filer type
```

## What We Actually Have in Silver

### PTR Transactions (3,025 records)
- **38 unique Congress members** with actual stock transactions
- These ARE the real members we care about for trading analytics
- Field: `filer_type = 'Member'`
- Field: `owner_code` = SP/DC/JT (Spouse/Dependent Child/Joint)

### All Filings (1,616 records)
- **985 unique filers** including:
  - Current members
  - Candidates (lost races)
  - New members (not yet sworn in)
  - Staff/relatives (maybe?)
- Not all have PTR transactions

## New KPI Structure

### Homepage Stats
```
1,616              985              2025            2025-11-24
TOTAL FILINGS    UNIQUE FILERS   LATEST YEAR    LAST UPDATED
```

### Gold Analytics - Member Trading Stats
```
📊 Member Trading Statistics
─────────────────────────────────────
38 Current Members | 3,025 Transactions | $XXM Volume

[TABLE of 38 members with trading activity]
```

### Gold Analytics - Document Quality
```
🔍 Document Quality & Compliance
─────────────────────────────────────
985 Filers Tracked | 980 Flagged | 30.0 Avg Quality

Filer Breakdown:
• 38 Current Members (with PTRs)
• 947 Candidates / Other Filers

[TABLE showing quality by filer]
```

### PTR Transactions Tab
```
💵 PTR Transactions
─────────────────────────────────────
3,025 Transactions | 38 Members

ℹ️  Owner Types Explained:
• Filer = The Congress member who filed
• SP (Spouse) = Member's spouse
• DC (Dependent Child) = Member's dependent child
• JT (Joint) = Joint ownership with member

[Filters]
Owner Type: [All | Member | Spouse | Dependent Child | Joint]
Member: [All 38 members dropdown]
Transaction Type: [All | Purchase | Sale | Partial Sale]

[TABLE showing transactions with proper labels]
```

## Correct Data Flow

### Bronze Layer
```
House Clerk PDFs → S3 bronze/
```

### Silver Layer
```
silver_ptr_filings        (1,616 filings, 985 unique filers)
silver_ptr_transactions   (3,025 transactions, 38 members)
silver_documents          (metadata about PDFs)
```

### Gold Layer
```
gold_agg_document_quality     (985 filers - ALL filers)
gold_agg_member_trading_stats (38 members - ONLY members with PTRs)
gold_agg_trending_stocks      (top 50 stocks from 3,025 transactions)
gold_agg_sector_activity      (sector breakdown from transactions)
```

## Key Changes Needed

### 1. Homepage KPIs ✅ (Already correct)
- "1,616 Filings" is accurate
- "985 Unique Filers" is accurate (not "members")

### 2. Document Quality Tab
**Current**: Shows "980 Members Tracked"
**New**: Show "985 Filers Tracked" with breakdown:
```sql
SELECT
  filer_type,
  COUNT(DISTINCT filer_id) as cnt
FROM silver_ptr_filings
GROUP BY filer_type
```

Expected output:
- Member: 38
- Candidate: ~900
- Other: ~47

### 3. Member Trading Stats Tab
**Current**: Sample data with fake stats
**New**: Real data from 38 members with PTR transactions
```sql
SELECT
  first_name,
  last_name,
  state_district,
  COUNT(*) as total_trades,
  SUM(CASE WHEN transaction_type LIKE '%Purchase%' THEN 1 ELSE 0 END) as buy_count,
  SUM(CASE WHEN transaction_type LIKE '%Sale%' THEN 1 ELSE 0 END) as sell_count,
  SUM(amount_midpoint) as total_volume
FROM silver_ptr_transactions
WHERE filer_type = 'Member'
GROUP BY first_name, last_name, state_district
ORDER BY total_trades DESC
```

### 4. Trending Stocks Tab
**Current**: Sample data with 10 stocks
**New**: Real data from transactions
```sql
SELECT
  asset_name,
  ticker,
  COUNT(*) as trade_count,
  SUM(CASE WHEN transaction_type LIKE '%Purchase%' THEN 1 ELSE 0 END) as buy_count,
  SUM(CASE WHEN transaction_type LIKE '%Sale%' THEN 1 ELSE 0 END) as sell_count,
  SUM(amount_midpoint) as total_volume
FROM silver_ptr_transactions
WHERE ticker IS NOT NULL
GROUP BY asset_name, ticker
ORDER BY trade_count DESC
LIMIT 50
```

### 5. PTR Transactions Tab
**Current**: Owner dropdown doesn't explain what it means
**New**: Add clarification alert box + rename labels:
- Dropdown: "Asset Owner Type" (not just "Owner")
- Alert box: Explain Filer vs Owner types
- Table columns: "Filer (Member)" and "Asset Owner"

## Implementation Order

1. ✅ **Fix navigation** (Phase 1.1) - DONE
2. **Add owner clarification** (Phase 1.3) - 2 hours
3. **Rebuild gold aggregates with real data** (Phase 3) - 6 hours
   - Member trading stats from PTR transactions
   - Trending stocks from PTR transactions
   - Sector analysis from PTR transactions
4. **Update website KPIs** - 2 hours
   - Change "Members" to "Filers" in document quality
   - Add filer type breakdown
5. **Fix PDF links** (Phase 2.2) - 2 hours
6. **Terraform** (Phase 4) - 16 hours
7. **Add trends** (Phase 5) - 8 hours
8. **Tests** (Phase 6) - 12 hours

**Total**: ~48 hours (down from 58)

## Benefits of This Approach

1. **Accurate**: Shows data as it really is
2. **No complex matching**: Avoids Congress API rate limits and matching issues
3. **Transparent**: Users understand 985 filers ≠ 985 members
4. **Simpler**: Less moving parts, fewer failure points
5. **Faster**: No API calls needed for every filer

## SQL Schema for Gold Analytics

### gold_agg_member_trading_stats
```sql
first_name              VARCHAR
last_name               VARCHAR
state_district          VARCHAR
total_trades            INT
buy_count               INT
sell_count              INT
buy_sell_ratio          FLOAT
total_volume            DECIMAL(15,2)
avg_transaction_size    DECIMAL(15,2)
unique_stocks           INT
period_start            DATE
period_end              DATE
```

### gold_agg_trending_stocks
```sql
rank                    INT
ticker                  VARCHAR
asset_name              VARCHAR
trade_count             INT
buy_count               INT
sell_count              INT
net_sentiment           VARCHAR (Bullish/Bearish/Neutral)
total_volume_usd        DECIMAL(15,2)
avg_transaction_size    DECIMAL(15,2)
unique_members          INT
period_start            DATE
period_end              DATE
```

### gold_agg_sector_activity
```sql
sector                  VARCHAR
trade_count             INT
buy_count               INT
sell_count              INT
net_position            INT (buy_count - sell_count)
total_volume            DECIMAL(15,2)
unique_members          INT
period_start            DATE
period_end              DATE
```

---

**Status**: Ready for implementation
**Approved**: Pending user review
**Created**: 2025-11-25
