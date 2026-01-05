# STORY-011: Create Data Flow Mermaid Diagram

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 2 | **Priority**: P2 | **Status**: To Do

## User Story
**As a** data engineer
**I want** a Bronze → Silver → Gold data flow diagram
**So that** I understand data transformations

## Acceptance Criteria
- **GIVEN** Mermaid diagram showing medallion architecture
- **WHEN** I view it
- **THEN** Shows data flow from source → Bronze → Silver → Gold
- **AND** Indicates file formats (ZIP, PDF, Parquet, JSON)
- **AND** Shows transformations at each layer

## Technical Tasks
- [x] Create data flow Mermaid diagram
- [x] Show all data sources (House Clerk, Congress.gov, LDA)
- [x] Indicate data volumes (5K PDFs, 100K transactions)
- [x] Add sample schemas at each layer

## Implementation Notes
- **Created**: `docs/DATA_FLOW_DIAGRAM.md` - Comprehensive medallion architecture diagram
- **Features**:
  - Complete Bronze → Silver → Gold data flow
  - All 3 data sources: House Clerk, Congress.gov API, Senate LDA
  - Data volumes: ~5K PDFs/year, ~100K transactions, ~75K filings
  - File formats at each layer: ZIP → PDF → Parquet → JSON
  - Detailed schemas for all major tables
  - Transformation details and processing times
  - Quality gates between layers
  - Cost breakdown (~$6.50/month)
  - Access patterns for API and research use cases
- **Updated**: `docs/DIAGRAMS.md` - Added reference to new diagram

## Estimated Effort: 2 hours
**Target**: Dec 19, 2025
