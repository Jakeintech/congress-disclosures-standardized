# STORY-047: Create Check Congress Updates Lambda

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 3 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** pipeline orchestrator
**I want** to detect new Congress.gov data before ingestion
**So that** incremental runs only fetch new bills/members (not duplicate existing data)

## Acceptance Criteria
- **GIVEN** Congress.gov API with bills data
- **WHEN** check_congress_updates Lambda executes
- **THEN** Returns `has_new_data: true` if new bills exist since last fetch
- **AND** Returns `has_new_data: false` if no new bills
- **AND** On first ingestion, uses 5-year lookback (fromDateTime = current_year - 5)
- **AND** On incremental updates, uses last watermark timestamp from DynamoDB
- **AND** Handles API rate limiting gracefully (HTTP 429)

## Technical Tasks
- [ ] Create Lambda function directory structure
- [ ] Implement watermark reading from DynamoDB (`pipeline_watermarks` table)
- [ ] Calculate `fromDateTime` (5-year lookback or last watermark)
- [ ] Query Congress.gov API `/v3/bill?fromDateTime={timestamp}`
- [ ] Count new bills returned
- [ ] Write watermark after successful check
- [ ] Add retry logic for transient API errors
- [ ] Add unit tests (5 test cases)
- [ ] Add integration test with real API
- [ ] Deploy via Terraform

## Implementation

### Lambda Handler
```python
# ingestion/lambdas/check_congress_updates/handler.py
import boto3
import requests
import os
from datetime import datetime, timedelta
from typing import Dict, Any

dynamodb = boto3.resource('dynamodb')
watermarks_table = dynamodb.Table(os.environ['WATERMARKS_TABLE_NAME'])

CONGRESS_API_KEY = os.environ.get('CONGRESS_GOV_API_KEY')
CONGRESS_API_BASE = "https://api.congress.gov"

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Check Congress.gov API for new bills since last fetch.

    Returns:
        {
            'has_new_data': bool,
            'bills_count': int,
            'from_date': str,
            'is_initial_load': bool
        }
    """
    # Read last watermark
    last_fetch = read_watermark('congress_bills')

    # Determine fromDateTime
    if last_fetch is None:
        # First ingestion: Use 5-year lookback
        CURRENT_YEAR = datetime.now().year
        LOOKBACK_YEARS = 5
        from_date = f"{CURRENT_YEAR - LOOKBACK_YEARS}-01-01T00:00:00Z"
        is_initial_load = True
        print(f"First ingestion: fetching from {from_date} (5-year window)")
    else:
        from_date = last_fetch
        is_initial_load = False
        print(f"Incremental update: fetching from {from_date}")

    # Query API
    url = f"{CONGRESS_API_BASE}/v3/bill?fromDateTime={from_date}&limit=1"
    headers = {'X-Api-Key': CONGRESS_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            # Rate limited - return no updates to skip this run
            print("Rate limited by Congress.gov API")
            return {
                'has_new_data': False,
                'bills_count': 0,
                'error': 'rate_limited'
            }
        raise

    data = response.json()
    new_count = data.get('pagination', {}).get('count', 0)

    # Update watermark (only if we checked successfully)
    current_timestamp = datetime.utcnow().isoformat() + 'Z'
    write_watermark('congress_bills', current_timestamp)

    return {
        'has_new_data': new_count > 0,
        'bills_count': new_count,
        'from_date': from_date,
        'is_initial_load': is_initial_load,
        'last_check': current_timestamp
    }

def read_watermark(table_name: str) -> str | None:
    """Read last processed timestamp from DynamoDB."""
    try:
        response = watermarks_table.get_item(
            Key={
                'table_name': table_name,
                'watermark_type': 'last_fetch'
            }
        )
        return response.get('Item', {}).get('last_processed_timestamp')
    except Exception as e:
        print(f"Error reading watermark: {e}")
        return None

def write_watermark(table_name: str, timestamp: str):
    """Write watermark to DynamoDB."""
    watermarks_table.put_item(
        Item={
            'table_name': table_name,
            'watermark_type': 'last_fetch',
            'last_processed_timestamp': timestamp,
            'updated_at': datetime.utcnow().isoformat()
        }
    )
```

### Terraform Resource
```hcl
# infra/terraform/step_functions.tf (append after line 405)

# Check Congress Updates Lambda
resource "aws_lambda_function" "check_congress_updates" {
  function_name = "${local.name_prefix}-check-congress-updates"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 256

  s3_bucket = var.s3_bucket_name
  s3_key    = "lambda-deployments/check_congress_updates/function.zip"

  environment {
    variables = {
      WATERMARKS_TABLE_NAME  = aws_dynamodb_table.pipeline_watermarks.name
      CONGRESS_GOV_API_KEY   = var.congress_gov_api_key
      LOG_LEVEL              = "INFO"
      ENVIRONMENT            = var.environment
    }
  }

  tags = local.standard_tags
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "check_congress_updates_logs" {
  name              = "/aws/lambda/${aws_lambda_function.check_congress_updates.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days
  tags              = local.standard_tags
}

# Output
output "check_congress_updates_function_name" {
  description = "Name of Check Congress Updates Lambda"
  value       = aws_lambda_function.check_congress_updates.function_name
}
```

