# Congress.gov S3 Bronze Layer Schema

**Purpose**: Define S3 prefix structure with Hive partitioning for all Congress.gov API entities in the Bronze layer.

**Design Principles**:
- **Immutability**: Bronze stores byte-for-byte raw API responses
- **Hive Partitioning**: All entities use `key=value` partition format for query efficiency
- **Compression**: All JSON files stored with gzip compression (`.json.gz`)
- **Deduplication**: Entity IDs in filename prevent duplicates within partition
- **Metadata**: S3 object metadata tracks ingestion provenance

---

## Bucket Structure

```
s3://congress-disclosures-standardized/bronze/congress/
│
├── member/                                    # Congressional members (House & Senate)
│   ├── chamber={house,senate}/
│   │   └── ingest_date=YYYY-MM-DD/
│   │       ├── {bioguide_id}.json.gz
│   │       └── ...
│
├── bill/                                      # Legislation (all types)
│   ├── congress=118/
│   │   ├── bill_type={hr,s,hjres,sjres,hconres,sconres,hres,sres}/
│   │   │   └── ingest_date=YYYY-MM-DD/
│   │   │       ├── {bill_number}.json.gz
│   │   │       └── ...
│
├── bill_actions/                              # Bill action timeline
│   ├── congress=118/
│   │   ├── bill_type={hr,s,...}/
│   │   │   └── ingest_date=YYYY-MM-DD/
│   │   │       ├── {bill_number}_actions.json.gz
│   │   │       └── ...
│
├── bill_cosponsors/                           # Bill cosponsorship records
│   ├── congress=118/
│   │   ├── bill_type={hr,s,...}/
│   │   │   └── ingest_date=YYYY-MM-DD/
│   │   │       ├── {bill_number}_cosponsors.json.gz
│   │   │       └── ...
│
├── bill_committees/                           # Committee referrals
│   ├── congress=118/
│   │   ├── bill_type={hr,s,...}/
│   │   │   └── ingest_date=YYYY-MM-DD/
│   │   │       ├── {bill_number}_committees.json.gz
│   │   │       └── ...
│
├── bill_subjects/                             # Legislative subjects (policy areas)
│   ├── congress=118/
│   │   ├── bill_type={hr,s,...}/
│   │   │   └── ingest_date=YYYY-MM-DD/
│   │   │       ├── {bill_number}_subjects.json.gz
│   │   │       └── ...
│
├── bill_titles/                               # All bill titles (short, long, official)
│   ├── congress=118/
│   │   ├── bill_type={hr,s,...}/
│   │   │   └── ingest_date=YYYY-MM-DD/
│   │   │       ├── {bill_number}_titles.json.gz
│   │   │       └── ...
│
├── bill_summaries/                            # Bill summaries (CRS)
│   ├── congress=118/
│   │   ├── bill_type={hr,s,...}/
│   │   │   └── ingest_date=YYYY-MM-DD/
│   │   │       ├── {bill_number}_summaries.json.gz
│   │   │       └── ...
│
├── bill_related_bills/                        # Related bills (amendments, companion bills)
│   ├── congress=118/
│   │   ├── bill_type={hr,s,...}/
│   │   │   └── ingest_date=YYYY-MM-DD/
│   │   │       ├── {bill_number}_related.json.gz
│   │   │       └── ...
│
├── amendment/                                 # Amendments to bills
│   ├── congress=118/
│   │   └── ingest_date=YYYY-MM-DD/
│   │       ├── {amendment_number}.json.gz
│   │       └── ...
│
├── committee/                                 # Standing committees (House & Senate)
│   ├── chamber={house,senate,joint}/
│   │   └── ingest_date=YYYY-MM-DD/
│   │       ├── {committee_code}.json.gz
│   │       └── ...
│
├── house_vote/                                # House roll call votes
│   ├── congress=118/
│   │   ├── session={1,2}/
│   │   │   └── ingest_date=YYYY-MM-DD/
│   │   │       ├── {vote_number}.json.gz
│   │   │       └── ...
│
├── senate_vote/                               # Senate roll call votes
│   ├── congress=118/
│   │   ├── session={1,2}/
│   │   │   └── ingest_date=YYYY-MM-DD/
│   │   │       ├── {vote_number}.json.gz
│   │   │       └── ...
│
└── _state/                                    # Pipeline state tracking
    ├── member_last_ingest.json                # Last successful member ingest
    ├── bill_last_ingest.json                  # Last successful bill ingest
    ├── house_vote_last_ingest.json
    └── ...
```

