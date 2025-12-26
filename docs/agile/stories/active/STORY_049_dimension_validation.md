# STORY-049: Add Dimension Validation Step

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 3 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** data quality engineer
**I want** validation that all dimensions exist before building facts
**So that** fact tables don't have orphaned foreign keys or referential integrity issues

## Acceptance Criteria
- **GIVEN** Gold dimensions phase completes
- **WHEN** Validation step executes
- **THEN** Verifies all 5 dimension tables exist in S3
- **AND** Checks each dimension has row_count > 0
- **AND** Validates dimension primary keys are unique
- **AND** Fails gracefully with clear error message if any dimension missing
- **AND** Logs validation results to CloudWatch

## Technical Tasks
- [ ] Create `validate_dimensions` Lambda function
- [ ] Check S3 for all dimension Parquet files
- [ ] Read each dimension and count rows
- [ ] Validate primary key uniqueness for each dimension
- [ ] Return validation report with pass/fail status
- [ ] Add state to unified state machine between dimensions and facts
- [ ] Add unit tests (5 test cases)
- [ ] Deploy via Terraform

## Implementation

### Lambda Handler
```python
# ingestion/lambdas/validate_dimensions/handler.py
import boto3
import pyarrow.parquet as pq
from typing import Dict, List, Any

s3 = boto3.client('s3')
BUCKET = os.environ['S3_BUCKET_NAME']

REQUIRED_DIMENSIONS = [
    {
        'name': 'dim_members',
        'path': 'gold/house/financial/dimensions/members/dim_members.parquet',
        'primary_key': 'member_key'
    },
    {
        'name': 'dim_assets',
        'path': 'gold/house/financial/dimensions/assets/dim_assets.parquet',
        'primary_key': 'asset_key'
    },
    {
        'name': 'dim_bills',
        'path': 'gold/house/financial/dimensions/bills/dim_bills.parquet',
        'primary_key': 'bill_key'
    },
    {
        'name': 'dim_lobbyists',
        'path': 'gold/house/financial/dimensions/lobbyists/dim_lobbyists.parquet',
        'primary_key': 'lobbyist_key'
    },
    {
        'name': 'dim_dates',
        'path': 'gold/house/financial/dimensions/dates/dim_dates.parquet',
        'primary_key': 'date_key'
    }
]

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Validate that all dimension tables exist and are valid.

    Returns:
        {
            'validation_passed': bool,
            'dimensions_validated': int,
            'failures': List[str],
            'details': Dict[str, Any]
        }
    """
    results = []
    failures = []

    for dim in REQUIRED_DIMENSIONS:
        try:
            result = validate_dimension(dim)
            results.append(result)

            if not result['passed']:
                failures.append(f"{dim['name']}: {result['error']}")

        except Exception as e:
            error_msg = f"{dim['name']}: Unexpected error - {str(e)}"
            failures.append(error_msg)
            results.append({
                'dimension': dim['name'],
                'passed': False,
                'error': str(e)
            })

    validation_passed = len(failures) == 0

    response = {
        'validation_passed': validation_passed,
        'dimensions_validated': len(REQUIRED_DIMENSIONS),
        'dimensions_passed': len([r for r in results if r['passed']]),
        'dimensions_failed': len(failures),
        'failures': failures,
        'details': results
    }

    # Log summary
    if validation_passed:
        print(f"✓ All {len(REQUIRED_DIMENSIONS)} dimensions validated successfully")
    else:
        print(f"✗ Validation failed: {len(failures)} dimension(s) have issues")
        for failure in failures:
            print(f"  - {failure}")

    return response

def validate_dimension(dim: Dict[str, str]) -> Dict[str, Any]:
    """
    Validate a single dimension table.

    Returns:
        {
            'dimension': str,
            'passed': bool,
            'row_count': int,
            'has_duplicates': bool,
            'error': str | None
        }
    """
    dim_name = dim['name']
    s3_path = dim['path']
    primary_key = dim['primary_key']

    # Step 1: Check if file exists
    try:
        s3.head_object(Bucket=BUCKET, Key=s3_path)
    except s3.exceptions.NoSuchKey:
        return {
            'dimension': dim_name,
            'passed': False,
            'error': f"File not found: s3://{BUCKET}/{s3_path}"
        }

    # Step 2: Read Parquet and count rows
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=s3_path)
        table = pq.read_table(obj['Body'])
        row_count = len(table)

        if row_count == 0:
            return {
                'dimension': dim_name,
                'passed': False,
                'row_count': 0,
                'error': 'Dimension table is empty (0 rows)'
            }

        # Step 3: Check for duplicate primary keys
        pk_column = table[primary_key].to_pylist()
        unique_count = len(set(pk_column))
        has_duplicates = unique_count < row_count

        if has_duplicates:
            return {
                'dimension': dim_name,
                'passed': False,
                'row_count': row_count,
                'has_duplicates': True,
                'error': f'Duplicate primary keys found: {row_count} rows but only {unique_count} unique keys'
            }

        # All checks passed
        return {
            'dimension': dim_name,
            'passed': True,
            'row_count': row_count,
            'has_duplicates': False,
            'error': None
        }

    except Exception as e:
        return {
            'dimension': dim_name,
            'passed': False,
            'error': f'Error reading Parquet: {str(e)}'
        }
```

