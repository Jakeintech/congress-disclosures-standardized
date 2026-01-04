# Selective Reprocessing Lambda (STORY-055)

## Overview

The `reprocess_filings` Lambda enables selective reprocessing of filings when extraction logic improves. This allows for iterative data quality improvements without reprocessing the entire dataset.

## Key Features

- **Selective Reprocessing**: Target specific filing types and year ranges
- **Version Comparison**: Automatic quality comparison between baseline and new versions
- **Side-by-Side Storage**: Multiple extraction versions coexist (no data loss)
- **Rollback Support**: Revert to previous version if new extractor underperforms
- **Dry Run Mode**: Validate reprocessing scope without executing

## Usage

### Basic Reprocessing

```bash
aws lambda invoke \
  --function-name congress-disclosures-reprocess-filings \
  --payload '{
    "filing_type": "type_p",
    "year_range": [2024, 2025],
    "extractor_version": "1.1.0"
  }' \
  output.json
```

### Dry Run (Validate Without Processing)

```bash
aws lambda invoke \
  --function-name congress-disclosures-reprocess-filings \
  --payload '{
    "filing_type": "type_p",
    "year_range": [2024, 2025],
    "extractor_version": "1.1.0",
    "dry_run": true
  }' \
  output.json

cat output.json
# Returns: {"status": "dry_run", "pdfs_found": 1245}
```

### With Custom Batch Size

```bash
aws lambda invoke \
  --function-name congress-disclosures-reprocess-filings \
  --payload '{
    "filing_type": "type_a",
    "year_range": [2020, 2025],
    "extractor_version": "2.0.0",
    "batch_size": 50,
    "comparison_mode": true
  }' \
  output.json
```

### Force Overwrite Existing Extractions

```bash
aws lambda invoke \
  --function-name congress-disclosures-reprocess-filings \
  --payload '{
    "filing_type": "type_p",
    "year_range": [2024, 2024],
    "extractor_version": "1.2.0",
    "overwrite": true
  }' \
  output.json
```

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filing_type` | string | Yes | - | Filing type code (e.g., `type_p`, `type_a`) |
| `year_range` | array[int] | Yes | - | [start_year, end_year] to reprocess |
| `extractor_version` | string | Yes | - | New extractor version (semantic versioning) |
| `comparison_mode` | boolean | No | `true` | Generate before/after quality comparison |
| `dry_run` | boolean | No | `false` | Validate without processing |
| `batch_size` | integer | No | `100` | PDFs per batch |
| `overwrite` | boolean | No | `false` | Overwrite existing extractions |

## Output Structure

```json
{
  "status": "completed",
  "summary": {
    "pdfs_reprocessed": 1245,
    "extractions_succeeded": 1201,
    "extractions_failed": 44,
    "processing_time_seconds": 892,
    "filing_type": "type_p",
    "year_range": [2024, 2025],
    "extractor_version": "1.1.0"
  },
  "comparison": {
    "baseline_version": "1.0.0",
    "new_version": "1.1.0",
    "quality_improvements": {
      "avg_confidence_score": {
        "old": 0.87,
        "new": 0.94,
        "delta": "+7.2%"
      },
      "transaction_date": {
        "old": 0.96,
        "new": 0.98,
        "delta": "+2.1%"
      }
    },
    "regressions": [],
    "new_extractions": 124,
    "recommendation": "PROMOTE"
  },
  "s3_paths": {
    "new_version": "silver/.../extractor_version=1.1.0/",
    "comparison_report": "s3://bucket/reports/reprocessing/..."
  }
}
```

## Version Management

### Promote Version to Production

```python
from lib.version_utils import ExtractionVersionRegistry

registry = ExtractionVersionRegistry('extraction-versions-table')
registry.promote_to_production('PTRExtractor', '1.1.0')
```

### Rollback to Previous Version

```python
registry.rollback_version('PTRExtractor', '1.0.0')
```

### Query Version History

```python
versions = registry.list_versions('PTRExtractor')
for v in versions:
    print(f"{v['extractor_version']}: {v['quality_metrics']}")
