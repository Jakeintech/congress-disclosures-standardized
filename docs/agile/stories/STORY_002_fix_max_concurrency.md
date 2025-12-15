# STORY-002: Fix MaxConcurrency in State Machines

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 1 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** platform operator
**I want** MaxConcurrency set to 10 (not 1) in Map states
**So that** PDF extraction is 10x faster (4 hours vs 41 hours)

## Acceptance Criteria

### Scenario 1: Map state processes 10 items concurrently
- **GIVEN** ExtractDocumentsMap state with 5,000 messages
- **WHEN** MaxConcurrency = 10
- **THEN** 10 Lambda invocations run in parallel
- **AND** Total time ~4 hours (vs 41 hours with MaxConcurrency=1)

## Technical Tasks
- [ ] Update `state_machines/house_fd_pipeline.json` line 110
- [ ] Change `"MaxConcurrency": 1` to `"MaxConcurrency": 10`
- [ ] Update Terraform template substitution
- [ ] Deploy state machine
- [ ] Test with 100 messages (verify 10 concurrent)

## Test Requirements
```python
def test_map_state_concurrency():
    # Parse state machine JSON
    # Assert MaxConcurrency == 10
    pass
```

## Estimated Effort
- Implementation: 10 minutes
- Testing: 20 minutes
- **Total**: 30 minutes

**Target**: Dec 16, 2025 (Sprint 1, Day 1)
