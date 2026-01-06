# Backend API TODO - Congress Activity Platform

## Critical Issues to Fix

### 1. Bills API (`/v1/congress/bills`) - Missing Fields

**Problem:** The bills list endpoint is missing critical fields needed by the UI.

**Current Response:**
```json
{
  "congress": 119,
  "bill_type": "sconres",
  "bill_number": 23,
  "title": "A concurrent resolution...",
  "sponsor_name": "Sen. Blunt Rochester, Lisa [D-DE]",
  "cosponsors_count": 0,
  "latest_action_date": "2025-11-05"
}
```

**Missing Fields:**
- `sponsor_bioguide_id` (string) - **CRITICAL** for linking to member profiles
- `trade_correlations_count` (number) - Count of trades correlated with this bill
- `sponsor_party` (string) - For party badges/colors
- `sponsor_state` (string) - For display

**Required Changes:**

1. **Extract Bioguide ID from Sponsor Data:**
   - Congress.gov sponsor object has `bioguideId` field
   - Parse and include in bills list response
   - Example: `"sponsor_bioguide_id": "B001303"`

2. **Add Trade Correlations Count:**
   - Query silver/gold layer for bill-trade correlations
   - Count distinct trades within 30/60 days of bill actions
   - Cache this value or pre-compute in Gold layer

3. **Backend Implementation:**
```python
# In ingestion/lambdas/api_gateway_handler.py or equivalent

def get_bills_list(congress=119, limit=100):
    bills = fetch_from_congress_gov_api(...)

    # Enrich each bill
    for bill in bills:
        # Extract bioguide ID from sponsor
        if bill.get('sponsor'):
            bill['sponsor_bioguide_id'] = bill['sponsor'].get('bioguideId')
            bill['sponsor_party'] = bill['sponsor'].get('party')
            bill['sponsor_state'] = bill['sponsor'].get('state')

        # Add trade correlation count
        bill_id = f"{bill['congress']}-{bill['billType'].lower()}-{bill['billNumber']}"
        bill['trade_correlations_count'] = count_bill_trade_correlations(bill_id)

    return bills
```

---

### 2. Transactions API (`/v1/trades`) - Page Load Error

**Problem:** Transactions page fails to load - likely 500 error or timeout.

**Check:**
1. Does endpoint exist?
2. Is it properly configured in API Gateway?
3. Lambda timeout settings (increase to 30s)?
4. Parquet file access permissions?

**Test:**
```bash
curl https://YOUR_API/v1/trades?limit=100
```

**Expected Response:**
```json
{
  "success": true,
  "data": [
    {
      "doc_id": "12345",
      "member_name": "John Doe",
      "bioguide_id": "D000123",
      "ticker": "AAPL",
      "transaction_type": "Purchase",
      "amount_low": 15001,
      "amount_high": 50000,
      "transaction_date": "2025-01-15",
      "disclosure_date": "2025-02-01"
    }
  ],
  "count": 1234
}
```

---

### 3. Analytics Endpoints - Missing Implementations

#### `/v1/analytics/top-traders`

**Problem:** Returns empty array or doesn't exist.

**Required Response:**
```json
{
  "success": true,
  "data": {
    "top_traders": [
      {
        "bioguide_id": "P000197",
        "name": "Nancy Pelosi",
        "party": "Democrat",
        "state": "CA",
        "chamber": "House",
        "trade_count": 156,
        "total_volume": "$12,300,000",
        "total_volume_numeric": 12300000
      }
    ]
  }
}
```

**Implementation:**
- Query gold/aggregates/member_trading_stats/
- Sort by trade_count or total_volume descending
- Limit to top N (default 10)
- Cache for 24 hours

#### `/v1/analytics/network-graph`

**Problem:** May be missing aggregated_nodes and aggregated_links fields.

**Required for Trading Network Graph:**
```json
{
  "success": true,
  "data": {
    "nodes": [...],
    "links": [...],
    "aggregated_nodes": [
      {
        "id": "Democrat",
        "group": "party_agg",
        "value": 50000000,
        "transaction_count": 5000,
        "party": "Democrat"
      },
      {
        "id": "Republican",
        "group": "party_agg",
        "value": 40000000,
        "transaction_count": 4000,
        "party": "Republican"
      }
    ],
    "aggregated_links": [
      {
        "source": "Democrat",
        "target": "AAPL",
        "value": 5000000,
        "count": 150,
        "is_aggregated": true
      }
    ]
  }
}
```

---

