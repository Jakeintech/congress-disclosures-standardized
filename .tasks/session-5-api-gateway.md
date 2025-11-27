# Session 5: Modern API Gateway Layer

**Duration**: Week 5 (7 days)
**Goal**: Build production API Gateway HTTP API with 30+ endpoints, OpenAPI 3.0 spec, Swagger UI, and maintain free tier S3 public access

---

## Prerequisites

- [x] Session 4 complete (Gold layer with all tables)
- [ ] Gold Parquet files in S3 and queryable
- [ ] API design patterns researched (REST best practices, pagination, filtering)
- [ ] DuckDB or PyArrow for fast Parquet queries

---

## Task Checklist

### 1. API Infrastructure Setup (Tasks 1-6)

- [ ] **Task 1.1**: Design API Gateway HTTP API in Terraform
  - **Action**: Create `/infra/terraform/api_gateway.tf`
  - **Config**: HTTP API (cheaper than REST), CloudWatch logging, CORS enabled
  - **Deliverable**: Terraform config (150 lines)
  - **Time**: 2 hours

- [ ] **Task 1.2**: Configure CORS for public access
  - **Action**: Add CORS configuration to API Gateway
  - **Allow**: All origins (*), GET/POST methods, standard headers
  - **Deliverable**: CORS config in Terraform
  - **Time**: 30 min

- [ ] **Task 1.3**: Set up CloudWatch logging
  - **Action**: Enable access logging and execution logging
  - **Config**: Log group `/aws/apigateway/congress-disclosures-api`
  - **Deliverable**: Logging enabled
  - **Time**: 30 min

- [ ] **Task 1.4**: Add rate limiting
  - **Action**: Configure throttling settings
  - **Limits**: 10 req/sec burst, 1000 req/hour (free tier friendly)
  - **Deliverable**: Rate limits in Terraform
  - **Time**: 30 min

- [ ] **Task 1.5**: Create API domain and routing
  - **Action**: Set up API Gateway routes
  - **Pattern**: `/v1/*` → Lambda integrations
  - **Deliverable**: Route configuration
  - **Time**: 1 hour

- [ ] **Task 1.6**: Deploy API Gateway infrastructure
  - **Action**: `terraform plan && terraform apply`
  - **Verify**: API Gateway created, endpoint URL available
  - **Deliverable**: Live API Gateway
  - **Time**: 30 min

### 2. Shared API Libraries (Tasks 7-12)

- [ ] **Task 2.1**: Create Parquet query library
  - **Action**: Write `/api/lib/query_builder.py`
  - **Functions**: `query_parquet()`, `filter_parquet()`, `aggregate_parquet()`
  - **Use**: DuckDB for fast Parquet queries (SQL interface)
  - **Deliverable**: Query library (300 lines)
  - **Time**: 4 hours

- [ ] **Task 2.2**: Create pagination helper
  - **Action**: Write `/api/lib/pagination.py`
  - **Functions**: `paginate()`, `build_pagination_response()`
  - **Support**: Limit/offset, cursor-based, next/prev links
  - **Deliverable**: Pagination library (150 lines)
  - **Time**: 2 hours

- [ ] **Task 2.3**: Create response formatter
  - **Action**: Write `/api/lib/response_formatter.py`
  - **Functions**: `success_response()`, `error_response()`, `add_cors_headers()`
  - **Format**: Consistent JSON structure with metadata
  - **Deliverable**: Response library (120 lines)
  - **Time**: 1.5 hours

- [ ] **Task 2.4**: Create filter parser
  - **Action**: Write `/api/lib/filter_parser.py`
  - **Functions**: `parse_query_params()`, `build_sql_where()`
  - **Support**: Operators (eq, ne, gt, lt, gte, lte, in, like)
  - **Deliverable**: Filter library (200 lines)
  - **Time**: 2.5 hours

- [ ] **Task 2.5**: Create caching helper
  - **Action**: Write `/api/lib/cache.py`
  - **Functions**: `cache_response()`, `get_cached()`, `invalidate_cache()`
  - **Use**: In-memory dict cache with TTL (Lambda execution context)
  - **Deliverable**: Cache library (100 lines)
  - **Time**: 1.5 hours

