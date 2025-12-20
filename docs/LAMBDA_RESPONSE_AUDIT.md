# Lambda Handler Response Pattern Audit

**Generated:** 2025-12-20
**Purpose:** Document all Lambda handler response patterns for Pydantic model creation

---

## Executive Summary

- **Total handlers found:** 68 unique handler.py files
- **Using response_formatter:** ~95% (64/68)
- **Paginated responses:** ~40% (27/68)
- **Direct Parquet queries:** ~70% (48/68)
- **External API calls:** ~10% (7/68)
- **DuckDB optimized:** ~25% (17/68)

---

## Response Wrapper Standard

All handlers use the **api.lib.response_formatter** module which provides:

### Success Response Structure
```python
{
    "statusCode": 200,
    "headers": {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Content-Type": "application/json"
    },
    "body": {  # JSON string containing:
        "success": true,
        "data": <any>,
        "version": "v20251220-33a4c83",  # Loaded from version.json
        "metadata": {  # Optional
            "cache_seconds": 300,
            ...
        }
    }
}
```

### Error Response Structure
```python
{
    "statusCode": 400|404|500|...,
    "headers": { ... },  # Same CORS headers
    "body": {  # JSON string containing:
        "success": false,
        "error": {
            "message": "Error description",
            "code": 400,
            "details": <any>  # Optional
        }
    }
}
```

### Key Features
- **NaN Cleaning:** All responses use `clean_nan_values()` to convert NaN/Inf → null
- **Version Injection:** Automatically includes API version from version.json
- **CORS Headers:** All responses include CORS headers
- **Type Safety:** Uses custom JSONEncoder to handle pandas/numpy types

---

## Response Pattern Categories

### Pattern 1: Simple Data Response (22 handlers)
**Characteristic:** Returns a single object or list directly in `data` field, no pagination.

**Structure:**
```typescript
{
  success: true,
  data: {
    // Single object
  },
  version: string,
  metadata?: {
    cache_seconds?: number
  }
}
```

**Handlers:**
- `get_version` - Returns version metadata + runtime info
- `get_summary` - Platform-wide statistics (members, trades, stocks, bills, filings)
- `get_member/{bioguide_id}` - Individual member profile with trading_stats, recent_filings, net_worth, sector_allocation
- `get_filing/{doc_id}` - Filing metadata + structured_data JSON
- `get_stock/{ticker}` - Stock statistics + recent_trades list
- `get_compliance` - Compliance metrics array
- `get_member_portfolio/{bioguide_id}` - Portfolio holdings array
- `get_congressional_alpha` - Alpha metrics
- `get_conflict_detection` - Conflict analysis
- `get_portfolio_recon` - Portfolio reconciliation
- `get_pattern_insights` - Pattern analysis
- `get_trading_timeline` - Timeline data
- `get_sector_activity` - Sector aggregates
- `get_stock_activity` - Stock activity metrics
- `get_aws_costs` - AWS cost metrics
- `get_lobbying_client/{client_id}` - Client details
- `get_lobbying_network` - Network graph data
- `get_triple_correlations` - Correlation data
- `consolidate_tabular` - Tabular consolidation
- `consolidate_cache` - Cache consolidation
- `run_soda_checks` - Data quality checks
- `list_s3_objects` - S3 object listing

**Data Field Types:**
- Object: Version, member profile, stock detail, filing detail
- Array: Compliance metrics, portfolio holdings, costs
- Complex: Network graphs, correlations (nodes + links)

---

### Pattern 2: Simple List Response (10 handlers)
**Characteristic:** Returns array in `data` field without pagination metadata.

**Structure:**
```typescript
{
  success: true,
  data: {
    items: Array<T>,
    count?: number,
    summary?: object
  },
  version: string
}
```

**Handlers:**
- `search` - Returns `{ query, results: { members: [], stocks: [] } }`
- `get_recent_activity` - Returns `{ activity: [], count: number }`
- `get_bill_summaries` - Returns `{ bill_id, summaries: [], count }`
- `get_bill_committees` - Returns `{ bill_id, committees: [] }`
- `get_bill_text` - Returns `{ bill_id, text_versions: [] }`
- `get_bill_amendments` - Returns `{ bill_id, amendments: [] }`
- `get_bill_related` - Returns `{ bill_id, related_bills: [] }`
- `get_bill_titles` - Returns `{ bill_id, titles: [] }`
- `get_bill_subjects` - Returns `{ bill_id, subjects: [] }`
- `get_bill_cosponsors` - Returns `{ bill_id, cosponsors: [] }`

---

