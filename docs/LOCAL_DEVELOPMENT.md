# Local Development Mode

Run the entire Congress Disclosures pipeline locally on your computer without AWS services. Perfect for testing, debugging, and development.

## Overview

The local emulator replaces AWS services with local filesystem storage:

- **S3** → Local filesystem (`local_data/congress-disclosures-standardized/`)
- **SQS** → Local JSON files (`local_data/sqs_queues/`)
- **Lambda** → Local function execution (logged only in current implementation)

All data is stored locally in the `local_data/` directory, making it easy to inspect, debug, and understand the pipeline.

## Quick Start

### 1. Run Locally

```bash
# Run the full pipeline locally
make local-run-full

# Or run incrementally
make local-run

# Or just aggregation
make local-run-aggregate
```

### 2. View Local Data

```bash
# View directory structure
make local-view

# Or browse via HTTP at http://localhost:8000
make local-serve
```

### 3. Clean Local Data

```bash
make local-clean
```

## Detailed Usage

### Running Specific Pipeline Modes

The local runner supports the same modes as the main pipeline:

```bash
# Full mode (clean ingestion, extraction, aggregation)
python3 scripts/local_runner.py --mode full --year 2025 --clean

# Incremental mode (skip existing files)
python3 scripts/local_runner.py --mode incremental --year 2025

# Reprocess mode (re-run extraction on existing Bronze files)
python3 scripts/local_runner.py --mode reprocess

# Aggregate only (skip ingestion, just run Gold scripts)
python3 scripts/local_runner.py --mode aggregate
```

### Options

- `--year YEAR` - Year to process (default: 2025)
- `--mode MODE` - Pipeline mode (full, incremental, reprocess, aggregate)
- `--clean` - Clean local data before running
- `--view-data` - Show local data structure after completion
- `--start-viewer` - Start HTTP server to browse data

## Local Data Directory Structure

After running the pipeline, your `local_data/` directory will look like:

```
local_data/
├── congress-disclosures-standardized/
│   ├── bronze/
│   │   ├── house/financial/
│   │   │   └── year=2025/
│   │   │       ├── index/2025FD.xml
│   │   │       ├── raw_zip/2025FD.zip
│   │   │       └── filing_type=P/pdfs/*.pdf
│   │   ├── congress/
│   │   │   ├── member/*.json.gz
│   │   │   └── bill/*.json.gz
│   │   └── lobbying/
│   │       ├── filings/*.json.gz
│   │       └── contributions/*.json.gz
│   ├── silver/
│   │   ├── house/financial/
│   │   │   ├── filings/*.parquet
│   │   │   ├── documents/*.parquet
│   │   │   └── text/*.txt.gz
│   │   ├── congress/
│   │   │   ├── bill_actions/*.parquet
│   │   │   └── bill_cosponsors/*.parquet
│   │   └── lobbying/
│   │       ├── filings/*.parquet
│   │       └── clients/*.parquet
│   └── gold/
│       ├── dimensions/
│       │   ├── dim_members/*.parquet
│       │   └── dim_bills/*.parquet
│       ├── facts/
│       │   ├── fact_filings/*.parquet
│       │   └── fact_transactions/*.parquet
│       └── aggregates/
│           ├── trending_stocks.json
│           └── member_trading_stats.json
└── sqs_queues/
    └── extraction-queue/*.json
```

## Using Local Mode in Your Scripts

### Option 1: Use the Helper Module (Recommended)

```python
# Instead of:
import boto3
s3 = boto3.client('s3')

# Use:
from ingestion.lib.aws_client import get_client
s3 = get_client('s3')
```

The `get_client()` function automatically returns a local emulator client when `USE_LOCAL_EMULATOR=true`.

### Option 2: Environment Variables

Set these environment variables before running any script:

```bash
export USE_LOCAL_EMULATOR=true
export LOCAL_DATA_DIR=./local_data

python3 scripts/your_script.py
```

### Option 3: Programmatic Setup

```python
import os
os.environ['USE_LOCAL_EMULATOR'] = 'true'
os.environ['LOCAL_DATA_DIR'] = './local_data'

from ingestion.lib.aws_client import get_client
s3 = get_client('s3')
```

