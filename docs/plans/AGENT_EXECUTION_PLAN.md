# Agent Execution Plan - Politics Data Platform

**Purpose**: Single-page sequential execution plan for final organization + high-value features
**Format**: Execute tasks in order, validate each before proceeding
**Estimated Total Time**: 8-10 hours

---

## SCENARIO 1: FINAL ROOT DIRECTORY ORGANIZATION (Tasks 1-7)

### Task 1: Move All Documentation to `docs/` Subdirectories
**Time**: 20 minutes

```bash
cd /Users/jake/Documents/GitHub/congress-disclosures-standardized

# Create subdirectories
mkdir -p docs/architecture
mkdir -p docs/guides
mkdir -p docs/plans
mkdir -p docs/terraform_audit
mkdir -p docs/archived/old_makefiles

# Move architectural docs
mv MASTER_EXECUTION_PLAN.md docs/plans/
mv AGENT_GUIDE.md docs/guides/
mv PROJECT_STRUCTURE.md docs/architecture/
mv REORGANIZATION_SUMMARY.md docs/architecture/

# Move Terraform audit files
mv docs/terraform_audit_*.md docs/terraform_audit/ 2>/dev/null || true

# Move old/archived docs
mv docs/DEPLOYMENT_ALTERNATIVE_*.md docs/archived/ 2>/dev/null || true
mv docs/Makefile.* docs/archived/old_makefiles/ 2>/dev/null || true

# Update docs/README.md with new structure
cat > docs/README.md << 'EOF'
# Documentation

## Structure

- `architecture/` - System architecture, data flow, reorganization summaries
- `guides/` - Setup guides, agent automation guides, API documentation
- `plans/` - Master execution plans, modernization roadmaps
- `terraform_audit/` - Infrastructure audit reports
- `archived/` - Historical documentation, old status reports
  - `status_reports/` - Implementation summaries, bug fix reports
  - `old_makefiles/` - Deprecated Makefile versions

## Quick Links

- [Master Execution Plan](plans/MASTER_EXECUTION_PLAN.md)
- [Agent Guide](guides/AGENT_GUIDE.md)
- [Architecture Overview](architecture/PROJECT_STRUCTURE.md)
- [API Documentation](API_ENDPOINTS.md)
- [Legal Compliance](LEGAL_NOTES.md)
EOF
```

**Validation**:
```bash
# Check docs/ structure
tree docs/ -L 2

# Verify no orphaned MD files at root (except README, CLAUDE, CONTRIBUTING)
ls -1 *.md | grep -v "README\|CLAUDE\|CONTRIBUTING" && echo "ERROR: Orphaned MD files found" || echo "✓ Documentation organized"
```

**DOD**:
- [ ] All architectural docs in `docs/architecture/`
- [ ] All plans in `docs/plans/`
- [ ] All guides in `docs/guides/`
- [ ] Terraform audits in `docs/terraform_audit/`
- [ ] Old docs in `docs/archived/`
- [ ] `docs/README.md` updated with structure
- [ ] Only README.md, CLAUDE.md, CONTRIBUTING.md remain at root

---

### Task 2: Create `config/` Directory for All Configuration Files
**Time**: 15 minutes

```bash
cd /Users/jake/Documents/GitHub/congress-disclosures-standardized

# Create config directory
mkdir -p config

# Move configuration files
mv .env.example config/
mv .flake8 config/ 2>/dev/null || true
mv .pylintrc config/ 2>/dev/null || true
mv pytest.ini config/ 2>/dev/null || true
mv mypy.ini config/ 2>/dev/null || true

# Create symlinks at root for tools that expect root configs
ln -sf config/.env.example .env.example
ln -sf config/.flake8 .flake8 2>/dev/null || true
ln -sf config/pytest.ini pytest.ini 2>/dev/null || true

# Update .gitignore to reference new structure
cat >> .gitignore << 'EOF'

# Config directory
config/.env
!config/.env.example
EOF
```

**Validation**:
```bash
# Verify config files moved
ls -la config/
test -f config/.env.example && echo "✓ Config files organized" || echo "ERROR: Missing config files"

# Verify symlinks work
python3 -c "import pytest" && pytest --version || echo "Note: pytest config symlink working"
```

**DOD**:
- [ ] `config/` directory created
- [ ] `.env.example` moved to `config/`
- [ ] All linter configs moved to `config/`
- [ ] Test configs moved to `config/`
- [ ] Symlinks created for tools requiring root configs
- [ ] `.gitignore` updated

---

### Task 3: Move Remaining Utility Scripts to `backend/scripts/utils/`
**Time**: 10 minutes

```bash
cd /Users/jake/Documents/GitHub/congress-disclosures-standardized

# Check for any remaining Python scripts at root
find . -maxdepth 1 -name "*.py" -type f

# Move any found scripts
mv find_filing_types.py backend/scripts/utils/ 2>/dev/null || true
mv inspect_pdf.py backend/scripts/utils/ 2>/dev/null || true
mv invoke_lambdas.py backend/scripts/utils/ 2>/dev/null || true
mv process_all_ptrs.py backend/scripts/utils/ 2>/dev/null || true
mv process_ptrs_local.py backend/scripts/utils/ 2>/dev/null || true
mv test_components.py backend/scripts/utils/ 2>/dev/null || true
mv test_dim_assets_quick.py backend/scripts/utils/ 2>/dev/null || true

# Update backend/scripts/utils/README.md
cat >> backend/scripts/utils/README.md << 'EOF'

## Newly Organized Scripts

- `find_filing_types.py` - Identify filing type distribution
- `inspect_pdf.py` - Debug PDF extraction issues
- `invoke_lambdas.py` - Manual Lambda testing
- `process_all_ptrs.py` - Bulk PTR processing
- `process_ptrs_local.py` - Local PTR extraction testing
- `test_components.py` - Component integration tests
- `test_dim_assets_quick.py` - Asset dimension validation
EOF
```

**Validation**:
```bash
# Verify no Python scripts at root
find . -maxdepth 1 -name "*.py" -type f | wc -l | grep -q "0" && echo "✓ Scripts organized" || echo "ERROR: Python scripts remain at root"

# Verify scripts moved
ls backend/scripts/utils/*.py | wc -l
```

**DOD**:
- [ ] No `.py` files at root (except setup.py if needed)
- [ ] All utility scripts in `backend/scripts/utils/`
- [ ] `backend/scripts/utils/README.md` updated

---

### Task 4: Reorganize Shell Scripts into `scripts/` Subdirectories
**Time**: 15 minutes

