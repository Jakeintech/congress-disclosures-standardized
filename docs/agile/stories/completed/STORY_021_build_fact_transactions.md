# STORY-021: Create build_fact_transactions Lambda Wrapper

**Epic**: EPIC-001 Unified Data Platform Migration | **Completed**: 2025-12-16
**Sprint**: Sprint 2 - Gold Layer
**Story Points**: 8
**Priority**: P0 (Critical - Core Gold Table)
**Status**: Done
**Assignee**: TBD
**Created**: 2025-12-14
**Updated**: 2025-12-14

---

## User Story

**As a** data engineer
**I want** a Lambda function that builds the fact_ptr_transactions table
**So that** the Step Function can orchestrate Gold layer transformations

## Business Value

- **Core Feature**: Fact table is the primary dataset for API queries
- **Enables Analysis**: Transaction trends, member activity, stock tracking
- **Star Schema**: Proper dimensional model with foreign keys to dimensions
- **Performance**: Partitioned by year/month for efficient queries

---

## Acceptance Criteria

### Scenario 1: Full rebuild of fact table
- **GIVEN** Silver objects exist for all Type P filings
- **AND** Dimensions exist (dim_members, dim_assets, dim_dates)
- **WHEN** Lambda executes with `{"rebuild": true}`
- **THEN** fact_ptr_transactions table is created from scratch
- **AND** All transactions from all years are included
- **AND** Foreign keys correctly reference dimensions
- **AND** Data partitioned by year/month
- **AND** Return summary: `{"transactions_processed": 50000, "files_written": 60}`

### Scenario 2: Incremental update
- **GIVEN** fact_ptr_transactions exists with data through 2024-11-30
- **AND** New Silver objects for 2024-12-01 through 2024-12-14
- **WHEN** Lambda executes with `{"rebuild": false, "since_date": "2024-12-01"}`
- **THEN** Only process new transactions since 2024-12-01
- **AND** Append to existing Parquet files (or create new partitions)
- **AND** Return summary: `{"transactions_processed": 250, "files_written": 1}`

### Scenario 3: Handle missing dimensions gracefully
- **GIVEN** Silver objects exist
- **AND** dim_members or dim_assets don't exist
- **WHEN** Lambda executes
- **THEN** Raise error: `"Dimension table dim_members not found"`
- **AND** Do NOT create partial fact table
- **AND** Log clear error message for troubleshooting

### Scenario 4: Deduplication (same transaction in multiple runs)
- **GIVEN** fact table contains transaction_id = "10063228-001"
- **WHEN** Reprocessing includes same transaction_id
- **THEN** Deduplicate (keep latest version)
- **AND** No duplicate rows in output

---

## Technical Tasks

### Development
- [ ] Create Lambda directory: `ingestion/lambdas/build_fact_transactions/`
- [ ] Create handler.py with lambda_handler function
- [ ] Wrap existing script: `scripts/build_fact_ptr_transactions.py`
- [ ] Pass event parameters to script (rebuild, since_date)
- [ ] Add S3 path configuration via environment variables
- [ ] Add comprehensive logging

### Lambda Wrapper Pattern
```python
# handler.py
import sys
import os
import json
import logging

sys.path.insert(0, '/opt/python/scripts')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Build fact_ptr_transactions from Silver objects."""
    from build_fact_ptr_transactions import main

    # Extract parameters
    rebuild = event.get('rebuild', False)
    since_date = event.get('since_date')

    logger.info(f"Building fact_ptr_transactions (rebuild={rebuild}, since_date={since_date})")

    try:
        # Run script
        result = main(
            rebuild=rebuild,
            since_date=since_date,
            bucket=os.environ['S3_BUCKET_NAME']
        )

        logger.info(f"Complete: {result['transactions_processed']} transactions processed")

        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }

    except Exception as e:
        logger.error(f"Failed to build fact table: {str(e)}")
        raise
```

### Script Enhancement (build_fact_ptr_transactions.py)
- [ ] Add `since_date` parameter for incremental processing
- [ ] Implement deduplication logic
- [ ] Add partition writing (year/month)
- [ ] Return summary statistics