- [ ] **Task 2.6**: Write tests for shared libraries
  - **Action**: Create `/tests/unit/test_api_libs.py`
  - **Tests**: Query builder, pagination, filters, responses
  - **Deliverable**: 20+ unit tests
  - **Time**: 2 hours

### 3. Member Endpoints (Tasks 13-16)

- [ ] **Task 3.1**: Implement GET /v1/members
  - **Action**: Write `/api/lambdas/get_members/handler.py`
  - **Query**: dim_members Gold table
  - **Filters**: state, district, party, active (has recent filings)
  - **Pagination**: Limit/offset (default 50, max 500)
  - **Response**: Array of members with summary stats
  - **Deliverable**: Lambda handler (180 lines)
  - **Time**: 3 hours

- [ ] **Task 3.2**: Implement GET /v1/members/{bioguide_id}
  - **Action**: Write `/api/lambdas/get_member/handler.py`
  - **Query**: dim_members + agg_member_trading_stats + agg_compliance_metrics
  - **Response**: Full member profile with trading stats, compliance, recent filings
  - **Deliverable**: Lambda handler (200 lines)
  - **Time**: 3 hours

- [ ] **Task 3.3**: Implement GET /v1/members/{bioguide_id}/trades
  - **Action**: Write `/api/lambdas/get_member_trades/handler.py`
  - **Query**: fact_ptr_transactions filtered by member_key
  - **Filters**: start_date, end_date, ticker, transaction_type
  - **Pagination**: Limit/offset
  - **Response**: Array of trades with asset details
  - **Deliverable**: Lambda handler (220 lines)
  - **Time**: 3.5 hours

- [ ] **Task 3.4**: Implement GET /v1/members/{bioguide_id}/portfolio
  - **Action**: Write `/api/lambdas/get_member_portfolio/handler.py`
  - **Query**: Latest fact_asset_holdings for member
  - **Response**: Current portfolio with asset breakdown, net worth estimate
  - **Deliverable**: Lambda handler (180 lines)
  - **Time**: 3 hours

### 4. Trading & Stock Endpoints (Tasks 17-20)

- [ ] **Task 4.1**: Implement GET /v1/trades
  - **Action**: Write `/api/lambdas/get_trades/handler.py`
  - **Query**: fact_ptr_transactions
  - **Filters**: start_date, end_date, ticker, member, transaction_type, min_amount, max_amount
  - **Pagination**: Limit/offset
  - **Sort**: By transaction_date DESC (default)
  - **Response**: Array of all trades with member and asset details
  - **Deliverable**: Lambda handler (250 lines)
  - **Time**: 4 hours

- [ ] **Task 4.2**: Implement GET /v1/stocks/{ticker}
  - **Action**: Write `/api/lambdas/get_stock/handler.py`
  - **Query**: agg_stock_activity + recent fact_ptr_transactions
  - **Response**: Stock summary with trading stats, recent trades
  - **Deliverable**: Lambda handler (180 lines)
  - **Time**: 3 hours

- [ ] **Task 4.3**: Implement GET /v1/stocks/{ticker}/activity
  - **Action**: Write `/api/lambdas/get_stock_activity/handler.py`
  - **Query**: fact_ptr_transactions filtered by ticker
  - **Filters**: start_date, end_date
  - **Response**: All trades for stock with timeline
  - **Deliverable**: Lambda handler (200 lines)
  - **Time**: 3 hours

- [ ] **Task 4.4**: Implement GET /v1/stocks
  - **Action**: Write `/api/lambdas/get_stocks/handler.py`
  - **Query**: agg_stock_activity
  - **Filters**: sector, min_trades, min_volume
  - **Sort**: By total_trades DESC (default)
  - **Pagination**: Limit/offset
  - **Response**: Array of stocks with summary stats
  - **Deliverable**: Lambda handler (190 lines)
  - **Time**: 3 hours

### 5. Analytics Endpoints (Tasks 21-26)

- [ ] **Task 5.1**: Implement GET /v1/analytics/top-traders
  - **Action**: Write `/api/lambdas/get_top_traders/handler.py`
  - **Query**: agg_member_trading_stats
  - **Filters**: year, min_trades
  - **Sort**: By total_trades DESC
  - **Limit**: Default 20, max 100
  - **Response**: Top traders with stats
  - **Deliverable**: Lambda handler (150 lines)
  - **Time**: 2.5 hours

