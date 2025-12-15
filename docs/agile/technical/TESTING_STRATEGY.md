# Testing Strategy

**Project**: Congress Disclosures Standardized Data Platform
**Last Updated**: 2025-12-14
**Target Coverage**: ≥80%

---

## Testing Pyramid

```
         ╱╲
        ╱  ╲          E2E Tests (10%)
       ╱ E2E╲         - 10 tests
      ╱──────╲        - Full pipeline flows
     ╱        ╲       - API + Website
    ╱   Integ  ╲      Integration Tests (20%)
   ╱────────────╲     - 20 tests
  ╱              ╲    - AWS service integration
 ╱      Unit      ╲   Unit Tests (70%)
╱──────────────────╲  - 70+ tests
                      - Lambda functions + libraries
```

---

## Test Coverage Goals

| Component | Unit | Integration | E2E | Total Coverage Target |
|-----------|------|-------------|-----|---------------------|
| Lambda Functions | ✅ Required | ✅ Required | ⚠️ Smoke | ≥80% |
| Extraction Libraries | ✅ Required | ⚠️ Sample PDFs | ❌ | ≥85% |
| State Machine | ❌ | ✅ Required | ✅ Full Flow | N/A (JSON) |
| API Endpoints | ✅ Logic | ✅ Required | ✅ User Flows | ≥80% |
| Scripts | ✅ Required | ⚠️ Optional | ❌ | ≥75% |

---

## 1. Unit Tests (70% of total tests)

### Purpose
Test individual functions/classes in isolation with mocked dependencies.

### Tools
- **Framework**: `pytest`
- **Mocking**: `pytest-mock`, `moto` (for AWS)
- **Coverage**: `pytest-cov`
- **Assertions**: Built-in pytest assertions

### Structure
```
tests/unit/
├── lambdas/
│   ├── test_check_house_fd_updates.py
│   ├── test_house_fd_ingest_zip.py
│   ├── test_house_fd_extract_document.py
│   ├── test_gold_builders.py
│   └── ...
├── lib/
│   ├── test_s3_utils.py
│   ├── test_parquet_writer.py
│   ├── test_extraction_pipeline.py
│   └── ...
├── extractors/
│   ├── test_type_p_ptr_extractor.py
│   ├── test_type_a_annual_extractor.py
│   └── ...
└── scripts/
    ├── test_build_dim_members.py
    ├── test_compute_trending_stocks.py
    └── ...
```

### Example Unit Test

**File**: `tests/unit/lambdas/test_check_house_fd_updates.py`

```python
import pytest
from unittest.mock import Mock, patch
from ingestion.lambdas.check_house_fd_updates.handler import lambda_handler

@pytest.fixture
def mock_s3():
    with patch('boto3.client') as mock:
        yield mock.return_value

@pytest.fixture
def mock_requests():
    with patch('requests.head') as mock:
        yield mock

def test_has_new_filings_when_sha_differs(mock_s3, mock_requests):
    """Test that function returns has_new_filings=True when SHA256 differs."""
    # Arrange
    mock_s3.head_object.return_value = {
        'Metadata': {'sha256': 'old_hash'}
    }
    mock_requests.return_value = Mock(
        status_code=200,
        headers={'Content-Length': '100', 'Last-Modified': 'new_date'}
    )

    event = {'year': 2024}

    # Act
    result = lambda_handler(event, None)

    # Assert
    assert result['has_new_filings'] is True
    assert result['year'] == 2024
    assert 'remote_sha256' in result

def test_no_new_filings_when_sha_matches(mock_s3, mock_requests):
    """Test that function returns has_new_filings=False when SHA256 matches."""
    # Arrange
    mock_s3.head_object.return_value = {
        'Metadata': {'sha256': 'same_hash'}
    }
    mock_requests.return_value = Mock(
        status_code=200,
        headers={'Content-Length': '100', 'Last-Modified': 'same_date'}
    )

    event = {'year': 2024}

    # Act
    result = lambda_handler(event, None)

    # Assert
    assert result['has_new_filings'] is False

def test_handles_404_gracefully(mock_requests):
    """Test that 404 (year not available) is handled gracefully."""
    # Arrange
    mock_requests.return_value = Mock(status_code=404)
    event = {'year': 2030}

    # Act
    result = lambda_handler(event, None)

    # Assert
    assert result['has_new_filings'] is False
    assert 'error' not in result

def test_retries_on_network_error(mock_requests):
    """Test that network errors trigger retry logic."""
    # Arrange
    mock_requests.side_effect = [
        ConnectionError("Network error"),
        ConnectionError("Network error"),
        Mock(status_code=200, headers={'Content-Length': '100', 'Last-Modified': 'date'})
    ]

    event = {'year': 2024}

    # Act
    result = lambda_handler(event, None)

    # Assert
    assert mock_requests.call_count == 3
    assert result['has_new_filings'] is True
```

