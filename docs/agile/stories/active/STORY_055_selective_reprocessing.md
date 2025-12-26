# STORY-055: Selective Reprocessing Lambda

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 8 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** data engineer
**I want** ability to selectively reprocess filings when extraction logic improves
**So that** I can iteratively improve data quality without reprocessing the entire dataset

## Acceptance Criteria
- **GIVEN** Improved extractor version deployed (e.g., Type P v1.1.0)
- **WHEN** I trigger selective reprocessing for specific filing type + year range
- **THEN** Lambda reprocesses only matching PDFs from Bronze layer
- **AND** New extractions stored alongside old versions (not replacing)
- **AND** Comparison report generated showing quality improvements
- **AND** Gold layer can be updated to use new version atomically
- **AND** Rollback capability exists if new version is worse

## Problem Statement

**Current Limitation**:
> When we improve Type P extraction from 87% → 94% accuracy, we face an all-or-nothing choice:
> - **Option A**: Reprocess ALL 50,000 Type P filings (expensive, 8+ hours)
> - **Option B**: Accept inconsistency (old years use old logic, new years use new logic)
>
> **Neither is acceptable for production.**

**Solution**: Selective reprocessing allows targeted improvements:
> 1. Deploy improved Type P v1.1.0
> 2. Reprocess only 2024-2025 Type P filings (1,200 PDFs, 15 minutes)
> 3. Compare v1.0.0 vs v1.1.0 quality metrics
> 4. Promote v1.1.0 to production if better
> 5. Gradually reprocess older years as needed

## Technical Design

### 1. Reprocessing Lambda Function

**Function**: `reprocess_filings`
**Trigger**: Manual invocation (AWS CLI, Step Functions, API Gateway)
**Timeout**: 15 minutes (for chunked processing)
**Memory**: 2048 MB

**Input Schema**:
```python
{
    "filing_type": "type_p",  # Required: "type_p", "type_a", "type_t", etc.
    "year_range": [2024, 2025],  # Required: Years to reprocess
    "extractor_version": "1.1.0",  # Required: New version to use
    "comparison_mode": true,  # Optional: Generate before/after comparison (default: true)
    "dry_run": false,  # Optional: Validate without writing (default: false)
    "batch_size": 100,  # Optional: PDFs per batch (default: 100)
    "overwrite": false  # Optional: Replace old version (default: false, side-by-side)
}
```

**Output Schema**:
```python
{
    "status": "completed",
    "summary": {
        "pdfs_reprocessed": 1245,
        "extractions_succeeded": 1201,
        "extractions_failed": 44,
        "processing_time_seconds": 892
    },
    "comparison": {
        "baseline_version": "1.0.0",
        "new_version": "1.1.0",
        "quality_improvements": {
            "avg_confidence_score": {"old": 0.87, "new": 0.94, "delta": "+7%"},
            "transaction_date_extraction": {"old": 0.96, "new": 0.98, "delta": "+2%"},
            "amount_low_extraction": {"old": 0.87, "new": 0.94, "delta": "+7%"},
            "amount_high_extraction": {"old": 0.87, "new": 0.94, "delta": "+7%"}
        },
        "regressions": [],  # Fields that got worse
        "new_extractions": 124  # Transactions not extracted before
    },
    "s3_paths": {
        "old_version": "silver/objects/filing_type=type_p/extractor_version=1.0.0/",
        "new_version": "silver/objects/filing_type=type_p/extractor_version=1.1.0/",
        "comparison_report": "reports/reprocessing/type_p_v1.0.0_to_v1.1.0_2025-01-15.json"
    }
}
```

### 2. Reprocessing Logic

