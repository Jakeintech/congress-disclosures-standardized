# STORY-054: Extraction Versioning Infrastructure

**Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 5 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** data engineer
**I want** version tracking for all extraction logic
**So that** I can iterate on extraction quality without losing data lineage or breaking existing data

## Acceptance Criteria
- **GIVEN** Extraction logic for any filing type
- **WHEN** Data is extracted from Bronze PDFs
- **THEN** Extraction results include `extractor_version` in metadata
- **AND** Silver layer stores multiple extraction versions side-by-side
- **AND** DynamoDB tracks version→quality metrics mapping
- **AND** All extractors follow semantic versioning (MAJOR.MINOR.PATCH)

## Problem Statement

**Current Limitations**:
- No way to track which extractor version produced each extraction
- When we improve Type P extraction logic, must reprocess ALL data or accept inconsistency
- Cannot A/B test extractor improvements
- No rollback capability if new extractor is worse
- Cannot trace data lineage (which Gold records came from which extractor version)

**Real-World Scenario**:
> We improve Type P transaction amount parsing from 87% → 94% accuracy. Currently, we have two bad choices:
> 1. Reprocess ALL 15 years of Type P filings (expensive, time-consuming)
> 2. Accept inconsistency (2020-2024 uses old logic, 2025+ uses new logic)
>
> **Solution**: Version tracking allows selective reprocessing and side-by-side comparison

## Technical Design

### 1. Extractor Version Tracking

**Add version to each extractor class**:
```python
# ingestion/lib/extractors/type_p_ptr/extractor.py

class PTRExtractor(BaseExtractor):
    """Extract structured data from Periodic Transaction Reports."""

    __version__ = "1.0.0"  # NEW: Semantic versioning
    __changelog__ = {
        "1.0.0": "Initial production release",
        "1.1.0": "Improved transaction amount parsing (+7% accuracy)",
        "1.1.1": "Fixed date format edge case for merged text"
    }

    def extract_from_text(self, text: str, pdf_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        # ... existing extraction logic ...

        result["extraction_metadata"]["extractor_version"] = self.__version__
        result["extraction_metadata"]["extractor_class"] = self.__class__.__name__
        result["extraction_metadata"]["baseline_version"] = "1.0.0"  # For comparison
```

**Versioning Guidelines**:
- **MAJOR (1.x.x → 2.x.x)**: Breaking schema changes (field renamed, removed)
- **MINOR (1.0.x → 1.1.x)**: Improvements to extraction logic (better regex, new field added)
- **PATCH (1.0.0 → 1.0.1)**: Bug fixes (no quality improvement expected)

### 2. Silver Layer Multi-Version Storage

**New S3 key structure**:
```
silver/objects/
├── filing_type=type_p/
│   ├── extractor_version=1.0.0/
│   │   ├── 20063228.json
│   │   └── 20074539.json
│   ├── extractor_version=1.1.0/
│   │   ├── 20063228.json  # Same doc_id, new extraction
│   │   └── 20074539.json
│   └── latest -> extractor_version=1.1.0/  # Symlink for current version
```

**Benefits**:
- Multiple versions coexist (no data loss)
- Gold layer can choose which version to use
- Rollback by pointing Gold to previous version
- Storage cost controlled by lifecycle policy (delete old versions after 90 days)

### 3. Extraction Version Registry (DynamoDB)

**Table**: `extraction_versions`
**Primary Key**: `filing_type` (HASH), `extractor_version` (RANGE)

**Schema**:
```python
{
    "filing_type": "type_p",  # PK
    "extractor_version": "1.1.0",  # SK
    "deployed_at": "2025-01-15T10:30:00Z",
    "extractor_class": "PTRExtractor",
    "changelog": "Improved transaction amount parsing (+7% accuracy)",
    "quality_metrics": {
        "avg_confidence_score": 0.91,
        "field_extraction_rates": {
            "transaction_date": 0.98,
            "amount_low": 0.94,  # Improved from 0.87
            "amount_high": 0.94,
            "asset_description": 0.89
        },
        "sample_size": 1245  # Number of filings tested
    },
    "is_production": True,  # False for experimental versions
    "replaced_version": "1.0.0",  # Previous version
    "filings_processed": 15234,  # Total extractions using this version
    "last_used_at": "2025-01-20T14:22:00Z"
}
```

