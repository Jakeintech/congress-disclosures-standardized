# Data Quality & Versioning Strategy

**Purpose**: Comprehensive strategy for managing extraction improvements, data versioning, and quality controls across the Bronze → Silver → Gold pipeline.

**Last Updated**: 2025-12-14

---

## Problem Statement

### Current Challenges
1. **No extraction versioning**: When we improve Type P extraction from 87% → 94% accuracy, we must either:
   - Reprocess ALL 50,000 Type P filings (expensive, 8+ hours)
   - Accept inconsistency (2020-2024 uses old logic, 2025+ uses new logic)

2. **No data lineage**: Cannot trace which Gold records came from which extractor version

3. **No quality tracking**: No systematic way to measure extraction improvements over time

4. **No rollback capability**: If new extractor is worse, can't easily revert

5. **Limited SCD support**: Gold dimensions don't track changes to member/asset details over time

---

## Solution Architecture

### 1. Extraction Versioning (Bronze → Silver)

**Implementation**: STORY-054 (Sprint 2, Day 3)

#### Extractor Versions
Every extractor class gets semantic versioning:

```python
# ingestion/lib/extractors/type_p_ptr/extractor.py
class PTRExtractor(BaseExtractor):
    __version__ = "1.0.0"  # MAJOR.MINOR.PATCH
    __changelog__ = {
        "1.0.0": "Initial production release",
        "1.1.0": "Improved transaction amount parsing (+7% accuracy)",
        "1.1.1": "Fixed date format edge case"
    }
```

**Versioning Guidelines**:
- **MAJOR** (1.x.x → 2.x.x): Breaking schema changes (field renamed/removed)
- **MINOR** (1.0.x → 1.1.x): Extraction logic improvements (better regex, new field)
- **PATCH** (1.0.0 → 1.0.1): Bug fixes (no quality improvement expected)

#### Multi-Version Silver Storage

```
silver/objects/
├── filing_type=type_p/
│   ├── extractor_version=1.0.0/
│   │   ├── 20063228.json  # Old extraction
│   │   └── 20074539.json
│   ├── extractor_version=1.1.0/
│   │   ├── 20063228.json  # Same doc_id, new extraction
│   │   └── 20074539.json
│   └── latest -> extractor_version=1.1.0/  # Symlink
```

**Benefits**:
- Multiple versions coexist (no data loss)
- Gold layer can choose which version to consume
- Rollback by pointing Gold to previous version
- Storage controlled by 90-day lifecycle policy

#### Version Registry (DynamoDB)

**Table**: `extraction_versions`

```python
{
    "filing_type": "type_p",  # PK
    "extractor_version": "1.1.0",  # SK
    "deployed_at": "2025-01-15T10:30:00Z",
    "changelog": "Improved transaction amount parsing (+7% accuracy)",
    "quality_metrics": {
        "avg_confidence_score": 0.91,
        "field_extraction_rates": {
            "transaction_date": 0.98,
            "amount_low": 0.94,  # Improved from 0.87
            "asset_description": 0.89
        }
    },
    "is_production": True,  # Which version Gold should use
    "filings_processed": 15234
}
```

---

### 2. Selective Reprocessing (Iterative Improvement)

**Implementation**: STORY-055 (Sprint 3, Day 4)

#### Reprocessing Lambda

Allows targeted reprocessing when extraction improves:

```bash
# Example: Reprocess only 2024-2025 Type P filings with new extractor
aws lambda invoke \
  --function-name reprocess-filings \
  --payload '{
    "filing_type": "type_p",
    "year_range": [2024, 2025],
    "extractor_version": "1.1.0",
    "comparison_mode": true
  }' \
  output.json
```

**Output**: Comparison report showing before/after quality metrics

```json
{
  "summary": {
    "pdfs_reprocessed": 1245,
    "extractions_succeeded": 1201
  },
  "comparison": {
    "baseline_version": "1.0.0",
    "new_version": "1.1.0",
    "quality_improvements": {
      "avg_confidence_score": {"old": 0.87, "new": 0.94, "delta": "+7%"},
      "amount_low_extraction": {"old": 0.87, "new": 0.94, "delta": "+7%"}
    },
    "regressions": []  # Fields that got worse
  }
}
```

#### Version Promotion Workflow

1. **Deploy new extractor** (e.g., Type P v1.1.0)
2. **Reprocess sample** (e.g., 2024-2025 only, 1,200 PDFs)
3. **Compare quality** (v1.0.0 vs v1.1.0 metrics)
4. **Promote if better** (update `is_production` flag in DynamoDB)
5. **Gradually migrate** (reprocess older years as needed)