---

## Entity-Specific Schemas

### 1. Member

**Endpoint**: `https://api.congress.gov/v3/member/{bioguideId}`

**S3 Path Pattern**:
```
bronze/congress/member/chamber={chamber}/ingest_date={YYYY-MM-DD}/{bioguide_id}.json.gz
```

**Partition Keys**:
- `chamber`: `house` or `senate` (derived from API response `member.terms[-1].chamber`)
- `ingest_date`: Date when API fetch occurred (YYYY-MM-DD format)

**Filename**:
- `{bioguide_id}.json.gz`: Unique bioguide ID (e.g., `A000360.json.gz`)

**Example Path**:
```
s3://congress-disclosures-standardized/bronze/congress/member/chamber=house/ingest_date=2025-12-04/A000360.json.gz
```

**S3 Object Metadata** (stored as S3 object tags or metadata):
```json
{
  "ingest-timestamp": "2025-12-04T10:30:00Z",
  "api-url": "https://api.congress.gov/v3/member/A000360",
  "http-status": "200",
  "source-system": "congress-api",
  "entity-type": "member",
  "ingest-version": "1.0.0"
}
```

**File Content Example** (gzipped JSON):
```json
{
  "member": {
    "bioguideId": "A000360",
    "firstName": "Lamar",
    "lastName": "Alexander",
    "party": "R",
    "state": "TN",
    "district": null,
    "terms": [
      {
        "chamber": "Senate",
        "startYear": 2003,
        "endYear": 2021
      }
    ],
    "depiction": {
      "imageUrl": "https://..."
    }
  }
}
```

---

### 2. Bill

**Endpoint**: `https://api.congress.gov/v3/bill/{congress}/{billType}/{billNumber}`

**S3 Path Pattern**:
```
bronze/congress/bill/congress={congress}/bill_type={billType}/ingest_date={YYYY-MM-DD}/{billNumber}.json.gz
```

**Partition Keys**:
- `congress`: Congress number (e.g., `118` for 118th Congress, 2023-2025)
- `bill_type`: Bill type code (`hr`, `s`, `hjres`, `sjres`, `hconres`, `sconres`, `hres`, `sres`)
- `ingest_date`: Date when API fetch occurred

**Filename**:
- `{billNumber}.json.gz`: Bill number without prefix (e.g., `1.json.gz` for H.R. 1)

**Example Path**:
```
s3://congress-disclosures-standardized/bronze/congress/bill/congress=118/bill_type=hr/ingest_date=2025-12-04/1.json.gz
```

**S3 Object Metadata**:
```json
{
  "ingest-timestamp": "2025-12-04T10:35:00Z",
  "api-url": "https://api.congress.gov/v3/bill/118/hr/1",
  "http-status": "200",
  "source-system": "congress-api",
  "entity-type": "bill",
  "congress": "118",
  "bill-type": "hr",
  "bill-number": "1",
  "ingest-version": "1.0.0"
}
```

**File Content Example** (gzipped JSON):
```json
{
  "bill": {
    "congress": 118,
    "type": "HR",
    "number": "1",
    "title": "Lower Energy Costs Act",
    "introducedDate": "2023-01-09",
    "originChamber": "House",
    "latestAction": {
      "actionDate": "2023-03-30",
      "text": "Received in the Senate and Read twice and referred to the Committee on Energy and Natural Resources."
    },
    "sponsors": [
      {
        "bioguideId": "S001213",
        "fullName": "Rep. Stauber, Pete [R-MN-8]",
        "state": "MN",
        "district": 8,
        "party": "Republican"
      }
    ],
    "policyArea": {
      "name": "Energy"
    },
    "subjects": {
      "legislativeSubjects": [
        {"name": "Alternative and renewable resources"},
        {"name": "Energy efficiency and conservation"}
      ]
    }
  }
}
```

---

### 3. Bill Actions

**Endpoint**: `https://api.congress.gov/v3/bill/{congress}/{billType}/{billNumber}/actions`