```bash
cd /Users/jake/Documents/GitHub/congress-disclosures-standardized

# Create script subdirectories
mkdir -p scripts/setup
mkdir -p scripts/deployment
mkdir -p scripts/data_operations

# Move setup scripts
mv scripts/sync_terraform_outputs.sh scripts/setup/ 2>/dev/null || true
mv scripts/sync-api-url.sh scripts/setup/ 2>/dev/null || true
mv scripts/generate-types.sh scripts/setup/ 2>/dev/null || true

# Move deployment scripts
mv scripts/package_gold_lambdas.sh scripts/deployment/ 2>/dev/null || true
mv deploy-week2.sh scripts/deployment/ 2>/dev/null || true
mv build.sh scripts/deployment/ 2>/dev/null || true

# Move data operation scripts
mv scripts/validate_pipeline_integrity.py scripts/data_operations/ 2>/dev/null || true
mv scripts/generate_pipeline_errors.py scripts/data_operations/ 2>/dev/null || true

# Create README for scripts/
cat > scripts/README.md << 'EOF'
# Scripts

Organized by purpose:

## `setup/`
Environment setup, configuration sync, type generation

- `sync_terraform_outputs.sh` - Sync Terraform outputs to .env
- `sync-api-url.sh` - Update API Gateway URL in frontend
- `generate-types.sh` - Generate TypeScript types from OpenAPI

## `deployment/`
Lambda packaging, infrastructure deployment

- `package_gold_lambdas.sh` - Package Gold layer Lambda functions
- `deploy-week2.sh` - Week 2 deployment script
- `build.sh` - Full build script

## `data_operations/`
Data validation, pipeline management

- `validate_pipeline_integrity.py` - Validate S3 data integrity
- `generate_pipeline_errors.py` - Generate error tracking report
- `run_smart_pipeline.py` - Main pipeline orchestrator

## Root-level Scripts
- `run_smart_pipeline.py` - Main entry point for pipeline operations
- `build_bronze_manifest.py` - Generate Bronze layer manifest
- `rebuild_silver_manifest.py` - Rebuild Silver layer manifest
EOF
```

**Validation**:
```bash
# Check scripts/ structure
tree scripts/ -L 2

# Verify organization
ls scripts/setup/ scripts/deployment/ scripts/data_operations/
```

**DOD**:
- [ ] Scripts organized into `setup/`, `deployment/`, `data_operations/`
- [ ] `scripts/README.md` created
- [ ] All shell scripts have clear purposes

---

### Task 5: Clean Up Root Terraform Files (Move Orphaned to infra/)
**Time**: 10 minutes

```bash
cd /Users/jake/Documents/GitHub/congress-disclosures-standardized

# Check for any .tf files at root
ls -1 *.tf 2>/dev/null || echo "No Terraform files at root"

# If any exist, move to infra/terraform/
mv *.tf infra/terraform/ 2>/dev/null || true

# Verify infra/ structure is clear
ls -la infra/
```

**Validation**:
```bash
# Verify no .tf files at root
ls -1 *.tf 2>/dev/null && echo "ERROR: Terraform files at root" || echo "✓ Terraform organized"

# Verify infra/terraform/ has all files
ls infra/terraform/*.tf | wc -l
```

**DOD**:
- [ ] No `.tf` files at root
- [ ] All Terraform files in `infra/terraform/`

---

### Task 6: Final Root Cleanup - Remove Orphaned Files
**Time**: 15 minutes

```bash
cd /Users/jake/Documents/GitHub/congress-disclosures-standardized

# List all root files (excluding directories)
echo "Current root files:"
ls -1 | grep -v "^[.]" | while read item; do [ -f "$item" ] && echo "  - $item"; done

# Remove known orphaned files (MANUAL REVIEW FIRST!)
# Common orphans to check:
rm -f cleanup_root_scripts.sh  # Temporary cleanup script
rm -f reorganize_structure.sh  # Temporary reorganization script
rm -f *.log                    # Log files
rm -f *.tmp                    # Temporary files

# Create .editorconfig for consistency
cat > .editorconfig << 'EOF'
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.{py,sh}]
indent_style = space
indent_size = 4

[*.{js,ts,jsx,tsx,json,yml,yaml}]
indent_style = space
indent_size = 2

[*.md]
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
EOF
```

**Validation**:
```bash
# Final root listing
echo "Final root structure:"
ls -1 | head -20

# Expected files at root (should be ~10-12 files):
# - README.md
# - CLAUDE.md
# - CONTRIBUTING.md
# - LICENSE
# - Makefile
# - .gitignore
# - .env.example (symlink)
# - .editorconfig
# - backend/ (dir)
# - frontend/ (dir)
# - infra/ (dir)
# - docs/ (dir)
# - scripts/ (dir)
# - tests/ (dir)
# - config/ (dir)
```

**DOD**:
- [ ] Root has ≤12 essential files
- [ ] All temporary scripts removed
- [ ] No orphaned .md, .py, .sh, .tf files
- [ ] `.editorconfig` created
- [ ] Only directories: backend/, frontend/, infra/, docs/, scripts/, tests/, config/

---

### Task 7: Update Repository Documentation with New Structure
**Time**: 15 minutes

```bash
cd /Users/jake/Documents/GitHub/congress-disclosures-standardized

# Update README.md with new structure section
cat > /tmp/structure_section.md << 'EOF'

## Repository Structure

```
congress-disclosures-standardized/
├── backend/                 # Backend code (Lambda functions, shared libraries, scripts)
│   ├── functions/           # Lambda function handlers
│   │   ├── ingestion/       # Data ingestion functions
│   │   ├── gold_layer/      # Analytics aggregation functions
│   │   └── api/             # API endpoint handlers
│   ├── lib/                 # Shared libraries
│   │   ├── ingestion/       # Extraction, S3 utils, parquet writers
│   │   └── gold/            # Aggregation utilities
│   ├── scripts/             # Data operations scripts
│   │   ├── utils/           # Helper scripts for debugging
│   │   └── data_operations/ # Pipeline validation, error tracking
│   └── orchestration/       # Step Functions state machine definitions
├── frontend/                # Frontend applications
│   └── website/             # Next.js website (React, TypeScript)
├── infra/                   # Infrastructure as Code
│   └── terraform/           # Terraform configuration files
├── docs/                    # Documentation
│   ├── architecture/        # System architecture, data flow
│   ├── guides/              # Setup guides, API docs
│   ├── plans/               # Modernization plans, roadmaps
│   └── archived/            # Historical documentation
├── scripts/                 # Operational scripts
│   ├── setup/               # Environment setup, config sync
│   ├── deployment/          # Lambda packaging, deployment
│   └── data_operations/     # Pipeline management
├── tests/                   # Test suites
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── config/                  # Configuration files
│   ├── .env.example         # Environment variables template
│   └── pytest.ini           # Test configuration
├── README.md                # This file
├── CLAUDE.md                # Claude Code instructions
├── CONTRIBUTING.md          # Contribution guidelines
├── Makefile                 # Development commands
└── .gitignore               # Git ignore rules
```
EOF

# Note: Manually append this to README.md in appropriate location
echo "✓ Structure documentation prepared in /tmp/structure_section.md"
echo "  Manual step: Add this section to README.md"
```

**Validation**:
```bash
# Verify structure matches reality
tree -L 2 -d --charset ascii
```

**DOD**:
- [ ] README.md updated with new structure
- [ ] Structure diagram matches actual directories
- [ ] CLAUDE.md references new paths
- [ ] CONTRIBUTING.md updated if needed

