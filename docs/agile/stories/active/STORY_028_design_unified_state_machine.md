# STORY-028: Design Unified State Machine JSON

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 5 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** platform architect
**I want** unified state machine JSON design
**So that** we replace 4 siloed pipelines with 1 orchestrated flow

## Acceptance Criteria
- **GIVEN** New state machine design
- **WHEN** I review JSON structure
- **THEN** Has 6 phases: UpdateDetection, Bronze, Silver, Gold, Quality, Publish
- **AND** Uses Parallel states for concurrent operations
- **AND** Has proper error handling (Catch, Retry)
- **AND** References all 47 Lambda ARNs

## Technical Tasks
- [ ] Create `state_machines/congress_data_platform.json`
- [ ] Design state hierarchy
- [ ] Define Choice states for conditional execution
- [ ] Add year range input validation (5-year lookback for initial load)
- [ ] Add Parallel states for Bronze/Silver/Gold
- [ ] Configure Map states with MaxConcurrency=10
- [ ] Add Catch/Retry blocks
- [ ] Document state transitions

## Implementation Structure
```json
{
  "Comment": "Congress Data Platform - Unified Pipeline",
  "StartAt": "ValidateInput",
  "States": {
    "ValidateInput": {
      "Type": "Pass",
      "Comment": "Validate year range (5-year lookback for initial load)",
      "Parameters": {
        "execution_type.$": "$.execution_type",
        "mode.$": "$.mode",
        "valid_year_range": {
          "min_year": 2020,
          "max_year": 2025,
          "comment": "5-year lookback window for initial ingestion"
        }
      },
      "Next": "CheckForUpdates"
    },
    "CheckForUpdates": {"Type": "Parallel"},
    "BronzeIngestion": {"Type": "Parallel"},
    "SilverTransformation": {"Type": "Parallel"},
    "GoldDimensions": {"Type": "Parallel"},
    "GoldFacts": {"Type": "Task"},
    "GoldAggregates": {"Type": "Parallel"},
    "RunSodaChecks": {"Type": "Task"},
    "PublishMetrics": {"Type": "Task"}
  }
}
```

**Important Design Notes**:
1. **5-Year Lookback Window**: Initial ingestion only processes data from (current_year - 5) to current_year
2. **Data Retention**: Once ingested, data is retained permanently (no deletion)
3. **Year Validation**: Each check function (House FD, Congress, Lobbying) validates year range
4. **Incremental Updates**: After initial load, daily incremental updates fetch latest data only

## Estimated Effort: 5 hours
**Target**: Dec 30, 2025
