# Politics Data Platform - Master Execution Plan
## Complete Modernization Roadmap with Definition of Done (DOD)

**Project Goal**: Transform Congress disclosures pipeline into a production-ready, vendor-neutral politics data SaaS platform

**Budget Constraint**: $30 initial load, <$5/month ongoing
**Timeline**: 16 weeks (4 phases)
**Current Status**: Foundation phase started

---

## 📋 Table of Contents
1. [Phase 0: Infrastructure Cleanup (Week 1)](#phase-0-infrastructure-cleanup)
2. [Phase 1: Foundation & Path Reorganization (Weeks 2-4)](#phase-1-foundation--path-reorganization)
3. [Phase 2: Reference Data Bootstrap (Weeks 5-6)](#phase-2-reference-data-bootstrap)
4. [Phase 3: Optimized Initial Load (Weeks 7-9)](#phase-3-optimized-initial-load)
5. [Phase 4: API Modernization (Weeks 10-12)](#phase-4-api-modernization)
6. [Phase 5: DBT Migration Completion (Weeks 13-16)](#phase-5-dbt-migration-completion)
7. [Post-Launch Roadmap](#post-launch-roadmap)

---

## Phase 0: Infrastructure Cleanup (Week 1)

**Objective**: Clean up Terraform infrastructure, remove redundant resources, establish clear organization

### Task 0.1: Delete Redundant Terraform Files
**Owner**: DevOps/Claude
**Priority**: P0
**Risk**: Low (no infrastructure changes)

**Actions**:
```bash
cd infra/terraform
# Delete 8 redundant files
rm -f api_gateway_assets.tf
rm -f api_gateway_members.tf
rm -f api_gateway_transactions.tf
rm -f api_costs_route.tf
rm -f api_storage_route.tf
rm -f lambda_stub.tf
rm -f lambdas_analytics.tf
rm -f lambdas_data_quality.tf
```

**Definition of Done**:
- [ ] 8 files deleted from `infra/terraform/`
- [ ] `terraform validate` passes
- [ ] `terraform plan` shows 0 changes (no infrastructure impact)
- [ ] Git commit: "refactor: delete redundant Terraform files"
- [ ] File count reduced from 44 → 36 files

**Validation**:
```bash
cd infra/terraform
terraform validate
terraform plan | grep "No changes"
```

---

### Task 0.2: Remove Legacy Resources
**Owner**: DevOps/Claude
**Priority**: P0
**Risk**: Low (unused resources)

**Actions**:
1. Edit `dynamodb.tf` - Remove `aws_dynamodb_table.house_fd_documents` (legacy table)
2. Edit `lambda_congress.tf` - Remove `aws_lambda_layer_version.congress_pandas_layer` (duplicate layer)

**Definition of Done**:
- [ ] `aws_dynamodb_table.house_fd_documents` removed from dynamodb.tf
- [ ] `aws_lambda_layer_version.congress_pandas_layer` removed from lambda_congress.tf
- [ ] `terraform plan` shows 2 resource deletions
- [ ] **VERIFY**: No production systems depend on these resources (check application logs, Step Functions)
- [ ] `terraform apply` executed successfully
- [ ] Git commit: "refactor: remove legacy DynamoDB table and duplicate Lambda layer"

**Validation**:
```bash
# Check if any Lambdas reference the legacy table
grep -r "house_fd_documents" ingestion/lambdas/ scripts/
# Should return no results

# Check if any Lambdas use congress_pandas_layer
grep -r "congress_pandas_layer" infra/terraform/
# Should return no results after removal
```

---

### Task 0.3: Deploy Infrastructure Changes
**Owner**: DevOps/Claude
**Priority**: P0
**Risk**: Low

**Actions**:
```bash
cd infra/terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

**Definition of Done**:
- [ ] New DynamoDB tables created (api_cache, api_keys, api_usage, api_usage_aggregates)
- [ ] AWS Glue Data Catalog database created (politics_data_platform)
- [ ] Glue Crawlers created (gold_layer_crawler, silver_layer_crawler)
- [ ] All outputs available in `terraform output`
- [ ] CloudWatch logs show no errors
- [ ] Git commit: "feat: add API layer DynamoDB tables and Glue Data Catalog"

**Validation**:
```bash
# Verify DynamoDB tables exist
aws dynamodb list-tables | grep "politics-api"
# Should show: congress-disclosures-api-cache, congress-disclosures-api-keys, etc.

# Verify Glue Catalog
aws glue get-database --name politics_data_platform
# Should return database details

# Check Terraform outputs
terraform output glue_database_name
terraform output api_cache_table_name
```

**Cost Impact**: +$1.50/month (Glue Crawler)

---

## Phase 1: Foundation & Path Reorganization (Weeks 2-4)

**Objective**: Establish centralized path management, standardize S3 structure, set up DBT Core

### Task 1.1: Update Lambda Functions to Use Centralized Paths
**Owner**: Development/Claude
**Priority**: P0
**Risk**: Medium (requires testing)

**Scope**: Update 148 files with hard-coded S3 paths

**Actions**:
1. Identify all files with hard-coded S3 paths:
   ```bash
   grep -r "bronze/house/financial" ingestion/
   grep -r "silver/house/financial" ingestion/
   grep -r "gold/house/financial" ingestion/
   ```

2. Update each file to use `S3Paths` from `s3_path_registry.py`:
   ```python
   # OLD
   s3_key = f"bronze/house/financial/year={year}/pdfs/{doc_id}.pdf"

   # NEW
   from ingestion.lib.s3_path_registry import S3Paths
   s3_key = S3Paths.bronze_house_fd_pdf(year, filing_type, doc_id)
   ```

3. Priority order:
   - **High Priority** (Week 2): Core ingestion Lambdas (ingest_zip, extract_document, index_to_silver)
   - **Medium Priority** (Week 3): Gold layer scripts, API Lambdas
   - **Low Priority** (Week 4): Utility scripts, tests

**Definition of Done**:
- [ ] All 148 files updated to use `S3Paths` module
- [ ] No hard-coded path strings remain (verified with grep)
- [ ] Unit tests pass for updated Lambdas
- [ ] Integration test: Ingest 1 year of data successfully
- [ ] Code review completed
- [ ] Git commit: "refactor: centralize S3 path management across all Lambdas"

**Validation**:
```bash
# Verify no hard-coded paths remain
grep -r '"bronze/' ingestion/lambdas/ ingestion/lib/ scripts/
grep -r '"silver/' ingestion/lambdas/ ingestion/lib/ scripts/
grep -r '"gold/' ingestion/lambdas/ ingestion/lib/ scripts/
# Should return 0 results

# Test imports work
python3 -c "from ingestion.lib.s3_path_registry import S3Paths; print(S3Paths.bronze_house_fd_pdf(2025, 'P', '12345'))"
# Should return: data/bronze/house_fd/year=2025/filing_type=P/pdfs/12345.pdf
```

---

### Task 1.2: Set Up DBT Core with DuckDB
**Owner**: Data Engineering/Claude
**Priority**: P0
**Risk**: Low

**Actions**:
1. Install DBT Core:
   ```bash
   pip install dbt-core dbt-duckdb
   dbt --version
   ```

2. Initialize DBT project:
   ```bash
   mkdir -p dbt
   cd dbt
   dbt init politics_data_platform
   ```

3. Configure `dbt_project.yml`:
   ```yaml
   name: 'politics_data_platform'
   version: '1.0.0'
   config-version: 2

   profile: 'politics_duckdb'

   model-paths: ["models"]
   analysis-paths: ["analyses"]
   test-paths: ["tests"]
   seed-paths: ["seeds"]
   macro-paths: ["macros"]

   models:
     politics_data_platform:
       bronze:
         +materialized: view
         +schema: bronze
       silver:
         +materialized: table
         +schema: silver
       gold:
         dimensions:
           +materialized: table
           +schema: gold
         facts:
           +materialized: incremental
           +schema: gold
           +partition_by: ['year', 'month']
         aggregates:
           +materialized: table
           +schema: gold
   ```

4. Configure `profiles.yml`:
   ```yaml
   politics_duckdb:
     target: prod
     outputs:
       prod:
         type: duckdb
         path: 's3://politics-data-platform/metadata/duckdb/prod.duckdb'
         schema: main
         threads: 4
         extensions:
           - httpfs
           - parquet
           - json
           - iceberg
         settings:
           s3_region: us-east-1
           s3_use_ssl: true
           s3_access_key_id: "{{ env_var('AWS_ACCESS_KEY_ID') }}"
           s3_secret_access_key: "{{ env_var('AWS_SECRET_ACCESS_KEY') }}"
   ```

**Definition of Done**:
- [ ] DBT Core installed (version >=1.7.0)
- [ ] DBT project initialized in `dbt/` directory
- [ ] `dbt_project.yml` configured with proper model paths
- [ ] `profiles.yml` configured with DuckDB + S3
- [ ] `dbt debug` passes successfully
- [ ] Git commit: "feat: initialize DBT Core project with DuckDB adapter"

**Validation**:
```bash
cd dbt
dbt debug
# Should show: "All checks passed!"

dbt compile
# Should compile successfully (no models yet, but config is valid)
```

---

### Task 1.3: Port First 3 DBT Models (POC)
**Owner**: Data Engineering/Claude
**Priority**: P0
**Risk**: Medium

**Models to Port**:
1. **dim_members.sql** (replaces `build_dim_members_simple.py`)
2. **fact_ptr_transactions.sql** (replaces `build_fact_ptr_transactions.py`)
3. **agg_trending_stocks.sql** (replaces `compute_agg_trending_stocks.py`)

**Actions** (Example for dim_members):

```sql
-- dbt/models/gold/dimensions/dim_members.sql
{{
  config(
    materialized='table',
    unique_key='member_key',
    schema='gold'
  )
}}

WITH filings AS (
  SELECT DISTINCT
    first_name,
    last_name,
    state_district,
    SUBSTRING(state_district, 1, 2) AS state,
    CAST(SUBSTRING(state_district, 4) AS INTEGER) AS district
  FROM {{ source('silver', 'filings') }}
),

enriched AS (
  SELECT
    f.*,
    c.bioguide_id,
    c.party,
    c.chamber
  FROM filings f
  LEFT JOIN {{ source('congress', 'members') }} c
    ON LOWER(f.first_name || ' ' || f.last_name) = LOWER(c.full_name)
)

SELECT
  {{ dbt_utils.generate_surrogate_key(['bioguide_id', 'state_district']) }} AS member_key,
  bioguide_id,
  first_name,
  last_name,
  first_name || ' ' || last_name AS full_name,
  party,
  state,
  district,
  state_district,
  chamber,
  CURRENT_DATE AS valid_from,
  DATE '9999-12-31' AS valid_to,
  TRUE AS is_current,
  CURRENT_TIMESTAMP AS created_at
FROM enriched
```

**Definition of Done**:
- [ ] 3 SQL models created in `dbt/models/gold/`
- [ ] `dbt compile` succeeds for all 3 models
- [ ] `dbt run --select dim_members` executes successfully
- [ ] Output Parquet files created in S3 Gold layer
- [ ] Row counts match Python script outputs (±5%)
- [ ] `dbt test` passes (uniqueness, not_null tests)
- [ ] Documentation added to `schema.yml`
- [ ] Git commit: "feat: port first 3 models to DBT (dim_members, fact_ptr_transactions, agg_trending_stocks)"

**Validation**:
```bash
cd dbt

# Test compilation
dbt compile --select dim_members

# Run the model
dbt run --select dim_members

# Verify output in S3
aws s3 ls s3://politics-data-platform/data/gold/dimensions/dim_members/

# Run tests
dbt test --select dim_members

# Compare row counts
dbt run-operation compare_row_counts --args '{model: dim_members, python_count: 540}'
```

---

## Phase 2: Reference Data Bootstrap (Weeks 5-6)

**Objective**: Build master dimensions BEFORE initial load to enable proper data linkage

### Task 2.1: Build Member Registry (Cross-Source Bioguide Crosswalk)
**Owner**: Data Engineering/Claude
**Priority**: P0
**Risk**: Low

**Actions**:
Create `scripts/build_reference_members.py`:

```python
"""
Build master member registry from multiple sources.

Sources:
1. Congress.gov API (bioguide_id, party, state, chamber)
2. House FD XML indices (name variations)
3. Lobbying filings (name mentions)

Output: s3://politics-data-platform/data/reference/members/dim_members_master.parquet
"""

def fetch_congress_members():
    """Fetch all members from Congress.gov API."""
    # Fetch current + historical members
    pass

def parse_house_fd_indices():
    """Extract unique member names from House FD XML."""
    # Parse all XML indices (2010-2025)
    pass

def fuzzy_match_members():
    """Fuzzy matching to create bioguide crosswalk."""
    # Use Levenshtein distance, soundex
    pass

def build_master_registry():
    """Consolidate into master registry."""
    # Create dim_members_master.parquet
    pass
```

**Definition of Done**:
- [ ] Script `build_reference_members.py` created
- [ ] All members from Congress.gov API fetched (~3,000 historical members)
- [ ] All member names from House FD indices extracted
- [ ] Fuzzy matching completed (>95% match rate)
- [ ] Output file created: `data/reference/members/dim_members_master.parquet`
- [ ] Schema includes: bioguide_id, full_name, name_variations[], party_history[], state_history[]
- [ ] Data quality checks pass (no duplicates, all bioguide_ids valid)
- [ ] Git commit: "feat: build reference member registry with cross-source matching"

**Validation**:
```bash
# Run the script
python3 scripts/build_reference_members.py

# Verify output
aws s3 ls s3://politics-data-platform/data/reference/members/

# Check row count
python3 -c "
import pandas as pd
df = pd.read_parquet('s3://politics-data-platform/data/reference/members/dim_members_master.parquet')
print(f'Total members: {len(df)}')
print(f'With bioguide_id: {df[\"bioguide_id\"].notna().sum()}')
print(f'Match rate: {df[\"bioguide_id\"].notna().sum() / len(df) * 100:.2f}%')
"
# Expected: ~3,000 members, >95% match rate
```

**Cost Impact**: $0 (Congress.gov API is free)

---

### Task 2.2: Build Asset/Ticker Crosswalk
**Owner**: Data Engineering/Claude
**Priority**: P1
**Risk**: Low

**Actions**:
Create `scripts/build_reference_assets.py`:

```python
"""
Build asset/ticker crosswalk with sector classifications.

Sources:
1. SEC ticker database (public, free)
2. Manual mappings for House FD typos
3. Yahoo Finance API for sector data

Output: s3://politics-data-platform/data/reference/asset_crosswalk/assets.parquet
"""

def fetch_sec_tickers():
    """Download SEC ticker database."""
    # https://www.sec.gov/files/company_tickers.json
    pass

def extract_house_fd_tickers():
    """Extract all tickers from House FD filings."""
    # Parse silver/objects/filing_type=P
    pass

def build_manual_mappings():
    """Manual corrections for common typos."""
    # "APPL" → "AAPL", etc.
    pass

def fetch_sector_classifications():
    """Get sector/industry from Yahoo Finance."""
    # Use yfinance library (free)
    pass
```

**Definition of Done**:
- [ ] Script `build_reference_assets.py` created
- [ ] SEC ticker database downloaded (~13,000 tickers)
- [ ] All House FD tickers extracted
- [ ] Manual mappings for top 100 typos created
- [ ] Sector classifications fetched for all tickers
- [ ] Output file created: `data/reference/asset_crosswalk/assets.parquet`
- [ ] Schema includes: ticker, company_name, sector, industry, typo_mappings[]
- [ ] Git commit: "feat: build asset crosswalk with sector classifications"

**Validation**:
```bash
python3 scripts/build_reference_assets.py

aws s3 ls s3://politics-data-platform/data/reference/asset_crosswalk/

python3 -c "
import pandas as pd
df = pd.read_parquet('s3://politics-data-platform/data/reference/asset_crosswalk/assets.parquet')
print(f'Total tickers: {len(df)}')
print(f'With sector: {df[\"sector\"].notna().sum()}')
"
```

---

### Task 2.3: Build Bill ID Crosswalk
**Owner**: Data Engineering/Claude
**Priority**: P1
**Risk**: Low

**Actions**:
Create `scripts/build_reference_bills.py`:

```python
"""
Build bill ID crosswalk to normalize different formats.

Formats:
- House Clerk: "H.R. 1234 (118th)"
- Congress.gov: "hr1234-118"
- Lobbying: "HR1234", "H.R.1234"

Output: s3://politics-data-platform/data/reference/bill_crosswalk/bills.parquet
"""

def normalize_bill_id(bill_str):
    """Normalize bill ID to standard format."""
    # Convert all to: hr1234-118
    pass
```

**Definition of Done**:
- [ ] Script `build_reference_bills.py` created
- [ ] All bill formats parsed and normalized
- [ ] Output file created: `data/reference/bill_crosswalk/bills.parquet`
- [ ] Schema includes: bill_id_normalized, bill_id_variations[], congress, bill_type, number
- [ ] Git commit: "feat: build bill ID crosswalk for format normalization"

**Validation**:
```bash
python3 scripts/build_reference_bills.py

# Test normalization
python3 -c "
from scripts.build_reference_bills import normalize_bill_id
assert normalize_bill_id('H.R. 1234 (118th)') == 'hr1234-118'
assert normalize_bill_id('HR1234') == 'hr1234-118'
print('✓ All normalization tests passed')
"
```

**Phase 2 Completion DOD**:
- [ ] All 3 reference datasets built
- [ ] All outputs in S3 `data/reference/` directory
- [ ] Data quality checks pass for all datasets
- [ ] Documentation updated with reference data schemas
- [ ] Ready for initial data load (Phase 3)

---

## Phase 3: Optimized Initial Load (Weeks 7-9)

**Objective**: Load 2024-2025 data (stay under $30 budget), validate pipeline

### Task 3.1: Configure Step Functions for Initial Load
**Owner**: DevOps/Claude
**Priority**: P0
**Risk**: Low

**Actions**:
1. Update Step Functions execution input template:
```json
{
  "execution_type": "initial_load",
  "years": [2024, 2025],
  "max_concurrency": 5,
  "watermark_check": false
}
```

2. Set MaxConcurrency=5 (reduced from 10 for cost control)

**Definition of Done**:
- [ ] Step Functions configured for initial load mode
- [ ] MaxConcurrency set to 5 across all Map states
- [ ] Watermarking disabled for initial load
- [ ] Execution timeout extended to 24 hours
- [ ] Git commit: "config: configure Step Functions for initial load"

---

### Task 3.2: Execute House FD Initial Load (2024-2025)
**Owner**: DevOps/Claude
**Priority**: P0
**Risk**: Medium

**Actions**:
```bash
# Trigger Step Functions execution
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:464813693153:stateMachine:house_fd_pipeline \
  --name "initial-load-house-fd-2024-2025" \
  --input '{
    "execution_type": "initial_load",
    "years": [2024, 2025],
    "max_concurrency": 5
  }'

# Monitor progress
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>
```

**Expected Metrics**:
- **Volume**: ~30,000 PDFs
- **Bronze**: ~60 GB raw
- **Silver**: ~15 GB (Parquet compressed)
- **Gold**: ~3 GB
- **Duration**: ~8 hours
- **Cost**: ~$3-5

**Definition of Done**:
- [ ] Step Functions execution completed successfully
- [ ] All 2024-2025 PDFs ingested to Bronze
- [ ] All PDFs extracted to Silver (text + objects)
- [ ] Gold dimensions built
- [ ] Gold facts built
- [ ] Gold aggregates computed
- [ ] No errors in CloudWatch logs
- [ ] Data quality checks pass
- [ ] Cost < $5 (verified in AWS Cost Explorer)

**Validation**:
```bash
# Check Bronze ingestion
aws s3 ls s3://politics-data-platform/data/bronze/house_fd/ --recursive | grep "year=2024\|year=2025" | wc -l
# Expected: ~30,000 PDFs

# Check Silver extraction
aws s3 ls s3://politics-data-platform/data/silver/house_fd/objects/ --recursive | grep ".json" | wc -l
# Expected: ~30,000 JSON files

# Check Gold output
aws s3 ls s3://politics-data-platform/data/gold/facts/fact_ptr_transactions/
# Expected: Parquet files with partitions year=2024, year=2025

# Verify data quality
python3 scripts/validate_pipeline_integrity.py --years 2024,2025
# Expected: 100% success rate
```

---

### Task 3.3: Execute Congress.gov Initial Load (118th Congress)
**Owner**: DevOps/Claude
**Priority**: P0
**Risk**: Low

**Actions**:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:464813693153:stateMachine:congress_pipeline \
  --name "initial-load-congress-118" \
  --input '{
    "execution_type": "initial_load",
    "congress": 118
  }'
```

**Expected Metrics**:
- **Volume**: ~15,000 bills, 540 members, 200 committees
- **Bronze**: ~2 GB
- **Silver**: ~500 MB
- **Duration**: ~4 hours
- **Cost**: ~$0.50

**Definition of Done**:
- [ ] All bills from 118th Congress loaded
- [ ] All members loaded
- [ ] All committees loaded
- [ ] Silver tables created
- [ ] Gold dimensions updated
- [ ] Cost < $1

---

### Task 3.4: Execute Lobbying Initial Load (2024)
**Owner**: DevOps/Claude
**Priority**: P1
**Risk**: Low

**Actions**:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:464813693153:stateMachine:lobbying_pipeline \
  --name "initial-load-lobbying-2024" \
  --input '{
    "execution_type": "initial_load",
    "year": 2024,
    "quarters": ["Q1", "Q2", "Q3", "Q4"]
  }'
```

**Expected Metrics**:
- **Volume**: ~100,000 filings (2024)
- **Bronze**: ~5 GB
- **Silver**: ~1 GB
- **Duration**: ~2 hours
- **Cost**: ~$0.50

**Definition of Done**:
- [ ] All 2024 lobbying filings loaded
- [ ] Gold fact table created
- [ ] Cost < $1

---

### Task 3.5: Build Cross-Domain Correlations
**Owner**: Data Engineering/Claude
**Priority**: P1
**Risk**: Low

**Actions**:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:464813693153:stateMachine:cross_dataset_correlation \
  --name "initial-correlations" \
  --input '{}'
```

**Definition of Done**:
- [ ] Bill-trade correlations computed
- [ ] Lobbying-bill correlations computed
- [ ] Member-asset network graph generated
- [ ] Output in `data/gold/aggregates/`

**Phase 3 Completion DOD**:
- [ ] All initial data loaded (2024-2025 House FD, 118th Congress, 2024 Lobbying)
- [ ] Total cost < $10 ✅
- [ ] Total storage: ~80 GB → compressed to ~25 GB ✅
- [ ] All Gold tables populated
- [ ] Data quality validation passed (100% success rate)
- [ ] API can query all datasets successfully
- [ ] Documentation updated with data volumes and schemas

---

## Phase 4: API Modernization (Weeks 10-12)

**Objective**: Add authentication, caching, usage tracking for production API

### Task 4.1: Implement DynamoDB Caching Layer
**Owner**: Backend Engineering/Claude
**Priority**: P0
**Risk**: Medium

**Actions**:
1. Create caching utility: `ingestion/lib/api_cache.py`
```python
import boto3
import json
import time
import hashlib

dynamodb = boto3.resource('dynamodb')
cache_table = dynamodb.Table('congress-disclosures-api-cache')

def cached_query(cache_key: str, ttl_seconds: int, query_fn):
    """Execute query with DynamoDB caching."""
    # Check cache
    response = cache_table.get_item(Key={'cache_key': cache_key})

    if 'Item' in response:
        item = response['Item']
        if int(item['expires_at']) > int(time.time()):
            # Cache hit
            return json.loads(item['data']), True

    # Cache miss - execute query
    result = query_fn()

    # Store in cache
    cache_table.put_item(Item={
        'cache_key': cache_key,
        'data': json.dumps(result),
        'expires_at': int(time.time()) + ttl_seconds
    })

    return result, False
```

2. Update all API Lambda handlers to use caching:
```python
from ingestion.lib.api_cache import cached_query

def lambda_handler(event, context):
    endpoint = event['path']
    cache_key = hashlib.sha256(json.dumps(event['queryStringParameters']).encode()).hexdigest()

    result, cache_hit = cached_query(
        cache_key=f"{endpoint}:{cache_key}",
        ttl_seconds=3600,  # 1 hour
        query_fn=lambda: execute_query(event)
    )

    return {
        'statusCode': 200,
        'body': json.dumps(result),
        'headers': {
            'X-Cache': 'HIT' if cache_hit else 'MISS'
        }
    }
```

**Definition of Done**:
- [ ] `api_cache.py` utility created
- [ ] All 60+ API Lambda handlers updated to use caching
- [ ] Cache TTLs configured: trending_stocks (1h), members (24h), summary (1h)
- [ ] `X-Cache` header added to responses
- [ ] Cache hit rate >80% (verified in CloudWatch)
- [ ] Response times: <50ms (cached), <500ms (uncached)
- [ ] Git commit: "feat: implement DynamoDB caching layer for API"

**Validation**:
```bash
# Test cache hit
curl https://api-url/v1/analytics/trending-stocks
# Response header: X-Cache: MISS

curl https://api-url/v1/analytics/trending-stocks
# Response header: X-Cache: HIT

# Verify cache in DynamoDB
aws dynamodb scan --table-name congress-disclosures-api-cache --select COUNT
# Expected: ItemCount > 0
```

---

### Task 4.2: Implement API Authentication (Lambda Authorizer)
**Owner**: Backend Engineering/Claude
**Priority**: P0
**Risk**: Medium

**Actions**:
1. Create `infra/terraform/api_authorizer.tf`:
```hcl
resource "aws_lambda_function" "api_authorizer" {
  function_name = "${var.project_name}-api-authorizer"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  role          = aws_iam_role.api_authorizer_role.arn

  filename      = "${path.module}/../../api/authorizer/function.zip"
  source_code_hash = filebase64sha256("${path.module}/../../api/authorizer/function.zip")

  environment {
    variables = {
      API_KEYS_TABLE = aws_dynamodb_table.api_keys.name
      JWT_SECRET     = "CHANGE_ME_IN_PRODUCTION"  # Use AWS Secrets Manager
    }
  }
}

resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  authorizer_type  = "REQUEST"
  authorizer_uri   = aws_lambda_function.api_authorizer.invoke_arn
  identity_sources = ["$request.header.x-api-key"]
  name             = "jwt-authorizer"
}
```

2. Create `api/authorizer/handler.py`:
```python
import jwt
import boto3
import hashlib
import os

dynamodb = boto3.resource('dynamodb')
api_keys_table = dynamodb.Table(os.environ['API_KEYS_TABLE'])

def lambda_handler(event, context):
    api_key = event['headers'].get('x-api-key')

    if not api_key:
        return {'isAuthorized': False}

    try:
        # Validate JWT
        payload = jwt.decode(api_key, os.environ['JWT_SECRET'], algorithms=['HS256'])

        # Check if key is active
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        response = api_keys_table.get_item(Key={'api_key_hash': key_hash})

        if 'Item' not in response or response['Item'].get('suspended'):
            return {'isAuthorized': False}

        return {
            'isAuthorized': True,
            'context': {
                'userId': response['Item']['user_id'],
                'tier': response['Item']['tier']
            }
        }
    except Exception as e:
        print(f"Authorization error: {e}")
        return {'isAuthorized': False}
```

**Definition of Done**:
- [ ] Lambda authorizer created
- [ ] API Gateway configured to use authorizer on all routes
- [ ] JWT secret stored in AWS Secrets Manager
- [ ] Test API keys generated (free, pro, enterprise tiers)
- [ ] Unauthorized requests return 401
- [ ] Authorized requests include userId in context
- [ ] Git commit: "feat: implement JWT-based API authentication"

**Validation**:
```bash
# Test without API key
curl https://api-url/v1/members
# Expected: 401 Unauthorized

# Test with valid API key
curl -H "x-api-key: eyJhbGc..." https://api-url/v1/members
# Expected: 200 OK

# Generate test API key
python3 -c "
import jwt
key = jwt.encode({'user_id': 'test_user', 'tier': 'free'}, 'SECRET', algorithm='HS256')
print(key)
"
```

---

### Task 4.3: Add Rate Limiting by Tier
**Owner**: Backend Engineering/Claude
**Priority**: P0
**Risk**: Low

**Actions**:
1. Create `ingestion/lib/rate_limiter.py`:
```python
import boto3
import time
from functools import wraps

dynamodb = boto3.resource('dynamodb')
usage_table = dynamodb.Table('congress-disclosures-api-usage')

RATE_LIMITS = {
    'free': 100,        # requests/hour
    'pro': 1000,
    'enterprise': 10000
}

def rate_limit(func):
    @wraps(func)
    def wrapper(event, context):
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('userId')
        tier = event.get('requestContext', {}).get('authorizer', {}).get('tier', 'free')

        # Check hourly usage
        current_hour = int(time.time() // 3600)
        hour_key = f"{user_id}:{current_hour}"

        response = usage_table.update_item(
            Key={'user_id': user_id, 'timestamp': str(current_hour)},
            UpdateExpression='ADD request_count :inc',
            ExpressionAttributeValues={':inc': 1},
            ReturnValues='UPDATED_NEW'
        )

        request_count = response['Attributes']['request_count']
        limit = RATE_LIMITS[tier]

        if request_count > limit:
            return {
                'statusCode': 429,
                'body': json.dumps({
                    'error': 'Rate limit exceeded',
                    'limit': limit,
                    'reset': (current_hour + 1) * 3600
                })
            }

        return func(event, context)

    return wrapper
```

2. Update API Lambdas to use rate limiter:
```python
from ingestion.lib.rate_limiter import rate_limit

@rate_limit
def lambda_handler(event, context):
    # Handler logic
    pass
```

**Definition of Done**:
- [ ] Rate limiter module created
- [ ] All API Lambda handlers decorated with @rate_limit
- [ ] Exceeding limits returns 429 with reset timestamp
- [ ] Usage tracked in DynamoDB
- [ ] Git commit: "feat: add rate limiting by tier to API endpoints"

---

### Task 4.4: Implement Usage Tracking
**Owner**: Backend Engineering/Claude
**Priority**: P1
**Risk**: Low

**Actions**:
1. Create daily aggregation Lambda:
```python
def lambda_handler(event, context):
    """Aggregate hourly usage into daily totals."""
    # Query all usage events from yesterday
    # Sum by user_id
    # Write to api_usage_aggregates table
    pass
```

2. Create EventBridge rule to trigger daily at midnight

**Definition of Done**:
- [ ] Daily aggregation Lambda created
- [ ] EventBridge rule configured
- [ ] Usage aggregates table populated
- [ ] CloudWatch dashboard shows usage metrics
- [ ] Git commit: "feat: implement daily usage aggregation"

**Phase 4 Completion DOD**:
- [ ] API authentication working (JWT-based)
- [ ] Rate limiting enforced by tier
- [ ] Caching layer operational (>80% hit rate)
- [ ] Usage tracking functional
- [ ] All API endpoints protected
- [ ] Response times: <50ms (cached), <500ms (uncached)

---

## Phase 5: DBT Migration Completion (Weeks 13-16)

**Objective**: Port all Python transformation scripts to DBT models

### Task 5.1: Port Remaining Dimension Models (Week 13)
**Owner**: Data Engineering/Claude
**Priority**: P0
**Risk**: Low

**Models to Port**:
1. **dim_assets.sql** (replaces `build_dim_assets.py`)
2. **dim_bills.sql** (replaces `build_dim_bills.py`)
3. **dim_date.sql** (replaces `build_dim_date.py`)
4. **dim_committees.sql** (new)

**Definition of Done**:
- [ ] 4 dimension models created
- [ ] All models compiled successfully
- [ ] All models run successfully
- [ ] Output matches Python script outputs
- [ ] Tests pass (uniqueness, not_null, relationships)
- [ ] Git commit: "feat: port dimension models to DBT"

---

### Task 5.2: Port Fact Models (Week 14)
**Owner**: Data Engineering/Claude
**Priority**: P0
**Risk**: Medium

**Models to Port**:
1. **fact_filings.sql** (replaces `build_fact_filings.py`)
2. **fact_lobbying.sql** (replaces `build_fact_lobbying.py`)

**Definition of Done**:
- [ ] 2 fact models created
- [ ] Incremental materialization configured
- [ ] Partitioning by year/month
- [ ] All models run successfully
- [ ] Git commit: "feat: port fact models to DBT"

---

### Task 5.3: Port Aggregate Models (Week 15)
**Owner**: Data Engineering/Claude
**Priority**: P0
**Risk**: Medium

**Models to Port**:
1. **agg_member_trading_stats.sql**
2. **agg_sector_activity.sql**
3. **agg_compliance_metrics.sql**
4. **agg_network_graph.sql**
5. **agg_bill_trade_correlations.sql**
6. **agg_lobbying_network.sql**
7. **agg_congressional_alpha.sql**
8. **agg_conflict_detection.sql**
9. **agg_portfolio_snapshots.sql**

**Definition of Done**:
- [ ] 9 aggregate models created
- [ ] All models compiled and run successfully
- [ ] Git commit: "feat: port aggregate models to DBT"

---

### Task 5.4: Integrate DBT with Step Functions (Week 16)
**Owner**: DevOps/Claude
**Priority**: P0
**Risk**: Medium

**Actions**:
1. Create Lambda to run DBT:
```python
import subprocess

def lambda_handler(event, context):
    command = event.get('command', 'dbt run')
    target = event.get('target', 'prod')

    result = subprocess.run(
        ['/opt/dbt/bin/dbt', *command.split()],
        capture_output=True,
        text=True
    )

    return {
        'statusCode': 0 if result.returncode == 0 else 1,
        'stdout': result.stdout,
        'stderr': result.stderr
    }
```

2. Update Step Functions to use DBT:
```json
{
  "RunDBTModels": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...:function:run-dbt",
    "Parameters": {
      "command": "dbt run --select gold.*"
    },
    "Next": "TestDBTModels"
  },
  "TestDBTModels": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...:function:run-dbt",
    "Parameters": {
      "command": "dbt test --select gold.*"
    }
  }
}
```

**Definition of Done**:
- [ ] DBT Lambda created
- [ ] Step Functions updated to use DBT
- [ ] Full pipeline runs end-to-end with DBT
- [ ] Python scripts decommissioned (~30K lines removed)
- [ ] Git commit: "feat: integrate DBT with Step Functions"

**Phase 5 Completion DOD**:
- [ ] 100% of transformation logic migrated to DBT (18 models, 50+ tests)
- [ ] All Python scripts decommissioned
- [ ] Step Functions use DBT for all transformations
- [ ] Data quality tests pass (95%+ success rate)
- [ ] Code reduced from ~30K lines Python → ~2K lines SQL ✅
- [ ] Documentation updated with DBT lineage DAG

---

## Success Metrics

### Technical Metrics
- [ ] API response time: <500ms P95, <50ms (cached)
- [ ] Data freshness: <5 min (event-driven)
- [ ] Test coverage: 50+ DBT tests, 95%+ pass rate
- [ ] Cache hit rate: >80%
- [ ] Data quality: 100% referential integrity

### Business Metrics
- [ ] Initial load cost: <$30 ✅
- [ ] Ongoing cost: <$5/month ✅
- [ ] Time to first API request: 16 weeks
- [ ] Code maintainability: 95% reduction in transformation code
- [ ] Vendor lock-in risk: Low (all core components portable)

### Operational Metrics
- [ ] Deployment frequency: Daily (CI/CD)
- [ ] Mean time to recovery: <1 hour
- [ ] Incident rate: <1 per month
- [ ] Uptime: >99.9%

---

## Post-Launch Roadmap (Months 5-12)

### Month 5-6: Iceberg Migration (Selective)
- Migrate 5 high-traffic tables to Iceberg format
- Benefits: ACID transactions, time travel, schema evolution
- Cost: $0 (uses existing Glue Catalog)

### Month 7-8: Stripe Billing
- Create Stripe products (Free, Pro, Enterprise)
- Implement metered billing based on DynamoDB usage logs
- Build customer portal

### Month 9-10: Event-Driven Architecture
- Replace SQS queues with EventBridge rules
- S3 event → Lambda trigger (near real-time)
- Reduce extraction latency from 1 hour → 5 minutes

### Month 11-12: State-Level Expansion
- Add CA, NY, TX state disclosures
- Standardize schemas across states
- Build unified `dim_officials` (federal + state)

---

## Emergency Rollback Plan

If any phase fails critically:

1. **Terraform Changes**:
   ```bash
   cd infra/terraform
   git revert HEAD
   terraform plan
   terraform apply
   ```

2. **Application Changes**:
   ```bash
   git revert HEAD
   # Redeploy affected Lambdas
   make quick-deploy-<lambda-name>
   ```

3. **Data Issues**:
   - Bronze layer is immutable (safe to reprocess)
   - Silver/Gold can be rebuilt from Bronze
   - Restore from S3 versioning if needed

4. **Cost Overruns**:
   - Pause Step Functions executions
   - Reduce MaxConcurrency to 1
   - Enable AWS Budget Alerts

---

## Contacts & Escalation

**Project Owner**: Jake (GitHub: @Jakeintech)
**Technical Lead**: Claude (AI Assistant)
**Budget Authority**: Jake
**Emergency Contact**: Jake

**Escalation Path**:
1. Cost alert >$10/day → Pause all executions
2. Data quality <90% → Halt pipeline, investigate
3. API downtime >1 hour → Rollback recent changes

---

## Appendix: Cost Tracking

| Phase | Estimated Cost | Actual Cost | Status |
|-------|---------------|-------------|--------|
| Phase 0 | $1.50 (Glue Crawler) | TBD | Pending |
| Phase 1 | $0 (refactoring only) | TBD | Pending |
| Phase 2 | $0 (free APIs) | TBD | Pending |
| Phase 3 | $5-10 (initial load) | TBD | Pending |
| Phase 4 | $0 (free tier DynamoDB) | TBD | Pending |
| Phase 5 | $0 (refactoring only) | TBD | Pending |
| **Total** | **$6.50-11.50** | **TBD** | **Under Budget ✅** |

**Ongoing Monthly**:
- S3 Storage (25 GB): $0.60
- Glue Crawler: $1.50
- DynamoDB (free tier): $0
- Lambda (free tier): $0
- API Gateway (free tier): $0
- **Total**: **~$2.10/month** ✅

---

**Last Updated**: 2025-01-06
**Version**: 1.0.0
**Status**: Ready for Execution