### Coverage Requirements

**Per Lambda Function**:
- ✅ Happy path test
- ✅ Error handling test (each error type)
- ✅ Input validation test
- ✅ Edge case test
- ✅ Retry logic test (if applicable)

**Minimum Coverage**: 80% line coverage per file

### Running Unit Tests
```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=ingestion --cov-report=html

# Run specific test file
pytest tests/unit/lambdas/test_check_house_fd_updates.py -v

# Run specific test
pytest tests/unit/lambdas/test_check_house_fd_updates.py::test_has_new_filings_when_sha_differs -v
```

---

## 2. Integration Tests (20% of total tests)

### Purpose
Test components working together with real AWS services (dev environment).

### Tools
- **Framework**: `pytest`
- **AWS**: Real AWS services (S3, Lambda, SQS, Step Functions)
- **Fixtures**: `pytest-fixture` for setup/teardown
- **Cleanup**: Automatic resource cleanup after tests

### Structure
```
tests/integration/
├── test_bronze_to_silver_flow.py
├── test_silver_to_gold_flow.py
├── test_state_machine_execution.py
├── test_sqs_extraction_queue.py
├── test_api_endpoints.py
└── fixtures/
    ├── sample_pdfs/
    ├── sample_xml/
    └── test_data.json
```

### Example Integration Test

**File**: `tests/integration/test_bronze_to_silver_flow.py`

```python
import pytest
import boto3
import os
from datetime import datetime

@pytest.fixture(scope='module')
def aws_resources():
    """Setup AWS resources for testing."""
    s3 = boto3.client('s3')
    bucket = os.environ['TEST_S3_BUCKET']

    # Upload test data
    test_pdf = 'tests/integration/fixtures/sample_pdfs/10063228.pdf'
    s3.upload_file(
        test_pdf,
        bucket,
        'bronze/house/financial/year=2020/filing_type=P/pdfs/10063228.pdf'
    )

    yield {'s3': s3, 'bucket': bucket}

    # Cleanup
    s3.delete_object(
        Bucket=bucket,
        Key='bronze/house/financial/year=2020/filing_type=P/pdfs/10063228.pdf'
    )
    s3.delete_object(
        Bucket=bucket,
        Key='silver/house/financial/text/extraction_method=direct_text/year=2020/10063228.txt.gz'
    )

def test_pdf_extraction_end_to_end(aws_resources):
    """Test PDF extraction from Bronze to Silver."""
    # Arrange
    lambda_client = boto3.client('lambda')
    function_name = 'congress-disclosures-test-house-fd-extract-document'

    # Act: Invoke extraction Lambda
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps({
            'Records': [{
                'body': json.dumps({
                    'doc_id': '10063228',
                    'pdf_s3_key': 'bronze/house/financial/year=2020/filing_type=P/pdfs/10063228.pdf'
                })
            }]
        })
    )

    # Assert: Check response
    payload = json.loads(response['Payload'].read())
    assert response['StatusCode'] == 200
    assert 'batchItemFailures' in payload
    assert len(payload['batchItemFailures']) == 0  # No failures

    # Assert: Check Silver output exists
    s3 = aws_resources['s3']
    bucket = aws_resources['bucket']

    objects = s3.list_objects_v2(
        Bucket=bucket,
        Prefix='silver/house/financial/text/'
    )

    assert objects['KeyCount'] > 0

    # Assert: Check metadata
    text_key = [obj['Key'] for obj in objects['Contents'] if '10063228' in obj['Key']][0]
    head = s3.head_object(Bucket=bucket, Key=text_key)
    assert 'extraction-method' in head['Metadata']

def test_state_machine_executes_successfully(aws_resources):
    """Test that state machine executes from start to finish."""
    # Arrange
    sfn = boto3.client('stepfunctions')
    state_machine_arn = os.environ['TEST_STATE_MACHINE_ARN']

    # Act: Start execution
    response = sfn.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps({
            'execution_type': 'test',
            'mode': 'incremental',
            'parameters': {'year': 2020}
        })
    )

    execution_arn = response['executionArn']

    # Wait for completion (max 5 minutes)
    import time
    for _ in range(60):  # 60 * 5s = 5 min
        status = sfn.describe_execution(executionArn=execution_arn)
        if status['status'] in ['SUCCEEDED', 'FAILED', 'TIMED_OUT']:
            break
        time.sleep(5)

    # Assert: Execution succeeded
    assert status['status'] == 'SUCCEEDED'

    # Assert: Check outputs
    output = json.loads(status['output'])
    assert 'bronze_results' in output
    assert 'silver_results' in output
```