```python
# ingestion/lambdas/reprocess_filings/handler.py

import boto3
from typing import Dict, List, Any
import concurrent.futures
from datetime import datetime

s3 = boto3.client('s3')
BUCKET = os.environ['S3_BUCKET_NAME']

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Selectively reprocess filings with improved extractor version.

    Args:
        event: Reprocessing configuration (filing_type, year_range, version, etc.)

    Returns:
        Reprocessing results with quality comparison
    """
    # Validate input
    validate_reprocessing_request(event)

    filing_type = event['filing_type']
    year_range = event['year_range']
    new_version = event['extractor_version']
    comparison_mode = event.get('comparison_mode', True)
    dry_run = event.get('dry_run', False)
    batch_size = event.get('batch_size', 100)

    # Step 1: Get list of PDFs to reprocess from Bronze
    pdfs_to_reprocess = get_bronze_pdfs(
        filing_type=filing_type,
        year_range=year_range
    )

    logger.info(f"Found {len(pdfs_to_reprocess)} PDFs to reprocess")

    if dry_run:
        return {"status": "dry_run", "pdfs_found": len(pdfs_to_reprocess)}

    # Step 2: Get baseline quality metrics (from old version)
    baseline_metrics = None
    if comparison_mode:
        baseline_version = get_current_production_version(filing_type)
        baseline_metrics = calculate_baseline_metrics(
            filing_type=filing_type,
            version=baseline_version,
            pdfs=pdfs_to_reprocess
        )

    # Step 3: Reprocess PDFs in batches
    results = []
    for batch in chunk_list(pdfs_to_reprocess, batch_size):
        batch_results = process_batch(
            pdfs=batch,
            filing_type=filing_type,
            extractor_version=new_version
        )
        results.extend(batch_results)

    # Step 4: Calculate new quality metrics
    new_metrics = calculate_quality_metrics(results)

    # Step 5: Generate comparison report
    comparison = None
    if comparison_mode and baseline_metrics:
        comparison = generate_comparison_report(
            baseline_metrics=baseline_metrics,
            new_metrics=new_metrics,
            baseline_version=baseline_version,
            new_version=new_version
        )

        # Store comparison report in S3
        report_key = f"reports/reprocessing/{filing_type}_{baseline_version}_to_{new_version}_{datetime.utcnow().isoformat()}.json"
        s3.put_object(
            Bucket=BUCKET,
            Key=report_key,
            Body=json.dumps(comparison, indent=2),
            ContentType='application/json'
        )

    # Step 6: Update version registry
    update_version_registry(
        filing_type=filing_type,
        version=new_version,
        quality_metrics=new_metrics,
        filings_processed=len(results)
    )

    return {
        "status": "completed",
        "summary": {
            "pdfs_reprocessed": len(results),
            "extractions_succeeded": len([r for r in results if r['status'] == 'success']),
            "extractions_failed": len([r for r in results if r['status'] == 'failed']),
            "processing_time_seconds": context.get_remaining_time_in_millis() / 1000
        },
        "comparison": comparison,
        "s3_paths": {
            "new_version": f"silver/objects/filing_type={filing_type}/extractor_version={new_version}/",
            "comparison_report": report_key if comparison else None
        }
    }


def get_bronze_pdfs(filing_type: str, year_range: List[int]) -> List[Dict[str, str]]:
    """Get list of PDFs from Bronze layer matching criteria."""
    pdfs = []

    for year in range(year_range[0], year_range[1] + 1):
        prefix = f"bronze/house/financial/year={year}/filing_type={filing_type}/pdfs/"

        # List all PDFs in Bronze
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
            for obj in page.get('Contents', []):
                if obj['Key'].endswith('.pdf'):
                    doc_id = obj['Key'].split('/')[-1].replace('.pdf', '')
                    pdfs.append({
                        'doc_id': doc_id,
                        'year': year,
                        'filing_type': filing_type,
                        's3_key': obj['Key']
                    })

    return pdfs


def process_batch(pdfs: List[Dict[str, str]], filing_type: str, extractor_version: str) -> List[Dict[str, Any]]:
    """Process batch of PDFs with new extractor version."""
    results = []

    # Import extractor dynamically based on filing type
    extractor_class = get_extractor_class(filing_type, extractor_version)

    for pdf_info in pdfs:
        try:
            # Download PDF from Bronze
            pdf_bytes = download_pdf(pdf_info['s3_key'])

            # Extract with new version
            extractor = extractor_class(pdf_bytes=pdf_bytes)
            extraction_result = extractor.extract_with_fallback()

            # Write to Silver with versioned path
            silver_key = construct_versioned_path(
                filing_type=filing_type,
                extractor_version=extractor_version,
                doc_id=pdf_info['doc_id']
            )

            s3.put_object(
                Bucket=BUCKET,
                Key=silver_key,
                Body=json.dumps(extraction_result, indent=2),
                ContentType='application/json'
            )

            results.append({
                'doc_id': pdf_info['doc_id'],
                'status': 'success',
                'confidence_score': extraction_result['extraction_metadata']['confidence_score'],
                'extraction_metadata': extraction_result['extraction_metadata']
            })

        except Exception as e:
            logger.error(f"Failed to process {pdf_info['doc_id']}: {str(e)}")
            results.append({
                'doc_id': pdf_info['doc_id'],
                'status': 'failed',
                'error': str(e)
            })

    return results


def generate_comparison_report(baseline_metrics, new_metrics, baseline_version, new_version):
    """Generate before/after comparison report."""
    improvements = {}
    regressions = []

    # Compare confidence scores
    for field in baseline_metrics['field_confidence']:
        old_val = baseline_metrics['field_confidence'][field]
        new_val = new_metrics['field_confidence'][field]

        delta = new_val - old_val
        delta_pct = (delta / old_val * 100) if old_val > 0 else 0

        improvements[field] = {
            "old": round(old_val, 4),
            "new": round(new_val, 4),
            "delta": f"{delta_pct:+.1f}%"
        }

        # Flag regressions
        if delta < -0.01:  # More than 1% worse
            regressions.append({
                "field": field,
                "old": old_val,
                "new": new_val,
                "delta": delta_pct
            })

    return {
        "baseline_version": baseline_version,
        "new_version": new_version,
        "quality_improvements": improvements,
        "regressions": regressions,
        "new_extractions": new_metrics.get('new_extractions_count', 0),
        "overall_improvement": improvements.get('avg_confidence_score', {}).get('delta', "N/A")
    }
```