### Terraform Resource
```hcl
resource "aws_lambda_function" "build_fact_transactions" {
  function_name = "${local.name_prefix}-build-fact-transactions"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  role          = aws_iam_role.gold_lambda_role.arn
  timeout       = 900  # 15 minutes
  memory_size   = 2048  # 2GB

  filename         = "${path.module}/../../lambda_packages/build_fact_transactions.zip"
  source_code_hash = filebase64sha256("${path.module}/../../lambda_packages/build_fact_transactions.zip")

  layers = [
    aws_lambda_layer_version.data_processing.arn
  ]

  environment {
    variables = {
      S3_BUCKET_NAME     = var.s3_bucket_name
      DIM_MEMBERS_KEY    = "gold/dimensions/dim_members/dim_members.parquet"
      DIM_ASSETS_KEY     = "gold/dimensions/dim_assets/dim_assets.parquet"
      DIM_DATES_KEY      = "gold/dimensions/dim_dates/dim_dates.parquet"
      FACT_OUTPUT_PREFIX = "gold/facts/ptr_transactions"
    }
  }
}
```

### Testing
- [ ] Unit test: Lambda wrapper passes parameters correctly
- [ ] Unit test: Error handling (missing dimensions)
- [ ] Integration test: End-to-end with real S3 data
- [ ] Load test: 50,000 transactions (performance benchmark)

### Documentation
- [ ] Add docstring to handler.py
- [ ] Update Lambda requirements spec
- [ ] Document partitioning strategy

---

## Definition of Done

- [x] Lambda function created and tested locally
- [x] Terraform resource created
- [x] Packaging via make command
- [x] Unit tests passing (≥80% coverage)
- [x] Integration test passing (real AWS)
- [x] Deployed to dev + tested
- [x] Deployed to prod
- [x] Documentation updated
- [x] Code review approved

---

## Implementation Details

### Star Schema Design

```
fact_ptr_transactions
├── transaction_key (PK)
├── transaction_id (business key)
├── member_key (FK → dim_members)
├── asset_key (FK → dim_assets)
├── transaction_date_key (FK → dim_dates)
├── notification_date_key (FK → dim_dates)
├── transaction_type
├── amount_low
├── amount_high
├── amount_midpoint (calculated)
├── doc_id (link to Silver)
└── filing_date
```

### Partitioning Strategy

```
gold/facts/ptr_transactions/
├── year=2024/
│   ├── month=11/
│   │   └── transactions.parquet
│   ├── month=12/
│   │   └── transactions.parquet
├── year=2023/
│   ├── month=01/
│   │   └── transactions.parquet
```

**Benefit**: Partition pruning improves query performance (scan only relevant partitions)

### Join Logic

```python
# Pseudocode
def build_fact_table(rebuild=False, since_date=None):
    # Read Silver objects
    silver_objects = read_silver_objects(since_date=since_date)
    transactions = []

    for obj in silver_objects:
        for txn in obj['transactions']:
            transactions.append({
                'transaction_id': f"{obj['doc_id']}-{txn_index}",
                'asset_name': txn['asset_name'],
                'member_name': obj['filer']['name'],
                # ...
            })

    df = pd.DataFrame(transactions)

    # Join with dimensions
    dim_members = pd.read_parquet('s3://.../dim_members.parquet')
    dim_assets = pd.read_parquet('s3://.../dim_assets.parquet')
    dim_dates = pd.read_parquet('s3://.../dim_dates.parquet')

    # Member join (fuzzy match on name)
    df = df.merge(
        dim_members[['member_key', 'full_name']],
        left_on='member_name',
        right_on='full_name',
        how='left'
    )

    # Asset join
    df = df.merge(
        dim_assets[['asset_key', 'asset_name']],
        on='asset_name',
        how='left'
    )

    # Date joins
    df = df.merge(
        dim_dates[['date_key', 'full_date']],
        left_on='transaction_date',
        right_on='full_date',
        how='left'
    )

    # Calculate amount_midpoint
    df['amount_midpoint'] = (df['amount_low'] + df['amount_high']) / 2

    # Partition by year/month
    for (year, month), group in df.groupby(['year', 'month']):
        output_path = f"s3://.../year={year}/month={month}/transactions.parquet"

        if rebuild:
            # Overwrite
            group.to_parquet(output_path)
        else:
            # Append (read existing, dedupe, write)
            existing = read_parquet_safe(output_path)
            combined = pd.concat([existing, group])
            combined = combined.drop_duplicates(subset=['transaction_id'], keep='last')
            combined.to_parquet(output_path)
```