**S3 Path Pattern**:
```
bronze/congress/bill_actions/congress={congress}/bill_type={billType}/ingest_date={YYYY-MM-DD}/{billNumber}_actions.json.gz
```

**Partition Keys**: Same as bill (congress, bill_type, ingest_date)

**Filename**:
- `{billNumber}_actions.json.gz`: Bill number + `_actions` suffix

**Example Path**:
```
s3://congress-disclosures-standardized/bronze/congress/bill_actions/congress=118/bill_type=hr/ingest_date=2025-12-04/1_actions.json.gz
```

**File Content Example** (gzipped JSON):
```json
{
  "actions": [
    {
      "actionDate": "2023-01-09",
      "text": "Introduced in House",
      "type": "IntroReferral",
      "actionCode": "Intro-H",
      "sourceSystem": {"code": 9, "name": "Library of Congress"}
    },
    {
      "actionDate": "2023-01-09",
      "text": "Referred to the Committee on Energy and Commerce",
      "type": "IntroReferral",
      "actionCode": "H11100"
    }
  ]
}
```

---

### 4. Bill Cosponsors

**Endpoint**: `https://api.congress.gov/v3/bill/{congress}/{billType}/{billNumber}/cosponsors`

**S3 Path Pattern**:
```
bronze/congress/bill_cosponsors/congress={congress}/bill_type={billType}/ingest_date={YYYY-MM-DD}/{billNumber}_cosponsors.json.gz
```

**File Content Example** (gzipped JSON):
```json
{
  "cosponsors": [
    {
      "bioguideId": "P000034",
      "fullName": "Rep. Pallone, Frank, Jr. [D-NJ-6]",
      "sponsorshipDate": "2023-01-09",
      "isOriginalCosponsor": true,
      "state": "NJ",
      "district": 6,
      "party": "Democratic"
    }
  ]
}
```

---

### 5. Bill Committees

**Endpoint**: `https://api.congress.gov/v3/bill/{congress}/{billType}/{billNumber}/committees`

**S3 Path Pattern**:
```
bronze/congress/bill_committees/congress={congress}/bill_type={billType}/ingest_date={YYYY-MM-DD}/{billNumber}_committees.json.gz
```

**File Content Example**:
```json
{
  "committees": [
    {
      "systemCode": "hsif00",
      "name": "Energy and Commerce Committee",
      "chamber": "House",
      "type": "Standing",
      "activities": [
        {
          "name": "Referred to",
          "date": "2023-01-09T00:00:00Z"
        }
      ]
    }
  ]
}
```

---

### 6. Bill Subjects

**Endpoint**: `https://api.congress.gov/v3/bill/{congress}/{billType}/{billNumber}/subjects`

**S3 Path Pattern**:
```
bronze/congress/bill_subjects/congress={congress}/bill_type={billType}/ingest_date={YYYY-MM-DD}/{billNumber}_subjects.json.gz
```

**File Content Example**:
```json
{
  "subjects": {
    "legislativeSubjects": [
      {"name": "Alternative and renewable resources"},
      {"name": "Energy efficiency and conservation"},
      {"name": "Oil and gas"}
    ],
    "policyArea": {
      "name": "Energy"
    }
  }
}
```

---

### 7. House Vote

**Endpoint**: `https://api.congress.gov/v3/vote/{congress}/house/{rollCallNumber}`

**S3 Path Pattern**:
```
bronze/congress/house_vote/congress={congress}/session={session}/ingest_date={YYYY-MM-DD}/{rollCallNumber}.json.gz
```

**Partition Keys**:
- `congress`: Congress number (e.g., `118`)
- `session`: Session number (1 or 2, derived from vote date)
- `ingest_date`: Date when API fetch occurred

**Example Path**:
```
s3://congress-disclosures-standardized/bronze/congress/house_vote/congress=118/session=1/ingest_date=2025-12-04/42.json.gz
```

**File Content Example**:
```json
{
  "vote": {
    "congress": 118,
    "chamber": "House",
    "rollCall": 42,
    "session": 1,
    "question": "On Passage",
    "result": "Passed",
    "date": "2023-01-13",
    "bill": {
      "congress": 118,
      "type": "HR",
      "number": 21
    },
    "members": [
      {
        "bioguideId": "A000370",
        "name": "Adams, Alma S.",
        "state": "NC",
        "party": "D",
        "vote": "Yea"
      }
    ]
  }
}
```

