# STORY-019: Create build_dim_lobbyists Lambda Wrapper

**Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 3 | **Priority**: P2 | **Status**: Done | **Completed**: 2025-12-16

## User Story
**As a** data engineer
**I want** dim_lobbyists dimension table
**So that** we track registrants and clients

## Acceptance Criteria
- **GIVEN** LDA Silver data
- **WHEN** Lambda executes
- **THEN** Extracts unique registrants and clients
- **AND** Deduplicates and normalizes names

## Technical Tasks
- [ ] Extract registrant names from Silver lobbying
- [ ] Extract client names
- [ ] Deduplicate
- [ ] Normalize names
- [ ] Write to dim_lobbyists.parquet

## Estimated Effort: 3 hours
**Target**: Dec 24, 2025
