# Congressional Trading API

Modern REST API for querying congressional trading data from the Gold Layer.

## Architecture

```
api/
├── lib/                    # Shared libraries (Lambda Layer)
│   ├── query_builder.py    # DuckDB-based Parquet queries
│   ├── pagination.py       # Pagination utilities
│   ├── response_formatter.py  # JSON response formatting with CORS
│   ├── filter_parser.py    # Query parameter parsing
│   └── cache.py            # In-memory caching
├── lambdas/                # Lambda function handlers
│   ├── get_members/        # GET /v1/members
│   ├── get_member/         # GET /v1/members/{id}
│   ├── get_trades/         # GET /v1/trades
│   ├── get_stock/          # GET /v1/stocks/{ticker}
│   ├── get_summary/        # GET /v1/analytics/summary
│   └── search/             # GET /v1/search
└── layers/                 # Lambda layers
    └── shared_libs/        # Shared library dependencies
```

## Technology Stack

- **API Gateway HTTP API**: Low-cost HTTP API ($1/million requests)
- **AWS Lambda**: Serverless compute (Python 3.11)
- **DuckDB**: Fast in-process SQL engine for Parquet queries (10-100x faster than pandas)
- **Parquet**: Columnar storage format for efficient queries
- **S3**: Data lake storage (Bronze/Silver/Gold layers)

## API Endpoints

### Members
- `GET /v1/members` - List members with filtering
- `GET /v1/members/{bioguide_id}` - Member profile
- `GET /v1/members/{bioguide_id}/trades` - Member's trades
- `GET /v1/members/{bioguide_id}/portfolio` - Member's portfolio

### Trading & Stocks
- `GET /v1/trades` - List all trades with filters
- `GET /v1/stocks/{ticker}` - Stock summary
- `GET /v1/stocks/{ticker}/activity` - Stock trading activity
- `GET /v1/stocks` - List stocks

### Analytics
- `GET /v1/analytics/top-traders` - Top traders by volume
- `GET /v1/analytics/trending-stocks` - Trending stocks
- `GET /v1/analytics/sector-activity` - Sector breakdown
- `GET /v1/analytics/compliance` - Compliance metrics
- `GET /v1/analytics/trading-timeline` - Daily trading volume
- `GET /v1/analytics/summary` - Platform-wide summary

### Search & Filings
- `GET /v1/search?q={query}` - Unified search
- `GET /v1/filings` - List filings
- `GET /v1/filings/{doc_id}` - Filing details

## Query Features

### Filtering

Simple equality:
```
GET /v1/trades?ticker=AAPL&transaction_type=Purchase
```

Operators:
```
GET /v1/trades?amount[gt]=50000&amount[lte]=100000
GET /v1/trades?transaction_type[in]=Purchase,Sale
GET /v1/search?q=Pelosi (LIKE operator)
```

Date ranges:
```
GET /v1/trades?start_date=2025-01-01&end_date=2025-03-31
```

### Pagination

```
GET /v1/members?limit=50&offset=0
```

Response includes next/prev links:
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "total": 435,
    "count": 50,
    "limit": 50,
    "offset": 0,
    "has_next": true,
    "next": "/v1/members?limit=50&offset=50"
  }
}
```

### Sorting

```
GET /v1/trades (sorted by transaction_date DESC)
GET /v1/members (sorted by last_name ASC)
```

## Development

### Local Testing

Run unit tests:
```bash
pytest tests/unit/test_api_libs.py -v
```

### Packaging Lambdas

Build Lambda packages:
```bash
./scripts/package_api_lambdas.sh
```

This creates:
- `build/api_lambdas/api_shared_layer.zip` - Shared library layer
- `build/api_lambdas/get_members.zip` - Individual Lambda functions

### Deployment

Deploy infrastructure:
```bash
cd infra/terraform
terraform plan
terraform apply
```

Get API endpoint:
```bash
terraform output api_gateway_url
```

### Testing Endpoints

```bash
export API_URL=$(cd infra/terraform && terraform output -raw api_gateway_url)

# Test summary
curl "$API_URL/v1/analytics/summary"

# Test members
curl "$API_URL/v1/members?limit=10"

# Test trades with filters
curl "$API_URL/v1/trades?ticker=AAPL&limit=10"

# Test search
curl "$API_URL/v1/search?q=Pelosi"
```

## Performance

- **Target**: p95 response time <200ms (simple queries), <500ms (complex)
- **Caching**: 5-minute TTL for frequently accessed data
- **Optimization**: DuckDB's zero-copy Parquet access, columnar pushdown

## Cost Optimization

- HTTP API vs REST API: 70% cost savings
- Lambda 512MB @ 29s timeout: Optimized for cost/performance
- DuckDB: No external database costs
- S3 Parquet: Efficient storage and transfer
- Rate limiting: Prevents runaway costs

**Expected monthly cost**: $1-5 for moderate usage (within free tier).

## Security

- **Public read-only API** (no authentication in MVP)
- **CORS enabled** for browser access
- **Rate limiting**: 10 req/sec burst, 1000 req/hour
- **SQL injection protection**: Parameterized queries

## Next Steps

1. Complete remaining Lambda handlers (11 more endpoints)
2. Add Terraform Lambda configurations
3. Create OpenAPI 3.0 specification
4. Build Swagger UI
5. Write integration tests
6. Deploy and verify
