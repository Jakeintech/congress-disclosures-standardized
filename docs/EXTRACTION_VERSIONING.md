# Extraction Versioning Strategy

**Sprint**: Sprint 2 (STORY-054)
**Purpose**: Enable iterative extraction quality improvements without massive reprocessing

---

## Overview

The extraction versioning system tracks extractor versions and allows incremental quality improvements. When we improve Type P extraction from 87% → 94% accuracy, we can reprocess just recent years (1,200 PDFs) instead of ALL years (50,000 PDFs).

## Architecture

### 1. Extractor Versioning

Each extractor class includes version metadata:

```python
class PTRExtractor(BaseExtractor):
    """PTR Extractor with version tracking."""

    EXTRACTOR_VERSION = "1.0.0"  # Semantic versioning
    EXTRACTOR_CLASS = "PTRExtractor"  # Class name for tracking
```

**Versioning Scheme** (Semantic Versioning):
- **Major** (1.x.x): Breaking changes to output schema
- **Minor** (x.1.x): New fields added, improved extraction logic
- **Patch** (x.x.1): Bug fixes, no logic changes

### 2. Extraction Metadata

Every extraction includes version information:

```json
{
  "extraction_metadata": {
    "extractor_version": "1.0.0",
    "extractor_class": "PTRExtractor",
    "baseline_version": "1.0.0",
    "confidence": 0.87,
    "method": "regex",
    "extraction_timestamp": "2025-12-15T10:30:00Z"
  }
}
```

### 3. Versioned Silver Storage

Extracted objects are partitioned by extractor version:

```
s3://congress-disclosures-standardized/
└── silver/house/financial/objects/
    └── filing_type=type_p/
        ├── extractor_version=1.0.0/
        │   ├── year=2023/doc_id=10063228.json
        │   └── year=2024/doc_id=10078945.json
        └── extractor_version=1.1.0/  # Future: improved version
            └── year=2024/doc_id=10078945.json  # Re-extracted
```

**Benefits**:
- Side-by-side version comparison
- Gradual migration to new versions
- Rollback capability
- Quality A/B testing

### 4. DynamoDB Version Tracking

`congress-disclosures-extraction-versions` table:

| Field | Type | Description |
|-------|------|-------------|
| `extractor_class` (PK) | String | Extractor class name (e.g., "PTRExtractor") |
| `extractor_version` (SK) | String | Version number (e.g., "1.0.0") |
| `deployment_date` | String | ISO 8601 deployment timestamp |
| `quality_metrics` | Map | Avg confidence, field coverage, error rate |
| `documents_processed` | Number | Count of documents extracted with this version |
| `avg_confidence_score` | Number | Average extraction confidence |
| `schema_hash` | String | SHA256 hash of output schema (detect breaking changes) |
| `notes` | String | Human-readable release notes |

**Example Record**:
```json
{
  "extractor_class": "PTRExtractor",
  "extractor_version": "1.0.0",
  "deployment_date": "2025-12-15T00:00:00Z",
  "quality_metrics": {
    "avg_confidence": 0.87,
    "field_coverage": 0.92,
    "transaction_extraction_rate": 0.89
  },
  "documents_processed": 12450,
  "avg_confidence_score": 0.87,
  "schema_hash": "a3f5...",
  "notes": "Baseline version - regex-based extraction"
}
```

### 5. Gold Layer Version Awareness

Gold layer builders specify which extractor version to use:

```python
def load_transactions_from_silver(bucket_name: str, extractor_version: str = "latest"):
    """Load transactions from specific extractor version."""

    if extractor_version == "latest":
        # Query DynamoDB for latest version
        extractor_version = get_latest_extractor_version("PTRExtractor")

    prefix = f'silver/house/financial/objects/filing_type=type_p/extractor_version={extractor_version}/'
    # ... load from S3
```

**Backward Compatibility**: Gold layer defaults to "latest" but can specify exact versions for reproducibility.

### 6. S3 Lifecycle Policy

Automatically clean up old extraction versions after 90 days:

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  rule {
    id     = "silver-versioned-extractions-cleanup"
    status = "Enabled"

    filter {
      prefix = "silver/house/financial/objects/"
    }

    expiration {
      days = 90  # 90-day grace period for validation
    }
  }
}
```

**Rationale**: 90 days allows time to:
1. Validate new extractor versions
2. Compare quality metrics
3. Migrate Gold layer to new version
4. Rollback if issues found

---

## Workflow: Improving Extraction Quality

### Scenario: Improve Type P Extraction from 87% → 94%

**Step 1: Develop Improved Extractor**

```python
# ingestion/lib/extractors/type_p_ptr/extractor.py

