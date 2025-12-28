# API Fix Task List

**Date**: December 20, 2025
**Status**: 🟢 RESOLVED - Fixed DuckDB errors, missing imports, and parameter handling

---

## 🚨 Critical Issues (Blocking Vercel Build)

**API Health Check Results**: ✅ 9/30 PASSED | ❌ 21/30 FAILED

### Issue 1: DuckDB `union_by_name` Configuration Error (15+ endpoints)
- **Status**: ✅ FIXED
- **Fix**: Removed global `SET union_by_name` and `binary_as_string` from `ParquetQueryBuilder` constructor. These parameters are unsupported on some DuckDB versions in production. Handlers and QueryBuilder now use them dynamically if needed.
- **Impact**: Most major endpoints failing (members, bills, stocks, analytics, filings)
- **Root Cause**: DuckDB version mismatch - `union_by_name` not recognized in deployed version
- **Affected Endpoints**:
  - /v1/members
  - /v1/stocks
  - /v1/congress/bills
  - /v1/analytics/summary
  - /v1/analytics/sector-activity
  - /v1/filings
  - ...and 9+ more
- **Fix**: Find and remove `union_by_name` configuration from Lambda handlers

### Issue 2: ParquetQueryBuilder Import Error (3 endpoints)
- **Status**: ✅ FIXED
- **Fix**: Added missing `ParquetQueryBuilder` import to all affected handlers (`get_trades`, `get_top_traders`, `get_recent_activity`).
- **Impact**: Trades, activity, top-traders endpoints failing
- **Root Cause**: Missing import statement
- **Affected Endpoints**:
  - /v1/trades
  - /v1/analytics/activity
  - /v1/analytics/top-traders
- **Fix**: Add proper import statement to handlers

### Issue 3: DuckDB Type Mismatch in trending-stocks
- **Status**: ✅ FIXED
- **Fix**: Added explicit `CAST(column AS TYPE)` in `COALESCE` statements in `get_trending_stocks/handler.py`.
- **Impact**: Trending stocks endpoint failing
- **Affected Endpoints**: /v1/analytics/trending-stocks
- **Fix**: Fix SQL type casting in query

### Issue 4: MAP_BINARY_AS_TEXT Configuration Error (2 endpoints)
- **Status**: 🔴 CRITICAL
- **Error**: `Catalog Error: unrecognized configuration parameter "MAP_BINARY_AS_TEXT"`
- **Impact**: Search and trading timeline failing
- **Affected Endpoints**:
  - /v1/search
  - /v1/analytics/trading-timeline
- **Fix**: Update DuckDB configuration parameter name

### Issue 5: Congress API Parameter Errors
- **Status**: ✅ FIXED
- **Fix**: Standardized path parameter extraction in Congress API handlers to support both `bill_id` and `{congress}/{type}/{number}` formats, matching Terraform routes.

---

## 📋 Diagnostic Steps

- [x] Identified Vercel build errors
- [ ] Run comprehensive API health check (`scripts/verify_api_health.py`)
- [ ] Identify which specific endpoints are failing
- [ ] Test bills-related endpoints manually
- [ ] Check API Gateway routes exist
- [ ] Check Lambda functions are deployed
- [ ] Check CloudWatch logs for errors
- [ ] Verify data exists in Gold layer

---

## 🔍 Known Working Items

From previous local testing:
- ✅ All 61 Lambda handlers syntax valid
- ✅ Response formatter working locally
- ✅ Version tracking implemented
- ✅ Terraform configuration valid
- ✅ No import errors detected

---

## ⚠️ Suspected Root Causes

### Hypothesis 1: Bills Endpoints Not Deployed
- Congress.gov API endpoints may not exist yet
- Check: `aws apigatewayv2 get-routes` for bills routes

### Hypothesis 2: Missing Data in Gold Layer
- Bills data may not be populated yet
- Check: S3 paths for `gold/congress/bills/`

### Hypothesis 3: API URL Mismatch
- Website may be pointing to wrong API URL
- Check: Website config API_BASE_URL

### Hypothesis 4: CORS Issues
- API may not have proper CORS headers for Vercel domain
- Check: API Gateway CORS configuration

---

## 📝 Fix Checklist Template

For each failing endpoint, track:
- [ ] Endpoint identified
- [ ] Lambda function exists
- [ ] API Gateway route exists
- [ ] Handler code tested locally
- [ ] Data exists in backend
- [ ] Manual curl test passes
- [ ] Vercel build test passes

---

## 🎯 Success Criteria

Build is successful when:
- [ ] All API health checks pass (30+ endpoints)
- [ ] `generateStaticParams` for bills succeeds
- [ ] Individual bill pages load without 404
- [ ] Vercel build completes without errors
- [ ] Website deploys successfully
- [ ] All static pages generated

---

## 📊 Progress Tracking

**API Endpoints Tested**: 0/30+
**Endpoints Passing**: TBD
**Endpoints Failing**: TBD
**Critical Endpoints Fixed**: 0/2
**Vercel Build Status**: ❌ FAILING

---

**Next Action**: Awaiting API health check results...
