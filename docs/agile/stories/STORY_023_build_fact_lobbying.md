# STORY-023: Create build_fact_lobbying Lambda Wrapper

**Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 5 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** data engineer
**I want** fact_lobbying table
**So that** we analyze lobbying expenditures

## Acceptance Criteria
- **GIVEN** LDA Silver data
- **WHEN** Lambda executes
- **THEN** Creates fact table with lobbying amounts
- **AND** Links to dim_lobbyists
- **AND** Extracts bills lobbied

## Technical Tasks
- [ ] Read Silver lobbying data
- [ ] Parse lobbying amounts
- [ ] Extract issues and bills
- [ ] Join with dimensions
- [ ] Partition by year/quarter
- [ ] Write to fact_lobbying.parquet

## Estimated Effort: 5 hours
**Target**: Dec 24, 2025