---

## SCENARIO 2: HIGH-VALUE QUIVERQUANT-STYLE FEATURES (Tasks 8-15)

### Task 8: Create `notable_transactions` Gold Aggregate
**Time**: 30 minutes

```bash
cd /Users/jake/Documents/GitHub/congress-disclosures-standardized
```

Create `backend/scripts/compute_agg_notable_transactions.py`:

```python
#!/usr/bin/env python3
"""
Compute notable/high-value transactions aggregate for real-time alerts.

QuiverQuant-style insights:
- Large transactions (>$50K)
- Committee-asset correlation
- Crypto transactions
- Recent trades with timing analysis
"""

import pandas as pd
import pyarrow.parquet as pq
from datetime import datetime, timedelta
from backend.lib.ingestion.s3_utils import upload_file_to_s3
from backend.lib.ingestion.s3_path_registry import S3Paths

BUCKET = S3Paths.BUCKET

# Thresholds
NOTABLE_AMOUNT_THRESHOLD = 50000  # $50K+
CRYPTO_KEYWORDS = ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'coinbase', 'binance']
RECENT_DAYS = 7

def load_transactions():
    """Load all PTR transactions from Gold fact table."""
    s3_path = f"s3://{BUCKET}/{S3Paths.gold_fact_transactions()}"
    df = pd.read_parquet(s3_path)
    return df

def load_members():
    """Load member dimension."""
    s3_path = f"s3://{BUCKET}/{S3Paths.gold_dim_members()}"
    df = pd.read_parquet(s3_path)
    return df[['bioguide_id', 'full_name', 'party', 'state', 'chamber']]

def load_committee_assignments():
    """Load committee assignments from reference data."""
    # TODO: Build this from Congress.gov API data
    # For now, return empty DataFrame
    return pd.DataFrame(columns=['bioguide_id', 'committee_name', 'subcommittee_name'])

def identify_notable_transactions(df_trans, df_members, df_committees):
    """Identify high-value notable transactions."""

    # Join with member data
    df = df_trans.merge(df_members, on='bioguide_id', how='left')

    # Join with committee data
    df = df.merge(df_committees, on='bioguide_id', how='left')

    # Filter for notable amounts (>$50K)
    df = df[df['amount_low'] >= NOTABLE_AMOUNT_THRESHOLD].copy()

    # Add flags
    df['is_crypto'] = df['asset_name'].str.lower().str.contains('|'.join(CRYPTO_KEYWORDS), na=False)
    df['is_recent'] = (pd.to_datetime('now') - pd.to_datetime(df['transaction_date'])) <= timedelta(days=RECENT_DAYS)

    # Calculate committee relevance score
    df['committee_relevance'] = 0.0

    # Crypto + Digital Assets committee
    df.loc[
        df['is_crypto'] & df['committee_name'].str.contains('Digital Assets|Financial Services', na=False),
        'committee_relevance'
    ] = 1.0

    # Tech stocks + Science/Tech committee
    tech_keywords = ['apple', 'microsoft', 'google', 'alphabet', 'meta', 'amazon', 'nvidia', 'tesla']
    df.loc[
        df['asset_name'].str.lower().str.contains('|'.join(tech_keywords), na=False) &
        df['committee_name'].str.contains('Science|Technology|Commerce', na=False),
        'committee_relevance'
    ] = 0.8

    # Defense stocks + Armed Services committee
    defense_keywords = ['lockheed', 'raytheon', 'northrop', 'general dynamics', 'boeing']
    df.loc[
        df['asset_name'].str.lower().str.contains('|'.join(defense_keywords), na=False) &
        df['committee_name'].str.contains('Armed Services|Defense', na=False),
        'committee_relevance'
    ] = 0.8

    # Sort by relevance and amount
    df = df.sort_values(['is_recent', 'committee_relevance', 'amount_low'], ascending=[False, False, False])

    # Select columns for output
    output_cols = [
        'bioguide_id', 'full_name', 'party', 'state', 'chamber',
        'transaction_date', 'filing_date', 'asset_name', 'ticker',
        'transaction_type', 'amount_low', 'amount_high',
        'committee_name', 'subcommittee_name', 'committee_relevance',
        'is_crypto', 'is_recent'
    ]

    return df[output_cols]

def generate_alert_text(row):
    """Generate QuiverQuant-style alert text."""

    # Format amount range
    if row['amount_high']:
        amount_str = f"${row['amount_low']:,}-${row['amount_high']:,}"
    else:
        amount_str = f"up to ${row['amount_low']:,}"

    # Base alert
    alert = f"BREAKING: Representative {row['full_name']} ({row['party']}-{row['state']}) has filed a {row['transaction_type'].lower()} of {amount_str} in {row['asset_name']}"

    # Add ticker if available
    if pd.notna(row['ticker']):
        alert += f", ${row['ticker']}"

    # Add committee context if relevant
    if row['committee_relevance'] > 0.5:
        alert += f". {row['full_name']} sits on the {row['committee_name']}"
        if pd.notna(row['subcommittee_name']):
            alert += f" ({row['subcommittee_name']})"

    alert += "."

    return alert

def main():
    print("Loading data...")
    df_trans = load_transactions()
    df_members = load_members()
    df_committees = load_committee_assignments()

    print(f"Processing {len(df_trans):,} transactions...")
    df_notable = identify_notable_transactions(df_trans, df_members, df_committees)

    print(f"Identified {len(df_notable):,} notable transactions")

    # Generate alert text
    df_notable['alert_text'] = df_notable.apply(generate_alert_text, axis=1)

    # Add metadata
    df_notable['computed_at'] = datetime.utcnow().isoformat()
    df_notable['alert_id'] = df_notable.apply(
        lambda x: f"{x['bioguide_id']}_{x['transaction_date']}_{x['ticker'] or 'NOTICKER'}",
        axis=1
    )

    # Upload to S3
    output_path = "data/gold/aggregates/notable_transactions/notable_transactions.parquet"
    local_path = "/tmp/notable_transactions.parquet"

    df_notable.to_parquet(local_path, index=False, compression='snappy')
    upload_file_to_s3(local_path, BUCKET, output_path)

    print(f"✓ Uploaded {len(df_notable):,} notable transactions to s3://{BUCKET}/{output_path}")

    # Print top 5 alerts
    print("\nTop 5 Notable Transactions:")
    for idx, row in df_notable.head(5).iterrows():
        print(f"\n{row['alert_text']}")

if __name__ == "__main__":
    main()
```

Make executable:
```bash
chmod +x backend/scripts/compute_agg_notable_transactions.py
```

**Validation**:
```bash
# Test run (requires Gold data to exist)
python3 backend/scripts/compute_agg_notable_transactions.py

# Expected output:
# ✓ Uploaded X notable transactions to s3://...
# Top 5 Notable Transactions:
# BREAKING: Representative Byron Donalds...
```

