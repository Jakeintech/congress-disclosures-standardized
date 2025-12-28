# STORY-049: Dimension Validation & SCD Type 2 Implementation

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 3 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** data analyst
**I want** dimension tables to track historical changes using SCD Type 2
**So that** I can accurately analyze member trading patterns at any point in time (e.g., "What did Republican members trade in 2023?" must use their 2023 party affiliation, not current)

## Acceptance Criteria
- **GIVEN** Member details change over time (party switch, district change due to redistricting)
- **WHEN** Dimension update process runs
- **THEN** Old record is closed with `effective_to` date and `is_current=False`
- **AND** New record is inserted with `effective_from` date and `is_current=True`
- **AND** All fact tables use SCD Type 2 lookups (point-in-time joins based on transaction_date)
- **AND** Quality checks validate SCD Type 2 integrity (no duplicate current members)

## Problem Statement

### Current Limitation: Type 1 SCD (Overwrite)
**Example**: Rep. Jeff Van Drew switched from Democrat → Republican in 2019.

**Current behavior** (SCD Type 1):
```python
# dim_members (current state)
{
    "bioguide_id": "V000133",
    "first_name": "Jeff",
    "last_name": "Van Drew",
    "party": "Republican",  # OVERWRITES old value
    "state": "NJ",
    "district": 2
}
```

**Problem**: When analyzing 2018 trades, queries show him as Republican (wrong!)

```sql
-- Query: "What stocks did Democrats trade in 2018?"
SELECT m.full_name, f.ticker, f.transaction_date
FROM fact_ptr_transactions f
JOIN dim_members m ON f.member_key = m.member_key
WHERE m.party = 'Democrat' AND f.transaction_date BETWEEN '2018-01-01' AND '2018-12-31'

-- RESULT: Jeff Van Drew is MISSING (his record shows party='Republican')
-- This is WRONG - he was a Democrat in 2018!
```

### Solution: SCD Type 2 (Historical Tracking)

**With SCD Type 2**:
```python
# dim_members (with historical versions)
[
    {
        "member_key": 1234,  # Surrogate key (version 1)
        "bioguide_id": "V000133",  # Natural key
        "first_name": "Jeff",
        "last_name": "Van Drew",
        "party": "Democrat",
        "state": "NJ",
        "district": 2,
        "effective_from": "2019-01-03",  # 116th Congress start
        "effective_to": "2019-12-19",    # Party switch date
        "is_current": False,
        "version": 1
    },
    {
        "member_key": 1235,  # Surrogate key (version 2)
        "bioguide_id": "V000133",  # Same natural key
        "first_name": "Jeff",
        "last_name": "Van Drew",
        "party": "Republican",
        "state": "NJ",
        "district": 2,
        "effective_from": "2019-12-19",  # Party switch date
        "effective_to": None,  # Still current
        "is_current": True,
        "version": 2
    }
]
```

**Correct query** (point-in-time join):
```sql
-- Query: "What stocks did Democrats trade in 2018?"
SELECT m.full_name, f.ticker, f.transaction_date
FROM fact_ptr_transactions f
JOIN dim_members m ON f.member_key = m.member_key
WHERE m.party = 'Democrat'
  AND f.transaction_date BETWEEN m.effective_from AND COALESCE(m.effective_to, '9999-12-31')
  AND f.transaction_date BETWEEN '2018-01-01' AND '2018-12-31'

-- RESULT: Jeff Van Drew's 2018 trades are INCLUDED (he was a Democrat in 2018)
-- This is CORRECT!
```

---

## Technical Design

### 1. SCD Type 2 Decision Matrix

| Dimension | SCD Type | Justification | Effective Dating |
|-----------|----------|---------------|------------------|
| **dim_members** | **Type 2** | Members change party, district (redistricting), chamber | `effective_from`, `effective_to` |
| **dim_lobbyists** | **Type 2** | Lobbyists change firms, registration status | `effective_from`, `effective_to` |
| **dim_assets** | **Type 1** | Asset descriptions rarely change meaningfully | N/A (overwrite) |
| **dim_bills** | **Type 1** | Bill metadata is static once introduced | N/A |
| **dim_dates** | **Type 0** | Date dimension never changes | N/A (static reference) |

**Focus for this story**: `dim_members` (Type 2)

---

### 2. dim_members Schema (SCD Type 2)

