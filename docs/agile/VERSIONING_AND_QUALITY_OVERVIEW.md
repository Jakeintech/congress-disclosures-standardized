# Data Versioning & Quality: Complete Overview

**Purpose**: Quick reference for how extraction versioning, SCD Type 2, and quality controls work together

**Last Updated**: 2025-12-14

---

## The Complete Picture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BRONZE LAYER (Immutable Source)                       │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ year=2024/filing_type=type_p/pdfs/20063228.pdf                 │    │
│  │ Metadata: extraction-processed: true ✓                         │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Extract (pypdf → OCR fallback)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              SILVER LAYER (Multi-Version Normalized)                     │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ filing_type=type_p/                                            │    │
│  │   ├── extractor_version=1.0.0/                                │    │
│  │   │   └── 20063228.json  (confidence: 0.87, amount_low: 87%)  │    │
│  │   ├── extractor_version=1.1.0/  ← NEW VERSION (improved)      │    │
│  │   │   └── 20063228.json  (confidence: 0.94, amount_low: 94%)  │    │
│  │   └── latest → 1.1.0  (symlink to production version)         │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  DynamoDB Version Registry:                                             │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ filing_type=type_p, version=1.1.0, is_production=True         │    │
│  │ quality_metrics: {amount_low: 0.94, avg_confidence: 0.94}     │    │
│  │ deployed_at: 2025-01-15, changelog: "Improved amount parsing" │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Transform (version-aware read)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                GOLD LAYER (Star Schema + SCD Type 2)                     │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  DIMENSIONS (SCD Type 2 where applicable)                   │       │
│  │                                                               │       │
│  │  dim_members (Type 2):                                       │       │
│  │  ┌────────────────────────────────────────────────────────┐ │       │
│  │  │ member_key: 1234 (surrogate key, version 1)           │ │       │
│  │  │ bioguide_id: V000133 (natural key)                    │ │       │
│  │  │ party: Democrat                                        │ │       │
│  │  │ effective_from: 2019-01-03                            │ │       │
│  │  │ effective_to: 2019-12-19  ← CLOSED (party switch)    │ │       │
│  │  │ is_current: False                                     │ │       │
│  │  │ version: 1                                            │ │       │
│  │  └────────────────────────────────────────────────────────┘ │       │
│  │  ┌────────────────────────────────────────────────────────┐ │       │
│  │  │ member_key: 1235 (surrogate key, version 2)           │ │       │
│  │  │ bioguide_id: V000133 (same natural key)               │ │       │
│  │  │ party: Republican  ← NEW VALUE                        │ │       │
│  │  │ effective_from: 2019-12-19                            │ │       │
│  │  │ effective_to: NULL  (still current)                   │ │       │
│  │  │ is_current: True                                      │ │       │
│  │  │ version: 2                                            │ │       │
│  │  └────────────────────────────────────────────────────────┘ │       │
│  │                                                               │       │
│  │  dim_assets (Type 1): Overwrite, no versioning              │       │
│  │  dim_dates (Type 0): Static reference data                  │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  FACTS (with extraction version lineage)                    │       │
│  │                                                               │       │
│  │  fact_ptr_transactions:                                      │       │
│  │  ┌────────────────────────────────────────────────────────┐ │       │
│  │  │ transaction_key: abc123                                │ │       │
│  │  │ member_key: 1234  ← Links to Democrat version (SCD2)  │ │       │
│  │  │ transaction_date: 2019-03-15                          │ │       │
│  │  │ ticker: AAPL                                          │ │       │
│  │  │ amount_low: 15001                                     │ │       │
│  │  │ extractor_version: 1.1.0  ← Lineage tracking         │ │       │
│  │  │ extraction_quality_score: 0.94                        │ │       │
│  │  └────────────────────────────────────────────────────────┘ │       │
│  │                                                               │       │
│  │  Point-in-time join ensures:                                 │       │
│  │    transaction_date BETWEEN effective_from AND effective_to  │       │
│  └─────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Quality Checks (Soda)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      QUALITY VALIDATION LAYER                            │
│                                                                          │
│  Bronze Checks:                                                         │
│    ✓ All PDFs have doc_id                                              │
│    ✓ No duplicate PDFs                                                 │
│    ✓ Extraction metadata valid                                         │
│                                                                          │
│  Silver Checks:                                                         │
│    ✓ Avg confidence ≥ 85%                                              │
│    ✓ Amount field extraction ≥ 85%                                     │
│    ⚠ Quality regression detection (fail if drops >10%)                 │
│    ✓ All objects have extractor_version                                │
│                                                                          │
│  Gold Checks:                                                           │
│    ✓ No duplicate current members (SCD Type 2 integrity)              │
│    ✓ No gaps in effective date ranges                                 │
│    ✓ All member_keys in facts exist in dimensions (referential)       │
│    ✓ Transaction dates within member effective ranges                 │
│    ✓ Amount ranges logical (low ≤ high)                               │
│                                                                          │
│  If CRITICAL checks fail → Pipeline fails → SNS alert                  │
│  If WARNINGS detected → Pipeline continues → SNS notification          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Monitor
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   CLOUDWATCH QUALITY DASHBOARD                           │
│                                                                          │
│  Extraction Confidence Scores (7-Day Average)                           │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │ Type P v1.1.0:  ████████████████████  94%  ↑ +7%           │       │
│  │ Type P v1.0.0:  ███████████████       87%                  │       │
│  │ Type A v1.0.0:  ████████████████      89%                  │       │
│  │ Type T v1.0.0:  ████████████          72%  ⚠ Needs work    │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                          │
│  Version Adoption Rate (Type P)                                         │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │ v1.1.0:  ████████░░░░░░░░░░░░  24% (12,450 / 52,320)       │       │
│  │ Target: 100% by Jan 31                                      │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                          │
│  Quality Regression Alarms                                              │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │ ✅ Type P - No regressions                                  │       │
│  │ ⚠️  Type T - Filer name field down 3% (alert sent)          │       │
│  └─────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Workflow: Improving Extraction Quality