**DOD**:
- [ ] Script created and executable
- [ ] Identifies transactions >$50K
- [ ] Detects crypto transactions
- [ ] Calculates committee relevance scores
- [ ] Generates QuiverQuant-style alert text
- [ ] Outputs to `gold/aggregates/notable_transactions/`

---

### Task 9: Create Crypto-Specific Aggregate
**Time**: 20 minutes

Create `backend/scripts/compute_agg_crypto_activity.py`:

```python
#!/usr/bin/env python3
"""
Compute crypto-specific trading activity aggregate.

Tracks:
- All cryptocurrency transactions
- Bitcoin, Ethereum, and major crypto holdings
- Crypto exchange stock trades (Coinbase, etc.)
- Trends over time
"""

import pandas as pd
from datetime import datetime
from backend.lib.ingestion.s3_utils import upload_file_to_s3
from backend.lib.ingestion.s3_path_registry import S3Paths

BUCKET = S3Paths.BUCKET

CRYPTO_KEYWORDS = {
    'bitcoin': ['bitcoin', 'btc', 'grayscale bitcoin'],
    'ethereum': ['ethereum', 'eth', 'grayscale ethereum'],
    'crypto_broad': ['crypto', 'cryptocurrency', 'digital currency', 'blockchain etf'],
    'crypto_exchanges': ['coinbase', 'binance', 'kraken', 'gemini', 'robinhood']
}

def load_transactions():
    """Load all PTR transactions."""
    s3_path = f"s3://{BUCKET}/{S3Paths.gold_fact_transactions()}"
    return pd.read_parquet(s3_path)

def identify_crypto_transactions(df):
    """Identify all crypto-related transactions."""

    df = df.copy()
    df['asset_name_lower'] = df['asset_name'].str.lower()

    # Tag crypto categories
    for category, keywords in CRYPTO_KEYWORDS.items():
        pattern = '|'.join(keywords)
        df[f'is_{category}'] = df['asset_name_lower'].str.contains(pattern, na=False)

    # Overall crypto flag
    df['is_crypto'] = (
        df['is_bitcoin'] | df['is_ethereum'] |
        df['is_crypto_broad'] | df['is_crypto_exchanges']
    )

    # Filter to crypto only
    df_crypto = df[df['is_crypto']].copy()

    # Add time dimensions
    df_crypto['year'] = pd.to_datetime(df_crypto['transaction_date']).dt.year
    df_crypto['month'] = pd.to_datetime(df_crypto['transaction_date']).dt.month
    df_crypto['quarter'] = pd.to_datetime(df_crypto['transaction_date']).dt.quarter

    return df_crypto

def compute_crypto_aggregates(df_crypto):
    """Compute aggregated crypto metrics."""

    aggs = []

    # Overall crypto activity by month
    monthly = df_crypto.groupby(['year', 'month']).agg({
        'bioguide_id': 'nunique',
        'transaction_type': 'count',
        'amount_low': 'sum'
    }).reset_index()
    monthly.columns = ['year', 'month', 'unique_members', 'transaction_count', 'total_amount']
    monthly['category'] = 'all_crypto'
    aggs.append(monthly)

    # Bitcoin-specific
    btc = df_crypto[df_crypto['is_bitcoin']].groupby(['year', 'month']).agg({
        'bioguide_id': 'nunique',
        'transaction_type': 'count',
        'amount_low': 'sum'
    }).reset_index()
    btc.columns = ['year', 'month', 'unique_members', 'transaction_count', 'total_amount']
    btc['category'] = 'bitcoin'
    aggs.append(btc)

    # Ethereum-specific
    eth = df_crypto[df_crypto['is_ethereum']].groupby(['year', 'month']).agg({
        'bioguide_id': 'nunique',
        'transaction_type': 'count',
        'amount_low': 'sum'
    }).reset_index()
    eth.columns = ['year', 'month', 'unique_members', 'transaction_count', 'total_amount']
    eth['category'] = 'ethereum'
    aggs.append(eth)

    # Combine
    df_agg = pd.concat(aggs, ignore_index=True)
    df_agg['computed_at'] = datetime.utcnow().isoformat()

    return df_agg

def main():
    print("Loading transactions...")
    df_trans = load_transactions()

    print("Identifying crypto transactions...")
    df_crypto = identify_crypto_transactions(df_trans)

    print(f"Found {len(df_crypto):,} crypto transactions")
    print(f"  - Bitcoin: {df_crypto['is_bitcoin'].sum():,}")
    print(f"  - Ethereum: {df_crypto['is_ethereum'].sum():,}")
    print(f"  - Exchanges: {df_crypto['is_crypto_exchanges'].sum():,}")

    # Compute aggregates
    df_agg = compute_crypto_aggregates(df_crypto)

    # Upload transaction-level data
    trans_path = "data/gold/aggregates/crypto_activity/crypto_transactions.parquet"
    local_trans = "/tmp/crypto_transactions.parquet"
    df_crypto.to_parquet(local_trans, index=False, compression='snappy')
    upload_file_to_s3(local_trans, BUCKET, trans_path)
    print(f"✓ Uploaded crypto transactions to s3://{BUCKET}/{trans_path}")

    # Upload aggregates
    agg_path = "data/gold/aggregates/crypto_activity/monthly_aggregates.parquet"
    local_agg = "/tmp/crypto_monthly_agg.parquet"
    df_agg.to_parquet(local_agg, index=False, compression='snappy')
    upload_file_to_s3(local_agg, BUCKET, agg_path)
    print(f"✓ Uploaded crypto aggregates to s3://{BUCKET}/{agg_path}")

if __name__ == "__main__":
    main()
```

Make executable:
```bash
chmod +x backend/scripts/compute_agg_crypto_activity.py
```

**Validation**:
```bash
python3 backend/scripts/compute_agg_crypto_activity.py
# Expected: ✓ Uploaded crypto transactions and aggregates
```

**DOD**:
- [ ] Script created and executable
- [ ] Identifies Bitcoin, Ethereum, and crypto exchange trades
- [ ] Computes monthly aggregates by crypto category
- [ ] Outputs transaction-level and aggregate data
- [ ] Ready for API consumption

---

### Task 10: Create Bill-Trade Temporal Correlation Aggregate
**Time**: 45 minutes

Create `backend/scripts/compute_agg_bill_trade_correlation.py`:

```python
#!/usr/bin/env python3
"""
Compute bill-trade temporal correlation aggregate.

Analyzes trades within ±7, ±14, ±30 days of:
- Bill introductions
- Committee votes
- Floor votes
- Bill passage

Identifies potential conflicts of interest.
"""

import pandas as pd
from datetime import datetime, timedelta
from backend.lib.ingestion.s3_utils import upload_file_to_s3
from backend.lib.ingestion.s3_path_registry import S3Paths

BUCKET = S3Paths.BUCKET

CORRELATION_WINDOWS = [7, 14, 30]  # Days before/after

def load_transactions():
    """Load all PTR transactions."""
    s3_path = f"s3://{BUCKET}/{S3Paths.gold_fact_transactions()}"
    df = pd.read_parquet(s3_path)
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
    return df

def load_bills():
    """Load Congress.gov bills data from Silver."""
    # TODO: Once Congress API is integrated, load from Silver
    # For now, return empty DataFrame
    return pd.DataFrame(columns=[
        'bill_id', 'congress', 'bill_type', 'bill_number',
        'sponsor_bioguide_id', 'introduced_date', 'title', 'policy_area'
    ])

def load_bill_actions():
    """Load bill actions (votes, committee activity)."""
    # TODO: Load from Silver congress_api tables
    return pd.DataFrame(columns=[
        'bill_id', 'action_date', 'action_type', 'description'
    ])

def find_correlations(df_trans, df_bills, df_actions):
    """Find temporal correlations between trades and bill activity."""

    correlations = []

    for window in CORRELATION_WINDOWS:
        delta = timedelta(days=window)

        # For each bill introduction
        for _, bill in df_bills.iterrows():
            bill_date = pd.to_datetime(bill['introduced_date'])
            sponsor = bill['sponsor_bioguide_id']

            # Find trades by sponsor within window
            trades = df_trans[
                (df_trans['bioguide_id'] == sponsor) &
                (df_trans['transaction_date'] >= bill_date - delta) &
                (df_trans['transaction_date'] <= bill_date + delta)
            ]

            for _, trade in trades.iterrows():
                days_diff = (trade['transaction_date'] - bill_date).days

                correlations.append({
                    'bioguide_id': sponsor,
                    'bill_id': bill['bill_id'],
                    'bill_title': bill['title'],
                    'policy_area': bill['policy_area'],
                    'bill_date': bill_date,
                    'bill_event_type': 'introduction',
                    'transaction_date': trade['transaction_date'],
                    'transaction_type': trade['transaction_type'],
                    'asset_name': trade['asset_name'],
                    'ticker': trade['ticker'],
                    'amount_low': trade['amount_low'],
                    'days_difference': days_diff,
                    'window': window,
                    'is_before_event': days_diff < 0,
                    'is_after_event': days_diff > 0
                })

        # Repeat for bill actions (votes, committee activity)
        for _, action in df_actions.iterrows():
            action_date = pd.to_datetime(action['action_date'])
            bill = df_bills[df_bills['bill_id'] == action['bill_id']].iloc[0]
            sponsor = bill['sponsor_bioguide_id']

            trades = df_trans[
                (df_trans['bioguide_id'] == sponsor) &
                (df_trans['transaction_date'] >= action_date - delta) &
                (df_trans['transaction_date'] <= action_date + delta)
            ]

            for _, trade in trades.iterrows():
                days_diff = (trade['transaction_date'] - action_date).days

                correlations.append({
                    'bioguide_id': sponsor,
                    'bill_id': bill['bill_id'],
                    'bill_title': bill['title'],
                    'policy_area': bill['policy_area'],
                    'bill_date': action_date,
                    'bill_event_type': action['action_type'],
                    'transaction_date': trade['transaction_date'],
                    'transaction_type': trade['transaction_type'],
                    'asset_name': trade['asset_name'],
                    'ticker': trade['ticker'],
                    'amount_low': trade['amount_low'],
                    'days_difference': days_diff,
                    'window': window,
                    'is_before_event': days_diff < 0,
                    'is_after_event': days_diff > 0
                })

    df_corr = pd.DataFrame(correlations)

    # Calculate suspicion score
    if len(df_corr) > 0:
        df_corr['suspicion_score'] = 0.0

        # Higher score for trades BEFORE votes (insider trading indicator)
        df_corr.loc[df_corr['is_before_event'] & (df_corr['bill_event_type'] == 'vote'), 'suspicion_score'] += 0.5

        # Higher score for trades close to event
        df_corr.loc[abs(df_corr['days_difference']) <= 7, 'suspicion_score'] += 0.3

        # Higher score for large amounts
        df_corr.loc[df_corr['amount_low'] >= 50000, 'suspicion_score'] += 0.2

        df_corr = df_corr.sort_values('suspicion_score', ascending=False)

    return df_corr

def main():
    print("Loading data...")
    df_trans = load_transactions()
    df_bills = load_bills()
    df_actions = load_bill_actions()

    if len(df_bills) == 0:
        print("⚠ No bill data available yet. Skipping correlation analysis.")
        print("  This will be enabled once Congress API integration is complete.")
        return

    print(f"Analyzing {len(df_trans):,} transactions against {len(df_bills):,} bills...")
    df_corr = find_correlations(df_trans, df_bills, df_actions)

    print(f"Found {len(df_corr):,} temporal correlations")

    # Add metadata
    df_corr['computed_at'] = datetime.utcnow().isoformat()

    # Upload
    output_path = "data/gold/aggregates/bill_trade_correlation/correlations.parquet"
    local_path = "/tmp/bill_trade_correlations.parquet"

    df_corr.to_parquet(local_path, index=False, compression='snappy')
    upload_file_to_s3(local_path, BUCKET, output_path)

    print(f"✓ Uploaded correlations to s3://{BUCKET}/{output_path}")

    # Print top suspicious correlations
    if len(df_corr) > 0:
        print("\nTop 5 Suspicious Correlations:")
        for _, row in df_corr.head(5).iterrows():
            print(f"\n{row['bioguide_id']}: Traded {row['asset_name']} {row['days_difference']} days from {row['bill_event_type']} on {row['bill_title'][:80]}...")
            print(f"  Suspicion Score: {row['suspicion_score']:.2f}")

if __name__ == "__main__":
    main()
```

Make executable:
```bash
chmod +x backend/scripts/compute_agg_bill_trade_correlation.py
```

**Validation**:
```bash
python3 backend/scripts/compute_agg_bill_trade_correlation.py
# Note: Will skip if no bill data exists yet
```

**DOD**:
- [ ] Script created and executable
- [ ] Analyzes ±7, ±14, ±30 day windows
- [ ] Calculates suspicion scores
- [ ] Handles bill introductions, votes, committee activity
- [ ] Ready for Congress API integration
- [ ] Outputs to `gold/aggregates/bill_trade_correlation/`

---

### Task 11: Create Real-Time Alert Lambda Function
**Time**: 45 minutes

Create `backend/functions/alerts/notable_transaction_alert/handler.py`:

```python
"""
Lambda: Notable Transaction Alert Handler

Triggered by: EventBridge rule when new transactions added to Gold layer
Purpose: Generate and publish real-time alerts for high-value transactions
"""

import json
import boto3
import os
from datetime import datetime
from typing import Dict, Any

sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')

SNS_TOPIC_ARN = os.environ.get('ALERT_SNS_TOPIC_ARN')
ALERTS_TABLE_NAME = os.environ.get('ALERTS_TABLE_NAME', 'congress-disclosures-alerts')

alerts_table = dynamodb.Table(ALERTS_TABLE_NAME)

# Thresholds
NOTABLE_AMOUNT = 50000  # $50K
CRYPTO_KEYWORDS = ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'coinbase']

def is_notable(transaction: Dict[str, Any]) -> bool:
    """Determine if transaction is notable enough for alert."""

    # High-value transactions
    if transaction.get('amount_low', 0) >= NOTABLE_AMOUNT:
        return True

    # Crypto transactions
    asset_name = transaction.get('asset_name', '').lower()
    if any(keyword in asset_name for keyword in CRYPTO_KEYWORDS):
        return True

    # Committee relevance (if provided)
    if transaction.get('committee_relevance', 0) > 0.7:
        return True

    return False

def generate_alert_text(transaction: Dict[str, Any]) -> str:
    """Generate QuiverQuant-style alert text."""

    member_name = transaction.get('member_name', 'Unknown Member')
    party = transaction.get('party', 'Unknown')
    state = transaction.get('state', 'Unknown')
    trans_type = transaction.get('transaction_type', 'transaction')
    asset_name = transaction.get('asset_name', 'Unknown Asset')
    ticker = transaction.get('ticker')
    amount_low = transaction.get('amount_low', 0)
    amount_high = transaction.get('amount_high')
    committee = transaction.get('committee_name')

    # Format amount
    if amount_high:
        amount_str = f"${amount_low:,}-${amount_high:,}"
    else:
        amount_str = f"up to ${amount_low:,}"

    # Base alert
    alert = f"BREAKING: Representative {member_name} ({party}-{state}) has filed a {trans_type.lower()} of {amount_str} in {asset_name}"

    # Add ticker
    if ticker:
        alert += f", ${ticker}"

    # Add committee context
    if committee:
        alert += f". {member_name} sits on the {committee}"

    alert += "."

    return alert

def publish_alert(alert_text: str, transaction: Dict[str, Any]):
    """Publish alert to SNS topic."""

    message = {
        'alert_text': alert_text,
        'transaction': transaction,
        'timestamp': datetime.utcnow().isoformat()
    }

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=json.dumps(message),
        Subject='New Notable Congressional Transaction',
        MessageAttributes={
            'alert_type': {'DataType': 'String', 'StringValue': 'notable_transaction'},
            'member_id': {'DataType': 'String', 'StringValue': transaction.get('bioguide_id', 'unknown')}
        }
    )

def store_alert(alert_id: str, alert_text: str, transaction: Dict[str, Any]):
    """Store alert in DynamoDB for tracking."""

    alerts_table.put_item(
        Item={
            'alert_id': alert_id,
            'alert_text': alert_text,
            'alert_type': 'notable_transaction',
            'bioguide_id': transaction.get('bioguide_id'),
            'transaction_date': transaction.get('transaction_date'),
            'asset_name': transaction.get('asset_name'),
            'ticker': transaction.get('ticker'),
            'amount_low': transaction.get('amount_low'),
            'created_at': datetime.utcnow().isoformat(),
            'ttl': int(datetime.utcnow().timestamp()) + (90 * 24 * 60 * 60)  # 90 days
        }
    )

def lambda_handler(event, context):
    """
    Event format:
    {
        "transactions": [
            {
                "bioguide_id": "D000032",
                "member_name": "Byron Donalds",
                "party": "R",
                "state": "FL",
                "transaction_date": "2025-01-05",
                "asset_name": "Bitcoin",
                "ticker": "BTC",
                "transaction_type": "Purchase",
                "amount_low": 100000,
                "amount_high": 250000,
                "committee_name": "House Subcommittee on Digital Assets"
            }
        ]
    }
    """

    transactions = event.get('transactions', [])
    alerts_generated = 0

    for transaction in transactions:
        if is_notable(transaction):
            # Generate alert
            alert_text = generate_alert_text(transaction)

            # Create unique alert ID
            alert_id = f"{transaction.get('bioguide_id')}_{transaction.get('transaction_date')}_{transaction.get('ticker', 'NOTICKER')}"

            # Check if alert already exists
            try:
                existing = alerts_table.get_item(Key={'alert_id': alert_id})
                if 'Item' in existing:
                    print(f"Alert {alert_id} already exists, skipping")
                    continue
            except Exception as e:
                print(f"Error checking existing alert: {e}")

            # Publish and store
            try:
                publish_alert(alert_text, transaction)
                store_alert(alert_id, alert_text, transaction)
                alerts_generated += 1
                print(f"✓ Alert generated: {alert_text}")
            except Exception as e:
                print(f"Error generating alert: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'alerts_generated': alerts_generated,
            'transactions_processed': len(transactions)
        })
    }
```

Create `backend/functions/alerts/notable_transaction_alert/requirements.txt`:
```
boto3>=1.28.0
```

**Validation**:
```bash
# Test locally with sample event
python3 -c "
from backend.functions.alerts.notable_transaction_alert.handler import lambda_handler
event = {
    'transactions': [{
        'bioguide_id': 'D000032',
        'member_name': 'Byron Donalds',
        'party': 'R',
        'state': 'FL',
        'transaction_date': '2025-01-05',
        'asset_name': 'Bitcoin',
        'ticker': 'BTC',
        'transaction_type': 'Purchase',
        'amount_low': 100000,
        'amount_high': 250000,
        'committee_name': 'House Subcommittee on Digital Assets'
    }]
}
result = lambda_handler(event, None)
print(result)
"
```

**DOD**:
- [ ] Lambda function created
- [ ] Identifies notable transactions
- [ ] Generates QuiverQuant-style alerts
- [ ] Publishes to SNS topic
- [ ] Stores alerts in DynamoDB
- [ ] Prevents duplicate alerts

---

### Task 12: Create Alert Infrastructure (Terraform)
**Time**: 30 minutes

Create `infra/terraform/alerts.tf`:

```hcl
# SNS Topic for Alerts
resource "aws_sns_topic" "transaction_alerts" {
  name         = "${var.project_name}-transaction-alerts"
  display_name = "Congressional Transaction Alerts"

  tags = {
    Name        = "${var.project_name}-transaction-alerts"
    Environment = var.environment
  }
}

# DynamoDB Table for Alert Storage
resource "aws_dynamodb_table" "alerts" {
  name         = "${var.project_name}-alerts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "alert_id"

  attribute {
    name = "alert_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "alert_type"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  global_secondary_index {
    name            = "alert-type-index"
    hash_key        = "alert_type"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  tags = {
    Name        = "${var.project_name}-alerts"
    Environment = var.environment
  }
}

# DynamoDB Table for Alert Subscriptions
resource "aws_dynamodb_table" "alert_subscriptions" {
  name         = "${var.project_name}-alert-subscriptions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "subscription_id"

  attribute {
    name = "subscription_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "user-subscriptions-index"
    hash_key        = "user_id"
    projection_type = "ALL"
  }

  tags = {
    Name        = "${var.project_name}-alert-subscriptions"
    Environment = var.environment
  }
}

# Lambda: Notable Transaction Alert
resource "aws_lambda_function" "notable_transaction_alert" {
  filename         = "${path.module}/../../backend/functions/alerts/notable_transaction_alert/function.zip"
  function_name    = "${var.project_name}-notable-transaction-alert"
  role            = aws_iam_role.notable_alert_lambda_role.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  environment {
    variables = {
      ALERT_SNS_TOPIC_ARN = aws_sns_topic.transaction_alerts.arn
      ALERTS_TABLE_NAME   = aws_dynamodb_table.alerts.name
      LOG_LEVEL           = "INFO"
    }
  }

  tags = {
    Name        = "${var.project_name}-notable-transaction-alert"
    Environment = var.environment
  }
}

# IAM Role for Alert Lambda
resource "aws_iam_role" "notable_alert_lambda_role" {
  name = "${var.project_name}-notable-alert-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "notable_alert_lambda_basic" {
  role       = aws_iam_role.notable_alert_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "notable_alert_lambda_policy" {
  name = "${var.project_name}-notable-alert-lambda-policy"
  role = aws_iam_role.notable_alert_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.transaction_alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.alerts.arn,
          "${aws_dynamodb_table.alerts.arn}/index/*"
        ]
      }
    ]
  })
}

# EventBridge Rule: Trigger on Gold Layer Updates
resource "aws_cloudwatch_event_rule" "gold_transactions_updated" {
  name        = "${var.project_name}-gold-transactions-updated"
  description = "Trigger when new transactions added to Gold layer"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [var.s3_bucket_name]
      }
      object = {
        key = [{
          prefix = "data/gold/facts/fact_transactions/"
        }]
      }
    }
  })
}

# Note: Actual trigger will use Step Functions completion event
# This is a placeholder for S3-based triggering

# Outputs
output "alert_sns_topic_arn" {
  value       = aws_sns_topic.transaction_alerts.arn
  description = "ARN of the transaction alerts SNS topic"
}

output "alerts_table_name" {
  value       = aws_dynamodb_table.alerts.name
  description = "Name of the alerts DynamoDB table"
}
```

**Validation**:
```bash
cd infra/terraform
terraform init
terraform validate
terraform plan | grep "aws_sns_topic.transaction_alerts\|aws_dynamodb_table.alerts\|aws_lambda_function.notable_transaction_alert"
```

**DOD**:
- [ ] `alerts.tf` created
- [ ] SNS topic defined
- [ ] 2 DynamoDB tables defined (alerts, subscriptions)
- [ ] Lambda function defined
- [ ] IAM roles and policies defined
- [ ] EventBridge rule placeholder created
- [ ] Terraform validates successfully

---

### Task 13: Create API Endpoints for Alerts
**Time**: 40 minutes

Create `backend/functions/api/get_notable_transactions/handler.py`:

```python
"""
API Endpoint: GET /v1/analytics/notable-transactions

Returns recent notable transactions with QuiverQuant-style alerts.
"""

import json
import boto3
import os
from datetime import datetime, timedelta

s3 = boto3.client('s3')

BUCKET = os.environ.get('S3_BUCKET_NAME', 'politics-data-platform')

def lambda_handler(event, context):
    """
    Query parameters:
    - days: Number of days to look back (default: 7)
    - limit: Max results (default: 50)
    - min_amount: Minimum transaction amount (default: 50000)
    - crypto_only: Filter to crypto only (default: false)
    """

    params = event.get('queryStringParameters', {}) or {}

    days = int(params.get('days', 7))
    limit = int(params.get('limit', 50))
    min_amount = int(params.get('min_amount', 50000))
    crypto_only = params.get('crypto_only', 'false').lower() == 'true'

    try:
        # Read notable transactions aggregate from S3
        s3_key = "data/gold/aggregates/notable_transactions/notable_transactions.parquet"

        obj = s3.get_object(Bucket=BUCKET, Key=s3_key)

        import pandas as pd
        import io

        df = pd.read_parquet(io.BytesIO(obj['Body'].read()))

        # Filter by date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        df = df[df['transaction_date'] >= cutoff_date]

        # Filter by amount
        df = df[df['amount_low'] >= min_amount]

        # Filter crypto if requested
        if crypto_only:
            df = df[df['is_crypto'] == True]

        # Sort and limit
        df = df.sort_values(['is_recent', 'committee_relevance', 'amount_low'], ascending=[False, False, False])
        df = df.head(limit)

        # Convert to JSON-friendly format
        records = df.to_dict('records')

        # Format dates
        for record in records:
            for field in ['transaction_date', 'filing_date', 'computed_at']:
                if field in record and record[field]:
                    record[field] = str(record[field])

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'data': records,
                'count': len(records),
                'filters': {
                    'days': days,
                    'min_amount': min_amount,
                    'crypto_only': crypto_only
                }
            })
        }

    except s3.exceptions.NoSuchKey:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Notable transactions data not yet available'})
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
```

Create `backend/functions/api/get_crypto_activity/handler.py`:

```python
"""
API Endpoint: GET /v1/analytics/crypto-activity

Returns crypto-specific trading activity and trends.
"""

import json
import boto3
import os

s3 = boto3.client('s3')

BUCKET = os.environ.get('S3_BUCKET_NAME', 'politics-data-platform')

def lambda_handler(event, context):
    """
    Query parameters:
    - category: bitcoin, ethereum, all_crypto (default: all_crypto)
    - months: Number of months to return (default: 12)
    """

    params = event.get('queryStringParameters', {}) or {}

    category = params.get('category', 'all_crypto')
    months = int(params.get('months', 12))

    try:
        # Read crypto aggregates from S3
        s3_key = "data/gold/aggregates/crypto_activity/monthly_aggregates.parquet"

        obj = s3.get_object(Bucket=BUCKET, Key=s3_key)

        import pandas as pd
        import io

        df = pd.read_parquet(io.BytesIO(obj['Body'].read()))

        # Filter by category
        if category != 'all':
            df = df[df['category'] == category]

        # Sort and limit
        df = df.sort_values(['year', 'month'], ascending=[False, False])
        df = df.head(months)

        # Convert to JSON
        records = df.to_dict('records')

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'data': records,
                'count': len(records),
                'category': category
            })
        }

    except s3.exceptions.NoSuchKey:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Crypto activity data not yet available'})
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
```

Create requirements.txt for both:
```bash
echo "boto3>=1.28.0
pandas>=2.0.0
pyarrow>=12.0.0" > backend/functions/api/get_notable_transactions/requirements.txt

cp backend/functions/api/get_notable_transactions/requirements.txt backend/functions/api/get_crypto_activity/requirements.txt
```

**Validation**:
```bash
# Test import locally
python3 -c "from backend.functions.api.get_notable_transactions.handler import lambda_handler; print('✓ Notable transactions handler OK')"
python3 -c "from backend.functions.api.get_crypto_activity.handler import lambda_handler; print('✓ Crypto activity handler OK')"
```

**DOD**:
- [ ] `/v1/analytics/notable-transactions` endpoint created
- [ ] `/v1/analytics/crypto-activity` endpoint created
- [ ] Query parameter filtering implemented
- [ ] CORS headers configured
- [ ] Error handling implemented
- [ ] Handlers tested locally