## Inspecting Local Data

### View Directory Structure

```bash
# With tree (if installed)
tree -L 4 local_data

# Without tree
find local_data -type f | head -20
```

### Browse via HTTP

```bash
make local-serve
# Open http://localhost:8000 in your browser
```

### Read Bronze PDFs

```bash
# PDFs are stored as actual files
ls local_data/congress-disclosures-standardized/bronze/house/financial/year=2025/filing_type=P/pdfs/

# Open a PDF
open local_data/congress-disclosures-standardized/bronze/house/financial/year=2025/filing_type=P/pdfs/10063228.pdf
```

### Read Silver Parquet Files

```python
import pandas as pd

# Read Silver documents
df = pd.read_parquet('local_data/congress-disclosures-standardized/silver/house/financial/documents/')
print(df.head())

# Read Silver bill actions
df = pd.read_parquet('local_data/congress-disclosures-standardized/silver/congress/bill_actions/')
print(df.head())
```

### Read Gold Aggregates

```python
import json

# Read trending stocks
with open('local_data/congress-disclosures-standardized/gold/aggregates/trending_stocks.json') as f:
    data = json.load(f)
    print(json.dumps(data, indent=2))
```

## Debugging Tips

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
make local-run
```

### Check Queue Messages

```bash
# View SQS queue messages (stored as JSON files)
cat local_data/sqs_queues/extraction-queue/*.json | jq .
```

### Compare Local vs AWS

Run the same script locally and against AWS to compare results:

```bash
# Run locally
USE_LOCAL_EMULATOR=true python3 scripts/build_dim_members_simple.py

# Run against AWS
USE_LOCAL_EMULATOR=false python3 scripts/build_dim_members_simple.py

# Compare results
diff local_data/... s3://congress-disclosures-standardized/...
```

## Limitations

The local emulator is designed for development and testing. It has some limitations:

1. **Lambda Functions**: Lambda invocations are logged but not actually executed locally (this can be extended)
2. **No Concurrent Processing**: No parallel Lambda execution (single-threaded)
3. **No SQS Polling**: SQS messages aren't automatically processed (queue workers not implemented)
4. **Simplified API**: Some advanced AWS features (versioning, tags, lifecycle) are not emulated

## Extending the Local Emulator

To add support for more AWS services or features:

### Add a New Service

Edit `ingestion/lib/local_emulator.py`:

```python
class LocalDynamoDBClient:
    """Local DynamoDB emulator."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir) / "dynamodb"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def put_item(self, TableName: str, Item: dict) -> dict:
        table_dir = self.base_dir / TableName
        table_dir.mkdir(parents=True, exist_ok=True)

        # Store as JSON file using primary key as filename
        item_id = Item.get('id', str(hash(str(Item))))
        item_path = table_dir / f"{item_id}.json"

        with open(item_path, 'w') as f:
            json.dump(Item, f, indent=2)

        return {'ResponseMetadata': {'HTTPStatusCode': 200}}
```

Then update `get_client()`:

```python
def get_client(service_name: str, **kwargs):
    if use_local:
        if service_name == 'dynamodb':
            return LocalDynamoDBClient(local_data_dir)
        # ... rest of services
```

## Troubleshooting

### Local Data Not Appearing

Check that `USE_LOCAL_EMULATOR=true` is set:

```bash
echo $USE_LOCAL_EMULATOR
```

Ensure the local_data directory exists:

```bash
mkdir -p local_data
```

### Scripts Still Hitting AWS

Make sure you're using `get_client()` instead of `boto3.client()`:

```python
# Wrong
import boto3
s3 = boto3.client('s3')

# Correct
from ingestion.lib.aws_client import get_client
s3 = get_client('s3')
```

### Permission Errors

The local_data directory must be writable:

```bash
chmod -R u+w local_data
```

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the pipeline flow
- Check [CLAUDE.md](../CLAUDE.md) for development patterns
- See [DEPLOYMENT.md](DEPLOYMENT.md) for deploying to AWS

## Contributing

If you add features to the local emulator, please:

1. Update this documentation
2. Add tests in `tests/unit/test_local_emulator.py`
3. Update the example scripts
4. Add your changes to the PR description

Happy local development! 🏠
