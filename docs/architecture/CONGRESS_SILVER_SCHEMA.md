# Congress.gov Silver Layer Schema

**Purpose**: Define normalized Parquet table schemas for the Silver layer, transforming raw Bronze JSON into queryable analytics tables.

**Design Principles**:
- **SCD Type 2**: Member history tracked with `effective_date`, `end_date`, `is_current`
- **Composite Keys**: Bills use `{congress}-{bill_type}-{bill_number}` format
- **Hive Partitioning**: Tables partitioned for query efficiency
- **CDC**: All tables include `source_last_modified` for change detection

---

## Table Index

| Table | Type | Primary Key | Partitions | SCD |
|-------|------|-------------|------------|-----|
| [dim_member](#dim_member) | Dimension | `member_sk` (surrogate) | `chamber`, `is_current` | Type 2 |
| [dim_bill](#dim_bill) | Dimension | `bill_id` | `congress`, `bill_type` | Type 1 |
| [bill_actions](#bill_actions) | Fact | `bill_id`, `action_date`, `action_seq` | `congress` | Append |
| [bill_cosponsors](#bill_cosponsors) | Fact | `bill_id`, `cosponsor_bioguide_id` | `congress` | Upsert |
| [house_vote_members](#house_vote_members) | Fact | `vote_id`, `bioguide_id` | `congress`, `session` | Upsert |
| [dim_committee](#dim_committee) | Dimension | `committee_code` | `chamber` | Type 1 |

---

## dim_member

**Description**: Congressional members with SCD Type 2 history for party/district changes.

**S3 Path Pattern**:
```
silver/congress/dim_member/chamber={chamber}/is_current={true|false}/part-{hash}.parquet
```

**Schema**:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `member_sk` | `string` | No | Surrogate key (UUID) |
| `bioguide_id` | `string` | No | Natural key (bioguide ID) |
| `first_name` | `string` | No | First name |
| `last_name` | `string` | No | Last name |
| `party` | `string` | No | Party code (R, D, I) |
| `state` | `string` | No | State abbreviation |
| `district` | `int32` | Yes | District number (null for senators) |
| `chamber` | `string` | No | `house` or `senate` |
| `depiction_url` | `string` | Yes | Official portrait URL |
| `effective_date` | `date` | No | SCD2: When record became effective |
| `end_date` | `date` | Yes | SCD2: When record was superseded (null if current) |
| `is_current` | `boolean` | No | SCD2: True if current record |
| `source_last_modified` | `timestamp` | No | Congress.gov API update time |
| `silver_ingest_ts` | `timestamp` | No | Silver layer ingestion time |

**Example Row**:
```json
{
  "member_sk": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "bioguide_id": "P000197",
  "first_name": "Nancy",
  "last_name": "Pelosi",
  "party": "D",
  "state": "CA",
  "district": 11,
  "chamber": "house",
  "depiction_url": "https://bioguide.congress.gov/...",
  "effective_date": "2023-01-03",
  "end_date": null,
  "is_current": true,
  "source_last_modified": "2025-12-04T10:00:00Z",
  "silver_ingest_ts": "2025-12-04T15:20:00Z"
}
```

**SCD Type 2 Logic**:
1. On first ingestion: Create record with `effective_date=today`, `is_current=True`
2. On update with attribute change (party, state, district):
   - Close old record: `end_date=today`, `is_current=False`
   - Insert new record: `effective_date=today`, `is_current=True`
3. On update with no changes: Skip (no action)

---

## dim_bill

**Description**: Bill metadata (normalized from Congress.gov bill endpoint).

**S3 Path Pattern**:
```
silver/congress/dim_bill/congress={congress}/bill_type={bill_type}/part-0000.parquet
```

**Schema**:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `bill_id` | `string` | No | Composite key: `{congress}-{bill_type}-{bill_number}` |
| `congress` | `int32` | No | Congress number (e.g., 118) |
| `bill_type` | `string` | No | Bill type (hr, s, hjres, etc.) |
| `bill_number` | `int32` | No | Bill number |
| `title` | `string` | No | Official bill title |
| `title_short` | `string` | Yes | Short title (if available) |
| `introduced_date` | `date` | No | Introduction date |
| `origin_chamber` | `string` | No | Originating chamber |
| `sponsor_bioguide_id` | `string` | Yes | Primary sponsor bioguide ID |
| `sponsor_name` | `string` | Yes | Primary sponsor name |
| `policy_area` | `string` | Yes | Primary policy area |
| `latest_action_date` | `date` | Yes | Date of most recent action |
| `latest_action_text` | `string` | Yes | Text of most recent action |
| `cosponsors_count` | `int32` | Yes | Number of cosponsors |
| `source_last_modified` | `timestamp` | No | Congress.gov API update time |
| `silver_ingest_ts` | `timestamp` | No | Silver layer ingestion time |

**Example Row**:
```json
{
  "bill_id": "118-hr-1",
  "congress": 118,
  "bill_type": "hr",
  "bill_number": 1,
  "title": "Lower Energy Costs Act",
  "introduced_date": "2023-01-09",
  "origin_chamber": "House",
  "sponsor_bioguide_id": "S001213",
  "sponsor_name": "Rep. Stauber, Pete",
  "policy_area": "Energy",
  "latest_action_date": "2023-03-30",
  "latest_action_text": "Received in the Senate...",
  "cosponsors_count": 0,
  "source_last_modified": "2025-12-04T10:00:00Z",
  "silver_ingest_ts": "2025-12-04T15:20:00Z"
}
```

---

## bill_actions

**Description**: Legislative timeline events for bills.

**S3 Path Pattern**:
```
silver/congress/bill_actions/congress={congress}/part-0000.parquet
```

**Schema**:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `bill_id` | `string` | No | Bill composite key |
| `action_date` | `date` | No | Action date |
| `action_seq` | `int32` | No | Sequence within day |
| `action_text` | `string` | No | Action description |
| `action_type` | `string` | Yes | Action type code |
| `action_code` | `string` | Yes | Action code (e.g., H11100) |
| `source_system` | `string` | Yes | Source system name |
| `silver_ingest_ts` | `timestamp` | No | Silver layer ingestion time |

---

## bill_cosponsors

**Description**: Bill cosponsorship records.

**S3 Path Pattern**:
```
silver/congress/bill_cosponsors/congress={congress}/part-0000.parquet
```

**Schema**:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `bill_id` | `string` | No | Bill composite key |
| `cosponsor_bioguide_id` | `string` | No | Cosponsor bioguide ID |
| `cosponsor_name` | `string` | No | Cosponsor full name |
| `sponsorship_date` | `date` | No | Date of cosponsorship |
| `is_original_cosponsor` | `boolean` | No | Original cosponsor flag |
| `party` | `string` | Yes | Cosponsor party |
| `state` | `string` | Yes | Cosponsor state |
| `silver_ingest_ts` | `timestamp` | No | Silver layer ingestion time |

---

## house_vote_members

**Description**: Individual member votes on House roll calls.

**S3 Path Pattern**:
```
silver/congress/house_vote_members/congress={congress}/session={session}/part-0000.parquet
```

**Schema**:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `vote_id` | `string` | No | Composite key: `{congress}-{session}-{roll_call}` |
| `bioguide_id` | `string` | No | Member bioguide ID |
| `member_name` | `string` | No | Member name |
| `party` | `string` | No | Party at time of vote |
| `state` | `string` | No | State |
| `vote_cast` | `string` | No | Vote: Yea, Nay, Present, Not Voting |
| `vote_date` | `date` | No | Vote date |
| `question` | `string` | No | Vote question |
| `result` | `string` | No | Vote result |
| `bill_id` | `string` | Yes | Related bill (if any) |
| `silver_ingest_ts` | `timestamp` | No | Silver layer ingestion time |

---

## dim_committee

**Description**: Congressional committees and subcommittees.

**S3 Path Pattern**:
```
silver/congress/dim_committee/chamber={chamber}/part-0000.parquet
```

**Schema**:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `committee_code` | `string` | No | System code (e.g., hsif00) |
| `name` | `string` | No | Committee name |
| `chamber` | `string` | No | house, senate, or joint |
| `committee_type` | `string` | No | Standing, Select, etc. |
| `parent_committee_code` | `string` | Yes | Parent code (for subcommittees) |
| `url` | `string` | Yes | Committee website URL |
| `source_last_modified` | `timestamp` | No | Congress.gov API update time |
| `silver_ingest_ts` | `timestamp` | No | Silver layer ingestion time |

---

## Partitioning Strategy

**Query Optimization**:
- `congress`: Most queries filter by Congress number
- `chamber`: Members/committees queried by chamber
- `bill_type`: Bill queries by type (hr, s, etc.)
- `is_current`: Member queries usually want current records only

**File Size Targets**:
- Target 50-200 MB per Parquet file
- Partition to achieve ~100k-1M rows per file

---

**Last Updated**: 2025-12-04