#### Rollback Safety

If new version causes issues:

```python
rollback_version(
    filing_type="type_p",
    rollback_to_version="1.0.0"
)
# Gold layer automatically reads old version again
```

---

### 3. SCD Type 2 for Gold Dimensions

**Implementation**: Integrated into dimension builders (Sprint 2-3)

#### Where SCD Type 2 Applies

| Dimension | SCD Type | Reason | Effective Dating |
|-----------|----------|--------|------------------|
| **dim_members** | **SCD Type 2** | Members change party, district, chamber | `effective_from`, `effective_to`, `is_current` |
| **dim_assets** | **SCD Type 1** | Asset descriptions don't meaningfully change | N/A (overwrite) |
| **dim_bills** | **SCD Type 1** | Bill metadata is static once introduced | N/A |
| **dim_dates** | **SCD Type 0** | Date dimension never changes | N/A (static) |
| **dim_lobbyists** | **SCD Type 2** | Lobbyists change firms, registration status | `effective_from`, `effective_to`, `is_current` |

#### dim_members SCD Type 2 Implementation

**Schema**:
```python
{
    "member_key": 1234,  # Surrogate key (auto-increment)
    "bioguide_id": "A000055",  # Natural key
    "first_name": "John",
    "last_name": "Smith",
    "party": "Republican",  # Can change
    "state": "CA",
    "district": 12,  # Can change (redistricting)
    "chamber": "House",

    # SCD Type 2 fields
    "effective_from": "2023-01-03",  # Congressional session start
    "effective_to": "2025-01-03",  # When this record was superseded
    "is_current": False,  # Only latest record has is_current=True
    "version": 2,  # Human-readable version number

    # Audit fields
    "created_at": "2023-01-03T00:00:00Z",
    "updated_at": "2025-01-04T10:30:00Z",
    "source_system": "house_clerk"
}
```

**Lookup Logic** (for fact tables):
```python
def get_member_key(bioguide_id: str, transaction_date: str) -> int:
    """Get member_key effective at transaction_date (SCD Type 2 lookup)."""
    query = f"""
    SELECT member_key
    FROM dim_members
    WHERE bioguide_id = '{bioguide_id}'
      AND '{transaction_date}' >= effective_from
      AND '{transaction_date}' < COALESCE(effective_to, '9999-12-31')
    """
    # Returns correct member_key for that point in time
```

**Change Detection**:
```python
def update_dim_members(new_member_data):
    """Update member dimension with SCD Type 2 logic."""
    existing = query_current_member(new_member_data['bioguide_id'])

    # Check if party or district changed
    if (existing['party'] != new_member_data['party'] or
        existing['district'] != new_member_data['district']):

        # Close old record
        update_record(
            member_key=existing['member_key'],
            effective_to=new_member_data['effective_from'],
            is_current=False
        )

        # Insert new record
        insert_record({
            **new_member_data,
            'is_current': True,
            'version': existing['version'] + 1
        })
    else:
        # No change, just update audit fields
        update_record(
            member_key=existing['member_key'],
            updated_at=datetime.utcnow()
        )
```

---

### 4. Version Tracking in Gold Layer

#### Fact Tables: Extraction Version Lineage

**Enhanced Schema** (all fact tables):

```python
{
    # Business keys
    "transaction_key": "abc123...",
    "doc_id": "20063228",
    "member_key": 1234,  # FK to dim_members (SCD Type 2 aware)

    # Fact data
    "transaction_date": "2024-01-15",
    "amount_low": 15001,
    "amount_high": 50000,

    # NEW: Version tracking fields
    "extractor_version": "1.1.0",  # Which extractor version created this
    "extraction_quality_score": 0.94,  # Confidence score
    "extraction_timestamp": "2025-01-15T10:30:00Z",

    # Audit fields
    "created_at": "2025-01-15T11:00:00Z",
    "updated_at": "2025-01-15T11:00:00Z",
    "is_deleted": False  # Soft delete flag
}
```

#### Gold Layer Script Updates

**Before** (current state):
```python
# scripts/build_fact_ptr_transactions.py
def read_silver_objects(filing_type: str):
    """Read ALL Type P objects (no version awareness)."""
    prefix = f"silver/objects/filing_type={filing_type}/"
    # Reads all objects regardless of version
```

