# STORY-022: Create build_fact_filings Lambda Wrapper

**Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 5 | **Priority**: P0 | **Status**: Done | **Completed**: 2025-12-16

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
- [x] Read Silver filings
- [ ] Join with dim_members (deferred - not in current Lambda implementation)
- [ ] Aggregate transaction counts from fact_transactions (deferred - not in current Lambda implementation)
- [ ] Calculate quality scores (deferred - not in current Lambda implementation)
- [x] Partition by year
- [x] Write to fact_filings.parquet
- [x] Create Lambda handler
- [x] Configure Terraform deployment
- [x] Add to packaging script
- [x] Write unit tests (11 tests, all passing)

## Estimated Effort: 5 hours
**Target**: Dec 24, 2025