```python
dim_members_schema = {
    # Surrogate key (auto-increment, unique per version)
    "member_key": "INT64 PRIMARY KEY",  # e.g., 1234, 1235, 1236...

    # Natural key (business key, not unique - multiple versions per bioguide_id)
    "bioguide_id": "STRING",  # e.g., "V000133"

    # Attributes (can change over time)
    "first_name": "STRING",
    "last_name": "STRING",
    "full_name": "STRING",
    "party": "STRING",  # Can change (e.g., D → R)
    "state": "STRING",
    "district": "INT64",  # Can change (redistricting)
    "state_district": "STRING",
    "chamber": "STRING",  # Can change (House → Senate)
    "member_type": "STRING",

    # SCD Type 2 fields
    "effective_from": "DATE",  # When this version became effective
    "effective_to": "DATE",    # When this version was superseded (NULL if current)
    "is_current": "BOOLEAN",   # True only for latest version
    "version": "INT64",        # Human-readable version number (1, 2, 3...)

    # Audit fields
    "created_at": "TIMESTAMP",
    "updated_at": "TIMESTAMP",
    "source_system": "STRING"  # e.g., "house_clerk", "congress_api"
}
```

**Indexes**:
- Primary Key: `member_key` (surrogate key)
- Index: `bioguide_id + is_current` (fast lookup for current version)
- Index: `bioguide_id + effective_from + effective_to` (point-in-time queries)

---

### 3. Change Detection Logic

```python
# scripts/build_dim_members_simple.py

def update_member_dimension(new_member_data: Dict[str, Any]):
    """
    Update member dimension with SCD Type 2 logic.

    Args:
        new_member_data: New member data from source (filings, API, etc.)
    """
    bioguide_id = new_member_data['bioguide_id']
    effective_date = new_member_data['effective_from']  # e.g., congressional session start

    # Step 1: Get current version of member
    current_member = query_current_member(bioguide_id)

    if not current_member:
        # New member - insert initial record
        insert_member_record({
            **new_member_data,
            'is_current': True,
            'version': 1,
            'effective_to': None
        })
        logger.info(f"Inserted new member: {bioguide_id} (version 1)")
        return

    # Step 2: Detect changes (only track meaningful changes)
    changed_fields = detect_changes(current_member, new_member_data)

    if not changed_fields:
        # No changes - just update audit timestamp
        update_member_record(
            member_key=current_member['member_key'],
            updated_at=datetime.utcnow()
        )
        logger.info(f"No changes for member: {bioguide_id}")
        return

    # Step 3: Meaningful change detected - create new version
    logger.info(f"Changes detected for {bioguide_id}: {changed_fields}")

    # Close old record
    update_member_record(
        member_key=current_member['member_key'],
        effective_to=effective_date,
        is_current=False,
        updated_at=datetime.utcnow()
    )

    # Insert new record
    new_version = current_member['version'] + 1
    insert_member_record({
        **new_member_data,
        'is_current': True,
        'version': new_version,
        'effective_to': None
    })

    logger.info(f"Created new version for {bioguide_id}: version {new_version}")


def detect_changes(old_record: Dict, new_record: Dict) -> List[str]:
    """
    Detect meaningful changes between old and new member records.

    Returns:
        List of changed field names (e.g., ['party', 'district'])
    """
    # Fields to track for changes (ignore audit fields)
    tracked_fields = ['party', 'district', 'state', 'chamber', 'first_name', 'last_name']

    changed = []
    for field in tracked_fields:
        old_val = old_record.get(field)
        new_val = new_record.get(field)

        if old_val != new_val:
            changed.append(field)

    return changed
```

---

### 4. Fact Table SCD Type 2 Lookups

**Problem**: Fact tables have `member_key` (surrogate key), but which version?

**Solution**: Point-in-time join based on `transaction_date`

#### Building fact_ptr_transactions