**After** (version-aware):
```python
def read_silver_objects(filing_type: str, extractor_version: str = None):
    """Read Type P objects from specific extractor version (or latest)."""

    # Check DynamoDB for production version
    if not extractor_version:
        extractor_version = get_production_version(filing_type)

    prefix = f"silver/objects/filing_type={filing_type}/extractor_version={extractor_version}/"
    logger.info(f"Reading Silver objects from version {extractor_version}")

    # Read only from specified version
    for obj in list_s3_objects(bucket, prefix):
        # ... process objects ...

        # Include version metadata in fact records
        fact_record['extractor_version'] = extractor_version
        fact_record['extraction_quality_score'] = obj['extraction_metadata']['confidence_score']
```

**Benefits**:
- Always know which extractor version produced each fact record
- Can compare Gold metrics before/after extractor improvements
- Can rebuild Gold from different Silver versions for A/B testing

---

### 5. Data Quality Validation Checkpoints

**Implementation**: STORY-033, STORY-048 (Sprint 3, Day 3)

#### Soda Quality Checks

**Bronze Layer Checks** (`soda/checks/bronze/bronze_quality.yml`):

```yaml
# Bronze completeness checks
checks for bronze_pdfs:
  - row_count > 0:
      name: Bronze PDFs exist

  - missing_count(doc_id) = 0:
      name: All PDFs have doc_id

  - duplicate_count(doc_id) = 0:
      name: No duplicate PDFs
      warn:
        when duplicate_count > 10
      fail:
        when duplicate_count > 100

# Bronze metadata validation
checks for bronze_metadata:
  - values in (extraction_processed) must be in ['true', 'false']:
      name: Valid extraction status
```

**Silver Layer Checks** (`soda/checks/silver/extraction_quality.yml`):

```yaml
# Silver extraction quality checks
checks for silver_objects_type_p:
  - avg(extraction_metadata.confidence_score) >= 0.85:
      name: Type P average confidence >= 85%
      warn:
        when avg(extraction_metadata.confidence_score) < 0.85
      fail:
        when avg(extraction_metadata.confidence_score) < 0.75

  # Field extraction rates
  - avg(field_confidence.transaction_date) >= 0.95:
      name: Transaction date extraction rate >= 95%

  - avg(field_confidence.amount_low) >= 0.85:
      name: Amount extraction rate >= 85%

  # Version consistency
  - schema:
      name: All objects have extractor_version field
      fail:
        when required column extractor_version

# Regression detection
checks for silver_objects_type_p:
  - change avg(extraction_metadata.confidence_score):
      name: Confidence score trend (detect regressions)
      warn:
        when decrease >= 5%  # Alert if quality drops 5%
      fail:
        when decrease >= 10%
```

**Gold Layer Checks** (`soda/checks/gold/gold_quality.yml`):

```yaml
# Gold dimension quality
checks for dim_members:
  - row_count >= 538:  # At least 435 House + 100 Senate + 3 territories
      name: Expected member count

  - missing_count(bioguide_id) = 0:
      name: All members have bioguide_id

  - duplicate_count(bioguide_id) where is_current = true = 0:
      name: No duplicate current members (SCD Type 2 integrity)

# Gold fact quality
checks for fact_ptr_transactions:
  - row_count > 0:
      name: Transactions exist

  - missing_count(extractor_version) = 0:
      name: All transactions have extractor_version (lineage)

  - avg(extraction_quality_score) >= 0.85:
      name: Average extraction quality >= 85%

  # Referential integrity
  - failed rows:
      name: All member_keys exist in dim_members
      fail query: |
        SELECT COUNT(*)
        FROM fact_ptr_transactions f
        LEFT JOIN dim_members m ON f.member_key = m.member_key
        WHERE m.member_key IS NULL
      fail:
        when fail count > 0

  # Business logic validation
  - values in (transaction_type) must be in ['Purchase', 'Sale', 'Exchange']:
      name: Valid transaction types only

  - amount_low <= amount_high:
      name: Amount range logical (low <= high)
```

#### Quality Check Lambda

**Function**: `run_soda_checks`
**Trigger**: After Gold aggregates in state machine
**Action**: Fail pipeline if critical checks don't pass

