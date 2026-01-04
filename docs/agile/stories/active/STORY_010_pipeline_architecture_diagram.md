# STORY-010: Create Pipeline Architecture Mermaid Diagram

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 2 | **Priority**: P2 | **Status**: To Do

## User Story
**As a** developer
**I want** a visual pipeline architecture diagram
**So that** I understand the overall system design

## Acceptance Criteria

### Scenario 1: Diagram shows all components
- **GIVEN** Mermaid diagram in `docs/agile/diagrams/pipeline_architecture.md`
- **WHEN** I view the diagram
- **THEN** It shows: EventBridge, Step Functions, Lambda, S3, SQS, SNS
- **AND** Data flow from triggers → Bronze → Silver → Gold
- **AND** All 29 Lambda functions categorized by phase

## Technical Tasks
- [x] Create `docs/agile/diagrams/` directory
- [x] Design Mermaid diagram structure
- [x] Include all AWS services
- [x] Show data flow with arrows
- [x] Add color coding by layer (Bronze=blue, Silver=green, Gold=yellow)
- [x] Include legend

## Mermaid Diagram Structure
```mermaid
graph TB
    subgraph Triggers
        EB[EventBridge Daily 6AM]
        Manual[Manual Execution]
    end

    subgraph Orchestration
        SF[Step Functions]
    end

    subgraph Bronze Layer
        L1[house_fd_ingest_zip]
        L2[congress_api_ingest]
        L3[lda_ingest_filings]
        S3B[(S3 Bronze)]
    end

    subgraph Silver Layer
        L4[extract_document]
        L5[extract_structured]
        SQS[SQS Queue]
        S3S[(S3 Silver)]
    end

    subgraph Gold Layer
        L6[build_dimensions]
        L7[build_facts]
        L8[build_aggregates]
        S3G[(S3 Gold)]
    end

    subgraph Quality
        L9[run_soda_checks]
        SNS[SNS Alerts]
    end

    EB --> SF
    Manual --> SF
    SF --> L1 & L2 & L3
    L1 --> S3B
    S3B --> L4
    L4 --> SQS
    SQS --> L5
    L5 --> S3S
    S3S --> L6
    L6 --> L7
    L7 --> L8
    L8 --> S3G
    S3G --> L9
    L9 --> SNS
```

## Estimated Effort: 2 hours

**Target**: Dec 19, 2025