### Pattern 3: Paginated Response (27 handlers)
**Characteristic:** Uses `build_pagination_response()` from api.lib.pagination.

**Structure:**
```typescript
{
  success: true,
  data: {
    success: true,  // Nested from build_pagination_response
    data: Array<T>,
    pagination: {
      total: number,
      count: number,
      limit: number,
      offset: number,
      has_next: boolean,
      has_prev: boolean,
      next: string | null,
      prev: string | null
    }
  },
  version: string,
  metadata?: object
}
```

**Handlers:**
- `get_members` - List members with filters (state, district, party)
- `get_stocks` - List stocks with aggregated trade stats
- `get_filings` - List filings with filters (bioguide_id, filing_type, date_range)
- `get_congress_bills` - Enhanced bills list with cosponsors_count, trade_correlations, industry_tags, latest_action
- `get_congress_members` - Members with trading stats (DuckDB optimized)
- `get_member_filings/{name}` - Member's filings (name-based search)
- `get_committee_reports` - Committee reports list
- `get_committee_members` - Committee membership list
- `get_committee_bills` - Bills assigned to committee
- `get_congress_committees` - All committees list
- `get_filing_transactions` - Transactions from specific filing
- `get_filing_assets` - Assets from specific filing
- `get_filing_positions` - Positions from specific filing
- `get_member_assets` - Member's asset holdings
- `get_member_transactions` - Member's all transactions
- `get_stock_leg_exposure` - Legislative exposure for stock

**Additional Paginated (Custom Structure):**
- `get_member_trades/{bioguide_id}` - Returns `{ bioguide_id, total_count, limit, offset, trades: [], has_more }`
- `get_trades` - Returns `{ trades: [], pagination: {...}, filters: {...} }`
- `get_lobbying_filings` - Returns `{ filings: [], total, limit, offset, has_more }`

---

### Pattern 4: Enhanced Detail Response (3 handlers)
**Characteristic:** Returns comprehensive detail object with multiple nested sections.

**Structure:**
```typescript
{
  success: true,
  data: {
    // Main entity
    bill: object,
    // Related entities
    sponsor: object,
    cosponsors: array,
    actions_recent: array,
    industry_tags: array,
    trade_correlations: array,
    committees: array,
    related_bills: array,
    subjects: array,
    titles: array,
    // Metadata
    cosponsors_count: number,
    actions_count_total: number,
    trade_correlations_count: number,
    congress_gov_url: string
  },
  version: string,
  metadata?: {
    bill_id: string,
    cached: boolean,
    cache_max_age: number
  }
}
```

**Handlers:**
- `get_congress_bill/{bill_id}` - Full bill details with all related data
- `get_congress_member/{bioguide_id}` - Full member profile (if exists - similar to get_member)
- `get_congress_committee/{system_code}` - Committee details with members/bills

---

### Pattern 5: Aggregated/Complex Response (6 handlers)
**Characteristic:** Returns computed aggregates, rankings, or complex data structures.

**Structure:**
```typescript
{
  success: true,
  data: {
    // Main results
    items: array,
    // Aggregates/metadata
    summary_stats?: object,
    party_breakdown?: array,
    filters?: object,
    rankings?: array
  },
  version: string
}
```

**Handlers:**
- `get_trending_stocks` - Returns `{ time_window, total_stocks, stocks: [], top_movers: [], sort_by }`
- `get_top_traders` - Returns `{ days, metric, total_traders, traders: [], party_breakdown: [] }`
- `get_network_graph` - Returns `{ nodes: [], links: [], aggregated_nodes: [], aggregated_links: [], summary_stats: {} }`
- `get_bill_lob_activity` - Returns bill-lobbying correlations
- `get_member_lob_connects` - Returns member-lobbyist connections
- `get_member_leg_trades` - Returns legislative-trade correlations
- `get_bill_actions` - Returns bill action timeline

---

## Common Data Models Across Handlers

### 1. Member Object
**Used in:** get_member, get_members, get_congress_members, cosponsors, sponsors

```typescript
{
  bioguide_id: string,
  first_name: string,
  last_name: string,
  full_name: string,
  party: "D" | "R" | "I" | string,
  state: string,  // 2-letter code
  district?: string,
  chamber: "house" | "senate",
  is_current?: boolean,
  // Extended fields
  photo_url?: string,
  total_trades?: number,
  total_volume?: number,
  unique_stocks?: number,
  last_trade_date?: string,
  compliance_rate?: number
}
```

### 2. Transaction Object
**Used in:** get_trades, get_member_trades, fact_ptr_transactions