---

### 8. Committee

**Endpoint**: `https://api.congress.gov/v3/committee/{chamber}/{committeeCode}`

**S3 Path Pattern**:
```
bronze/congress/committee/chamber={chamber}/ingest_date={YYYY-MM-DD}/{committeeCode}.json.gz
```

**Partition Keys**:
- `chamber`: `house`, `senate`, or `joint`
- `ingest_date`: Date when API fetch occurred

**Example Path**:
```
s3://congress-disclosures-standardized/bronze/congress/committee/chamber=house/ingest_date=2025-12-04/hsif00.json.gz
```

**File Content Example**:
```json
{
  "committee": {
    "systemCode": "hsif00",
    "name": "Energy and Commerce Committee",
    "chamber": "House",
    "committeeTypeCode": "Standing",
    "subcommittees": [
      {
        "systemCode": "hsif03",
        "name": "Energy Subcommittee"
      }
    ]
  }
}
```

---

## Partitioning Strategy

### Why These Partition Keys?

**congress**: Queries almost always filter by Congress number (e.g., "118th Congress bills"). Partitioning by congress enables partition pruning.

**bill_type**: Bill type queries are common ("all House resolutions"). Partitioning reduces scan size.

**chamber**: Members and committees are queried by chamber. Enables fast lookups.

**session**: Votes are often queried by session. Partitioning improves query performance.

**ingest_date**: Enables incremental processing ("process all files ingested since yesterday") and pipeline debugging.

### Object Count Estimates

| Entity Type       | Objects per Congress | Partition Strategy                           | Avg Objects per Partition |
|-------------------|----------------------|----------------------------------------------|---------------------------|
| member            | ~540                 | chamber (2) × ingest_date (30)               | ~9 per partition          |
| bill              | ~10,000              | congress (1) × bill_type (8) × ingest_date   | ~40 per partition         |
| bill_actions      | ~10,000              | congress × bill_type × ingest_date           | ~40 per partition         |
| bill_cosponsors   | ~10,000              | congress × bill_type × ingest_date           | ~40 per partition         |
| house_vote        | ~1,000               | congress × session (2) × ingest_date         | ~17 per partition         |
| committee         | ~200                 | chamber (3) × ingest_date                    | ~3 per partition          |

**Design Goal**: Keep 10-100 objects per partition to balance query efficiency vs S3 overhead.

---

## File Naming Conventions

### Pattern: `{entity_id}.json.gz`

**entity_id**: Natural key from API (bioguide_id, bill_number, vote_number, committee_code)

**Why not UUIDs?**
- Natural keys enable idempotent writes (re-ingesting same entity overwrites file)
- Debugging easier (recognizable IDs in S3 Console)
- API queries map directly to S3 keys

### Special Case: Bill Subresources

**Pattern**: `{bill_number}_{subresource_type}.json.gz`

Example: `1_actions.json.gz`, `1_cosponsors.json.gz`

**Why append suffix?**
- Prevents conflicts between bill and bill_actions in same prefix
- Groups related files together in S3 listing

---

## Compression Format

**All files**: gzip compression (`.json.gz`)

**Rationale**:
- 70-90% size reduction vs raw JSON
- Native support in AWS SDK, Pandas, PyArrow
- Fast compression/decompression (vs bzip2)

**Trade-off**: Files not readable in S3 Console without download, but acceptable for Bronze layer.

---

## S3 Object Metadata

Every Bronze object includes metadata for auditability and debugging.

**Standard Metadata** (S3 object metadata):
```json
{
  "ingest-timestamp": "2025-12-04T10:30:00Z",
  "api-url": "https://api.congress.gov/v3/member/A000360",
  "http-status": "200",
  "source-system": "congress-api",
  "entity-type": "member",
  "ingest-version": "1.0.0"
}
```

**Access Metadata**:
```python
import boto3
s3 = boto3.client('s3')
response = s3.head_object(Bucket='congress-disclosures-standardized', Key='bronze/congress/member/chamber=house/ingest_date=2025-12-04/A000360.json.gz')
metadata = response['Metadata']
print(metadata['ingest-timestamp'])  # "2025-12-04T10:30:00Z"
```

---

## State Tracking Files