### State Machine Integration
```json
{
  "GoldDimensions": {
    "Type": "Parallel",
    "Next": "ValidateDimensions",
    "Comment": "Build all dimension tables in parallel"
  },
  "ValidateDimensions": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${LAMBDA_VALIDATE_DIMENSIONS}",
    "ResultPath": "$.validation_results",
    "Catch": [
      {
        "ErrorEquals": ["States.ALL"],
        "ResultPath": "$.error",
        "Next": "NotifyValidationFailure"
      }
    ],
    "Next": "CheckValidationResults"
  },
  "CheckValidationResults": {
    "Type": "Choice",
    "Choices": [
      {
        "Variable": "$.validation_results.validation_passed",
        "BooleanEquals": true,
        "Next": "GoldFacts"
      }
    ],
    "Default": "NotifyValidationFailure"
  },
  "NotifyValidationFailure": {
    "Type": "Task",
    "Resource": "arn:aws:states:::sns:publish",
    "Parameters": {
      "TopicArn": "${SNS_PIPELINE_ALERTS_ARN}",
      "Subject": "Gold Layer Validation Failed",
      "Message.$": "States.JsonToString($.validation_results)"
    },
    "Next": "FailDimensionValidation"
  },
  "FailDimensionValidation": {
    "Type": "Fail",
    "Error": "DimensionValidationFailed",
    "Cause": "One or more dimension tables are missing or invalid"
  },
  "GoldFacts": {
    "Type": "Task",
    "Comment": "Build fact tables (only if dimensions valid)"
  }
}
```

### Terraform Resource
```hcl
# infra/terraform/lambdas_gold_validation.tf (new file)

# Validate Dimensions Lambda
resource "aws_lambda_function" "validate_dimensions" {
  function_name = "${local.name_prefix}-validate-dimensions"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 120
  memory_size   = 512

  s3_bucket = var.s3_bucket_name
  s3_key    = "lambda-deployments/validate_dimensions/function.zip"

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
      ENVIRONMENT    = var.environment
    }
  }

  tags = local.standard_tags
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "validate_dimensions_logs" {
  name              = "/aws/lambda/${aws_lambda_function.validate_dimensions.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days
  tags              = local.standard_tags
}

# Output
output "validate_dimensions_function_name" {
  description = "Name of Validate Dimensions Lambda"
  value       = aws_lambda_function.validate_dimensions.function_name
}
```

## Testing Strategy