class PTRExtractor(BaseExtractor):
    EXTRACTOR_VERSION = "1.1.0"  # Bump minor version
    EXTRACTOR_CLASS = "PTRExtractor"

    def _extract_transactions(self, text: str):
        # NEW: Improved regex patterns
        # NEW: Better date parsing
        # NEW: Enhanced ticker symbol extraction
```

**Step 2: Deploy New Version**

```bash
make package-extract-structured
terraform apply  # Deploy Lambda with new code
```

**Step 3: Reprocess Recent Data (2024-2025 only)**

```bash
aws stepfunctions start-execution \
  --state-machine-arn $HOUSE_FD_STATE_MACHINE_ARN \
  --input '{
    "execution_type": "reprocess",
    "years": [2024, 2025],
    "extractor_version": "1.1.0"
  }'
```

**Impact**: Process 1,200 PDFs instead of 50,000 (98% reduction!)

**Step 4: Compare Quality Metrics**

```sql
-- Query DynamoDB extraction_versions table
SELECT
  extractor_version,
  avg_confidence_score,
  documents_processed
FROM extraction_versions
WHERE extractor_class = 'PTRExtractor'
ORDER BY deployment_date DESC
```

**Expected Results**:
| Version | Avg Confidence | Documents | Notes |
|---------|---------------|-----------|-------|
| 1.1.0 | 0.94 | 1,200 | Improved regex, better ticker extraction |
| 1.0.0 | 0.87 | 12,450 | Baseline version |

**Step 5: Validate Output**

```bash
# Compare sample outputs
aws s3 cp s3://bucket/silver/.../extractor_version=1.0.0/year=2024/10078945.json v1.json
aws s3 cp s3://bucket/silver/.../extractor_version=1.1.0/year=2024/10078945.json v1.1.json
diff -u v1.json v1.1.json
```

**Step 6: Migrate Gold Layer**

Update Gold layer to use new version:

```python
# ingestion/lambdas/build_fact_transactions/handler.py
PREFERRED_EXTRACTOR_VERSION = "1.1.0"  # Pin to validated version
```

**Step 7: Cleanup (Automatic)**

After 90 days, S3 lifecycle policy deletes old extraction versions.

---

## Implementation Status (Sprint 2)

### ✅ Completed
- [x] DynamoDB `extraction_versions` table created
- [x] S3 lifecycle policy added (90-day expiration)
- [x] Type P (PTR) extractor versioned
- [x] Extraction metadata includes version fields
- [x] Documentation created

### 🔄 In Progress
- [ ] Add versioning to remaining 5 extractors:
  - [ ] Type A/B (Annual) - `type_a_b_annual/extractor.py`
  - [ ] Type T (Termination) - `type_t_termination/extractor.py`
  - [ ] Type X (Extension) - `type_x_extension_request/extractor.py`
  - [ ] Type D (Campaign Notice) - `type_d_campaign_notice/extractor.py`
  - [ ] Type W (Withdrawal) - `type_w_withdrawal_notice/extractor.py`

### 📋 Future Work (Sprint 3/4)
- [ ] Update `house_fd_extract_structured_code` Lambda to use versioned S3 paths
- [ ] Create helper script: `scripts/compare_extractor_versions.py`
- [ ] Add Grafana dashboard for version quality metrics
- [ ] Implement automatic version promotion based on quality gates

---

## Terraform Resources

**DynamoDB Table**:
```bash
terraform state show aws_dynamodb_table.extraction_versions
```

**S3 Lifecycle Rule**:
```bash
aws s3api get-bucket-lifecycle-configuration \
  --bucket congress-disclosures-standardized \
  | jq '.Rules[] | select(.Id == "silver-versioned-extractions-cleanup")'
```

---

## Cost Impact

**Before Versioning**:
- Reprocessing improvement: 50,000 PDFs × $0.0001/extraction = **$5.00**
- Lambda execution time: ~12 hours

**After Versioning**:
- Reprocessing recent years: 1,200 PDFs × $0.0001/extraction = **$0.12**
- Lambda execution time: ~20 minutes
- **Cost savings: 98%** ($4.88 per quality improvement)

**Storage Cost**:
- Versioned extractions: ~100MB per year × $0.023/GB/month = **$0.002/month**
- Negligible compared to reprocessing savings

---

## References

- Sprint 2 Plan: `docs/agile/sprints/SPRINT_02_GOLD_LAYER.md`
- Data Quality Strategy: `docs/agile/DATA_QUALITY_AND_VERSIONING_STRATEGY.md` (if exists)
- Extraction Architecture: `docs/EXTRACTION_ARCHITECTURE.md`

**Last Updated**: 2025-12-15
**Owner**: Engineering Team
