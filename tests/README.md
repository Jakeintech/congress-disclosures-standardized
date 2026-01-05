# Testing Guide

This directory contains tests for the Congress Financial Disclosures pipeline.

## Test Structure

```
tests/
├── unit/           # Unit tests (fast, no AWS required)
│   ├── watermarking/  # Watermarking function tests (STORY-051)
│   ├── api/           # API endpoint tests
│   └── ...
├── integration/    # Integration tests (require AWS)
└── fixtures/       # Test data fixtures
```

## Watermarking Tests (Sprint 1)

The watermarking tests validate incremental processing logic for all data sources:

### Running Watermarking Tests

```bash
# Run all watermarking tests
pytest tests/unit/watermarking/ -v

# With coverage report
pytest tests/unit/watermarking/ --cov=ingestion/lambdas/check_house_fd_updates \
       --cov=ingestion/lambdas/check_congress_updates \
       --cov=ingestion/lambdas/check_lobbying_updates \
       --cov-report=term-missing
```

### Test Coverage

**Target**: ≥85% coverage for watermarking modules  
**Current**: 85% (26 tests passing)

- `check_house_fd_updates`: 88% coverage (11 tests)
- `check_congress_updates`: 79% coverage (8 tests)
- `check_lobbying_updates`: 89% coverage (6 tests)

### Test Patterns

**House FD Watermarking** (SHA256-based):
- Tests SHA256 hash comparison
- Tests DynamoDB watermark storage/retrieval
- Tests HTTP error handling (404, timeout)
- Tests year validation (lookback window)

**Congress Watermarking** (timestamp-based):
- Tests DynamoDB timestamp watermarks
- Tests Congress.gov API integration
- Tests rate limiting (HTTP 429)
- Tests incremental vs. initial ingestion

**Lobbying Watermarking** (S3 existence-based):
- Tests S3 object existence checks
- Tests quarter validation
- Tests year validation
- Tests partial quarter processing

## Running Tests

### All Tests

```bash
pytest tests/
```

### Unit Tests Only (Recommended for Development)

```bash
pytest tests/unit/
# or
pytest -m unit
```

### Integration Tests (Requires AWS Credentials)

```bash
pytest tests/integration/
# or
pytest -m integration
```

### With Coverage Report

```bash
pytest --cov=ingestion --cov-report=html tests/unit/
# Open htmlcov/index.html in browser
```

## Writing Tests

### Unit Tests

Unit tests should:
- Be fast (<100ms each)
- Not require AWS credentials
- Mock external dependencies (S3, Textract, SQS)
- Test single functions/methods in isolation
- Use descriptive test names starting with `test_`

Example:

```python
import pytest
from unittest.mock import patch, MagicMock

def test_function_name_success():
    """Test successful case with clear description."""
    # Arrange
    input_data = "test"

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_output
```

### Integration Tests

Integration tests should:
- Use `@pytest.mark.integration` decorator
- Clean up AWS resources after running
- Use test-specific prefixes (e.g., `test-{uuid}`)
- Be idempotent (can run multiple times safely)
- Document any AWS costs incurred

Example:

```python
import pytest
import boto3

@pytest.mark.integration
def test_end_to_end_ingestion():
    """Test complete ingestion pipeline (requires AWS)."""
    # Uses real S3, Lambda, etc.
    # Cleanup in try/finally or pytest fixtures
```

## Test Fixtures

Common fixtures are defined in `tests/conftest.py`:

- `mock_s3_client`: Mocked boto3 S3 client
- `mock_textract_client`: Mocked boto3 Textract client
- `sample_pdf_path`: Path to sample PDF file
- `sample_xml_index`: Sample XML index content

## Continuous Integration

Tests run automatically on:
- Every push to `main`
- Every pull request
- Nightly schedule (full suite including integration)

See `.github/workflows/test.yml` for CI configuration.

## Coverage Goals

- **Minimum**: 80% overall coverage
- **Critical paths**: 100% coverage (extraction, parsing)
- **Integration tests**: Cover major use cases end-to-end

Current coverage: Run `make test-cov` to see report.

## Debugging Tests

```bash
# Run with verbose output
pytest -vv tests/

# Run specific test
pytest tests/unit/test_s3_utils.py::TestS3Utils::test_calculate_sha256_bytes

# Stop on first failure
pytest -x tests/

# Enter debugger on failure
pytest --pdb tests/

# Show print statements
pytest -s tests/
```

## Performance Testing

For performance regression testing:

```bash
pytest --durations=10 tests/
```

This shows the 10 slowest tests.

## Test Data

Test data should be:
- Minimal (small files for speed)
- Representative (cover edge cases)
- Committed to git (under `tests/fixtures/`)
- Never contain real PII or sensitive data

For large test files, document how to generate them locally.

## Contributing

Before submitting a PR:

1. Run full test suite: `make test`
2. Check coverage: `make test-cov`
3. Run linting: `make lint`
4. Add tests for new features
5. Update this README if adding new test categories

## Questions?

See [CONTRIBUTING.md](../CONTRIBUTING.md) for more details on development practices.