### Running Integration Tests
```bash
# Set test environment variables
export TEST_S3_BUCKET=congress-disclosures-test
export TEST_STATE_MACHINE_ARN=arn:aws:states:...

# Run integration tests (requires AWS credentials)
pytest tests/integration/ -v --tb=short

# Run specific integration test
pytest tests/integration/test_bronze_to_silver_flow.py::test_pdf_extraction_end_to_end -v
```

---

## 3. End-to-End (E2E) Tests (10% of total tests)

### Purpose
Test complete user workflows including API and website.

### Tools
- **Framework**: `pytest` + `playwright`
- **API Testing**: `requests`
- **Website Testing**: Playwright (browser automation)
- **Data Validation**: Custom assertions

### Structure
```
tests/e2e/
├── test_full_pipeline_execution.py
├── test_api_endpoints.py
├── test_website_functionality.py
└── playwright/
    ├── test_dashboard_loads.py
    ├── test_member_filtering.py
    └── test_transaction_search.py
```

### Example E2E Test (API)

**File**: `tests/e2e/test_api_endpoints.py`

```python
import pytest
import requests
from datetime import datetime

@pytest.fixture
def api_base_url():
    return os.environ.get('API_BASE_URL', 'https://api.example.com')

def test_get_members_returns_data(api_base_url):
    """Test GET /members endpoint returns member list."""
    # Act
    response = requests.get(f"{api_base_url}/v1/members")

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert 'data' in data
    assert len(data['data']) > 0

    # Validate schema
    member = data['data'][0]
    assert 'bioguide_id' in member
    assert 'full_name' in member
    assert 'party' in member
    assert 'chamber' in member

def test_get_transactions_with_filters(api_base_url):
    """Test GET /transactions endpoint with filters."""
    # Arrange
    params = {
        'member': 'P000197',
        'start_date': '2024-01-01',
        'end_date': '2024-12-31'
    }

    # Act
    response = requests.get(f"{api_base_url}/v1/transactions", params=params)

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert 'data' in data

    # Verify filters applied
    for txn in data['data']:
        assert txn['member']['bioguide_id'] == 'P000197'
        txn_date = datetime.strptime(txn['transaction_date'], '%Y-%m-%d')
        assert datetime(2024, 1, 1) <= txn_date <= datetime(2024, 12, 31)

def test_trending_stocks_returns_ranked_list(api_base_url):
    """Test GET /trending-stocks endpoint."""
    # Act
    response = requests.get(f"{api_base_url}/v1/trending-stocks?window=30")

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert 'data' in data

    stocks = data['data']
    assert len(stocks) > 0

    # Verify ranking (sorted by rank)
    ranks = [s['rank'] for s in stocks]
    assert ranks == sorted(ranks)

    # Verify structure
    stock = stocks[0]
    assert 'ticker' in stock
    assert 'activity' in stock
    assert stock['activity']['purchase_count'] >= 0
```