```python
# scripts/build_fact_ptr_transactions.py

def get_member_key_for_transaction(bioguide_id: str, transaction_date: str) -> int:
    """
    Get correct member_key for transaction (SCD Type 2 aware).

    Args:
        bioguide_id: Natural key for member
        transaction_date: Date of transaction (e.g., '2024-01-15')

    Returns:
        member_key: Surrogate key for member version effective at transaction_date
    """
    query = f"""
    SELECT member_key
    FROM dim_members
    WHERE bioguide_id = '{bioguide_id}'
      AND '{transaction_date}' >= effective_from
      AND '{transaction_date}' < COALESCE(effective_to, '9999-12-31')
    LIMIT 1
    """

    result = execute_query(query)

    if not result:
        logger.warning(f"No member found for {bioguide_id} at {transaction_date}")
        return None

    return result[0]['member_key']


# Usage in fact builder
def build_transaction_record(transaction_data: Dict) -> Dict:
    """Build fact transaction record with SCD Type 2 member lookup."""

    # Parse transaction details
    bioguide_id = transaction_data['bioguide_id']
    transaction_date = transaction_data['transaction_date']

    # SCD Type 2 lookup - get member version effective at transaction date
    member_key = get_member_key_for_transaction(bioguide_id, transaction_date)

    if not member_key:
        logger.error(f"Failed to find member for {bioguide_id} at {transaction_date}")
        # Option 1: Use current version as fallback
        # Option 2: Skip this transaction (quality control)
        # Option 3: Create placeholder member record

    return {
        'transaction_key': generate_transaction_key(transaction_data),
        'member_key': member_key,  # Links to correct historical version
        'transaction_date': transaction_date,
        'ticker': transaction_data['ticker'],
        'amount_low': transaction_data['amount_low'],
        # ... other fields
    }
```

#### Querying with SCD Type 2

**Example Query**: "What stocks did Democrats trade in 2018?"

```sql
-- CORRECT: Point-in-time join
SELECT
    m.full_name,
    m.party,
    f.ticker,
    f.transaction_date,
    f.amount_low,
    f.amount_high
FROM fact_ptr_transactions f
JOIN dim_members m ON f.member_key = m.member_key  -- Uses correct version
WHERE m.party = 'Democrat'
  AND YEAR(f.transaction_date) = 2018

-- Result: Returns correct results because f.member_key links to
-- the member version that was effective at f.transaction_date
```

**Example Query**: "Track Jeff Van Drew's trades across party switch"

```sql
SELECT
    m.party,
    m.effective_from,
    m.effective_to,
    f.transaction_date,
    f.ticker,
    f.transaction_type
FROM fact_ptr_transactions f
JOIN dim_members m ON f.member_key = m.member_key
WHERE m.bioguide_id = 'V000133'
ORDER BY f.transaction_date

-- Result:
-- | party    | effective_from | effective_to | transaction_date | ticker | type     |
-- |----------|----------------|--------------|------------------|--------|----------|
-- | Democrat | 2019-01-03     | 2019-12-19   | 2019-03-15       | AAPL   | Purchase |
-- | Democrat | 2019-01-03     | 2019-12-19   | 2019-11-02       | MSFT   | Sale     |
-- | Republican | 2019-12-19   | NULL         | 2020-02-10       | TSLA   | Purchase |
-- | Republican | 2019-12-19   | NULL         | 2024-06-20       | NVDA   | Purchase |
```

---

### 5. Data Quality Checks for SCD Type 2

**Soda Quality Checks** (`soda/checks/gold/dim_members_scd2.yml`):

```yaml
# SCD Type 2 Integrity Checks
checks for dim_members:
  # No duplicate current members (only one is_current=True per bioguide_id)
  - duplicate_count(bioguide_id) where is_current = true = 0:
      name: No duplicate current members
      fail:
        when duplicate_count > 0

  # All current members have effective_to = NULL
  - failed rows:
      name: Current members have NULL effective_to
      fail query: |
        SELECT COUNT(*)
        FROM dim_members
        WHERE is_current = true AND effective_to IS NOT NULL
      fail:
        when fail count > 0

  # No gaps in effective date ranges (effective_to of version N = effective_from of version N+1)
  - failed rows:
      name: No gaps in date ranges
      fail query: |
        SELECT COUNT(*)
        FROM dim_members m1
        JOIN dim_members m2 ON m1.bioguide_id = m2.bioguide_id
          AND m1.version + 1 = m2.version
        WHERE m1.effective_to != m2.effective_from
      fail:
        when fail count > 0

  # effective_from < effective_to (logical date range)
  - failed rows:
      name: Effective dates are logical
      fail query: |
        SELECT COUNT(*)
        FROM dim_members
        WHERE effective_to IS NOT NULL AND effective_from >= effective_to
      fail:
        when fail count > 0

  # All members have version >= 1
  - min(version) >= 1:
      name: All members have valid version number

# Fact table referential integrity
checks for fact_ptr_transactions:
  - failed rows:
      name: All member_keys exist in dim_members
      fail query: |
        SELECT COUNT(*)
        FROM fact_ptr_transactions f
        LEFT JOIN dim_members m ON f.member_key = m.member_key
        WHERE m.member_key IS NULL
      fail:
        when fail count > 0

  # Transaction date is within member's effective date range
  - failed rows:
      name: Transaction dates match member effective dates
      fail query: |
        SELECT COUNT(*)
        FROM fact_ptr_transactions f
        JOIN dim_members m ON f.member_key = m.member_key
        WHERE f.transaction_date < m.effective_from
          OR f.transaction_date >= COALESCE(m.effective_to, '9999-12-31')
      fail:
        when fail count > 0
```