- [ ] **Task 5.2**: Implement GET /v1/analytics/trending-stocks
  - **Action**: Write `/api/lambdas/get_trending_stocks/handler.py`
  - **Query**: agg_stock_activity + recent fact_ptr_transactions
  - **Logic**: Stocks with most trades in last 30/90 days
  - **Response**: Trending stocks with recent activity
  - **Deliverable**: Lambda handler (170 lines)
  - **Time**: 3 hours

- [ ] **Task 5.3**: Implement GET /v1/analytics/sector-activity
  - **Action**: Write `/api/lambdas/get_sector_activity/handler.py`
  - **Query**: agg_sector_activity
  - **Filters**: year, month
  - **Response**: Sector breakdown with trends
  - **Deliverable**: Lambda handler (160 lines)
  - **Time**: 2.5 hours

- [ ] **Task 5.4**: Implement GET /v1/analytics/compliance
  - **Action**: Write `/api/lambdas/get_compliance/handler.py`
  - **Query**: agg_compliance_metrics
  - **Filters**: state, district, min_late_filings
  - **Response**: Compliance stats, late filers
  - **Deliverable**: Lambda handler (170 lines)
  - **Time**: 2.5 hours

- [ ] **Task 5.5**: Implement GET /v1/analytics/trading-timeline
  - **Action**: Write `/api/lambdas/get_trading_timeline/handler.py`
  - **Query**: agg_trading_timeline_daily
  - **Filters**: start_date, end_date
  - **Response**: Daily trading volume over time
  - **Deliverable**: Lambda handler (150 lines)
  - **Time**: 2.5 hours

- [ ] **Task 5.6**: Implement GET /v1/analytics/summary
  - **Action**: Write `/api/lambdas/get_summary/handler.py`
  - **Query**: Multiple Gold aggregates
  - **Response**: Platform-wide summary (total members, trades, stocks, latest filing date)
  - **Deliverable**: Lambda handler (140 lines)
  - **Time**: 2 hours

### 6. Search & Filing Endpoints (Tasks 27-29)

- [ ] **Task 6.1**: Implement GET /v1/search
  - **Action**: Write `/api/lambdas/search/handler.py`
  - **Query**: Multiple tables (members, stocks, trades)
  - **Logic**: Full-text search on names, tickers, using SQL LIKE
  - **Response**: Unified search results (members, stocks, recent trades)
  - **Deliverable**: Lambda handler (280 lines)
  - **Time**: 4.5 hours

- [ ] **Task 6.2**: Implement GET /v1/filings
  - **Action**: Write `/api/lambdas/get_filings/handler.py`
  - **Query**: fact_filings (enhanced in Session 4)
  - **Filters**: member, filing_type, start_date, end_date
  - **Pagination**: Limit/offset
  - **Response**: Array of filings with metadata
  - **Deliverable**: Lambda handler (200 lines)
  - **Time**: 3 hours

- [ ] **Task 6.3**: Implement GET /v1/filings/{doc_id}
  - **Action**: Write `/api/lambdas/get_filing/handler.py`
  - **Query**: fact_filings + Silver structured JSON
  - **Response**: Full filing details with all extracted schedules
  - **Deliverable**: Lambda handler (180 lines)
  - **Time**: 3 hours

### 7. OpenAPI Specification (Tasks 30-32)

- [ ] **Task 7.1**: Write OpenAPI 3.0 specification
  - **Action**: Create `/docs/openapi.yaml`
  - **Include**: All 30+ endpoints with paths, parameters, request/response schemas
  - **Components**: Reusable schemas for Member, Trade, Stock, Filing, etc.
  - **Deliverable**: Complete OpenAPI spec (1000+ lines)
  - **Time**: 8 hours

- [ ] **Task 7.2**: Generate Swagger UI
  - **Action**: Create `/website/api-docs/` directory
  - **Files**: index.html (Swagger UI), swagger-initializer.js
  - **Config**: Point to openapi.yaml
  - **Deliverable**: Swagger UI hosted on S3
  - **Time**: 2 hours

- [ ] **Task 7.3**: Add API examples to OpenAPI
  - **Action**: Enhance openapi.yaml with example requests/responses
  - **Include**: 50+ examples covering common use cases
  - **Deliverable**: Rich OpenAPI spec with examples
  - **Time**: 3 hours