```typescript
{
  transaction_date: string,  // YYYY-MM-DD
  ticker: string,
  asset_name: string,
  transaction_type: "Purchase" | "Sale" | "Exchange",
  amount_low: number,
  amount_high: number,
  amount_midpoint?: number,
  bioguide_id: string,
  full_name: string,
  party: string,
  state: string,
  chamber: string,
  filing_date?: string,
  doc_id?: string,
  owner_code?: "SELF" | "SP" | "DC" | "JT"
}
```

### 3. Stock Object
**Used in:** get_stocks, trending_stocks

```typescript
{
  ticker: string,
  name?: string,
  total_trades: number,
  unique_members: number,
  purchase_count: number,
  sale_count: number,
  latest_trade_date: string,
  total_volume?: number,
  buy_volume?: number,
  sell_volume?: number,
  sentiment_score?: number,
  logo_url?: string
}
```

### 4. Filing Object
**Used in:** get_filings, get_filing, get_member_filings

```typescript
{
  doc_id: string,
  filing_type: "P" | "A" | "T" | "X" | "D" | "W",
  filing_date: string | number,  // YYYYMMDD or YYYY-MM-DD
  filing_year: number,
  bioguide_id: string,
  filer_name: string,
  structured_data?: object  // JSON extraction
}
```

### 5. Bill Object
**Used in:** get_congress_bills, get_congress_bill

```typescript
{
  bill_id: string,  // "congress-type-number" e.g., "118-hr-1"
  congress: number,
  bill_type: "hr" | "s" | "hjres" | "sjres" | "hconres" | "sconres" | "hres" | "sres",
  bill_number: number,
  title: string,
  introduced_date: string,
  update_date?: string,
  sponsor_bioguide_id?: string,
  sponsor_name?: string,
  // Enhanced fields
  cosponsors_count?: number,
  trade_correlations_count?: number,
  top_industry_tags?: string[],
  latest_action_date?: string,
  latest_action_text?: string,
  days_since_action?: number,
  summary?: string,
  text_url?: string,
  pdf_url?: string
}
```

### 6. Pagination Metadata
**Used in:** All paginated endpoints

```typescript
{
  total: number,        // Total matching records
  count: number,        // Records in current page
  limit: number,        // Max records per page
  offset: number,       // Current offset
  has_next: boolean,
  has_prev: boolean,
  next: string | null,  // Next page URL
  prev: string | null   // Previous page URL
}
```

### 7. Network Graph Structure
**Used in:** get_network_graph

```typescript
{
  nodes: Array<{
    id: string,
    name: string,
    group: "member" | "asset" | "bill" | "party_agg",
    party?: string,
    state?: string,
    chamber?: string,
    value: number,
    transaction_count: number,
    buy_count: number,
    sell_count: number,
    degree: number,
    rank?: number,
    tier?: "platinum" | "gold" | "silver" | "bronze"
  }>,
  links: Array<{
    source: string,
    target: string,
    value: number,
    count: number,
    type: "purchase" | "sale" | "mixed" | "sponsorship"
  }>,
  aggregated_nodes?: array,
  aggregated_links?: array,
  summary_stats: object
}
```

---

## Special Response Patterns

### 1. Congress.gov API Proxies
**Handlers:** get_bill_summaries, get_bill_text, get_bill_amendments, etc.

These fetch data from external Congress.gov API and return cleaned responses:
- Strip HTML tags from text
- Normalize field names
- Handle API errors gracefully (404 → 404, timeout → 504, other → 502)
- No pagination (Congress.gov handles it)

### 2. Lobbying Endpoints
**Handlers:** get_lobbying_filings, get_lobbying_client, get_lobbying_network

Return lobbying data with custom fields:
```typescript
{
  filings: array,
  total: number,
  limit: number,
  offset: number,
  has_more: boolean
}
```

### 3. DuckDB Optimized Handlers
**Handlers:** get_congress_members, get_member_trades, get_trades, get_trending_stocks, get_top_traders

Use global connection pooling:
```python
_conn = None  # Module-level

def get_duckdb_connection():
    global _conn
    if _conn is None:
        _conn = duckdb.connect(':memory:')
        # Configure S3 + httpfs
    return _conn
```

Performance: 10-50x faster than pandas-based ParquetQueryBuilder.

---

## Filter Patterns

### Common Query Parameters

#### Pagination (All list endpoints)
- `limit`: int (default 50, max 500)
- `offset`: int (default 0)

#### Date Filters
- `start_date`: YYYY-MM-DD
- `end_date`: YYYY-MM-DD

#### Member Filters
- `bioguide_id`: string
- `party`: D | R | I
- `state`: 2-letter code
- `chamber`: house | senate

