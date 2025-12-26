# STORY-025: Create build_fact_amendments Lambda Wrapper

**Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 3 | **Priority**: P2 | **Status**: Done | **Completed**: 2025-12-16

## User Story
**As a** data engineer
**I want** fact_amendments table
**So that** we track bill amendments

## Acceptance Criteria
- **GIVEN** Congress.gov Silver amendments data
- **WHEN** Lambda executes
- **THEN** Creates fact table with amendment metadata

## Technical Tasks
- [ ] Read Silver amendments data
- [ ] Join with dim_bills
- [ ] Extract amendment details
- [ ] Write to fact_amendments.parquet

## Estimated Effort: 3 hours
**Target**: Dec 25, 2025