### 3. State Machine Integration

**Add optional reprocessing branch to unified state machine**:

```json
{
  "GoldAggregates": {
    "Type": "Parallel",
    "Next": "CheckReprocessingRequested"
  },
  "CheckReprocessingRequested": {
    "Type": "Choice",
    "Choices": [
      {
        "Variable": "$.reprocessing_requested",
        "BooleanEquals": true,
        "Next": "ReprocessFilings"
      }
    ],
    "Default": "RunSodaChecks"
  },
  "ReprocessFilings": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${LAMBDA_REPROCESS_FILINGS}",
    "ResultPath": "$.reprocessing_results",
    "Catch": [
      {
        "ErrorEquals": ["States.ALL"],
        "ResultPath": "$.error",
        "Next": "NotifyReprocessingFailure"
      }
    ],
    "Next": "EvaluateReprocessingResults"
  },
  "EvaluateReprocessingResults": {
    "Type": "Choice",
    "Choices": [
      {
        "Variable": "$.reprocessing_results.comparison.regressions",
        "IsPresent": true,
        "Next": "NotifyRegressionsDetected"
      }
    ],
    "Default": "RunSodaChecks"
  },
  "NotifyRegressionsDetected": {
    "Type": "Task",
    "Resource": "arn:aws:states:::sns:publish",
    "Parameters": {
      "TopicArn": "${SNS_PIPELINE_ALERTS_ARN}",
      "Subject": "⚠️ Extraction Quality Regressions Detected",
      "Message.$": "States.JsonToString($.reprocessing_results.comparison)"
    },
    "Next": "RunSodaChecks"
  }
}
```