### Problem
Type P extractor has 87% accuracy on `amount_low` field. We want to improve to 94%.

### Solution: Iterative Improvement (No Full Reprocessing!)

#### Step 1: Develop Improved Extractor
```python
# ingestion/lib/extractors/type_p_ptr/extractor.py
class PTRExtractor(BaseExtractor):
    __version__ = "1.1.0"  # ← Bump from 1.0.0
    __changelog__ = {
        "1.1.0": "Improved amount parsing with better regex (+7%)"
    }
```

#### Step 2: Deploy & Test on Sample
```bash
# Deploy new version
make package-extract-structured
make deploy-extractors

# Test on 2024-2025 only (1,200 PDFs, 15 minutes)
aws lambda invoke --function-name reprocess-filings --payload '{
  "filing_type": "type_p",
  "year_range": [2024, 2025],
  "extractor_version": "1.1.0",
  "comparison_mode": true
}' output.json

# Review comparison report
cat output.json | jq '.comparison.quality_improvements'
# {
#   "amount_low_extraction": {"old": 0.87, "new": 0.94, "delta": "+7%"},
#   "regressions": []  ← No fields got worse!
# }
```

#### Step 3: Promote to Production
```python
# New version is better → promote
promote_version_to_production(
    filing_type="type_p",
    new_version="1.1.0"
)

# DynamoDB: is_production=True for v1.1.0
# Gold layer now reads from extractor_version=1.1.0/
```

#### Step 4: Gradually Reprocess Older Years
```bash
# Reprocess 2020-2023 when capacity allows
aws lambda invoke --function-name reprocess-filings --payload '{
  "filing_type": "type_p",
  "year_range": [2020, 2023],
  "extractor_version": "1.1.0"
}'

# Monitor version adoption in CloudWatch dashboard
# 24% → 48% → 72% → 100% over weeks
```

#### Step 5: Rollback if Needed (Safety Net)
```python
# If new version causes issues downstream
rollback_version(
    filing_type="type_p",
    rollback_to_version="1.0.0"
)

# Gold layer instantly switches back to old extractions
# No data loss - both versions still in Silver
```

---

## Story Dependencies

### Sprint 2: Foundation
**STORY-054: Extraction Versioning** (5 hours, Day 3)
- ✅ Add `__version__` to all extractors
- ✅ Multi-version Silver storage
- ✅ DynamoDB version registry
- ✅ Version-aware Gold layer scripts