---

## Implementation Tasks

### Phase 1: Update dim_members Schema (1 hour)
- [ ] Add SCD Type 2 fields to `build_dim_members_simple.py`:
  - `effective_from: DATE`
  - `effective_to: DATE`
  - `is_current: BOOLEAN`
  - `version: INT64`
- [ ] Update Parquet schema definition
- [ ] Backfill existing records with default values:
  - `effective_from = '1900-01-01'` (unknown start date)
  - `effective_to = NULL` (still current)
  - `is_current = True`
  - `version = 1`

### Phase 2: Implement Change Detection (1 hour)
- [ ] Add `detect_changes()` function (compare old vs new member data)
- [ ] Add `update_member_dimension()` function (SCD Type 2 logic)
- [ ] Handle edge cases:
  - First-time member (insert version 1)
  - No changes (update audit timestamp only)
  - Meaningful change (close old record, insert new version)

### Phase 3: Update Fact Builders (30 min)
- [ ] Update `build_fact_ptr_transactions.py`:
  - Implement `get_member_key_for_transaction()` (point-in-time lookup)
  - Replace direct member_key assignment with SCD Type 2 lookup
- [ ] Update other fact builders:
  - `build_fact_asset_holdings.py`
  - `build_fact_gifts_travel.py`
  - `build_fact_positions.py`

### Phase 4: Add Quality Checks (30 min)
- [ ] Create `soda/checks/gold/dim_members_scd2.yml` (8 checks)
- [ ] Integrate into `run_soda_checks` Lambda
- [ ] Test failure scenarios:
  - Duplicate current members
  - Gaps in date ranges
  - Invalid date ranges

---

## Testing Strategy

### Unit Tests (8 tests)
```python
# tests/unit/scripts/test_dim_members_scd2.py

def test_detect_changes_party_switch():
    """Test that party changes are detected."""
    old = {'bioguide_id': 'V000133', 'party': 'Democrat', 'district': 2}
    new = {'bioguide_id': 'V000133', 'party': 'Republican', 'district': 2}

    changed = detect_changes(old, new)
    assert 'party' in changed
    assert 'district' not in changed

def test_detect_changes_redistricting():
    """Test that district changes are detected."""
    old = {'bioguide_id': 'A000055', 'party': 'Republican', 'district': 5}
    new = {'bioguide_id': 'A000055', 'party': 'Republican', 'district': 7}

    changed = detect_changes(old, new)
    assert 'district' in changed
    assert 'party' not in changed

def test_update_member_new_member():
    """Test inserting a new member (version 1)."""
    new_member = {
        'bioguide_id': 'X000999',
        'party': 'Democrat',
        'effective_from': '2025-01-03'
    }

    update_member_dimension(new_member)

    # Verify record created
    member = query_current_member('X000999')
    assert member['version'] == 1
    assert member['is_current'] == True
    assert member['effective_to'] == None

def test_update_member_no_changes():
    """Test updating member with no changes (audit timestamp only)."""
    # Member already exists, no changes
    update_member_dimension({'bioguide_id': 'A000055', 'party': 'Republican'})

    # Verify version not incremented
    member = query_current_member('A000055')
    assert member['version'] == 1

def test_update_member_party_switch():
    """Test party switch creates new version (SCD Type 2)."""
    # Existing member
    assert query_current_member('V000133')['party'] == 'Democrat'

    # Party switch
    update_member_dimension({
        'bioguide_id': 'V000133',
        'party': 'Republican',
        'effective_from': '2019-12-19'
    })

    # Verify old record closed
    old_version = query_member_version('V000133', version=1)
    assert old_version['is_current'] == False
    assert old_version['effective_to'] == '2019-12-19'

    # Verify new record created
    new_version = query_current_member('V000133')
    assert new_version['version'] == 2
    assert new_version['party'] == 'Republican'
    assert new_version['is_current'] == True

def test_get_member_key_point_in_time():
    """Test SCD Type 2 lookup returns correct version for transaction date."""
    # Jeff Van Drew: Democrat (2019-01-03 to 2019-12-19), Republican (2019-12-19 to present)

    # Transaction in 2019-03 (Democrat era)
    member_key = get_member_key_for_transaction('V000133', '2019-03-15')
    member = query_member_by_key(member_key)
    assert member['party'] == 'Democrat'

    # Transaction in 2020-02 (Republican era)
    member_key = get_member_key_for_transaction('V000133', '2020-02-10')
    member = query_member_by_key(member_key)
    assert member['party'] == 'Republican'

def test_scd2_quality_check_no_duplicate_current():
    """Test quality check: no duplicate current members."""
    # Artificially create duplicate current members
    create_duplicate_current_member('A000055')

    # Run quality checks
    soda_result = run_soda_checks()

    # Verify check failed
    assert soda_result['failed'] > 0
    assert 'No duplicate current members' in soda_result['failed_checks']

def test_scd2_quality_check_date_range_gaps():
    """Test quality check: no gaps in date ranges."""
    # Create gap: version 1 ends 2020-01-01, version 2 starts 2020-01-15 (14-day gap)
    create_member_with_date_gap('B000111')

    # Run quality checks
    soda_result = run_soda_checks()

    # Verify check failed
    assert 'No gaps in date ranges' in soda_result['failed_checks']
```