### 4. Promotion & Rollback Strategy

**Promote new version to production**:
```python
def promote_version_to_production(filing_type: str, new_version: str):
    """Update Gold layer to use new extraction version."""
    # Update DynamoDB version registry
    dynamodb.update_item(
        TableName='extraction_versions',
        Key={'filing_type': filing_type, 'extractor_version': new_version},
        UpdateExpression='SET is_production = :true',
        ExpressionAttributeValues={':true': True}
    )

    # Update Gold layer to read from new version
    # (Gold Lambdas check version registry to determine which Silver path to read)
```

**Rollback to previous version**:
```python
def rollback_version(filing_type: str, rollback_to_version: str):
    """Rollback to previous extraction version."""
    # Mark current version as non-production
    current_version = get_current_production_version(filing_type)
    dynamodb.update_item(
        TableName='extraction_versions',
        Key={'filing_type': filing_type, 'extractor_version': current_version},
        UpdateExpression='SET is_production = :false',
        ExpressionAttributeValues={':false': False}
    )

    # Promote rollback version
    promote_version_to_production(filing_type, rollback_to_version)

    # Send SNS notification
    sns.publish(
        TopicArn=os.environ['SNS_ALERTS_ARN'],
        Subject=f"Extraction version rolled back: {filing_type}",
        Message=f"Rolled back from {current_version} to {rollback_to_version}"
    )
```

## Usage Examples

### Example 1: Reprocess 2024-2025 Type P Filings
```bash
aws lambda invoke \
  --function-name reprocess-filings \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "filing_type": "type_p",
    "year_range": [2024, 2025],
    "extractor_version": "1.1.0",
    "comparison_mode": true
  }' \
  output.json

cat output.json
# {
#   "status": "completed",
#   "summary": {
#     "pdfs_reprocessed": 1245,
#     "extractions_succeeded": 1201,
#     "extractions_failed": 44
#   },
#   "comparison": {
#     "overall_improvement": "+7.2%",
#     "regressions": []
#   }
# }
```

### Example 2: Dry Run (Validate Without Processing)
```bash
aws lambda invoke \
  --function-name reprocess-filings \
  --payload '{
    "filing_type": "type_a",
    "year_range": [2020, 2025],
    "extractor_version": "2.0.0",
    "dry_run": true
  }' \
  output.json

# Returns: {"status": "dry_run", "pdfs_found": 8420}
```

### Example 3: Promote Version After Successful Reprocessing
```python
# After reviewing comparison report and confirming improvements:
promote_version_to_production(
    filing_type="type_p",
    new_version="1.1.0"
)
```

### Example 4: Rollback If New Version Has Issues
```python
# If new version causes downstream issues:
rollback_version(
    filing_type="type_p",
    rollback_to_version="1.0.0"
)
```

## Terraform Resources

```hcl
# infra/terraform/lambda_reprocess_filings.tf (new file)

resource "aws_lambda_function" "reprocess_filings" {
  function_name = "${local.name_prefix}-reprocess-filings"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 900  # 15 minutes
  memory_size   = 2048

  filename         = "${path.module}/../../lambda_packages/reprocess_filings.zip"
  source_code_hash = filebase64sha256("${path.module}/../../lambda_packages/reprocess_filings.zip")

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      DYNAMODB_VERSIONS_TABLE = aws_dynamodb_table.extraction_versions.name
      SNS_ALERTS_ARN = aws_sns_topic.pipeline_alerts.arn
      LOG_LEVEL = "INFO"
    }
  }

  tags = local.standard_tags
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "reprocess_filings_logs" {
  name              = "/aws/lambda/${aws_lambda_function.reprocess_filings.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days
  tags              = local.standard_tags
}

# IAM Policy for Bronze/Silver access
resource "aws_iam_role_policy" "reprocess_filings_s3" {
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.main.arn}/bronze/*",
          "${aws_s3_bucket.main.arn}/silver/*",
          "${aws_s3_bucket.main.arn}/reports/*"
        ]
      }
    ]
  })
}
```