### Example E2E Test (Playwright)

**File**: `tests/e2e/playwright/test_dashboard_loads.py`

```python
import pytest
from playwright.sync_api import Page, expect

def test_dashboard_page_loads(page: Page):
    """Test that dashboard page loads successfully."""
    # Navigate
    page.goto("https://example.com/dashboard")

    # Assert: Page title
    expect(page).to_have_title(/Dashboard/)

    # Assert: Key elements visible
    expect(page.locator('h1')).to_contain_text('Dashboard')
    expect(page.locator('[data-testid="stats-overview"]')).to_be_visible()
    expect(page.locator('[data-testid="trending-stocks"]')).to_be_visible()

def test_member_filtering_works(page: Page):
    """Test that member filtering updates results."""
    # Navigate
    page.goto("https://example.com/members")

    # Act: Apply party filter
    page.click('[data-testid="filter-party"]')
    page.click('text=Democrat')

    # Wait for results to update
    page.wait_for_selector('[data-testid="member-card"]')

    # Assert: All members are Democrats
    members = page.locator('[data-testid="member-party"]').all_text_contents()
    assert all(party == 'D' for party in members)

def test_transaction_search_returns_results(page: Page):
    """Test transaction search functionality."""
    # Navigate
    page.goto("https://example.com/transactions")

    # Act: Search for ticker
    page.fill('[data-testid="search-input"]', 'NVDA')
    page.click('[data-testid="search-button"]')

    # Wait for results
    page.wait_for_selector('[data-testid="transaction-row"]')

    # Assert: Results contain NVDA
    tickers = page.locator('[data-testid="transaction-ticker"]').all_text_contents()
    assert all('NVDA' in ticker for ticker in tickers)
```

### Running E2E Tests
```bash
# Install Playwright
playwright install

# Run E2E tests
pytest tests/e2e/ -v

# Run Playwright tests with headed browser (visible)
pytest tests/e2e/playwright/ --headed

# Run specific E2E test
pytest tests/e2e/test_full_pipeline_execution.py::test_pipeline_processes_new_data -v
```

---

## 4. Performance Tests

### Load Testing

**File**: `tests/performance/test_api_load.py`

```python
import pytest
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_members(self):
        self.client.get("/v1/members")

    @task(2)
    def get_transactions(self):
        self.client.get("/v1/transactions?limit=50")

    @task(1)
    def get_trending_stocks(self):
        self.client.get("/v1/trending-stocks?window=30")
```

**Run Load Test**:
```bash
locust -f tests/performance/test_api_load.py --host=https://api.example.com
# Open http://localhost:8089 and configure users/spawn rate
```

---

## 5. Test Data Management

### Fixtures

**File**: `tests/fixtures/conftest.py`

```python
import pytest
import json

@pytest.fixture
def sample_ptr_filing():
    """Sample Type P (PTR) filing for testing."""
    return {
        "doc_id": "10063228",
        "filing_type": "P",
        "transactions": [
            {
                "asset_name": "NVIDIA CORP",
                "ticker": "NVDA",
                "transaction_type": "Purchase",
                "amount_low": 100001,
                "amount_high": 250000
            }
        ]
    }

@pytest.fixture
def sample_annual_filing():
    """Sample Type A (Annual) filing for testing."""
    return {
        "doc_id": "10050123",
        "filing_type": "A",
        "schedules": {
            "schedule_a_assets": [...],
            "schedule_b_income": [...]
        }
    }

@pytest.fixture
def mock_aws_env(monkeypatch):
    """Mock AWS environment variables."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    monkeypatch.setenv('ENVIRONMENT', 'test')
```