**DynamoDB Indexes**:
- GSI: `is_production` (HASH) + `deployed_at` (RANGE) → Find all production versions by date
- GSI: `filing_type` (HASH) + `is_production` (RANGE) → Get current production version per filing type

### 4. Enhanced Extraction Metadata

**Updated extraction_metadata structure**:
```python
{
    "extractor_version": "1.1.0",  # NEW
    "extractor_class": "PTRExtractor",  # NEW
    "baseline_version": "1.0.0",  # NEW: For comparison
    "extraction_timestamp": "2025-01-15T10:30:00Z",
    "extraction_method": "regex",
    "pdf_type": "text",
    "confidence_score": 0.91,
    "field_confidence": {
        "transaction_date": 0.98,
        "amount_low": 0.94,
        "amount_high": 0.94,
        "asset_description": 0.89
    },
    "data_completeness": 0.87,
    "version_changelog": "Improved transaction amount parsing (+7% accuracy)"  # NEW
}
```

## Implementation Tasks

### Phase 1: Base Extractor Updates (1 hour)
- [ ] Add `__version__` and `__changelog__` to BaseExtractor
- [ ] Update `create_extraction_metadata()` to include version fields
- [ ] Add version comparison utilities (`compare_versions()`, `is_newer_version()`)

### Phase 2: Extractor Versioning (1.5 hours)
- [ ] Add `__version__ = "1.0.0"` to all 6 extractor classes:
  - type_p_ptr/extractor.py
  - type_a_b_annual/extractor.py
  - type_t_termination/extractor.py
  - type_x_extension_request/extractor.py
  - type_d_campaign_notice/extractor.py
  - type_w_withdrawal_notice/extractor.py
- [ ] Update extraction outputs to include version in metadata

### Phase 3: Silver Layer Multi-Version Support (1 hour)
- [ ] Update `house_fd_extract_structured_code` Lambda to write versioned paths
- [ ] Create S3 lifecycle policy to expire old versions after 90 days
- [ ] Update manifest generation to list all available versions

### Phase 4: DynamoDB Version Registry (1 hour)
- [ ] Create `extraction_versions` table via Terraform
- [ ] Add Lambda function to register new versions on deployment
- [ ] Create API to query version history

### Phase 5: Testing (30 min)
- [ ] Unit test: Version comparison logic
- [ ] Integration test: Extract same PDF with two versions, verify both stored
- [ ] E2E test: Deploy new version, verify registration in DynamoDB

## Terraform Resources

```hcl
# infra/terraform/dynamodb_extraction_versions.tf (new file)

resource "aws_dynamodb_table" "extraction_versions" {
  name           = "${local.name_prefix}-extraction-versions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "filing_type"
  range_key      = "extractor_version"

  attribute {
    name = "filing_type"
    type = "S"
  }

  attribute {
    name = "extractor_version"
    type = "S"
  }

  attribute {
    name = "is_production"
    type = "S"
  }

  attribute {
    name = "deployed_at"
    type = "S"
  }

  global_secondary_index {
    name            = "production-versions-index"
    hash_key        = "is_production"
    range_key       = "deployed_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = local.standard_tags
}

# S3 Lifecycle Policy for Old Versions
resource "aws_s3_bucket_lifecycle_configuration" "silver_versioning" {
  bucket = var.s3_bucket_name

  rule {
    id     = "expire-old-extraction-versions"
    status = "Enabled"

    filter {
      prefix = "silver/objects/"
    }

    expiration {
      days = 90  # Delete versions older than 90 days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30  # Keep non-current versions for 30 days
    }
  }
}
```

## Benefits

1. **Iterative Quality Improvement**: Deploy new extractor versions without fear of breaking existing data
2. **A/B Testing**: Compare extraction quality side-by-side before promoting to production
3. **Data Lineage**: Always know which extractor version produced each Gold record
4. **Rollback Safety**: Revert to previous version if new extractor is worse
5. **Targeted Reprocessing**: Only reprocess specific filing types/years (enabled by STORY-055)
6. **Quality Metrics Over Time**: Track extraction accuracy improvements across versions

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Storage cost increase** | Medium | 90-day expiration policy on old versions |
| **Backward compatibility** | High | Enforce semantic versioning, schema validation |
| **Version confusion** | Medium | Clear "latest" symlinks, production flag in registry |
| **Performance overhead** | Low | Minimal (just metadata fields) |