```python
def lambda_handler(event, context):
    """Run Soda quality checks and fail pipeline if critical issues."""

    # Run all checks
    scan = Scan()
    scan.set_scan_definition_name("congress_data_quality")
    scan.execute()

    # Parse results
    results = {
        "total_checks": scan.get_checks_count(),
        "passed": scan.get_checks_passed_count(),
        "failed": scan.get_checks_failed_count(),
        "warnings": scan.get_checks_warned_count()
    }

    # Categorize failures
    critical_failures = [c for c in scan.get_checks_failed() if c.severity == 'critical']
    warnings = [c for c in scan.get_checks_warned()]

    # Publish to SNS
    if critical_failures:
        sns.publish(
            TopicArn=SNS_ALERTS_ARN,
            Subject="❌ Data Quality CRITICAL FAILURE",
            Message=format_failure_report(critical_failures)
        )

        # Fail state machine
        raise Exception(f"{len(critical_failures)} critical quality checks failed")

    if warnings:
        sns.publish(
            TopicArn=SNS_ALERTS_ARN,
            Subject="⚠️ Data Quality Warnings",
            Message=format_warning_report(warnings)
        )

    return results
```

---

### 6. Extraction Quality Dashboard

**Implementation**: STORY-056 (Sprint 4, Day 1)

#### CloudWatch Custom Metrics

**Published by extraction Lambdas**:

```python
cloudwatch.put_metric_data(
    Namespace='CongressDisclosures/Extraction',
    MetricData=[
        {
            'MetricName': 'ConfidenceScore',
            'Dimensions': [
                {'Name': 'FilingType', 'Value': 'type_p'},
                {'Name': 'ExtractorVersion', 'Value': '1.1.0'}
            ],
            'Value': 0.94,
            'Unit': 'None'
        },
        {
            'MetricName': 'FieldExtractionRate',
            'Dimensions': [
                {'Name': 'FilingType', 'Value': 'type_p'},
                {'Name': 'Field', 'Value': 'amount_low'},
                {'Name': 'ExtractorVersion', 'Value': '1.1.0'}
            ],
            'Value': 0.94
        }
    ]
)
```

#### Dashboard Widgets

1. **Confidence Scores Over Time** (line chart)
   - Shows extraction quality trends by filing type and version
   - 7-day rolling average

2. **Field Extraction Rates** (heatmap)
   - Grid showing extraction success rate per field
   - Color-coded (green=good, yellow=ok, red=bad)

3. **Version Adoption Rate** (gauge)
   - % of data using latest extractor version
   - Tracks reprocessing progress

4. **Quality Regression Alarms** (alarm widget)
   - Alerts if extraction quality drops below threshold

---

## Implementation Roadmap

### Sprint 2 (Dec 23-27): Foundation

#### STORY-054: Extraction Versioning Infrastructure (5 hours, Day 3)
- [x] Add `__version__` to all 6 extractor classes
- [x] Update extraction metadata to include version fields
- [x] Create DynamoDB `extraction_versions` table
- [x] Implement multi-version Silver storage (versioned S3 paths)
- [x] Add S3 lifecycle policy (expire old versions after 90 days)

**Deliverable**: All extractors versioned, Silver supports multiple versions

---

### Sprint 3 (Dec 30-Jan 3): Selective Reprocessing

#### STORY-055: Selective Reprocessing Lambda (8 hours, Day 4)
- [x] Create `reprocess_filings` Lambda
- [x] Implement comparison report generation (before/after metrics)
- [x] Add version promotion/rollback utilities
- [x] Integrate optional reprocessing branch into state machine

**Deliverable**: Can reprocess specific filing types/years, validate improvements

---

### Sprint 3 (Dec 30-Jan 3): Quality Infrastructure

#### STORY-048: Soda Quality Checks (5 hours, Day 3)
- [x] Create 15+ Soda YAML check definitions
- [x] Bronze checks: completeness, uniqueness
- [x] Silver checks: extraction quality, confidence scores, regression detection
- [x] Gold checks: referential integrity, business logic, SCD Type 2 integrity

#### STORY-033: run_soda_checks Lambda (5 hours, Day 3)
- [x] Lambda wrapper for Soda Core
- [x] Severity-based failure logic (critical vs warning)
- [x] SNS notifications for failures

**Deliverable**: Automated quality validation at each pipeline phase

---

### Sprint 3 (Dec 30-Jan 3): SCD Type 2 Dimensions

#### STORY-049: Dimension Validation (3 hours, Day 3)
- [x] Add SCD Type 2 support to `build_dim_members`
- [x] Implement change detection logic
- [x] Add `effective_from`, `effective_to`, `is_current` fields
- [x] Update fact builders to use SCD Type 2 lookups

