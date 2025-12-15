# STORY-022: Create build_fact_filings Lambda Wrapper

**Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 5 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** data engineer
**I want** fact_filings table
**So that** we track filing metadata and compliance

## Acceptance Criteria
- **GIVEN** Silver filings data
- **WHEN** Lambda executes
- **THEN** Creates fact table with member_key FK
- **AND** Calculates transaction counts per filing
- **AND** Computes quality scores

## Technical Tasks
- [ ] Read Silver filings
- [ ] Join with dim_members
- [ ] Aggregate transaction counts from fact_transactions
- [ ] Calculate quality scores
- [ ] Partition by year
- [ ] Write to fact_filings.parquet

## Estimated Effort: 5 hours
**Target**: Dec 24, 2025
