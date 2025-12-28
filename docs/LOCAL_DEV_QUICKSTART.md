# Local Development Quickstart

Run the entire pipeline on your computer, inspect all data locally, and debug without touching AWS!

## Quick Commands

### Option 1: Mirror Your S3 Data (Recommended)

Download everything from your S3 bucket to `local_data/`:

```bash
# Download a small sample (100 files) to test
make local-sync-sample

# Download everything (may be large!)
make local-sync

# Download only Bronze layer
make local-sync-bronze

# Download specific year
make local-sync-year YEAR=2025

# Preview what would be downloaded (no actual download)
make local-sync-dry-run
```

### Option 2: Download Fresh Data from Source

Download data directly from House Clerk, Congress.gov, and LDA APIs:

```bash
# Download small sample (10 PDFs, 5 bills, 5 lobbying filings)
make local-ingest-sample

# Download 50 PDFs (good for testing)
make local-ingest

# Download ALL data (large - hundreds of MB)
make local-ingest-full
```

### View Your Local Data

```bash
# Show directory structure
make local-view

# Browse via HTTP at http://localhost:8000
make local-serve
```

### Clean Local Data

```bash
make local-clean
```

## Step-by-Step Example

### 1. Download Sample Data

```bash
# Download 100 files from your S3 bucket
make local-sync-sample
```

Expected output:
```
📦 S3 TO LOCAL SYNC
================================================================================
☁️  S3 Bucket: congress-disclosures-standardized
📁 Local Dir: /path/to/local_data
🎯 Layer: all
📊 Source: all
================================================================================

✅ Connected to S3 bucket: congress-disclosures-standardized

📦 Syncing: bronze/house/financial/
   Downloaded 50 files (25 MB)...
   ✅ bronze/house/financial/: 75 downloaded, 0 skipped

📦 Syncing: silver/house/financial/
   Downloaded 15 files (5 MB)...
   ✅ silver/house/financial/: 20 downloaded, 0 skipped

📊 SYNC SUMMARY
================================================================================
Total files scanned: 100
Files downloaded: 95
Files skipped (already exist): 5
Files failed: 0
Total size: 30 MB
================================================================================

✅ Sync complete!
📁 Data saved to: /path/to/local_data/congress-disclosures-standardized
```

### 2. Inspect the Data

```bash
# View structure
make local-view
```

Output:
```
local_data
└── congress-disclosures-standardized
    ├── bronze
    │   ├── house/financial/year=2025/filing_type=P/pdfs/
    │   ├── congress/bill/
    │   └── lobbying/filings/
    ├── silver
    │   ├── house/financial/documents/
    │   ├── congress/bill_actions/
    │   └── lobbying/filings/
    └── gold
        ├── aggregates/
        └── dimensions/
```

### 3. Browse PDFs Locally

```bash
# List all PDFs
find local_data -name "*.pdf"

# Open a PDF
open local_data/congress-disclosures-standardized/bronze/house/financial/year=2025/filing_type=P/pdfs/10063228.pdf
```

### 4. Read Parquet Files

```python
import pandas as pd

# Read Silver documents
df = pd.read_parquet('local_data/congress-disclosures-standardized/silver/house/financial/documents/')
print(df.head())
print(f"Total documents: {len(df)}")

# Read bill actions
df = pd.read_parquet('local_data/congress-disclosures-standardized/silver/congress/bill_actions/')
print(df.head())
```

### 5. Read JSON Files

```python
import json
import gzip

# Read Bronze lobbying filing
with gzip.open('local_data/congress-disclosures-standardized/bronze/lobbying/filings/year=2025/filing_uuid=12345.json.gz', 'rt') as f:
    data = json.load(f)
    print(json.dumps(data, indent=2))

# Read Gold aggregate
with open('local_data/congress-disclosures-standardized/gold/aggregates/trending_stocks.json') as f:
    data = json.load(f)
    print(json.dumps(data, indent=2))
```

### 6. Start HTTP Server

```bash
# Start server on port 8000
make local-serve
```

Then open http://localhost:8000 in your browser to navigate the data.

## Advanced Usage

### Sync Specific Layer

```bash
# Bronze only (raw data)
python3 scripts/sync_s3_to_local.py --layer bronze

# Silver only (normalized tables)
python3 scripts/sync_s3_to_local.py --layer silver

# Gold only (analytics)
python3 scripts/sync_s3_to_local.py --layer gold
```