### Unit Tests
```python
# tests/unit/lambdas/test_validate_dimensions.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from ingestion.lambdas.validate_dimensions.handler import lambda_handler, validate_dimension

@pytest.fixture
def mock_s3():
    with patch('boto3.client') as mock:
        yield mock.return_value

def test_all_dimensions_exist_and_valid(mock_s3):
    """Test that all dimensions pass validation."""
    # Arrange
    mock_s3.head_object.return_value = {}  # File exists
    mock_s3.get_object.return_value = {
        'Body': create_mock_parquet_with_rows(100)
    }

    # Act
    result = lambda_handler({}, None)

    # Assert
    assert result['validation_passed'] is True
    assert result['dimensions_validated'] == 5
    assert result['dimensions_passed'] == 5
    assert len(result['failures']) == 0

def test_missing_dimension_fails_validation(mock_s3):
    """Test that missing dimension file fails validation."""
    # Arrange
    from botocore.exceptions import ClientError
    mock_s3.head_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchKey'}}, 'HeadObject'
    )

    # Act
    result = validate_dimension({
        'name': 'dim_members',
        'path': 'missing/path.parquet',
        'primary_key': 'member_key'
    })

    # Assert
    assert result['passed'] is False
    assert 'not found' in result['error']

def test_empty_dimension_fails_validation(mock_s3):
    """Test that dimension with 0 rows fails validation."""
    # Arrange
    mock_s3.head_object.return_value = {}
    mock_s3.get_object.return_value = {
        'Body': create_mock_parquet_with_rows(0)  # Empty
    }

    # Act
    result = validate_dimension({
        'name': 'dim_assets',
        'path': 'gold/dimensions/assets.parquet',
        'primary_key': 'asset_key'
    })

    # Assert
    assert result['passed'] is False
    assert result['row_count'] == 0
    assert 'empty' in result['error'].lower()

def test_duplicate_primary_keys_fails_validation(mock_s3):
    """Test that duplicate primary keys fail validation."""
    # Arrange
    mock_s3.head_object.return_value = {}
    mock_s3.get_object.return_value = {
        'Body': create_mock_parquet_with_duplicates()
    }

    # Act
    result = validate_dimension({
        'name': 'dim_bills',
        'path': 'gold/dimensions/bills.parquet',
        'primary_key': 'bill_key'
    })

    # Assert
    assert result['passed'] is False
    assert result['has_duplicates'] is True
    assert 'Duplicate' in result['error']

def test_partial_failure_reports_correctly(mock_s3):
    """Test that partial failures are reported correctly."""
    # Arrange: 3 dimensions pass, 2 fail
    def head_object_side_effect(Bucket, Key):
        if 'dim_lobbyists' in Key or 'dim_dates' in Key:
            from botocore.exceptions import ClientError
            raise ClientError({'Error': {'Code': 'NoSuchKey'}}, 'HeadObject')
        return {}

    mock_s3.head_object.side_effect = head_object_side_effect
    mock_s3.get_object.return_value = {
        'Body': create_mock_parquet_with_rows(50)
    }

    # Act
    result = lambda_handler({}, None)

    # Assert
    assert result['validation_passed'] is False
    assert result['dimensions_passed'] == 3
    assert result['dimensions_failed'] == 2
    assert len(result['failures']) == 2
```

### Integration Test
```python
# tests/integration/test_dimension_validation_integration.py
def test_validate_dimensions_after_gold_layer_build():
    """Test dimension validation with real S3 data."""
    lambda_client = boto3.client('lambda')

    # First, build dimensions (assume they exist)
    # Then validate
    response = lambda_client.invoke(
        FunctionName='congress-disclosures-dev-validate-dimensions',
        InvocationType='RequestResponse',
        Payload=json.dumps({})
    )

    payload = json.loads(response['Payload'].read())

    assert payload['validation_passed'] is True
    assert payload['dimensions_validated'] == 5
    assert payload['dimensions_passed'] == 5
```

## Estimated Effort: 3 hours
- 1.5 hours: Lambda implementation + S3 + Parquet validation
- 1 hour: Unit tests (5 tests)
- 30 min: State machine integration + Terraform

## AI Development Notes
**Baseline**: Similar validation pattern from existing pipeline scripts
**Pattern**: Read Parquet files from S3, validate structure and content
**Files to Create**:
- ingestion/lambdas/validate_dimensions/handler.py (new, ~200 lines)
- ingestion/lambdas/validate_dimensions/requirements.txt (new)
- tests/unit/lambdas/test_validate_dimensions.py (new, 5 tests)
- infra/terraform/lambdas_gold_validation.tf (new file)
- state_machines/congress_data_platform.json:300-350 (add validation states)

**Token Budget**: 2,500 tokens (Lambda + tests + Terraform + state machine)

**Dependencies**:
- Sprint 2 Gold dimension Lambdas must be complete
- PyArrow library for Parquet reading

**Acceptance Criteria Verification**:
1. ✅ All 5 dimensions validated (members, assets, bills, lobbyists, dates)
2. ✅ Row count > 0 check passes
3. ✅ Primary key uniqueness validated
4. ✅ Missing dimension fails pipeline with clear error
5. ✅ Fact building only proceeds if all dimensions valid

**Target**: Sprint 3, Day 3 (January 1, 2026)