---

## Test Requirements

### Unit Tests

```python
import pytest
from unittest.mock import Mock, patch
from handler import lambda_handler

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')
    monkeypatch.setenv('DIM_MEMBERS_KEY', 'gold/dimensions/dim_members/dim_members.parquet')

def test_lambda_handler_rebuild_mode(mock_env):
    """Test Lambda handler in rebuild mode."""
    event = {'rebuild': True}

    with patch('build_fact_ptr_transactions.main') as mock_main:
        mock_main.return_value = {
            'transactions_processed': 50000,
            'files_written': 60
        }

        result = lambda_handler(event, None)

    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['transactions_processed'] == 50000
    mock_main.assert_called_once_with(rebuild=True, since_date=None, bucket='test-bucket')

def test_lambda_handler_incremental_mode(mock_env):
    """Test Lambda handler in incremental mode."""
    event = {'rebuild': False, 'since_date': '2024-12-01'}

    with patch('build_fact_ptr_transactions.main') as mock_main:
        mock_main.return_value = {
            'transactions_processed': 250,
            'files_written': 1
        }

        result = lambda_handler(event, None)

    body = json.loads(result['body'])
    assert body['transactions_processed'] == 250
    mock_main.assert_called_once_with(
        rebuild=False,
        since_date='2024-12-01',
        bucket='test-bucket'
    )

def test_lambda_handler_error_handling(mock_env):
    """Test Lambda raises error when dimensions missing."""
    event = {'rebuild': True}

    with patch('build_fact_ptr_transactions.main') as mock_main:
        mock_main.side_effect = FileNotFoundError("dim_members.parquet not found")

        with pytest.raises(FileNotFoundError):
            lambda_handler(event, None)
```

### Integration Test

```python
def test_end_to_end_fact_table_build():
    """Integration test: Build fact table with real S3 data."""
    lambda_client = boto3.client('lambda')
    function_name = 'congress-disclosures-test-build-fact-transactions'

    # Invoke Lambda
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps({'rebuild': True, 'test_mode': True})
    )

    # Assert success
    payload = json.loads(response['Payload'].read())
    assert response['StatusCode'] == 200

    body = json.loads(payload['body'])
    assert body['transactions_processed'] > 0

    # Verify output in S3
    s3 = boto3.client('s3')
    objects = s3.list_objects_v2(
        Bucket='test-bucket',
        Prefix='gold/facts/ptr_transactions/'
    )

    assert objects['KeyCount'] > 0
```

---

## Performance Considerations

### Memory Requirements
- **50,000 transactions**: ~200MB RAM (DataFrame)
- **Dimension tables**: ~50MB (members), ~20MB (assets), ~10MB (dates)
- **Total**: ~300MB
- **Lambda Memory**: 2GB (comfortable buffer)

### Execution Time
- **Full rebuild**: ~10 minutes (50K transactions)
- **Incremental (daily)**: ~30 seconds (250 transactions)
- **Lambda Timeout**: 900s (15 min) - sufficient

### Cost per Execution
- **Full rebuild**: 10 min × 2GB = 1,200 GB-seconds × $0.0000166667 = $0.02
- **Incremental**: 30s × 2GB = 60 GB-seconds = $0.001
- **Monthly** (30 incremental): $0.03/month

---

## Rollback Plan

```bash
# Revert Lambda code
git revert <commit-sha>

# Redeploy
make package-gold
terraform apply -target=aws_lambda_function.build_fact_transactions

# Verify
aws lambda invoke \
  --function-name congress-disclosures-dev-build-fact-transactions \
  --payload '{"rebuild": false, "test_mode": true}' \
  response.json
```

---

## Estimated Effort

| Activity | Time |
|----------|------|
| Lambda wrapper | 1 hour |
| Script enhancements | 3 hours |
| Terraform resource | 30 min |
| Unit tests | 2 hours |
| Integration test | 1 hour |
| Performance testing | 1 hour |
| Documentation | 1 hour |
| **Total** | **~10 hours** |

**Story Points**: 8 (Fibonacci, ~10 hours over 2 days)

---

**Story Owner**: TBD
**Target Completion**: Dec 24, 2025 (Sprint 2, Day 3)