### Sync Specific Source

```bash
# House Financial Disclosures only
python3 scripts/sync_s3_to_local.py --source house

# Congress bills only
python3 scripts/sync_s3_to_local.py --source congress

# Lobbying data only
python3 scripts/sync_s3_to_local.py --source lobbying
```

### Sync Specific Prefix

```bash
# Download specific folder
python3 scripts/sync_s3_to_local.py --prefix "bronze/house/financial/year=2025/filing_type=P/"
```

### Download Fresh Data from Source APIs

```bash
# House FD: Download 100 PDFs
python3 scripts/local_ingestion.py --year 2025 --limit-pdfs 100

# Congress bills: Requires CONGRESS_API_KEY
export CONGRESS_API_KEY=your_key_here
python3 scripts/local_ingestion.py --skip-house --limit-bills 50

# Lobbying filings
python3 scripts/local_ingestion.py --skip-house --skip-bills --limit-lobbying 100
```

## File Structure

After syncing, your `local_data/` will mirror your S3 structure:

```
local_data/
└── congress-disclosures-standardized/
    ├── bronze/                    # Raw source data
    │   ├── house/financial/
    │   │   └── year=2025/
    │   │       ├── index/2025FD.xml
    │   │       ├── raw_zip/2025FD.zip
    │   │       └── filing_type=P/pdfs/*.pdf
    │   ├── congress/
    │   │   ├── member/*.json.gz
    │   │   ├── bill/*.json.gz
    │   │   └── bill_actions/*.json.gz
    │   └── lobbying/
    │       ├── filings/*.json.gz
    │       └── contributions/*.json.gz
    ├── silver/                    # Normalized tables
    │   ├── house/financial/
    │   │   ├── filings/*.parquet
    │   │   ├── documents/*.parquet
    │   │   ├── text/*.txt.gz
    │   │   └── objects/*.json
    │   ├── congress/
    │   │   ├── bill_actions/*.parquet
    │   │   └── bill_cosponsors/*.parquet
    │   └── lobbying/
    │       ├── filings/*.parquet
    │       ├── clients/*.parquet
    │       └── activities/*.parquet
    └── gold/                      # Analytics & aggregates
        ├── dimensions/
        │   ├── dim_members/*.parquet
        │   ├── dim_bills/*.parquet
        │   └── dim_lobbyists/*.parquet
        ├── facts/
        │   ├── fact_filings/*.parquet
        │   ├── fact_transactions/*.parquet
        │   └── fact_lobbying_activity/*.parquet
        └── aggregates/
            ├── trending_stocks.json
            ├── member_trading_stats.json
            ├── bill_lobbying_correlation.json
            └── network_graph.json
```

## Troubleshooting

### Python Version Error

If you see:
```
/Users/jake/Library/Python/3.9/lib/python/site-packages/boto3/compat.py:84: PythonDeprecationWarning
```

You're using Python 3.9. Upgrade to 3.11:

```bash
brew install python@3.11
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
python3 --version  # Should show 3.11.x
```

See [PYTHON_UPGRADE_GUIDE.md](PYTHON_UPGRADE_GUIDE.md) for details.

### AWS Credentials Not Found

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

### Permission Denied on local_data/

```bash
chmod -R u+w local_data
```

### Disk Space Issues

Check how much space you have:

```bash
df -h .
```

The full sync can be 5-50GB depending on your data. Use `--max-files` or `--layer bronze` to limit download size.

## Benefits of Local Development

✅ **Inspect Everything**: View PDFs, Parquet files, JSON directly
✅ **No AWS Costs**: Read data without S3 API calls
✅ **Offline Access**: Work without internet
✅ **Easy Debugging**: Print, grep, and explore files
✅ **Fast Iteration**: Test scripts locally before deploying

## Next Steps

- [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) - Full local emulator docs
- [PYTHON_UPGRADE_GUIDE.md](PYTHON_UPGRADE_GUIDE.md) - Upgrade Python 3.9 → 3.11
- [ARCHITECTURE.md](ARCHITECTURE.md) - Understand the pipeline
- [CLAUDE.md](../CLAUDE.md) - Development guidelines

Happy local development! 🏠