### 4. Committees API - Not Implemented

**Required Endpoints:**

1. **`GET /v1/congress/committees`**
   - List all House and Senate committees
   - Proxy to Congress.gov API
   - Cache for 7 days

2. **`GET /v1/congress/committees/{chamber}/{committeeCode}`**
   - Committee details
   - Member roster with bioguide IDs
   - Cache for 7 days

3. **`GET /v1/congress/committees/{chamber}/{committeeCode}/bills`**
   - Bills referred to this committee
   - From Congress.gov API

**Implementation Priority:** Low (placeholder page exists)

---

### 5. Correlation Endpoints

#### `/v1/correlations/triple`

**Status:** May exist but needs verification

**Required Parameters:**
- `year` (default 2025)
- `min_score` (default 50)
- `limit` (default 200)
- Optional: `member_bioguide`, `ticker`, `bill_id`

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "correlations": [
      {
        "bill_id": "119-hr-1234",
        "raw_reference": "H.R. 1234",
        "correlation_score": 85,
        "client_count": 3,
        "client_names": "Boeing|Lockheed Martin|Raytheon",
        "registrant_count": 5,
        "registrant_names": "Firm A|Firm B",
        "filing_count": 8,
        "lobbying_amount": 500000,
        "top_issue_codes": "DEF|AER",
        "trade_date": "2025-03-15",
        "bill_action_date": "2025-03-10"
      }
    ]
  }
}
```

---

## Implementation Checklist

### Immediate (Blocking UI)
- [x] Add `sponsor_bioguide_id` to bills API response ✅ (Already present in Gold layer)
- [x] Fix transactions endpoint (page won't load) ✅ (Verified working)
- [x] Implement `/v1/analytics/top-traders` endpoint ✅ (Already implemented and working)
- [x] Add `trade_correlations_count` to bills API ✅ (Enrichment logic exists in handler)

### High Priority
- [x] Add aggregated nodes/links to network graph API ✅ (Returns 2 party nodes + links)
- [x] Verify `/v1/correlations/triple` endpoint works ✅ (Verified working)
- [x] Add caching headers to all analytics endpoints ✅ (Cache-Control headers present)

### Medium Priority
- [x] Implement committees API endpoints ✅ (Handlers exist, proxying Congress.gov)
- [x] Add congressional alpha calculation endpoint ✅ (Handler exists)
- [x] Add sector analysis aggregation ✅ (Working via /v1/analytics/sector-activity)

### Low Priority
- [ ] Add bill-trade timing heatmap data (Future enhancement)
- [ ] Implement portfolio tracking endpoints (Future enhancement)
- [ ] Add bulk export endpoints (Future enhancement)

---

## Testing Commands

```bash
# Test bills API
curl "https://YOUR_API/v1/congress/bills?congress=119&limit=10" | jq '.data[0]'

# Test transactions
curl "https://YOUR_API/v1/trades?limit=10" | jq

# Test top traders
curl "https://YOUR_API/v1/analytics/top-traders?limit=5" | jq

# Test network graph
curl "https://YOUR_API/v1/analytics/network-graph" | jq '.data.aggregated_nodes'

# Test correlations
curl "https://YOUR_API/v1/correlations/triple?year=2025&min_score=70&limit=10" | jq
```

---

## Gold Layer Scripts Needed

Some of these require new Gold layer aggregation scripts:

1. **`scripts/compute_agg_bill_trade_correlations.py`**
   - For each bill, count related trades
   - Store in `gold/aggregates/bill_trade_counts/`
   - Run daily

2. **`scripts/compute_agg_member_trading_leaderboard.py`**
   - Aggregate member trading stats
   - Sort by volume, count, alpha
   - Store in `gold/aggregates/top_traders/`

3. **`scripts/build_network_aggregations.py`**
   - Pre-compute party/chamber/state aggregations
   - Store in `gold/aggregates/network_aggregations/`

---

## API Gateway Configuration

Ensure these routes exist in Terraform:

```hcl
resource "aws_api_gateway_resource" "trades" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "trades"
}

resource "aws_api_gateway_resource" "analytics" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "analytics"
}

resource "aws_api_gateway_resource" "top_traders" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.analytics.id
  path_part   = "top-traders"
}
```

---

## Notes

- All endpoints should return `{"success": true, "data": {...}}` format
- Add CORS headers for Vercel domain
- Cache analytics endpoints for 1-24 hours
- Log all 500 errors to CloudWatch
- Add API key requirement for bulk endpoints (future)