**Blocks**: STORY-055 (can't reprocess without versioning)
**Enables**: Iterative quality improvements

---

### Sprint 3: Quality Infrastructure
**STORY-055: Selective Reprocessing** (8 hours, Day 4)
- ✅ Reprocess by filing type + year range
- ✅ Comparison report generation
- ✅ Version promotion/rollback

**Requires**: STORY-054 (versioning infrastructure)
**Enables**: Gradual quality improvements without full reprocessing

---

**STORY-048: Soda Quality Checks** (5 hours, Day 3)
- ✅ 15+ YAML check definitions
- ✅ Bronze/Silver/Gold validation
- ✅ Regression detection

**Complements**: STORY-054/055 (validates improvements)

---

**STORY-049: SCD Type 2 Dimensions** (3 hours, Day 3)
- ✅ dim_members tracks party/district changes
- ✅ Point-in-time fact joins
- ✅ SCD Type 2 integrity checks

**Independent**: Can be implemented separately
**Enables**: Historical accuracy for queries

---

**STORY-033: run_soda_checks Lambda** (5 hours, Day 3)
- ✅ Lambda wrapper for Soda Core
- ✅ Severity-based failures
- ✅ SNS notifications

**Requires**: STORY-048 (YAML definitions)
**Integrates**: State machine quality gate

---

### Sprint 4: Monitoring
**STORY-056: Extraction Quality Dashboard** (3 hours, Day 1)
- ✅ CloudWatch dashboard
- ✅ Confidence score trends
- ✅ Version adoption tracking
- ✅ Regression alarms

**Requires**: STORY-054 (metrics from versioned extractions)
**Enhances**: Visibility into quality improvements

---

## Key Benefits

### 1. Iterative Quality Improvement
**Before**: Must reprocess ALL 50,000 PDFs (8+ hours) to improve extraction
**After**: Reprocess sample (1,200 PDFs, 15 minutes), validate, then gradually migrate

### 2. Data Lineage & Auditability
**Before**: Unknown which extraction logic produced each Gold record
**After**: Every fact has `extractor_version` and `extraction_quality_score`

### 3. Risk Mitigation
**Before**: New extractor might be worse, no rollback
**After**: Comparison reports detect regressions, rollback in seconds

### 4. Historical Accuracy (SCD Type 2)
**Before**: "What did Democrats trade in 2018?" returns wrong results if member switched parties
**After**: Point-in-time joins ensure correct member attributes at transaction date

### 5. Cost Optimization
**Before**: Reprocess entire dataset for every improvement
**After**: Selective reprocessing (10-20x less Lambda compute)

---

## Testing Coverage

### Unit Tests (30+ tests)
- Extractor version comparison
- SCD Type 2 change detection
- Soda check YAML parsing
- Version promotion/rollback logic

### Integration Tests (15+ tests)
- Multi-version Silver storage
- Comparison report generation
- Quality check failures → SNS
- State machine executes with quality gates

### E2E Tests (5 tests)
- Full improvement workflow (deploy → reprocess → promote)
- Rollback scenario
- SCD Type 2 updates propagate to facts

---

## Success Metrics

- [ ] All 6 extractor classes have semantic versioning
- [ ] DynamoDB tracks quality metrics per version
- [ ] Selective reprocessing operational (<30 min for 2,000 PDFs)
- [ ] 15+ Soda quality checks enforced
- [ ] SCD Type 2 for dim_members (track party/district changes)
- [ ] CloudWatch dashboard shows quality trends
- [ ] Rollback capability tested and verified
- [ ] 80%+ test coverage for versioning/quality modules

---

## References

- **Full Strategy**: `docs/agile/DATA_QUALITY_AND_VERSIONING_STRATEGY.md`
- **Stories**:
  - `docs/agile/stories/STORY_054_extraction_versioning.md`
  - `docs/agile/stories/STORY_055_selective_reprocessing.md`
  - `docs/agile/stories/STORY_056_extraction_quality_dashboard.md`
  - `docs/agile/stories/STORY_049_dimension_validation_scd2.md`
- **Sprint Plans**:
  - `docs/agile/sprints/SPRINT_02_GOLD_LAYER.md` (STORY-054)
  - `docs/agile/sprints/SPRINT_03_INTEGRATION.md` (STORY-055, STORY-048, STORY-049, STORY-033)

---

**Ownership**: Data Engineering Team
**Status**: Ready for implementation (Sprint 2-3)
