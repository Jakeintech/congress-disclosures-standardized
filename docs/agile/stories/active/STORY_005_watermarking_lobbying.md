# STORY-005: Implement Watermarking in check_lobbying_updates

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 2 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** platform operator
**I want** LDA lobbying watermarking
**So that** we only fetch new quarterly filings

## Acceptance Criteria

### Scenario 1: Current quarter already ingested
- **GIVEN** Bronze has complete Q4 2024 data
- **WHEN** check_lobbying_updates executes for Q4 2024
- **THEN** return `{"has_new_filings": false}`

### Scenario 2: New quarter available
- **GIVEN** Q1 2025 filings now available
- **AND** Bronze has no Q1 2025 data
- **WHEN** check_lobbying_updates executes
- **THEN** return `{"has_new_filings": true, "filing_quarter": "Q1-2025"}`

### Scenario 3: Year/Quarter outside 5-year lookback
- **GIVEN** Request to check Q1 2015 (outside 5-year window)
- **WHEN** check_lobbying_updates executes
- **THEN** return `{"has_new_filings": false, "reason": "outside_lookback_window"}`
- **AND** Log "Q1 2015 outside 5-year lookback window"

## Technical Tasks
- [ ] Validate year/quarter is within 5-year lookback window
- [ ] Check Bronze manifest for latest quarter
- [ ] Query LDA database for current quarter
- [ ] Compare filing counts
- [ ] Return has_new_filings boolean

## Implementation
```python
from datetime import datetime

def lambda_handler(event, context):
    year = event['year']
    quarter = event['quarter']

    # Validate year is within 5-year lookback window
    CURRENT_YEAR = datetime.now().year
    LOOKBACK_YEARS = 5
    MIN_YEAR = CURRENT_YEAR - LOOKBACK_YEARS

    if year < MIN_YEAR:
        logger.info(f"Year {year} outside 5-year lookback window (>= {MIN_YEAR})")
        return {
            'has_new_filings': False,
            'reason': 'outside_lookback_window',
            'valid_year_range': f"{MIN_YEAR}-{CURRENT_YEAR}"
        }

    # Check Bronze
    bronze_key = f"bronze/lobbying/lda/year={year}/quarter={quarter}/manifest.json"
    try:
        s3.head_object(Bucket=bucket, Key=bronze_key)
        return {'has_new_filings': False}
    except ClientError:
        return {'has_new_filings': True}
```

**Note**: Once data is ingested, it's retained permanently. The 5-year window only applies to the initial load scope.

## Estimated Effort: 2 hours

**Target**: Dec 17, 2025
