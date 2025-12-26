# STORY-018: Create build_dim_bills Lambda Wrapper

**Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 5 | **Priority**: P1 | **Status**: Done | **Completed**: 2025-12-16

## User Story
**As a** data engineer
**I want** dim_bills dimension table
**So that** we can analyze bill-trade correlations

## Acceptance Criteria
- **GIVEN** Congress.gov Silver data
- **WHEN** Lambda executes
- **THEN** Creates bills dimension with metadata
- **AND** Includes sponsor, policy area, introduced date

## Technical Tasks
- [ ] Read Silver congress_gov/bills
- [ ] Join with sponsor info
- [ ] Extract policy areas
- [ ] Write to dim_bills.parquet

## Estimated Effort: 5 hours
**Target**: Dec 23, 2025