```

## Quality Comparison Recommendations

The Lambda provides automated recommendations based on quality metrics:

- **PROMOTE**: Significant improvements, no regressions detected
- **NEUTRAL**: No significant changes
- **REVIEW_REQUIRED**: Quality regressions detected (manual review needed)

## S3 Storage Structure

### Versioned Extractions

```
silver/house/financial/objects/
├── year=2024/
│   └── filing_type=type_p/
│       ├── extractor_version=1.0.0/
│       │   └── doc_id=10063228/
│       │       └── extraction.json
│       └── extractor_version=1.1.0/
│           └── doc_id=10063228/
│               └── extraction.json  # New version (side-by-side)
```

### Comparison Reports

```
reports/reprocessing/
└── type_p_1.0.0_to_1.1.0_20250104_120000.json
```

## DynamoDB Version Registry

The `extraction_versions` table tracks:

- Extractor class and version
- Deployment date
- Quality metrics (avg confidence, field-level scores)
- Production status
- Changelog

**Example Entry**:

```json
{
  "extractor_class": "PTRExtractor",
  "extractor_version": "1.1.0",
  "deployment_date": "2025-01-04T12:00:00Z",
  "is_production": true,
  "quality_metrics": {
    "avg_confidence_score": 0.94,
    "field_extraction_rates": {
      "transaction_date": 0.98,
      "amount_low": 0.94
    },
    "sample_size": 1245
  }
}
```

## Error Handling

The Lambda uses **partial batch failure** patterns:

- Failed PDFs are logged and returned in response
- Successful extractions are committed
- Failed items can be retried independently

## Performance Optimization

- **Batch Processing**: Processes PDFs in configurable batches (default: 100)
- **Timeout**: 15 minutes (sufficient for ~1000 PDFs)
- **Memory**: 2048 MB for parallel processing
- **Concurrent Execution**: Can run multiple instances for different filing types

## Monitoring

**CloudWatch Logs**: `/aws/lambda/congress-disclosures-reprocess-filings`

**Key Metrics**:
- Extraction success rate
- Processing time per batch
- Quality comparison deltas
- Version registry updates

## Example Workflow

### 1. Deploy New Extractor Version

Update extractor code with improvements and deploy:

```python
# ingestion/lib/extractors/type_p_ptr/extractor.py
class PTRExtractor(BaseExtractor):
    EXTRACTOR_VERSION = "1.1.0"  # Increment version
    # ... improved extraction logic ...
```

### 2. Test on Recent Data

```bash
aws lambda invoke \
  --function-name congress-disclosures-reprocess-filings \
  --payload '{
    "filing_type": "type_p",
    "year_range": [2024, 2025],
    "extractor_version": "1.1.0",
    "comparison_mode": true
  }' \
  output.json
```

### 3. Review Quality Comparison

```bash
cat output.json | jq '.comparison'
```

### 4. Promote if Successful

```python
registry.promote_to_production('PTRExtractor', '1.1.0')
```

### 5. Gradually Reprocess Older Years

```bash
# Reprocess 2023
aws lambda invoke ... --payload '{"year_range": [2023, 2023], ...}'

# Reprocess 2022
aws lambda invoke ... --payload '{"year_range": [2022, 2022], ...}'
```

## Benefits

1. **Risk Mitigation**: Side-by-side storage enables A/B testing before promotion
2. **Cost Optimization**: Avoid reprocessing entire dataset (save compute hours)
3. **Data Provenance**: Always know which version produced each extraction
4. **Rollback Safety**: Quick revert if new version underperforms
5. **Incremental Migration**: Gradually improve data quality year-by-year

## Limitations

- Maximum 15-minute execution time per invocation
- For very large datasets, use multiple invocations with different year ranges
- Version comparison limited to metrics from existing extractions

## Related

- **STORY-054**: Extraction Versioning Infrastructure
- **STORY-056**: Extraction Quality Dashboard (displays reprocessing metrics)
- See `docs/agile/stories/active/STORY_055_selective_reprocessing.md` for full specifications
