# API Endpoints Documentation

**Base URL**: `https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com`

## Overview

This document lists all API endpoints used by the website, their purpose, and which pages consume them.

## Dashboard Endpoints

### GET /v1/analytics/summary
- **Purpose**: Retrieve summary statistics for the dashboard
- **Used by**: Dashboard (`/`)
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "members": { "total": 1020 },
      "trades": { "total": 5433, "unique_stocks": 1018, "latest_transaction": "2025-11-28" },
      "filings": { "total": 1669, "latest_filing": "20251203" },
      "bills": { "total": 1136 }
    }
  }
  ```

### GET /v1/analytics/trending-stocks?limit=10
- **Purpose**: Get most traded stocks
- **Used by**: Dashboard (`/`)
- **Response**: Array of `{ ticker, company_name, trade_count, net_direction }`

### GET /v1/analytics/top-traders?limit=10
- **Purpose**: Get most active traders
- **Used by**: Dashboard (`/`)
- **Response**: Array of `{ name, bioguide_id, party, state, trade_count, total_volume }`

## Members Endpoints

### GET /v1/congress/members?limit=100&party=D&chamber=house&state=CA
- **Purpose**: List congressional members with filtering
- **Used by**: Members page (`/members`), Politician profile (`/politician/[id]`)
- **Parameters**:
  - `congress` (optional): Filter by congress number
  - `chamber` (optional): `house` or `senate`
  - `party` (optional): `D`, `R`, or `I`
  - `state` (optional): Two-letter state code
  - `limit` (optional): Results limit (default: 100)
  - `offset` (optional): Pagination offset
- **Response**: Array of member objects with `bioguide_id`, `first_name`, `last_name`, `party`, `state`, `chamber`, etc.

### GET /v1/members/{bioguide_id}
- **Purpose**: Get detailed member profile
- **Used by**: Politician profile (`/politician/[id]`)
- **Response**: Member object with full details

### GET /v1/members/{bioguide_id}/trades?limit=50
- **Purpose**: Get member's trading history
- **Used by**: Politician profile (`/politician/[id]`)
- **Response**: Array of trade objects

### GET /v1/members/{bioguide_id}/portfolio
- **Purpose**: Get member's current portfolio holdings
- **Used by**: Politician profile (`/politician/[id]`)
- **Response**: `{ holdings: [...] }`

## Bills Endpoints

### GET /v1/congress/bills?congress=119&limit=50
- **Purpose**: List bills with filtering
- **Used by**: Bills page (`/bills`)
- **Parameters**:
  - `congress` (optional): Congress number (e.g., 119)
  - `bill_type` (optional): `hr`, `s`, `hres`, `sres`, etc.
  - `sponsor` (optional): Sponsor bioguide_id
  - `industry` (optional): Industry tag
  - `has_trade_correlations` (optional): boolean
  - `sort_by` (optional): `latest_action_date`, `cosponsors_count`, etc.
  - `sort_order` (optional): `asc` or `desc`
  - `limit`/`offset`: Pagination
- **Response**: Array of bill objects

### GET /v1/congress/bills/{bill_id}
- **Purpose**: Get detailed bill information
- **Used by**: Bill detail page (`/bills/[congress]/[type]/[number]`)
- **Response**: Bill object with sponsor, cosponsors, actions, trade_correlations

### GET /v1/congress/bills/{bill_id}/actions
- **Purpose**: Get bill actions/history
- **Used by**: Bill detail page
- **Response**: `{ actions: [...], count: N }`

### GET /v1/congress/bills/{bill_id}/text
- **Purpose**: Get bill text content
- **Used by**: Bill detail page
- **Response**: `{ text_url, content, format, text_versions: [...] }`

### GET /v1/congress/bills/{bill_id}/cosponsors
- **Purpose**: Get bill cosponsors
- **Used by**: Bill detail page
- **Response**: `{ cosponsors: [...], count: N }`

### GET /v1/congress/bills/{bill_id}/subjects
- **Purpose**: Get bill subject tags
- **Used by**: Bill detail page
- **Response**: `{ subjects: [...], count: N }`

### GET /v1/congress/bills/{bill_id}/summaries
- **Purpose**: Get bill summaries
- **Used by**: Bill detail page
- **Response**: `{ summaries: [...], count: N }`

### GET /v1/congress/bills/{bill_id}/titles
- **Purpose**: Get bill titles
- **Used by**: Bill detail page
- **Response**: `{ titles: [...], count: N }`

### GET /v1/congress/bills/{bill_id}/amendments
- **Purpose**: Get bill amendments
- **Used by**: Bill detail page
- **Response**: `{ amendments: [...], count: N }`

### GET /v1/congress/bills/{bill_id}/related
- **Purpose**: Get related bills
- **Used by**: Bill detail page
- **Response**: `{ relatedBills: [...], count: N }`

## Transactions Endpoints

### GET /v1/trades?limit=50&ticker=AAPL&trade_type=purchase
- **Purpose**: List stock transactions
- **Used by**: Transactions page (`/transactions`)
- **Parameters**:
  - `ticker` (optional): Stock ticker symbol
  - `member` (optional): Member bioguide_id
  - `trade_type` (optional): `purchase` or `sale`
  - `min_amount` (optional): Minimum transaction amount
  - `limit`/`offset`: Pagination
- **Response**: Array of transaction objects

## Lobbying Endpoints

### GET /v1/correlations/triple?limit=50&min_score=40
- **Purpose**: Get trade-bill-lobbying correlations
- **Used by**: Influence Tracker page (`/influence`)
- **Parameters**:
  - `min_score` (optional): Minimum correlation score
  - `year` (optional): Filter by year
  - `limit` (optional): Results limit
- **Response**: Array of correlation objects

### GET /v1/lobbying/network-graph?year=2025
- **Purpose**: Get lobbying network graph data
- **Used by**: Lobbying Network page (`/lobbying/network`)
- **Response**: `{ graph: { nodes: [...], links: [...] }, metadata: {...} }`

## CORS Configuration

All endpoints support CORS with:
- **Access-Control-Allow-Origin**: `*`
- **Access-Control-Allow-Methods**: `GET, POST, OPTIONS`
- **Access-Control-Allow-Headers**: `Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token`

## Rate Limiting

- No explicit rate limits enforced
- During build time (SSG), may encounter 503 errors due to high concurrency
- Recommendation: Add retry logic for build-time failures

## Error Responses

All endpoints return errors in this format:
```json
{
  "success": false,
  "error": "Error message here"
}
```

Common HTTP status codes:
- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Temporary service disruption

## Monitoring

To check endpoint health:
```bash
curl https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com/v1/analytics/summary
```

## Notes

- All responses include a `success` boolean field
- Data is typically wrapped in a `data` field
- Timestamps are in ISO 8601 format
- Amounts are stored as strings to preserve precision