## Testing Strategy

### Unit Tests
```python
# tests/unit/lambdas/test_check_congress_updates.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from ingestion.lambdas.check_congress_updates.handler import lambda_handler

@pytest.fixture
def mock_dynamodb():
    with patch('boto3.resource') as mock:
        table = MagicMock()
        mock.return_value.Table.return_value = table
        yield table

@pytest.fixture
def mock_requests():
    with patch('requests.get') as mock:
        yield mock

def test_first_ingestion_uses_5_year_lookback(mock_dynamodb, mock_requests):
    """Test that first ingestion uses 5-year lookback."""
    # Arrange
    mock_dynamodb.get_item.return_value = {}  # No watermark exists
    mock_requests.return_value = Mock(
        status_code=200,
        json=lambda: {'pagination': {'count': 100}}
    )

    # Act
    result = lambda_handler({}, None)

    # Assert
    assert result['is_initial_load'] is True
    assert '2020-01-01' in result['from_date']  # 5 years ago
    assert result['has_new_data'] is True
    assert result['bills_count'] == 100

def test_incremental_uses_last_watermark(mock_dynamodb, mock_requests):
    """Test that incremental updates use last watermark."""
    # Arrange
    mock_dynamodb.get_item.return_value = {
        'Item': {'last_processed_timestamp': '2025-12-01T00:00:00Z'}
    }
    mock_requests.return_value = Mock(
        status_code=200,
        json=lambda: {'pagination': {'count': 5}}
    )

    # Act
    result = lambda_handler({}, None)

    # Assert
    assert result['is_initial_load'] is False
    assert result['from_date'] == '2025-12-01T00:00:00Z'
    assert result['bills_count'] == 5

def test_rate_limiting_handled_gracefully(mock_dynamodb, mock_requests):
    """Test that HTTP 429 returns no updates without failing."""
    # Arrange
    mock_requests.return_value = Mock(status_code=429)
    mock_requests.return_value.raise_for_status.side_effect = \
        requests.exceptions.HTTPError(response=Mock(status_code=429))

    # Act
    result = lambda_handler({}, None)

    # Assert
    assert result['has_new_data'] is False
    assert result['error'] == 'rate_limited'

def test_no_new_data_returns_false(mock_dynamodb, mock_requests):
    """Test that 0 new bills returns has_new_data=False."""
    # Arrange
    mock_dynamodb.get_item.return_value = {
        'Item': {'last_processed_timestamp': '2025-12-14T00:00:00Z'}
    }
    mock_requests.return_value = Mock(
        status_code=200,
        json=lambda: {'pagination': {'count': 0}}
    )

    # Act
    result = lambda_handler({}, None)

    # Assert
    assert result['has_new_data'] is False
    assert result['bills_count'] == 0
```

### Integration Test
```python
# tests/integration/test_check_congress_updates_integration.py
def test_check_congress_updates_with_real_api():
    """Test Lambda with real Congress.gov API."""
    lambda_client = boto3.client('lambda')

    response = lambda_client.invoke(
        FunctionName='congress-disclosures-dev-check-congress-updates',
        InvocationType='RequestResponse',
        Payload=json.dumps({})
    )

    payload = json.loads(response['Payload'].read())

    assert 'has_new_data' in payload
    assert 'bills_count' in payload
    assert 'from_date' in payload
```

## Estimated Effort: 3 hours
- 1 hour: Lambda implementation + DynamoDB integration
- 1 hour: Unit tests (5 tests)
- 30 min: Terraform resource + deployment
- 30 min: Integration testing

## AI Development Notes
**Baseline**: ingestion/lambdas/check_house_fd_updates/handler.py:1-100 (similar pattern)
**Pattern**: Watermark-based incremental processing with DynamoDB
**Files to Create**:
- ingestion/lambdas/check_congress_updates/handler.py (new, ~150 lines)
- ingestion/lambdas/check_congress_updates/requirements.txt (new)
- tests/unit/lambdas/test_check_congress_updates.py (new, 5 tests)
- infra/terraform/step_functions.tf:405-450 (append Terraform resource)

**Token Budget**: 2,500 tokens (Lambda + tests + Terraform)

**Dependencies**:
- DynamoDB `pipeline_watermarks` table already exists (verified)
- Congress.gov API key in environment variables

**Acceptance Criteria Verification**:
1. ✅ First execution returns `is_initial_load: true` with 5-year fromDateTime
2. ✅ Subsequent executions use watermark timestamp
3. ✅ HTTP 429 handled without failure
4. ✅ Watermark updated after successful check
5. ✅ Unit tests achieve 85%+ coverage

**Target**: Sprint 1, Day 2 (December 17, 2025)