### 8. Lambda Packaging & Deployment (Tasks 33-36)

- [ ] **Task 8.1**: Create Lambda layer for shared libraries
  - **Action**: Create `/api/layers/shared_libs/` directory
  - **Include**: query_builder, pagination, response_formatter, filter_parser, cache
  - **Package**: As Lambda layer (reduces individual Lambda sizes)
  - **Deliverable**: Lambda layer ZIP
  - **Time**: 2 hours

- [ ] **Task 8.2**: Update Terraform for API Lambdas
  - **Action**: Edit `/infra/terraform/lambda.tf`
  - **Add**: 15+ API Lambda functions with API Gateway integrations
  - **Config**: Memory (512MB), timeout (29s for API Gateway limit), layer attachment
  - **Deliverable**: Terraform config for all API Lambdas
  - **Time**: 3 hours

- [ ] **Task 8.3**: Package all API Lambdas
  - **Action**: Create `/scripts/package_api_lambdas.sh`
  - **Logic**: Package each Lambda + dependencies, upload to S3
  - **Deliverable**: Packaging script
  - **Time**: 2 hours

- [ ] **Task 8.4**: Deploy API Lambdas
  - **Action**: Run packaging script + `terraform apply`
  - **Verify**: All Lambdas deployed, API Gateway routes connected
  - **Deliverable**: Live API
  - **Time**: 1 hour

### 9. Testing & Documentation (Tasks 37-38)

- [ ] **Task 9.1**: Create API integration tests
  - **Action**: Write `/tests/integration/test_api_endpoints.py`
  - **Tests**: Call each endpoint, verify response structure, status codes
  - **Use**: Requests library, assertions on JSON responses
  - **Deliverable**: 30+ endpoint tests
  - **Time**: 5 hours

- [ ] **Task 9.2**: Write API usage documentation
  - **Action**: Create `/docs/API_USAGE.md`
  - **Include**: Authentication (if any), rate limits, pagination, filtering, examples
  - **Deliverable**: Complete API documentation
  - **Time**: 3 hours

---

## Files Created/Modified

### Created (48 files)
- **Terraform**: api_gateway.tf, lambda.tf updates
- **Shared Libraries (5)**: query_builder.py, pagination.py, response_formatter.py, filter_parser.py, cache.py
- **Lambda Handlers (15)**: get_members, get_member, get_member_trades, get_member_portfolio, get_trades, get_stock, get_stock_activity, get_stocks, get_top_traders, get_trending_stocks, get_sector_activity, get_compliance, get_trading_timeline, get_summary, search, get_filings, get_filing
- **OpenAPI**: openapi.yaml (1000+ lines)
- **Swagger UI (3)**: index.html, swagger-initializer.js, custom CSS
- **Scripts**: package_api_lambdas.sh
- **Tests**: test_api_libs.py, test_api_endpoints.py
- **Docs**: API_USAGE.md

### Modified (2 files)
- `/infra/terraform/lambda.tf` - API Lambda configurations
- `/Makefile` - Add API packaging/deployment targets

---

## Acceptance Criteria

✅ **API Gateway Deployed**
- HTTP API live with public endpoint
- CORS enabled for all origins
- Rate limiting configured
- CloudWatch logging enabled

✅ **30+ Endpoints Functional**
- All member endpoints working
- All trading/stock endpoints working
- All analytics endpoints working
- Search and filing endpoints working

✅ **OpenAPI 3.0 Spec Complete**
- All endpoints documented
- Request/response schemas defined
- Examples provided
- Swagger UI hosted and accessible

✅ **Performance**
- p95 response time <200ms for simple queries
- p95 response time <500ms for complex queries
- All queries use efficient Parquet reads

✅ **Free Tier Compliance**
- API Gateway: <1M requests/month
- Lambda: <1M invocations/month
- Response times optimized (reduce GB-seconds)

✅ **Testing**
- 50+ tests passing (20 unit + 30 integration)
- All endpoints tested
- Error handling verified

---

## Testing Checklist

### Unit Tests
- [ ] Query builder: 5+ tests
- [ ] Pagination: 4+ tests
- [ ] Response formatter: 3+ tests
- [ ] Filter parser: 6+ tests
- [ ] Cache: 3+ tests
- [ ] Run: `pytest tests/unit/test_api_libs.py -v`