---

### Task 14: Add API Endpoints to Terraform
**Time**: 20 minutes

Create `infra/terraform/api_analytics.tf`:

```hcl
# Lambda: Get Notable Transactions
resource "aws_lambda_function" "get_notable_transactions" {
  filename      = "${path.module}/../../backend/functions/api/get_notable_transactions/function.zip"
  function_name = "${var.project_name}-get-notable-transactions"
  role          = aws_iam_role.api_lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
    }
  }

  tags = {
    Name        = "${var.project_name}-get-notable-transactions"
    Environment = var.environment
  }
}

# Lambda: Get Crypto Activity
resource "aws_lambda_function" "get_crypto_activity" {
  filename      = "${path.module}/../../backend/functions/api/get_crypto_activity/function.zip"
  function_name = "${var.project_name}-get-crypto-activity"
  role          = aws_iam_role.api_lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
    }
  }

  tags = {
    Name        = "${var.project_name}-get-crypto-activity"
    Environment = var.environment
  }
}

# API Gateway Integration: Notable Transactions
resource "aws_apigatewayv2_integration" "notable_transactions" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.get_notable_transactions.invoke_arn
}

resource "aws_apigatewayv2_route" "notable_transactions" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /v1/analytics/notable-transactions"
  target    = "integrations/${aws_apigatewayv2_integration.notable_transactions.id}"
}

resource "aws_lambda_permission" "notable_transactions_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_notable_transactions.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# API Gateway Integration: Crypto Activity
resource "aws_apigatewayv2_integration" "crypto_activity" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.get_crypto_activity.invoke_arn
}

resource "aws_apigatewayv2_route" "crypto_activity" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /v1/analytics/crypto-activity"
  target    = "integrations/${aws_apigatewayv2_integration.crypto_activity.id}"
}

resource "aws_lambda_permission" "crypto_activity_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_crypto_activity.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Outputs
output "api_endpoint_notable_transactions" {
  value = "${aws_apigatewayv2_api.main.api_endpoint}/v1/analytics/notable-transactions"
}

output "api_endpoint_crypto_activity" {
  value = "${aws_apigatewayv2_api.main.api_endpoint}/v1/analytics/crypto-activity"
}
```

**Validation**:
```bash
cd infra/terraform
terraform validate
terraform plan | grep "aws_lambda_function.get_notable_transactions\|aws_lambda_function.get_crypto_activity"
```

**DOD**:
- [ ] `api_analytics.tf` created
- [ ] 2 Lambda functions defined
- [ ] API Gateway integrations created
- [ ] Routes configured
- [ ] Lambda permissions granted
- [ ] Outputs defined
- [ ] Terraform validates successfully

---

### Task 15: Update Makefile with New Aggregate Commands
**Time**: 10 minutes

Add to `Makefile`:

```makefile
# High-Value Analytics Aggregates
.PHONY: aggregate-notable-transactions aggregate-crypto aggregate-bill-correlations aggregate-all-analytics

aggregate-notable-transactions:  ## Compute notable transactions aggregate
	@echo "Computing notable transactions..."
	python3 backend/scripts/compute_agg_notable_transactions.py

aggregate-crypto:  ## Compute crypto activity aggregate
	@echo "Computing crypto activity..."
	python3 backend/scripts/compute_agg_crypto_activity.py

aggregate-bill-correlations:  ## Compute bill-trade correlations
	@echo "Computing bill-trade correlations..."
	python3 backend/scripts/compute_agg_bill_trade_correlation.py

aggregate-all-analytics:  ## Run all analytics aggregates
	@echo "Running all analytics aggregates..."
	@make aggregate-notable-transactions
	@make aggregate-crypto
	@make aggregate-bill-correlations
	@echo "✓ All analytics aggregates complete"

# Package and deploy analytics API
package-analytics-api:  ## Package analytics API Lambda functions
	@echo "Packaging analytics API functions..."
	cd backend/functions/api/get_notable_transactions && \
		pip install -r requirements.txt -t . && \
		zip -r function.zip . -x "*.pyc" -x "__pycache__/*"
	cd backend/functions/api/get_crypto_activity && \
		pip install -r requirements.txt -t . && \
		zip -r function.zip . -x "*.pyc" -x "__pycache__/*"

deploy-analytics:  ## Deploy analytics infrastructure
	@echo "Deploying analytics infrastructure..."
	@make package-analytics-api
	cd infra/terraform && terraform apply -target=aws_lambda_function.get_notable_transactions -target=aws_lambda_function.get_crypto_activity -auto-approve
```

**Validation**:
```bash
make help | grep "aggregate-"
# Should show all new aggregate commands
```

**DOD**:
- [ ] Makefile updated with 4 new aggregate commands
- [ ] Package command for analytics API added
- [ ] Deploy command for analytics infrastructure added
- [ ] Commands documented with ## comments
- [ ] `make help` shows new commands

---

## COMPLETION CHECKLIST

### Scenario 1: Root Directory Organization
- [ ] Task 1: Documentation organized into `docs/` subdirectories
- [ ] Task 2: Configuration files in `config/`
- [ ] Task 3: Utility scripts in `backend/scripts/utils/`
- [ ] Task 4: Shell scripts organized by purpose
- [ ] Task 5: No orphaned Terraform files at root
- [ ] Task 6: Root has ≤12 essential files
- [ ] Task 7: Repository documentation updated

### Scenario 2: High-Value QuiverQuant Features
- [ ] Task 8: Notable transactions aggregate created
- [ ] Task 9: Crypto activity aggregate created
- [ ] Task 10: Bill-trade correlation aggregate created
- [ ] Task 11: Real-time alert Lambda created
- [ ] Task 12: Alert infrastructure (Terraform) created
- [ ] Task 13: API endpoints for alerts created
- [ ] Task 14: API endpoints added to Terraform
- [ ] Task 15: Makefile updated with new commands

### Final Validation
```bash
# Verify root organization
ls -1 | wc -l  # Should be ≤12 files

# Verify analytics scripts exist
ls backend/scripts/compute_agg_*.py

# Verify API handlers exist
ls backend/functions/api/get_*/handler.py

# Verify Terraform is valid
cd infra/terraform && terraform validate

# Verify Makefile commands
make help | grep -E "aggregate-|deploy-analytics"
```

---

## NEXT STEPS (After This Plan)

Once this plan is complete:

1. **Deploy Infrastructure**:
   ```bash
   cd infra/terraform
   terraform init
   terraform apply
   ```

2. **Run Initial Aggregates**:
   ```bash
   make aggregate-all-analytics
   ```

3. **Test API Endpoints**:
   ```bash
   curl "$(terraform output -raw api_endpoint_notable_transactions)?days=7&limit=10"
   ```

4. **Continue with Master Execution Plan**:
   - Phase 0: Terraform cleanup
   - Phase 1: Path reorganization
   - Phase 2: Reference data bootstrap
   - Phase 3: Initial data load

See `docs/plans/MASTER_EXECUTION_PLAN.md` for full roadmap.