### Integration Test (2 tests)
```python
# tests/integration/test_scd2_e2e.py

def test_fact_transaction_lookup_scd2():
    """End-to-end test: fact transaction uses correct member version."""
    # Build dim_members with SCD Type 2
    build_dim_members()

    # Build fact_ptr_transactions (should lookup correct member version)
    build_fact_ptr_transactions()

    # Query: Jeff Van Drew's 2019-03 transaction (should link to Democrat version)
    result = query("""
        SELECT m.party
        FROM fact_ptr_transactions f
        JOIN dim_members m ON f.member_key = m.member_key
        WHERE m.bioguide_id = 'V000133'
          AND f.transaction_date = '2019-03-15'
    """)

    assert result[0]['party'] == 'Democrat'

def test_scd2_quality_checks_pass():
    """Test that SCD Type 2 quality checks pass for well-formed data."""
    # Build dimension with SCD Type 2
    build_dim_members()

    # Run quality checks
    soda_result = run_soda_checks()

    # Verify all SCD Type 2 checks passed
    assert soda_result['failed'] == 0
    assert 'No duplicate current members' in soda_result['passed_checks']
    assert 'No gaps in date ranges' in soda_result['passed_checks']
```

---

## Estimated Effort: 3 hours
- 1 hour: Schema updates + backfill
- 1 hour: Change detection logic
- 30 min: Fact builder updates (SCD Type 2 lookups)
- 30 min: Quality checks + testing

---

## Benefits

1. **Historical Accuracy**: Queries always use member attributes effective at transaction date
2. **Party Analysis**: Correctly attribute trades to member's party at time of trade
3. **Redistricting Support**: Track district changes over time
4. **Audit Trail**: Complete history of member attribute changes
5. **Regulatory Compliance**: Can prove member affiliation at any point in time

---

## Dependencies
- **Requires**: dim_members dimension exists (Sprint 2, STORY-016)
- **Builds on**: STORY-054 (extraction versioning) for overall data lineage strategy
- **Enables**: Accurate historical analysis in Gold aggregates

---

## AI Development Notes
**Baseline**: SCD Type 2 pattern (Kimball methodology)
**Pattern**: Surrogate key + effective dating + is_current flag
**Files to Modify**:
- scripts/build_dim_members_simple.py:80-150 (add SCD Type 2 logic)
- scripts/build_fact_ptr_transactions.py:200-250 (add SCD Type 2 lookups)
- soda/checks/gold/dim_members_scd2.yml (new file, 8 checks)

**Token Budget**: 2,500 tokens

**Acceptance Criteria Verification**:
1. ✅ Old record closed with `effective_to` and `is_current=False`
2. ✅ New record inserted with `effective_from` and `is_current=True`
3. ✅ Fact tables use SCD Type 2 lookups (point-in-time joins)
4. ✅ Quality checks validate SCD Type 2 integrity

**Target**: Sprint 3, Day 3 (January 1, 2026)

---

**NOTE**: SCD Type 2 is critical for historical accuracy. Without it, queries like "What did Democrats trade in 2018?" would be wrong if members switched parties after 2018. See `docs/agile/DATA_QUALITY_AND_VERSIONING_STRATEGY.md` for full strategy.
