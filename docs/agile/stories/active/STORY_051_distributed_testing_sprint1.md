# STORY-051: Write Unit Tests - Sprint 1 Watermarking Functions

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 3 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** developer
**I want** comprehensive unit tests for watermarking functions
**So that** incremental processing logic is thoroughly validated before Sprint 2

## Acceptance Criteria
- **GIVEN** Watermarking functions implemented (STORY-003, 004, 005)
- **WHEN** Tests execute
- **THEN** 15+ unit tests pass successfully
- **AND** Test coverage ≥ 85% for watermarking modules
- **AND** All edge cases covered (SHA mismatch, missing objects, HTTP errors, year validation)
- **AND** Tests run in < 30 seconds

## Technical Tasks
- [ ] Write 6 tests for check_house_fd_updates (STORY-003)
- [ ] Write 5 tests for check_congress_updates (STORY-047)
- [ ] Write 4 tests for check_lobbying_updates (STORY-005)
- [ ] Add pytest fixtures for S3/DynamoDB mocking
- [ ] Configure pytest-cov for coverage reporting
- [ ] Run tests in CI/CD pipeline (GitHub Actions)
- [ ] Document test patterns in testing guide

## Test Breakdown

### 1. check_house_fd_updates Tests (6 tests)
```python
# tests/unit/lambdas/test_check_house_fd_updates.py

def test_year_outside_lookback_window_returns_false():
    """Test that years outside 5-year window are rejected."""

def test_sha256_matches_returns_no_new_filings():
    """Test that matching SHA256 returns has_new_filings=False."""

def test_sha256_differs_returns_has_new_filings():
    """Test that different SHA256 returns has_new_filings=True."""

def test_bronze_object_missing_returns_has_new_filings():
    """Test that missing Bronze object triggers ingestion."""

def test_http_404_handled_gracefully():
    """Test that HTTP 404 (year not available) doesn't raise error."""

def test_http_timeout_retries_and_succeeds():
    """Test retry logic on network timeout."""
```

### 2. check_congress_updates Tests (5 tests)
```python
# tests/unit/lambdas/test_check_congress_updates.py

def test_first_ingestion_uses_5_year_lookback():
    """Test that first ingestion uses current_year - 5 as fromDateTime."""

def test_incremental_uses_last_watermark():
    """Test that incremental updates use watermark from DynamoDB."""

def test_rate_limiting_handled_gracefully():
    """Test that HTTP 429 returns no updates without failing."""

def test_no_new_bills_returns_false():
    """Test that 0 new bills returns has_new_data=False."""

def test_watermark_updated_after_successful_check():
    """Test that DynamoDB watermark is written after check."""
```

### 3. check_lobbying_updates Tests (4 tests)
```python
# tests/unit/lambdas/test_check_lobbying_updates.py

def test_year_outside_lookback_window_rejected():
    """Test that years < (current_year - 5) are rejected."""

def test_bronze_object_exists_returns_false():
    """Test that existing Bronze object returns has_new_filings=False."""

def test_bronze_object_missing_returns_true():
    """Test that missing Bronze object triggers ingestion."""

def test_quarter_validation():
    """Test that quarters must be Q1, Q2, Q3, or Q4."""
```

## Shared Test Fixtures
```python
# tests/conftest.py (update)

import pytest
from unittest.mock import MagicMock
from moto import mock_s3, mock_dynamodb

@pytest.fixture
def mock_s3_client():
    """Mock S3 client for all tests."""
    with mock_s3():
        import boto3
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='congress-disclosures-standardized')
        yield s3

@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB watermarks table."""
    with mock_dynamodb():
        import boto3
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        table = dynamodb.create_table(
            TableName='congress-disclosures-pipeline-watermarks',
            KeySchema=[
                {'AttributeName': 'table_name', 'KeyType': 'HASH'},
                {'AttributeName': 'watermark_type', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'table_name', 'AttributeType': 'S'},
                {'AttributeName': 'watermark_type', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        yield table

@pytest.fixture
def mock_requests_success():
    """Mock requests.get for successful API calls."""
    with patch('requests.get') as mock:
        mock.return_value = MagicMock(
            status_code=200,
            headers={'Content-Length': '100000', 'Last-Modified': 'Mon, 01 Jan 2024 00:00:00 GMT'},
            json=lambda: {'pagination': {'count': 10}}
        )
        yield mock
```

## Coverage Configuration
```ini
# pytest.ini (update)
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --cov=ingestion/lambdas
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=85

[coverage:run]
source = ingestion
omit =
    */tests/*
    */venv/*
    */__pycache__/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

## CI/CD Integration
```yaml
# .github/workflows/test.yml (update)

name: Run Tests

on:
  push:
    branches: [main, development, enhancement]
  pull_request:
    branches: [main]

jobs:
  unit-tests-sprint1:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          pip install pytest pytest-cov pytest-mock moto

      - name: Run Sprint 1 unit tests
        run: |
          pytest tests/unit/lambdas/test_check_house_fd_updates.py \
                 tests/unit/lambdas/test_check_congress_updates.py \
                 tests/unit/lambdas/test_check_lobbying_updates.py \
                 -v --cov=ingestion/lambdas --cov-report=xml

      - name: Check coverage threshold
        run: |
          coverage report --fail-under=85

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: sprint1-unit-tests
```

## Estimated Effort: 3 hours
- 1.5 hours: Write 15 unit tests
- 30 min: Configure fixtures and mocking
- 30 min: Configure pytest-cov and CI/CD
- 30 min: Fix any failing tests and reach 85% coverage

## AI Development Notes
**Baseline**: tests/unit/lambdas/ directory structure exists with some tests
**Pattern**: pytest + moto for AWS service mocking
**Files to Create**:
- tests/unit/lambdas/test_check_house_fd_updates.py (6 tests, ~150 lines)
- tests/unit/lambdas/test_check_congress_updates.py (5 tests, ~120 lines)
- tests/unit/lambdas/test_check_lobbying_updates.py (4 tests, ~100 lines)

**Files to Modify**:
- tests/conftest.py (add fixtures)
- pytest.ini (add coverage config)
- .github/workflows/test.yml (update)

**Token Budget**: 2,500 tokens (15 tests + fixtures + config)

**Dependencies**:
- STORY-003 (House FD watermarking) complete
- STORY-047 (Congress updates) complete
- STORY-005 (Lobbying watermarking) complete

**Acceptance Criteria Verification**:
1. ✅ 15 unit tests written and passing
2. ✅ Coverage ≥ 85% for watermarking modules
3. ✅ All edge cases covered
4. ✅ Tests run in < 30 seconds
5. ✅ CI/CD pipeline updated

**Target**: Sprint 1, Day 5 (December 20, 2025)

---

**NOTE**: This story replaces the original STORY-034 "Write 70+ unit tests (8 points)" which was unrealistic. Testing is now distributed across all 4 sprints:
- **Sprint 1** (this story): 15 tests for watermarking (3 points)
- **Sprint 2**: 20 tests for Gold layer wrappers (4 points) - see STORY-052
- **Sprint 3**: 35 tests for state machine + integration (6 points) - see STORY-053
- **Sprint 4**: 10 E2E tests (3 points) - see STORY-036

**Total**: 80 tests across 4 sprints (16 points) vs original 70 tests in 1 sprint (8 points)
