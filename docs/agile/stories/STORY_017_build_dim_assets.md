# STORY-017: Create build_dim_assets Lambda Wrapper

**Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 5 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** data engineer
**I want** dim_assets dimension table
**So that** we have normalized asset names with tickers

## Acceptance Criteria
- **GIVEN** Transactions with asset names ("NVIDIA CORP")
- **WHEN** Lambda executes
- **THEN** Normalizes names, looks up tickers
- **AND** Classifies asset types (stock, bond, fund)
- **AND** Maps to industries (GICS sectors)

## Technical Tasks
- [ ] Extract unique asset names from Silver
- [ ] Normalize names (NVIDIA CORP → NVIDIA)
- [ ] Lookup tickers (manual mapping or API)
- [ ] Classify asset types
- [ ] Map to GICS sectors
- [ ] Write to Parquet

## Estimated Effort: 5 hours
**Target**: Dec 23, 2025
