# STORY-029: Implement Bronze Ingestion Phase

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 3 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** data engineer
**I want** Bronze ingestion phase in state machine
**So that** all 3 sources ingest in parallel

## Acceptance Criteria
- **GIVEN** State machine Bronze phase
- **WHEN** Execution reaches Bronze
- **THEN** Runs 3 Lambdas in parallel (House FD, Congress, Lobbying)
- **AND** Continues only when all complete

## Technical Tasks
- [ ] Add BronzeIngestion Parallel state
- [ ] Add branches for House FD, Congress, Lobbying
- [ ] Configure Lambda ARNs
- [ ] Add error handling
- [ ] Test parallel execution

## Estimated Effort: 3 hours
**Target**: Dec 30, 2025
