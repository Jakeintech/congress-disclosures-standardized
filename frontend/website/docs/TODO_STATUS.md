# TODO Status - Website Documentation

**Generated**: December 11, 2025
**Status**: Overview of all pending tasks in website/docs

---

## Summary

The website documentation contains **13 uncompleted TODO items** related to API endpoints and features. These are **separate from the medallion architecture migration** (Weeks 1-4) which is **100% complete**.

---

## ✅ COMPLETED: Medallion Architecture (Weeks 1-4)

All backend infrastructure, data pipeline, and optimization work is **DONE**:

- ✅ Week 1: Step Functions, EventBridge, DynamoDB
- ✅ Week 2: DuckDB Gold transformations (15x faster)
- ✅ Week 3: Data quality framework (30+ checks)
- ✅ Week 4: API optimization (10-17x faster)

**Result**: Production-ready pipeline, 10-100x faster, 94% cost reduction

See: `docs/MIGRATION_COMPLETE.md` for full details.

---

## ❌ PENDING: Frontend API Features (13 items)

These TODOs are in `website/docs/BACKEND_TODO.md` and relate to **frontend UI features**, not core pipeline infrastructure.

### Immediate Priority (4 items)

**Blocking UI functionality:**

1. ❌ Add `sponsor_bioguide_id` to bills API response
   - **Impact**: Bills page can't link to member profiles
   - **Location**: `/v1/congress/bills` endpoint
   - **Effort**: Low (extract from existing sponsor data)

2. ❌ Fix transactions endpoint (page won't load)
   - **Impact**: Transactions page returns 500 error
   - **Location**: `/v1/trades` endpoint
   - **Effort**: Medium (debug Lambda timeout or permissions)

3. ❌ Implement `/v1/analytics/top-traders` endpoint
   - **Impact**: Dashboard "Top Traders" section empty
   - **Location**: New endpoint needed
   - **Effort**: Low (query existing Gold aggregates)

4. ❌ Add `trade_correlations_count` to bills API
   - **Impact**: Bills page missing trade correlation count
   - **Location**: `/v1/congress/bills` endpoint
   - **Effort**: Medium (requires Gold layer aggregation)

### High Priority (3 items)

**Important for analytics features:**

5. ❌ Add aggregated nodes/links to network graph API
   - **Impact**: Network graph can't show party/chamber aggregations
   - **Location**: `/v1/analytics/network-graph` endpoint
   - **Effort**: Medium (requires pre-computation)

6. ❌ Verify `/v1/correlations/triple` endpoint works
   - **Impact**: Influence Tracker page may fail
   - **Location**: `/v1/correlations/triple` endpoint
   - **Effort**: Low (test and fix if needed)

7. ❌ Add caching headers to all analytics endpoints
   - **Impact**: Poor performance for dashboards
   - **Location**: All `/v1/analytics/*` endpoints
   - **Effort**: Low (add Cache-Control headers)

### Medium Priority (3 items)

**Nice-to-have features:**

8. ❌ Implement committees API endpoints
   - **Impact**: Committees page is placeholder
   - **Location**: `/v1/congress/committees/*` endpoints
   - **Effort**: Medium (proxy to Congress.gov API)

9. ❌ Add congressional alpha calculation endpoint
   - **Impact**: No performance benchmarking vs S&P 500
   - **Location**: New endpoint needed
   - **Effort**: High (complex financial calculations)

10. ❌ Add sector analysis aggregation
    - **Impact**: No sector-level analytics
    - **Location**: New endpoint needed
    - **Effort**: Medium (group by industry)

### Low Priority (3 items)

**Future enhancements:**

11. ❌ Add bill-trade timing heatmap data
    - **Impact**: No timing analysis visualization
    - **Location**: New endpoint needed
    - **Effort**: High (statistical analysis)

12. ❌ Implement portfolio tracking endpoints
    - **Impact**: No member portfolio tracking
    - **Location**: New endpoints needed
    - **Effort**: High (complex state management)

13. ❌ Add bulk export endpoints
    - **Impact**: No CSV/JSON bulk downloads
    - **Location**: New endpoints needed
    - **Effort**: Medium (generate and stream files)

---

## Additional Pending Features (IMPLEMENTATION_STATUS.md)

These are **UI features** (not backend todos):

### Advanced Analytics ❌
- Congressional Alpha performance metrics
- Sector analysis charts
- Timing analysis heatmaps
- Portfolio tracking
- Benchmark comparisons (vs S&P 500)

### Bill Features ❌
- Committee detail pages with reports and hearings
- Bill text comparison tool (side-by-side versions)
- Amendment impact analysis

### Member Features ❌
- Committee assignments tab
- Voting record tab
- Network analysis (cosponsor relationships)
- Performance metrics (bills passed rate, etc.)

### Search & Discovery ❌
- Global search (Cmd+K)
- Advanced bill search with full-text
- Member effectiveness scoring
- Saved searches / watchlists

### Data Export ❌
- PDF report generation
- Bulk data export
- API access for researchers

---

## What IS Complete

### Backend Infrastructure ✅
- DuckDB Lambda layer (66MB)
- Soda Core Lambda layer (24MB)
- 3 Gold transformation functions
- run_soda_checks Lambda function
- 30+ data quality checks
- DynamoDB watermark tables
- SNS alert topics
- Optimized API handlers (3 created)

### Frontend UI ✅
- Dashboard with charts and metrics
- Member directory and profiles
- Bill search and detail pages
- Transaction search and filtering
- Influence Tracker (triple correlations)
- Trading Network visualization
- Lobbying Network graph
- Bill lifecycle timeline
- 50+ React components
- TypeScript types for all APIs
- Error boundaries and loading states

---

## Recommendation

### For Medallion Architecture Migration
**Status**: ✅ **100% COMPLETE**
- No remaining work on Weeks 1-4
- All infrastructure deployed
- All documentation updated
- Production-ready

### For Website Features
**Status**: 🚧 **13 Backend TODOs Remaining**

**Next Steps** (in order):
1. Fix `/v1/trades` endpoint (blocking)
2. Add `sponsor_bioguide_id` to bills API (blocking)
3. Implement `/v1/analytics/top-traders` (high value)
4. Add `trade_correlations_count` to bills (high value)
5. Other items as time permits

**Estimated Effort**:
- Items 1-4: 4-8 hours total
- Items 5-7: 4-6 hours total
- Items 8-13: 10-20 hours total
- **Total**: 18-34 hours of development

---

## Files Referenced

**Completed Work**:
- `docs/MIGRATION_COMPLETE.md` - Full Weeks 1-4 summary
- `docs/WEEKS_3_4_COMPLETE.md` - Weeks 3-4 detailed report
- `docs/WEEK2_COMPLETE.md` - Week 2 detailed report

**Pending Work**:
- `website/docs/BACKEND_TODO.md` - 13 API endpoint tasks
- `website/docs/IMPLEMENTATION_STATUS.md` - UI feature status
- `website/docs/TODO_STATUS.md` (this file) - Comprehensive summary

---

## Conclusion

**Medallion Architecture Migration (Weeks 1-4)**: ✅ **COMPLETE**
- All backend infrastructure deployed
- All performance optimizations done
- All data quality checks implemented
- All documentation up to date

**Website API Features**: 🚧 **13 Pending TODOs**
- 4 immediate (blocking UI)
- 3 high priority (analytics)
- 3 medium priority (nice-to-have)
- 3 low priority (future)

The core pipeline is **production-ready**. The remaining work is **frontend feature enhancements**.
