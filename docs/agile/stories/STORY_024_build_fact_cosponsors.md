# STORY-024: Create build_fact_cosponsors Lambda Wrapper

**Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 3 | **Priority**: P2 | **Status**: To Do

## User Story
**As a** data engineer
**I want** fact_cosponsors table
**So that** we analyze bill cosponsorship patterns

## Acceptance Criteria
- **GIVEN** Congress.gov Silver cosponsorship data
- **WHEN** Lambda executes
- **THEN** Creates fact table with bill-member relationships
- **AND** Includes cosponsor dates

## Technical Tasks
- [ ] Read Silver cosponsors data
- [ ] Join with dim_bills and dim_members
- [ ] Write to fact_cosponsors.parquet

## Estimated Effort: 3 hours
**Target**: Dec 25, 2025