## Benefits

1. **Targeted Quality Improvements**: Only reprocess filings that benefit from new extractor
2. **Risk Mitigation**: Compare quality before/after, detect regressions early
3. **Cost Optimization**: Avoid reprocessing entire dataset (save hours of Lambda compute)
4. **Data Provenance**: Multiple versions coexist, always know which version produced data
5. **Rollback Safety**: Can revert to previous version if new extractor causes issues
6. **Incremental Migration**: Gradually migrate to new version year-by-year

## Testing Strategy

### Unit Tests (8 tests)
```python
# tests/unit/lambdas/test_reprocess_filings.py

def test_get_bronze_pdfs_by_year_range():
    """Test that Bronze PDFs are correctly filtered by year range."""

def test_reprocessing_request_validation():
    """Test that invalid requests are rejected with clear error messages."""

def test_comparison_report_generation():
    """Test that comparison report correctly identifies improvements and regressions."""

def test_version_promotion():
    """Test that promoting a version updates DynamoDB and Gold layer reads new version."""

def test_version_rollback():
    """Test that rolling back a version reverts to previous extraction data."""

def test_dry_run_mode():
    """Test that dry run mode validates without writing any data."""

def test_batch_processing():
    """Test that large datasets are processed in batches without timeout."""

def test_regression_detection():
    """Test that quality regressions are detected and flagged in comparison report."""
```

### Integration Test (2 tests)
```python
# tests/integration/test_reprocessing_e2e.py

def test_reprocess_type_p_2024():
    """End-to-end test: Reprocess 2024 Type P filings with new version."""
    # Deploy new extractor version 1.1.0
    # Reprocess 2024 Type P filings
    # Verify new extractions in Silver
    # Verify comparison report generated
    # Verify version registry updated

def test_reprocessing_with_rollback():
    """Test reprocessing followed by rollback if new version is worse."""
    # Reprocess with intentionally worse extractor
    # Verify regressions detected
    # Rollback to previous version
    # Verify Gold layer uses old version again
```

## Estimated Effort: 8 hours
- 2 hours: Lambda function (reprocessing logic, batch processing)
- 2 hours: Comparison report generation (before/after metrics)
- 2 hours: Version promotion/rollback utilities
- 1 hour: State machine integration (optional reprocessing branch)
- 1 hour: Terraform + testing

## Dependencies
- **Requires STORY-054**: Extraction versioning infrastructure must exist first
- **Enables STORY-056**: Extraction quality dashboard displays reprocessing metrics
- **Blocks**: None (optional enhancement, doesn't block production)

## AI Development Notes
**Baseline**: Lambda batch processing pattern + S3 select for filtering
**Pattern**: Parallel processing with MaxConcurrency + comparison report generation
**Files to Create**:
- ingestion/lambdas/reprocess_filings/handler.py (new, ~400 lines)
- ingestion/lib/version_comparison.py (new, comparison utilities)
- infra/terraform/lambda_reprocess_filings.tf (new)
- tests/unit/lambdas/test_reprocess_filings.py (new, 8 tests)
- tests/integration/test_reprocessing_e2e.py (new, 2 tests)

**Files to Modify**:
- state_machines/congress_data_platform.json:350-400 (add reprocessing branch)

**Token Budget**: 4,500 tokens (Lambda + comparison logic + Terraform + tests)

**Acceptance Criteria Verification**:
1. ✅ Selective reprocessing by filing type + year range
2. ✅ Multi-version storage (no data loss)
3. ✅ Comparison report with quality improvements
4. ✅ Version promotion/rollback capability
5. ✅ State machine integration (optional trigger)

**Target**: Sprint 3, Day 4 (January 2, 2026)

---

**NOTE**: This story builds on STORY-054 (versioning) and enables data quality iteration without fear of breaking production data. Critical for long-term maintainability.