### Integration Tests (API Endpoint Tests)
- [ ] GET /v1/members - list, filters, pagination
- [ ] GET /v1/members/{id} - member profile
- [ ] GET /v1/members/{id}/trades - member trades
- [ ] GET /v1/members/{id}/portfolio - portfolio
- [ ] GET /v1/trades - all trades, filters
- [ ] GET /v1/stocks/{ticker} - stock details
- [ ] GET /v1/stocks/{ticker}/activity - stock trades
- [ ] GET /v1/stocks - list stocks
- [ ] GET /v1/analytics/top-traders
- [ ] GET /v1/analytics/trending-stocks
- [ ] GET /v1/analytics/sector-activity
- [ ] GET /v1/analytics/compliance
- [ ] GET /v1/analytics/trading-timeline
- [ ] GET /v1/analytics/summary
- [ ] GET /v1/search - search functionality
- [ ] GET /v1/filings - list filings
- [ ] GET /v1/filings/{doc_id} - filing details
- [ ] Run: `pytest tests/integration/test_api_endpoints.py -v`

### Manual Tests
- [ ] Test Swagger UI (open in browser)
- [ ] Test CORS (call from different origin)
- [ ] Test rate limiting (exceed limits)
- [ ] Test pagination (next/prev links)
- [ ] Test filters (complex queries)
- [ ] Load test (simulate 100 concurrent requests)

---

## Deployment Steps

1. **Deploy Infrastructure**
   ```bash
   cd infra/terraform
   terraform plan -out=api.tfplan
   terraform apply api.tfplan
   ```

2. **Package Shared Layer**
   ```bash
   cd api/layers/shared_libs
   pip install -r requirements.txt -t python/
   zip -r shared_libs.zip python/
   aws lambda publish-layer-version \
     --layer-name congress-disclosures-api-libs \
     --zip-file fileb://shared_libs.zip \
     --compatible-runtimes python3.11
   ```

3. **Package API Lambdas**
   ```bash
   bash scripts/package_api_lambdas.sh
   ```

4. **Deploy Lambdas**
   ```bash
   terraform apply
   ```

5. **Test Endpoints**
   ```bash
   export API_URL=$(terraform output -raw api_gateway_url)
   curl "$API_URL/v1/analytics/summary"
   curl "$API_URL/v1/members?limit=10"
   ```

6. **Deploy Swagger UI**
   ```bash
   aws s3 sync website/api-docs/ s3://congress-disclosures-standardized/api-docs/
   ```

7. **Run Integration Tests**
   ```bash
   export API_BASE_URL=$API_URL
   pytest tests/integration/test_api_endpoints.py -v
   ```

---

## Rollback Plan

If API deployment fails:

1. **Terraform Rollback**: Revert infrastructure changes
   ```bash
   terraform destroy -target=aws_apigatewayv2_api.congress_api
   ```

2. **Lambda Rollback**: Revert to previous versions
   ```bash
   aws lambda update-function-code --function-name get-members --s3-bucket ... --s3-key lambdas/previous/get_members.zip
   ```

3. **Keep S3 API**: S3-based API remains functional as fallback

---

## Next Session Handoff

**Prerequisites for Session 6 (Automation)**:
- ✅ API Gateway live with all endpoints
- ✅ Gold layer queryable via API
- ✅ OpenAPI spec complete
- ✅ Performance verified (<200ms p95)

**Integration Points**:
- Step Functions will trigger Gold rebuild → API automatically serves new data
- EventBridge daily trigger → incremental updates → API reflects latest filings

**Code Dependencies**:
- API Lambdas will remain unchanged
- Automation will trigger data updates, API serves updated data

---

## Session 5 Success Metrics

- **API Endpoints**: 30+ endpoints deployed
- **OpenAPI Spec**: 1000+ lines, complete documentation
- **Lambda Functions**: 15+ API handlers
- **Test coverage**: 50+ tests passing
- **Performance**: p95 <200ms (simple), <500ms (complex)
- **Free tier compliance**: ✅ All within limits
- **Code volume**: ~4,000 lines (handlers + libs + tests + spec)
- **Time**: Completed in 7 days (Week 5)

**Status**: ⏸️ NOT STARTED | 🔄 IN PROGRESS | ✅ COMPLETE