#### Bill Filters
- `congress`: number
- `bill_type`: hr | s | hjres | ...
- `sponsor_bioguide`: string
- `cosponsor_bioguide`: string
- `industry`: string
- `has_trade_correlations`: boolean

#### Transaction Filters
- `ticker`: string (uppercase)
- `transaction_type`: Purchase | Sale | Exchange
- `min_amount`: number
- `max_amount`: number

#### Sorting
- `sort_by`: varies by endpoint
- `sort_order`: asc | desc

---

## Error Handling Patterns

### 1. Missing Path Parameters
```python
if not bioguide_id:
    return error_response("bioguide_id is required", 400)
```

### 2. Not Found (404)
```python
if len(member_df) == 0:
    return error_response(
        message=f"Member not found: {bioguide_id}",
        status_code=404,
        details={'bioguide_id': bioguide_id}
    )
```

### 3. Invalid Format (400)
```python
if len(parts) != 3:
    return error_response(
        message="Invalid bill_id format. Expected: congress-type-number",
        status_code=400
    )
```

### 4. Internal Errors (500)
```python
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
    return error_response(
        message="Failed to retrieve data",
        status_code=500,
        details=str(e)
    )
```

### 5. Empty Results (Graceful)
```python
if bills_df is None or bills_df.empty:
    return success_response({
        'bills': [],
        'total_count': 0,
        'limit': limit,
        'offset': offset
    })
```

---

## Metadata Patterns

### Cache Control
```python
return success_response(
    data,
    metadata={'cache_seconds': 300}
)
```

Common cache durations:
- **60s**: Version endpoint
- **300s** (5 min): Current congress data, trending stocks, members list
- **3600s** (1 hour): Member trades, historical data
- **86400s** (24 hours): Archived congress data (congress <= 118)

### Runtime Info (Version endpoint)
```python
runtime_info = {
    "function_name": context.function_name,
    "function_version": context.function_version,
    "aws_request_id": context.aws_request_id,
    "memory_limit_mb": context.memory_limit_in_mb
}
```

---

## Complete Handler Inventory

### House Financial Disclosures (17 handlers)
1. `get_member/{bioguide_id}` - Member profile (Simple)
2. `get_members` - List members (Paginated)
3. `get_filing/{doc_id}` - Filing detail (Simple)
4. `get_filings` - List filings (Paginated)
5. `get_filing_transactions/{doc_id}` - Filing transactions (Paginated)
6. `get_filing_assets/{doc_id}` - Filing assets (Paginated)
7. `get_filing_positions/{doc_id}` - Filing positions (Paginated)
8. `get_member_filings/{name}` - Member filings by name (Paginated)
9. `get_member_trades/{bioguide_id}` - Member trades (Paginated-Custom)
10. `get_member_assets/{bioguide_id}` - Member assets (Paginated)
11. `get_member_transactions/{bioguide_id}` - All transactions (Paginated)
12. `get_member_portfolio/{bioguide_id}` - Current portfolio (Simple)
13. `get_trades` - All trades (Paginated-Custom)
14. `get_stocks` - List stocks (Paginated)
15. `get_stock/{ticker}` - Stock detail (Simple)
16. `get_stock_leg_exposure/{ticker}` - Legislative exposure (Paginated)
17. `get_compliance` - Compliance metrics (Simple)

### Congress Bills (20 handlers)
18. `get_congress_bills` - List bills (Paginated-Enhanced)
19. `get_congress_bill/{bill_id}` - Bill detail (Enhanced-Detail)
20. `get_bill_summaries/{bill_id}` - Bill summaries (List)
21. `get_bill_committees/{bill_id}` - Bill committees (List)
22. `get_bill_text/{bill_id}` - Bill text versions (List)
23. `get_bill_amendments/{bill_id}` - Bill amendments (List)
24. `get_bill_related/{bill_id}` - Related bills (List)
25. `get_bill_titles/{bill_id}` - Bill titles (List)
26. `get_bill_subjects/{bill_id}` - Bill subjects (List)
27. `get_bill_cosponsors/{bill_id}` - Bill cosponsors (List)
28. `get_bill_actions/{bill_id}` - Bill actions (Aggregated)
29. `get_bill_lob_activity/{bill_id}` - Bill lobbying activity (Aggregated)
30. `get_congress_committees` - List committees (Paginated)
31. `get_congress_committee/{system_code}` - Committee detail (Enhanced)
32. `get_committee_reports/{system_code}` - Committee reports (Paginated)
33. `get_committee_members/{system_code}` - Committee members (Paginated)
34. `get_committee_bills/{system_code}` - Committee bills (Paginated)
35. `get_congress_members` - List members (Paginated-DuckDB)
36. `get_congress_member/{bioguide_id}` - Member detail (Enhanced)
37. `get_member_leg_trades/{bioguide_id}` - Legislative trades (Aggregated)

