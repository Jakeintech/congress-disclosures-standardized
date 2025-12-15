# STORY-016: Create build_dim_members Lambda Wrapper

**Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 5 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** data engineer
**I want** dim_members dimension table builder Lambda
**So that** Gold layer has member master data

## Acceptance Criteria
- **GIVEN** Silver filings with member names
- **WHEN** Lambda executes
- **THEN** Creates dim_members.parquet with SCD Type 2
- **AND** Fuzzy matches names to Congress.gov data
- **AND** Tracks party changes over time

## Technical Tasks
- [ ] Create Lambda wrapper for `scripts/build_dim_members_simple.py`
- [ ] Implement SCD Type 2 logic (expire old rows, create new rows on change)
- [ ] Add fuzzy name matching
- [ ] Package with pandas/pyarrow layer
- [ ] Write unit tests
- [ ] Deploy via Terraform

## Implementation
```python
def lambda_handler(event, context):
    from build_dim_members_simple import main
    result = main(rebuild=event.get('rebuild', False))
    return {'statusCode': 200, 'body': result}
```

## Estimated Effort: 5 hours
**Target**: Dec 23, 2025
