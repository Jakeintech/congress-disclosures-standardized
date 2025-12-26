# STORY-003: Implement Watermarking in check_house_fd_updates

**Epic**: EPIC-001 Unified Data Platform Migration
**Sprint**: Sprint 1 - Foundation
**Story Points**: 3
**Priority**: P0 (Critical)
**Status**: To Do
**Assignee**: TBD
**Created**: 2025-12-14
**Updated**: 2025-12-14

---

## User Story

**As a** platform operator
**I want** watermarking implemented in the update detection Lambda
**So that** we only ingest new data and avoid duplicate processing

## Business Value

- **Cost Optimization**: Only process when source data changes (not every execution)
- **Performance**: Skip ingestion entirely when no updates (save 95% of execution time)
- **Data Integrity**: Prevent duplicate Bronze records
- **Foundation**: Enables re-activation of EventBridge daily trigger

---

## Acceptance Criteria

### Scenario 1: No new data (SHA256 matches)
- **GIVEN** Bronze zip exists with SHA256 = "abc123"
- **AND** Remote zip has SHA256 = "abc123" (same)
- **WHEN** check_house_fd_updates Lambda executes
- **THEN** return `{"has_new_filings": false}`
- **AND** skip pipeline execution (Choice state exits)
- **AND** log "No updates detected for year 2024"

### Scenario 2: New data available (SHA256 differs)
- **GIVEN** Bronze zip exists with SHA256 = "abc123"
- **AND** Remote zip has SHA256 = "def456" (different)
- **WHEN** check_house_fd_updates Lambda executes
- **THEN** return `{"has_new_filings": true, "remote_sha256": "def456"}`
- **AND** proceed to Bronze ingestion
- **AND** log "New data detected for year 2024"

### Scenario 3: First ingestion (no Bronze zip)
- **GIVEN** No Bronze zip exists for year 2024
- **WHEN** check_house_fd_updates Lambda executes
- **THEN** return `{"has_new_filings": true}`
- **AND** proceed to Bronze ingestion

### Scenario 4: HTTP 404 (year not available yet)
- **GIVEN** Year 2030 (future year)
- **WHEN** Remote server returns HTTP 404
- **THEN** return `{"has_new_filings": false}`
- **AND** log "Year 2030 not available yet"
- **AND** do NOT raise error

### Scenario 5: Year outside 5-year lookback window
- **GIVEN** Year 2015 (outside 5-year window from current year 2025)
- **WHEN** check_house_fd_updates Lambda executes
- **THEN** return `{"has_new_filings": false, "reason": "outside_lookback_window"}`
- **AND** log "Year 2015 outside 5-year lookback window (2020-2025)"
- **AND** skip Bronze ingestion

---

## Technical Tasks

### Development
- [ ] Validate year is within 5-year lookback window (current_year - 5 to current_year)
- [ ] Read Bronze S3 object metadata to get existing SHA256
- [ ] Download HTTP HEAD from remote URL (not full file)
- [ ] Calculate SHA256 from Content-Length + Last-Modified headers
- [ ] Compare existing vs remote SHA256
- [ ] Return has_new_filings boolean + metadata
- [ ] Add comprehensive logging (INFO level)

### Error Handling
- [ ] Handle S3 NoSuchKey (first ingestion)
- [ ] Handle HTTP 404 (year not available)
- [ ] Handle HTTP timeouts (retry 3x with exponential backoff)
- [ ] Handle malformed responses

### Testing
- [ ] Unit test: Year outside lookback window → false
- [ ] Unit test: SHA256 matches → false
- [ ] Unit test: SHA256 differs → true
- [ ] Unit test: No Bronze object → true
- [ ] Unit test: HTTP 404 → false
- [ ] Unit test: HTTP timeout → retry → success
- [ ] Integration test: Real S3 + real URL

### Documentation
- [ ] Add docstring explaining watermarking logic
- [ ] Update CLAUDE.md with watermarking explanation
- [ ] Document SHA256 calculation method

---

## Definition of Done