---

## 6. CI/CD Integration

### GitHub Actions Workflow

**File**: `.github/workflows/test.yml`

```yaml
name: Run Tests

on:
  push:
    branches: [main, development]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      - name: Run unit tests
        run: |
          pytest tests/unit/ -v --cov=ingestion --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push'  # Only on push, not PR
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_TEST_ROLE_ARN }}
          aws-region: us-east-1
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v
        env:
          TEST_S3_BUCKET: congress-disclosures-test
          TEST_STATE_MACHINE_ARN: ${{ secrets.TEST_STATE_MACHINE_ARN }}

  e2e-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install Playwright
        run: |
          pip install playwright pytest-playwright
          playwright install
      - name: Run E2E tests
        run: |
          pytest tests/e2e/ -v
        env:
          API_BASE_URL: ${{ secrets.API_BASE_URL }}
```

---

## 7. Test Coverage Reporting

### Coverage Requirements

| Component | Minimum Coverage | Current Coverage | Status |
|-----------|-----------------|------------------|--------|
| Lambda Functions | 80% | TBD | 🟡 To be measured |
| Extraction Libraries | 85% | ~65% | 🔴 Below target |
| Utilities (lib/) | 80% | ~45% | 🔴 Below target |
| Scripts | 75% | ~15% | 🔴 Below target |
| **Overall** | **80%** | **~30%** | 🔴 **Below target** |

### Coverage Reports

**Generate HTML Report**:
```bash
pytest tests/unit/ --cov=ingestion --cov-report=html
open htmlcov/index.html
```

**Generate Terminal Report**:
```bash
pytest tests/unit/ --cov=ingestion --cov-report=term-missing
```

---

## 8. Test Execution Strategy

### Local Development
```bash
# Fast: Unit tests only (< 1 minute)
pytest tests/unit/

# Medium: Unit + Integration (5-10 minutes, requires AWS)
pytest tests/unit/ tests/integration/

# Full: All tests (15-30 minutes)
pytest tests/
```

### Pull Request
- ✅ Unit tests (required, must pass)
- ✅ Linting (flake8, black, mypy)
- ⚠️ Integration tests (optional, only if AWS creds available)

### Main Branch Push
- ✅ Unit tests
- ✅ Integration tests
- ✅ E2E tests (smoke tests only)

### Nightly Build
- ✅ All tests (unit + integration + E2E)
- ✅ Performance tests
- ✅ Security scans

---

## 9. Testing Checklist

### Per User Story

- [ ] **Unit Tests Written**
  - [ ] Happy path test
  - [ ] Error handling tests
  - [ ] Edge case tests
  - [ ] Input validation tests
  - [ ] Coverage ≥ 80%

- [ ] **Integration Tests Written** (if applicable)
  - [ ] AWS service integration tested
  - [ ] End-to-end flow tested

- [ ] **Manual Testing Completed**
  - [ ] Tested in dev environment
  - [ ] Tested edge cases
  - [ ] Performance validated

- [ ] **Tests Pass in CI/CD**
  - [ ] All tests passing
  - [ ] Coverage thresholds met
  - [ ] No flaky tests

---

## 10. Testing Anti-Patterns to Avoid

❌ **Don't**:
- Test implementation details (test behavior, not internals)
- Write flaky tests (use proper waits, not sleep)
- Mock everything (test real integration when possible)
- Skip error handling tests
- Commit failing tests

✅ **Do**:
- Test user-facing behavior
- Use fixtures for reusable test data
- Clean up resources after tests
- Write descriptive test names
- Test both happy and sad paths

---

**Document Owner**: Engineering Team + QA
**Review Cycle**: Monthly or when testing strategy changes
**Next Steps**: Implement unit tests for all Lambda functions, achieve 80% coverage