**Location**: `bronze/congress/_state/`

**Purpose**: Track last successful ingest timestamp for incremental mode.

**Example**: `bronze/congress/_state/member_last_ingest.json`

**Content**:
```json
{
  "last_ingest_date": "2025-12-04T10:30:00Z",
  "last_item_count": 540,
  "congress": 118,
  "status": "success"
}
```

**Usage**:
1. Orchestrator reads state file before querying API
2. API query includes `?fromDateTime={last_ingest_date}` to get only updated entities
3. After successful ingest, orchestrator writes new state file

---

## Migration from Financial Disclosures (FD) Pattern

**FD Pattern**: `bronze/house/financial/year=YYYY/filing_type=X/pdfs/`

**Congress Pattern**: `bronze/congress/{entity_type}/congress=XXX/...`

**Key Differences**:
1. **Entity-centric**: Congress uses top-level entity types (member, bill) instead of source system (house/financial)
2. **Congress number**: Partitioned by Congress (118) instead of year (2025)
3. **JSON**: Congress stores JSON (API responses) instead of PDFs
4. **Subresources**: Bill subresources (actions, cosponsors) get separate prefixes

**Similarities**:
1. **Hive partitioning**: Both use `key=value` format
2. **Immutability**: Both preserve raw source data
3. **Metadata**: Both track ingestion provenance in S3 metadata
4. **Compression**: Both use compression (gzip for JSON, native for PDF)

---

## Examples: Complete Paths

### Example 1: Rep. Alexandria Ocasio-Cortez (current House member)
```
s3://congress-disclosures-standardized/bronze/congress/member/chamber=house/ingest_date=2025-12-04/O000172.json.gz
```

### Example 2: H.R. 1 (118th Congress)
```
# Main bill
s3://congress-disclosures-standardized/bronze/congress/bill/congress=118/bill_type=hr/ingest_date=2025-12-04/1.json.gz

# Actions
s3://congress-disclosures-standardized/bronze/congress/bill_actions/congress=118/bill_type=hr/ingest_date=2025-12-04/1_actions.json.gz

# Cosponsors
s3://congress-disclosures-standardized/bronze/congress/bill_cosponsors/congress=118/bill_type=hr/ingest_date=2025-12-04/1_cosponsors.json.gz

# Committees
s3://congress-disclosures-standardized/bronze/congress/bill_committees/congress=118/bill_type=hr/ingest_date=2025-12-04/1_committees.json.gz

# Subjects
s3://congress-disclosures-standardized/bronze/congress/bill_subjects/congress=118/bill_type=hr/ingest_date=2025-12-04/1_subjects.json.gz

# Titles
s3://congress-disclosures-standardized/bronze/congress/bill_titles/congress=118/bill_type=hr/ingest_date=2025-12-04/1_titles.json.gz
```

### Example 3: House Vote 42 (118th Congress, Session 1)
```
s3://congress-disclosures-standardized/bronze/congress/house_vote/congress=118/session=1/ingest_date=2025-12-04/42.json.gz
```

### Example 4: House Energy and Commerce Committee
```
s3://congress-disclosures-standardized/bronze/congress/committee/chamber=house/ingest_date=2025-12-04/hsif00.json.gz
```

---

## Validation Checklist

When implementing Bronze ingestion:

✅ **Path determinism**: Given (entity_type, entity_id, congress), can compute exact S3 key
✅ **Idempotence**: Re-ingesting same entity overwrites file (no duplicates)
✅ **Partition balance**: 10-100 objects per partition (not 1, not 10,000)
✅ **Compression**: All JSON files use gzip
✅ **Metadata**: All objects have ingest-timestamp, api-url, http-status
✅ **State tracking**: State files enable incremental mode
✅ **Naming consistency**: Follow patterns (entity_id.json.gz, bill_number_subresource.json.gz)

---

## Next Steps

After Bronze schema is documented:
1. **TASK 1.1.2**: Create Terraform variables for Congress.gov API configuration
2. **TASK 1.1.3**: Update S3 bucket policies to allow Lambda writes to Congress prefixes
3. **STORY 1.2**: Create SQS queues for API fetch orchestration
4. **STORY 1.3**: Implement `congress_api_fetch_entity` Lambda to populate Bronze

**Last Updated**: 2025-12-04