**Deliverable**: dim_members tracks member changes over time

---

### Sprint 4 (Jan 6-10): Monitoring

#### STORY-056: Extraction Quality Dashboard (3 hours, Day 1)
- [ ] CloudWatch dashboard with 6 widgets
- [ ] Custom metrics for confidence scores and field extraction rates
- [ ] Quality regression alarms (SNS notifications)
- [ ] Version adoption tracking

**Deliverable**: Real-time visibility into extraction quality

---

## Data Improvement Workflow (Example)

### Scenario: Improve Type P Amount Extraction

**Current State**: 87% accuracy on amount field extraction
**Goal**: Improve to 94% accuracy

#### Step 1: Develop Improved Extractor
```python
# ingestion/lib/extractors/type_p_ptr/extractor.py
class PTRExtractor(BaseExtractor):
    __version__ = "1.1.0"  # Bumped from 1.0.0
    __changelog__ = {
        "1.1.0": "Improved transaction amount parsing with better regex (+7% accuracy)"
    }

    def extract_amount(self, text):
        # New improved logic here...
```

#### Step 2: Deploy New Version
```bash
make package-extract-structured
make deploy-extractors
```

#### Step 3: Test on Sample Data (2024-2025 only)
```bash
aws lambda invoke \
  --function-name reprocess-filings \
  --payload '{
    "filing_type": "type_p",
    "year_range": [2024, 2025],
    "extractor_version": "1.1.0",
    "comparison_mode": true
  }' \
  output.json

# Review comparison report
cat output.json | jq '.comparison.quality_improvements'
# {
#   "amount_low_extraction": {"old": 0.87, "new": 0.94, "delta": "+7%"}
# }
```

#### Step 4: Promote to Production (if quality improved)
```python
promote_version_to_production(
    filing_type="type_p",
    new_version="1.1.0"
)
```

#### Step 5: Gradually Reprocess Older Years
```bash
# Reprocess 2020-2023 (when capacity allows)
aws lambda invoke --function-name reprocess-filings --payload '{
  "filing_type": "type_p",
  "year_range": [2020, 2023],
  "extractor_version": "1.1.0"
}'
```

#### Step 6: Monitor Quality Dashboard
- CloudWatch dashboard shows improvement in confidence scores
- No regressions detected in other fields
- Version adoption rate increases from 24% → 100% over weeks

---

## Key Benefits

### 1. Iterative Quality Improvement
- Deploy new extractor versions without fear
- Test on samples before full reprocessing
- A/B test extraction approaches

### 2. Data Lineage & Auditability
- Always know which extractor version produced each record
- Trace Gold records back to extraction logic
- Regulatory compliance (can prove data provenance)

### 3. Risk Mitigation
- Rollback capability if new version is worse
- Quality regression alarms prevent silent failures
- Multi-version storage prevents data loss

### 4. Cost Optimization
- Selective reprocessing (1,200 PDFs vs 50,000)
- Only reprocess what benefits from improvements
- Avoid expensive full dataset reprocessing

### 5. SCD Type 2 for Historical Accuracy
- Track member party/district changes over time
- Accurate point-in-time queries
- Correct joins for historical analysis

---

## Testing Strategy

### Unit Tests (30+ tests)
- Extractor version comparison logic
- SCD Type 2 change detection
- Soda check YAML parsing
- Version promotion/rollback

### Integration Tests (15+ tests)
- Multi-version Silver storage
- Reprocessing comparison report generation
- Quality check failures trigger SNS
- State machine executes with quality gates

### E2E Tests (5 tests)
- Full improvement workflow (deploy → reprocess → promote)
- Rollback scenario (revert to previous version)
- SCD Type 2 dimension updates propagate to facts

---

## Success Metrics

- [ ] All 6 extractor classes have semantic versioning
- [ ] DynamoDB version registry tracks quality metrics per version
- [ ] Selective reprocessing Lambda operational
- [ ] 15+ Soda quality checks enforced
- [ ] SCD Type 2 implemented for dim_members
- [ ] CloudWatch dashboard shows extraction quality trends
- [ ] Can improve extractor and reprocess <2,000 PDFs in <30 minutes
- [ ] Rollback capability tested and verified
- [ ] 80%+ test coverage for versioning/quality modules

---

**Ownership**: Data Engineering Team
**Dependencies**: STORY-054, STORY-055, STORY-056, STORY-048, STORY-033, STORY-049