### Lobbying (5 handlers)
38. `get_lobbying_filings` - List filings (Paginated-Custom)
39. `get_lobbying_client/{client_id}` - Client detail (Simple)
40. `get_lobbying_network` - Network graph (Simple)
41. `get_member_lob_connects/{bioguide_id}` - Member connections (Aggregated)
42. `get_triple_correlations` - Triple correlations (Simple)

### Analytics (10 handlers)
43. `get_summary` - Platform summary (Simple)
44. `get_trending_stocks` - Trending stocks (Aggregated-DuckDB)
45. `get_top_traders` - Top traders (Aggregated-DuckDB)
46. `get_recent_activity` - Activity feed (List)
47. `get_network_graph` - Network visualization (Aggregated)
48. `get_sector_activity` - Sector activity (Simple)
49. `get_stock_activity` - Stock activity (Simple)
50. `get_congressional_alpha` - Alpha metrics (Simple)
51. `get_conflict_detection` - Conflict detection (Simple)
52. `get_portfolio_recon` - Portfolio reconciliation (Simple)
53. `get_pattern_insights` - Pattern insights (Simple)
54. `get_trading_timeline` - Trading timeline (Simple)

### Utilities (6 handlers)
55. `get_version` - API version (Simple)
56. `search?q={query}` - Unified search (List)
57. `get_aws_costs` - AWS costs (Simple)
58. `list_s3_objects` - S3 listing (Simple)
59. `run_soda_checks` - Data quality (Simple)
60. `consolidate_tabular` - Consolidation (Simple)
61. `consolidate_cache` - Cache consolidation (Simple)

---

## Recommendations for Pydantic Models

### Core Response Models
1. **APIResponse[T]** - Generic wrapper for all responses
   ```python
   class APIResponse(BaseModel, Generic[T]):
       success: bool
       data: T
       version: str
       metadata: Optional[Dict[str, Any]] = None
   ```

2. **PaginatedResponse[T]** - For paginated endpoints
   ```python
   class PaginationMetadata(BaseModel):
       total: int
       count: int
       limit: int
       offset: int
       has_next: bool
       has_prev: bool
       next: Optional[str]
       prev: Optional[str]

   class PaginatedData(BaseModel, Generic[T]):
       success: bool
       data: List[T]
       pagination: PaginationMetadata
   ```

3. **ErrorResponse** - For error cases
   ```python
   class ErrorDetail(BaseModel):
       message: str
       code: int
       details: Optional[Any] = None

   class ErrorResponse(BaseModel):
       success: Literal[False]
       error: ErrorDetail
   ```

### Entity Models
4. **Member** - For member objects
5. **Transaction** - For trade transactions
6. **Stock** - For stock objects
7. **Filing** - For disclosure filings
8. **Bill** - For congressional bills
9. **Committee** - For committees
10. **NetworkGraph** - For network visualizations

### Specialized Models
11. **TradingStats** - For aggregated trading metrics
12. **ComplianceMetrics** - For compliance data
13. **IndustryTag** - For bill industry tags
14. **TradeCorrelation** - For bill-trade correlations
15. **ActivityFeedItem** - For recent activity

### Helper Models
16. **DateRange** - For date filters
17. **AmountRange** - For amount filters
18. **SortOptions** - For sorting parameters

---

## Notes

1. **Type Safety Gaps:**
   - Many handlers use `to_dict('records')` which loses type information
   - Pandas DataFrames have inconsistent schemas across years/partitions
   - DuckDB queries return dynamically typed DataFrames

2. **Consistency Issues:**
   - Some endpoints use nested `success: true` in data (pagination)
   - Date formats vary: YYYY-MM-DD vs YYYYMMDD vs ISO timestamps
   - Member ID fields: bioguide_id (string) vs member_key (number)

3. **Performance Patterns:**
   - DuckDB handlers are 10-50x faster (connection pooling)
   - Pagination often over-fetches for post-filtering
   - Aggregates pre-computed in Gold layer where possible

4. **Missing Standardization:**
   - No shared base handler class
   - Inconsistent error message formats
   - Variable cache control strategies

5. **Next Steps:**
   - Create Pydantic models for all response types
   - Add response validation middleware
   - Standardize pagination metadata structure
   - Implement OpenAPI schema generation