## Testing Strategy

### Unit Tests (5 tests)
```python
# tests/unit/lib/extractors/test_versioning.py

def test_extractor_has_version():
    """Test that all extractors have __version__ attribute."""
    from ingestion.lib.extractors.type_p_ptr.extractor import PTRExtractor
    assert hasattr(PTRExtractor, '__version__')
    assert PTRExtractor.__version__ == "1.0.0"

def test_extraction_metadata_includes_version():
    """Test that extraction metadata includes version fields."""
    extractor = PTRExtractor()
    metadata = extractor.create_extraction_metadata(confidence=0.9, method="regex")
    assert "extractor_version" in metadata
    assert "extractor_class" in metadata
    assert metadata["extractor_class"] == "PTRExtractor"

def test_version_comparison():
    """Test version comparison logic."""
    assert compare_versions("1.1.0", "1.0.0") == 1  # 1.1.0 is newer
    assert compare_versions("1.0.0", "1.1.0") == -1  # 1.0.0 is older
    assert compare_versions("1.0.0", "1.0.0") == 0  # Same

def test_versioned_s3_path():
    """Test that versioned S3 paths are constructed correctly."""
    path = construct_versioned_path(
        filing_type="type_p",
        extractor_version="1.1.0",
        doc_id="20063228"
    )
    assert path == "silver/objects/filing_type=type_p/extractor_version=1.1.0/20063228.json"

def test_version_registry_registration():
    """Test that new versions are registered in DynamoDB."""
    # Mock DynamoDB
    register_extractor_version(
        filing_type="type_p",
        extractor_version="1.1.0",
        changelog="Improved amount parsing"
    )
    # Verify item written to DynamoDB
```

### Integration Test (1 test)
```python
def test_multi_version_storage():
    """Test that multiple versions can coexist in S3."""
    # Extract same PDF with version 1.0.0
    extract_and_store(doc_id="20063228", version="1.0.0")

    # Extract same PDF with version 1.1.0
    extract_and_store(doc_id="20063228", version="1.1.0")

    # Verify both versions exist
    assert s3_object_exists("silver/objects/.../extractor_version=1.0.0/20063228.json")
    assert s3_object_exists("silver/objects/.../extractor_version=1.1.0/20063228.json")
```

## Estimated Effort: 5 hours
- 1 hour: Base extractor version tracking
- 1.5 hours: Add versions to all 6 extractors
- 1 hour: Silver layer multi-version storage
- 1 hour: DynamoDB version registry + Terraform
- 30 min: Testing and validation

## Dependencies
- Requires existing extraction framework (already in place)
- Blocks STORY-055 (Selective Reprocessing) - must have versioning first
- Enables STORY-056 (Extraction Quality Dashboard) - provides version metrics

## AI Development Notes
**Baseline**: ingestion/lib/extractors/base_extractor.py, type_p_ptr/extractor.py
**Pattern**: Semantic versioning + multi-version storage
**Files to Create**:
- infra/terraform/dynamodb_extraction_versions.tf (new)
- ingestion/lib/version_utils.py (new, version comparison utilities)
- tests/unit/lib/extractors/test_versioning.py (new, 5 tests)

**Files to Modify**:
- ingestion/lib/extractors/base_extractor.py:15-50 (add __version__, update create_extraction_metadata)
- ingestion/lib/extractors/type_p_ptr/extractor.py:14-20 (add __version__ = "1.0.0")
- (Repeat for all 6 extractor classes)
- ingestion/lambdas/house_fd_extract_structured_code/handler.py:80-120 (versioned S3 paths)

**Token Budget**: 3,000 tokens (6 extractor updates + DynamoDB table + utilities)

**Acceptance Criteria Verification**:
1. ✅ All extractors have `__version__` attribute
2. ✅ Extraction metadata includes version fields
3. ✅ Silver layer supports multi-version storage
4. ✅ DynamoDB version registry tracks quality metrics
5. ✅ Tests verify version coexistence

**Target**: Sprint 2, Day 3 (December 25, 2025)

---

**NOTE**: This story provides the foundation for STORY-055 (Selective Reprocessing). Without version tracking, reprocessing improvements would be impossible to manage safely.
