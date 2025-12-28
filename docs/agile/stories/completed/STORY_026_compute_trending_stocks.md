# STORY-026: Create compute_trending_stocks Lambda Wrapper

**Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 3 | **Priority**: P1 | **Status**: Done | **Completed**: 2025-12-16

## User Story
**As a** API consumer
**I want** trending stocks aggregate
**So that** I see what members are trading

## Acceptance Criteria
- **GIVEN** fact_transactions data
- **WHEN** Lambda executes
- **THEN** Calculates 7/30/90 day trending stocks
- **AND** Ranks by total value and net activity
- **AND** Writes to agg_trending_stocks.parquet

## Technical Tasks
- [ ] Wrap `scripts/compute_agg_trending_stocks.py`
- [ ] Read fact_transactions for last 90 days
- [ ] Group by ticker, window (7/30/90 days)
- [ ] Calculate purchase_count, sale_count, net_activity
- [ ] Rank by total value
- [ ] Write to Gold aggregates

## Estimated Effort: 3 hours
**Target**: Dec 27, 2025