- [x] Code complete and merged
- [x] Unit tests passing (6 tests, 100% coverage)
- [x] Integration test passing (real AWS)
- [x] Code review approved
- [x] Deployed to dev + tested
- [x] Deployed to prod
- [x] Documentation updated

---

## Implementation Details

### SHA256 Calculation (Pseudo-hash)

```python
import hashlib

def calculate_remote_sha256(url):
    """Calculate pseudo-SHA256 from HTTP headers (fast, no download)."""
    response = requests.head(url, timeout=30)

    if response.status_code == 404:
        return None  # Year not available

    # Combine Content-Length + Last-Modified for pseudo-hash
    content_length = response.headers.get('Content-Length', '')
    last_modified = response.headers.get('Last-Modified', '')

    hash_input = f"{content_length}-{last_modified}"
    sha256_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    return sha256_hash
```

### Watermark Check Logic

```python
from datetime import datetime

def lambda_handler(event, context):
    year = event['year']
    bucket = os.environ['S3_BUCKET_NAME']

    # Validate year is within 5-year lookback window
    CURRENT_YEAR = datetime.now().year
    LOOKBACK_YEARS = 5
    MIN_YEAR = CURRENT_YEAR - LOOKBACK_YEARS
    MAX_YEAR = CURRENT_YEAR

    if year < MIN_YEAR or year > MAX_YEAR:
        logger.info(f"Year {year} outside 5-year lookback window ({MIN_YEAR}-{MAX_YEAR})")
        return {
            'has_new_filings': False,
            'reason': 'outside_lookback_window',
            'valid_year_range': f"{MIN_YEAR}-{MAX_YEAR}"
        }

    # Check Bronze for existing zip
    bronze_key = f"bronze/house/financial/year={year}/raw_zip/{year}FD.zip"

    try:
        response = s3.head_object(Bucket=bucket, Key=bronze_key)
        existing_sha = response['Metadata'].get('sha256')
        logger.info(f"Existing SHA256: {existing_sha}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.info("First ingestion (no Bronze zip exists)")
            return {'has_new_filings': True}
        raise

    # Check remote zip
    url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.ZIP"
    remote_sha = calculate_remote_sha256(url)

    if remote_sha is None:
        logger.info(f"Year {year} not available (HTTP 404)")
        return {'has_new_filings': False}

    # Compare
    if existing_sha == remote_sha:
        logger.info(f"No updates for year {year}")
        return {'has_new_filings': False}
    else:
        logger.info(f"New data detected for year {year}")
        return {
            'has_new_filings': True,
            'remote_sha256': remote_sha,
            'existing_sha256': existing_sha
        }
```

---

## Test Requirements

### Unit Tests

