# STORY-004: Implement Watermarking in check_congress_updates

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 2 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** platform operator
**I want** Congress.gov API watermarking
**So that** we only fetch new bills/members

## Acceptance Criteria

### Scenario 1: No new data since last check
- **GIVEN** Last fetch timestamp = "2025-12-14T00:00:00Z"
- **AND** Congress.gov API has no new data since that time
- **WHEN** check_congress_updates executes
- **THEN** return `{"has_new_data": false}`

### Scenario 2: New data available
- **GIVEN** Last fetch timestamp = "2025-12-13T00:00:00Z"
- **AND** API has 15 new bills since that time
- **WHEN** check_congress_updates executes
- **THEN** return `{"has_new_data": true, "bills_count": 15}`

### Scenario 3: First ingestion (5-year lookback)
- **GIVEN** No prior ingestion (fresh system)
- **WHEN** check_congress_updates executes
- **THEN** Set fromDateTime to 5 years ago (2020-01-01 for year 2025)
- **AND** Fetch only bills from last 5 years
- **AND** Return `{"has_new_data": true, "is_initial_load": true}`

## Technical Tasks
- [ ] Validate if first ingestion (no watermark exists)
- [ ] If first ingestion: Set fromDateTime to (current_year - 5) + "-01-01"
- [ ] If incremental: Use last fetch timestamp from S3 metadata
- [ ] Query Congress.gov API: `/v3/bill?fromDateTime={timestamp}`
- [ ] Count results
- [ ] Compare with last fetch
- [ ] Update watermark after successful ingestion

## Implementation
```python
from datetime import datetime

def lambda_handler(event, context):
    # Read last watermark from S3 (returns None if not exists)
    last_fetch = read_watermark('congress_bills')

    # First ingestion: Use 5-year lookback
    if last_fetch is None:
        CURRENT_YEAR = datetime.now().year
        LOOKBACK_YEARS = 5
        from_date = f"{CURRENT_YEAR - LOOKBACK_YEARS}-01-01"
        is_initial_load = True
        logger.info(f"First ingestion: fetching from {from_date} (5-year window)")
    else:
        from_date = last_fetch
        is_initial_load = False
        logger.info(f"Incremental update: fetching from {from_date}")

    # Query API
    url = f"{BASE_URL}/v3/bill?fromDateTime={from_date}"
    response = requests.get(url, headers={'X-Api-Key': API_KEY})

    new_count = len(response.json()['bills'])

    return {
        'has_new_data': new_count > 0,
        'bills_count': new_count,
        'is_initial_load': is_initial_load,
        'from_date': from_date
    }
```

**Note**: Once data is ingested, it's retained permanently. The 5-year window only applies to the initial load, not to data retention.

## Estimated Effort: 2 hours

**Target**: Dec 17, 2025
