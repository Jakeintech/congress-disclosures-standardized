# STORY-027: Create compute_member_stats Lambda Wrapper

**Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 3 | **Priority**: P1 | **Status**: Done | **Completed**: 2025-12-16

## User Story
**As a** API consumer
**I want** member trading statistics
**So that** I see member activity levels

## Acceptance Criteria
- **GIVEN** fact_transactions and fact_filings data
- **WHEN** Lambda executes
- **THEN** Calculates per-member statistics
- **AND** Includes total_transactions, compliance_score
- **AND** Writes to agg_member_trading_stats.parquet

## Technical Tasks
- [ ] Wrap `scripts/compute_agg_member_trading_stats.py`
- [ ] Read fact_transactions
- [ ] Group by member_key, year
- [ ] Calculate total_transactions, total_value, compliance_score
- [ ] Write to Gold aggregates

## Estimated Effort: 3 hours
**Target**: Dec 27, 2025