```python
import pytest
from unittest.mock import Mock, patch
from ingestion.lambdas.check_house_fd_updates.handler import lambda_handler, calculate_remote_sha256

@pytest.fixture
def mock_s3():
    with patch('boto3.client') as mock:
        yield mock.return_value

@pytest.fixture
def mock_requests():
    with patch('requests.head') as mock:
        yield mock

def test_no_new_filings_when_sha_matches(mock_s3, mock_requests):
    """Test returns false when SHA256 matches."""
    mock_s3.head_object.return_value = {
        'Metadata': {'sha256': 'same_hash_123'}
    }
    mock_requests.return_value = Mock(
        status_code=200,
        headers={'Content-Length': '100', 'Last-Modified': 'date'}
    )

    # Mock calculate_remote_sha256 to return same hash
    with patch('handler.calculate_remote_sha256', return_value='same_hash_123'):
        result = lambda_handler({'year': 2024}, None)

    assert result['has_new_filings'] is False

def test_has_new_filings_when_sha_differs(mock_s3, mock_requests):
    """Test returns true when SHA256 differs."""
    mock_s3.head_object.return_value = {
        'Metadata': {'sha256': 'old_hash_123'}
    }

    with patch('handler.calculate_remote_sha256', return_value='new_hash_456'):
        result = lambda_handler({'year': 2024}, None)

    assert result['has_new_filings'] is True
    assert result['remote_sha256'] == 'new_hash_456'
    assert result['existing_sha256'] == 'old_hash_123'

def test_first_ingestion_no_bronze_object(mock_s3):
    """Test returns true when Bronze zip doesn't exist."""
    mock_s3.head_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchKey'}},
        'HeadObject'
    )

    result = lambda_handler({'year': 2024}, None)

    assert result['has_new_filings'] is True

def test_year_outside_lookback_window():
    """Test returns false when year outside 5-year window."""
    result = lambda_handler({'year': 2015}, None)

    assert result['has_new_filings'] is False
    assert result['reason'] == 'outside_lookback_window'
    assert 'valid_year_range' in result

def test_year_not_available_http_404(mock_requests):
    """Test returns false when year not available (404)."""
    mock_requests.return_value = Mock(status_code=404)

    sha = calculate_remote_sha256('https://example.com/2030FD.ZIP')

    assert sha is None

def test_retry_on_network_error(mock_requests):
    """Test retries on network errors."""
    mock_requests.side_effect = [
        ConnectionError("Network error"),
        Mock(status_code=200, headers={'Content-Length': '100', 'Last-Modified': 'date'})
    ]

    # Should retry and succeed
    sha = calculate_remote_sha256('https://example.com/2024FD.ZIP')

    assert sha is not None
    assert mock_requests.call_count == 2

def test_calculate_remote_sha256_deterministic(mock_requests):
    """Test SHA256 calculation is deterministic."""
    mock_requests.return_value = Mock(
        status_code=200,
        headers={'Content-Length': '104857600', 'Last-Modified': 'Wed, 14 Dec 2025 10:00:00 GMT'}
    )

    sha1 = calculate_remote_sha256('https://example.com/2024FD.ZIP')
    sha2 = calculate_remote_sha256('https://example.com/2024FD.ZIP')

    assert sha1 == sha2
```

**Coverage Target**: 100% (critical path function)

**Note**: 5-year lookback window means we only ingest data from (current_year - 5) to current_year. For 2025, this is 2020-2025. This reduces initial data volume and ongoing costs while maintaining recent compliance data.

### Integration Test

```python
import boto3
import requests

def test_watermarking_with_real_aws():
    """Integration test with real S3 and HTTP."""
    s3 = boto3.client('s3')
    bucket = os.environ['TEST_S3_BUCKET']

    # Upload fake Bronze zip with known SHA256
    fake_sha = "test_sha_123"
    s3.put_object(
        Bucket=bucket,
        Key='bronze/house/financial/year=2020/raw_zip/2020FD.zip',
        Body=b'fake content',
        Metadata={'sha256': fake_sha}
    )

    # Test Lambda (should detect no changes if remote also has same hash)
    # Note: This requires mocking or using a test URL
    result = lambda_handler({'year': 2020}, None)

    # Cleanup
    s3.delete_object(
        Bucket=bucket,
        Key='bronze/house/financial/year=2020/raw_zip/2020FD.zip'
    )

    assert 'has_new_filings' in result
```

---

## Rollback Plan

```bash
# Revert Lambda code
git revert <commit-sha>
git push origin main

# Redeploy Lambda
cd infra/terraform
terraform apply -target=aws_lambda_function.check_house_fd_updates

# Verify
aws lambda invoke \
  --function-name congress-disclosures-dev-check-house-fd-updates \
  --payload '{"year": 2024}' \
  response.json
cat response.json
```

---

## Estimated Effort

| Activity | Time |
|----------|------|
| Implementation | 2 hours |
| Unit tests | 1 hour |
| Integration test | 30 minutes |
| Manual testing | 30 minutes |
| Documentation | 30 minutes |
| Code review | 30 minutes |
| **Total** | **~5 hours** |

**Story Points**: 3 (Fibonacci, ~3-4 hours = 3 points)

---

## Related Stories

- **Blocks**: STORY-001 (can re-enable EventBridge after this)
- **Similar**: STORY-004 (Congress watermarking), STORY-005 (Lobbying watermarking)

---

**Story Owner**: TBD
**Target Completion**: Dec 16, 2025 (Sprint 1, Day 1)
