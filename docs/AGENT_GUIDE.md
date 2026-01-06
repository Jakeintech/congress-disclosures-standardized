# Agent Execution Guide - Politics Data Platform Modernization

**For AI Agents (Claude Code, GitHub Copilot, etc.)**

This guide provides clear, executable commands with validation checks for each phase.

---

## Quick Start - Run Entire Phase at Once

Each phase is fully automated. Copy-paste commands directly.

### Phase 0: Infrastructure Cleanup (30 minutes)

```bash
# Navigate to project root
cd /Users/jake/Documents/GitHub/congress-disclosures-standardized

# Execute Phase 0 Script
./scripts/execute_phase0.sh

# Expected output:
# ✓ Deleted 8 redundant Terraform files
# ✓ Removed 2 legacy resources
# ✓ Terraform plan shows expected changes
# ✓ All validations passed
```

**Manual Alternative (if script doesn't exist yet)**:

```bash
cd /Users/jake/Documents/GitHub/congress-disclosures-standardized

# Task 0.1: Delete redundant files
cd infra/terraform
rm -f api_gateway_assets.tf api_gateway_members.tf api_gateway_transactions.tf \
      api_costs_route.tf api_storage_route.tf lambda_stub.tf \
      lambdas_analytics.tf lambdas_data_quality.tf

# Validate
terraform validate
terraform plan | head -20  # Should show "No changes" for most resources

# Task 0.2: Deploy new infrastructure
terraform plan -out=tfplan
terraform apply tfplan

# Validate new resources
aws dynamodb list-tables | grep "politics-api"
aws glue get-database --name politics_data_platform

# Commit
cd ../../
git add -A
git commit -m "refactor(terraform): cleanup redundant files and deploy API infrastructure"
```

**Definition of Done Check**:
```bash
# Verify file count reduced
ls infra/terraform/*.tf | wc -l
# Expected: 36 (down from 44)

# Verify new tables exist
aws dynamodb describe-table --table-name congress-disclosures-api-cache
aws glue get-database --name politics_data_platform

# Verify zero unexpected changes
cd infra/terraform && terraform plan | grep "No changes"
```

---

### Phase 1: Foundation (2 weeks)

```bash
# Execute Phase 1 Script
./scripts/execute_phase1.sh

# Expected output:
# ✓ Updated 148 files to use S3Paths registry
# ✓ DBT Core installed and configured
# ✓ First 3 DBT models ported and tested
# ✓ All validations passed
```

**Manual Alternative**:

#### Task 1.1: Update Lambdas to Use Centralized Paths (Week 2-4)

```bash
# Find all files with hard-coded paths
grep -r "bronze/house/financial" ingestion/ --files-with-matches > /tmp/files_to_update.txt
grep -r "silver/house/financial" ingestion/ --files-with-matches >> /tmp/files_to_update.txt
grep -r "gold/house/financial" ingestion/ --files-with-matches >> /tmp/files_to_update.txt

# Count files
wc -l /tmp/files_to_update.txt
# Expected: ~148 files

# Automated replacement (example for one pattern)
find ingestion/lambdas -type f -name "*.py" -exec sed -i '' \
  's|f"bronze/house/financial/year={year}"|S3Paths.bronze_house_fd_base(year)|g' {} +

# Add import to all Lambda handlers
find ingestion/lambdas -type f -name "handler.py" -exec sed -i '' \
  '1s|^|from ingestion.lib.s3_path_registry import S3Paths\n|' {} +

# Verify no hard-coded paths remain
grep -r '"bronze/' ingestion/lambdas/ ingestion/lib/ scripts/ && echo "❌ Hard-coded paths found" || echo "✓ All paths centralized"
```

**DOD Check**:
```bash
# Test imports
python3 -c "from ingestion.lib.s3_path_registry import S3Paths; print(S3Paths.bronze_house_fd_pdf(2025, 'P', '12345'))"
# Expected: data/bronze/house_fd/year=2025/filing_type=P/pdfs/12345.pdf

# Run unit tests
pytest tests/unit/test_s3_paths.py -v
```

#### Task 1.2: Set Up DBT Core (30 minutes)

```bash
# Install DBT
pip install dbt-core dbt-duckdb
dbt --version

# Initialize project
mkdir -p dbt
cd dbt
dbt init politics_data_platform --skip-profile-setup

# Create profiles.yml
mkdir -p ~/.dbt
cat > ~/.dbt/profiles.yml <<'EOF'
politics_data_platform:
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
      settings:
        s3_region: us-east-1
        s3_use_ssl: true
EOF

# Test configuration
dbt debug

# Expected output: "All checks passed!"
```

**DOD Check**:
```bash
cd dbt
dbt debug
# Should show: Connection test: [OK connection ok]
```

#### Task 1.3: Port First 3 DBT Models (Week 4)

```bash
cd dbt

# Create directory structure
mkdir -p models/gold/dimensions models/gold/facts models/gold/aggregates

# Create dim_members.sql (see MASTER_PLAN.md for full SQL)
cat > models/gold/dimensions/dim_members.sql <<'EOF'
{{ config(
    materialized='table',
    unique_key='member_key',
    schema='gold'
) }}

WITH filings AS (
  SELECT DISTINCT
    first_name,
    last_name,
    state_district
  FROM {{ source('silver', 'filings') }}
)

SELECT
  {{ dbt_utils.generate_surrogate_key(['first_name', 'last_name', 'state_district']) }} AS member_key,
  first_name,
  last_name,
  first_name || ' ' || last_name AS full_name,
  state_district,
  CURRENT_TIMESTAMP AS created_at
FROM filings
EOF

# Test compilation
dbt compile --select dim_members

# Run the model
dbt run --select dim_members

# Verify output in S3
aws s3 ls s3://politics-data-platform/data/gold/dimensions/dim_members/
```

**DOD Check**:
```bash
# Verify model compiled
ls target/compiled/politics_data_platform/models/gold/dimensions/dim_members.sql

# Verify model ran successfully
dbt run --select dim_members
# Should show: "1 of 1 OK created table model gold.dim_members"

# Verify output exists
aws s3 ls s3://politics-data-platform/data/gold/dimensions/dim_members/ | grep ".parquet"
```

---

### Phase 2: Reference Data (1 week)

```bash
# Execute Phase 2 Script
./scripts/execute_phase2.sh

# Expected output:
# ✓ Built member registry with 3,000+ members
# ✓ Built asset crosswalk with 13,000+ tickers
# ✓ Built bill ID crosswalk
# ✓ All reference data in S3
```

**Manual Alternative**:

```bash
# Task 2.1: Build Member Registry
python3 scripts/build_reference_members.py

# Validate
aws s3 ls s3://politics-data-platform/data/reference/members/
python3 -c "
import pandas as pd
df = pd.read_parquet('s3://politics-data-platform/data/reference/members/dim_members_master.parquet')
print(f'Total members: {len(df)}')
assert len(df) > 2000, 'Expected >2000 members'
print('✓ Member registry built successfully')
"

# Task 2.2: Build Asset Crosswalk
python3 scripts/build_reference_assets.py

# Validate
python3 -c "
import pandas as pd
df = pd.read_parquet('s3://politics-data-platform/data/reference/asset_crosswalk/assets.parquet')
print(f'Total tickers: {len(df)}')
assert len(df) > 10000, 'Expected >10K tickers'
print('✓ Asset crosswalk built successfully')
"

# Task 2.3: Build Bill Crosswalk
python3 scripts/build_reference_bills.py

# Commit
git add -A
git commit -m "feat(reference-data): build member, asset, and bill crosswalks"
```

**DOD Check**:
```bash
# Verify all 3 reference datasets exist
aws s3 ls s3://politics-data-platform/data/reference/ --recursive | grep ".parquet"
# Expected: 3 parquet files (members, assets, bills)
```

---

### Phase 3: Initial Load (2 weeks)

```bash
# Execute Phase 3 Script
./scripts/execute_phase3.sh

# Expected output:
# ✓ Loaded 30K House FD filings (2024-2025)
# ✓ Loaded 118th Congress data
# ✓ Loaded 2024 lobbying data
# ✓ Built Gold aggregates
# ✓ Total cost: <$10
```

**Manual Alternative**:

```bash
# Task 3.2: Execute House FD Initial Load
EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:464813693153:stateMachine:house_fd_pipeline \
  --name "initial-load-$(date +%Y%m%d-%H%M%S)" \
  --input '{
    "execution_type": "initial_load",
    "years": [2024, 2025],
    "max_concurrency": 5
  }' \
  --query 'executionArn' \
  --output text)

echo "Execution started: $EXECUTION_ARN"

# Monitor progress (run in separate terminal)
watch -n 30 "aws stepfunctions describe-execution --execution-arn $EXECUTION_ARN | jq '.status'"

# Wait for completion (automated)
while true; do
  STATUS=$(aws stepfunctions describe-execution \
    --execution-arn $EXECUTION_ARN \
    --query 'status' \
    --output text)

  if [ "$STATUS" = "SUCCEEDED" ]; then
    echo "✓ Execution completed successfully"
    break
  elif [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "TIMED_OUT" ] || [ "$STATUS" = "ABORTED" ]; then
    echo "❌ Execution failed with status: $STATUS"
    exit 1
  fi

  echo "Status: $STATUS (waiting 60s...)"
  sleep 60
done

# Validate output
aws s3 ls s3://politics-data-platform/data/bronze/house_fd/year=2024/ --recursive | wc -l
aws s3 ls s3://politics-data-platform/data/bronze/house_fd/year=2025/ --recursive | wc -l
# Expected: ~30,000 total files

# Check cost
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '24 hours ago' +%Y-%m-%d),End=$(date -u +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --query 'ResultsByTime[].Total.BlendedCost.Amount' \
  --output text
# Expected: <$5
```

**DOD Check**:
```bash
# Verify data loaded
python3 scripts/validate_pipeline_integrity.py --years 2024,2025
# Expected: 100% success rate

# Check storage
aws s3 ls s3://politics-data-platform/data/ --recursive --summarize | tail -2
# Expected: ~80 GB total, compressed to ~25 GB
```

---

### Phase 4: API Modernization (2 weeks)

```bash
# Execute Phase 4 Script
./scripts/execute_phase4.sh

# Expected output:
# ✓ DynamoDB caching layer implemented
# ✓ API authentication configured
# ✓ Rate limiting enabled
# ✓ Cache hit rate >80%
```

**Manual Alternative**:

```bash
# Task 4.1: Implement Caching
# (Create api_cache.py utility - see MASTER_PLAN.md)

# Update Lambda to use caching
# Deploy
cd ingestion/lambdas/api/get_trending_stocks
zip -r function.zip .
aws lambda update-function-code \
  --function-name congress-disclosures-api-get-trending-stocks \
  --zip-file fileb://function.zip

# Test caching
curl https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com/v1/analytics/trending-stocks \
  -H "x-api-key: test" -i | grep "X-Cache"
# First call: X-Cache: MISS
# Second call: X-Cache: HIT

# Task 4.2: Deploy API Authorizer
cd infra/terraform
terraform plan -target=aws_lambda_function.api_authorizer
terraform apply -target=aws_lambda_function.api_authorizer

# Generate test API key
python3 -c "
import jwt
import hashlib
user_id = 'test_user_123'
tier = 'free'
api_key = jwt.encode({'user_id': user_id, 'tier': tier}, 'SECRET_CHANGE_ME', algorithm='HS256')
print(f'API Key: {api_key}')
print(f'Hash: {hashlib.sha256(api_key.encode()).hexdigest()}')
"

# Store in DynamoDB
aws dynamodb put-item \
  --table-name congress-disclosures-api-keys \
  --item '{
    "api_key_hash": {"S": "<hash_from_above>"},
    "user_id": {"S": "test_user_123"},
    "tier": {"S": "free"},
    "created_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"},
    "suspended": {"BOOL": false}
  }'

# Test authentication
curl https://api-url/v1/members \
  -H "x-api-key: <api_key_from_above>"
# Expected: 200 OK
```

**DOD Check**:
```bash
# Verify caching works
curl https://api-url/v1/analytics/trending-stocks -H "x-api-key: test" -i | grep "X-Cache: HIT"

# Verify authentication
curl https://api-url/v1/members
# Expected: 401 Unauthorized

curl https://api-url/v1/members -H "x-api-key: valid_key"
# Expected: 200 OK

# Verify rate limiting
for i in {1..101}; do
  curl https://api-url/v1/members -H "x-api-key: free_tier_key"
done
# 101st request should return 429 Rate Limit Exceeded
```

---

### Phase 5: DBT Migration (4 weeks)

```bash
# Execute Phase 5 Script
./scripts/execute_phase5.sh

# Expected output:
# ✓ Ported 18 DBT models
# ✓ All tests passing
# ✓ Decommissioned 30K lines of Python code
# ✓ Step Functions integrated with DBT
```

**Manual Alternative**:

```bash
# Task 5.1-5.3: Port all models (see MASTER_PLAN.md for SQL)
cd dbt

# Create all models (automated script)
for model in dim_assets dim_bills dim_date fact_filings fact_lobbying agg_member_stats; do
  echo "Porting $model..."
  # Copy from templates (see MASTER_PLAN.md)
done

# Run all models
dbt run --select gold.*

# Run tests
dbt test --select gold.*

# Task 5.4: Integrate with Step Functions
cd ../infra/terraform

# Deploy run-dbt Lambda
terraform plan -target=aws_lambda_function.run_dbt
terraform apply -target=aws_lambda_function.run_dbt

# Update Step Functions
terraform plan -target=aws_sfn_state_machine.house_fd_pipeline
terraform apply -target=aws_sfn_state_machine.house_fd_pipeline

# Test end-to-end
aws stepfunctions start-execution \
  --state-machine-arn <arn> \
  --input '{"execution_type": "dbt_test", "year": 2025}'
```

**DOD Check**:
```bash
# Verify all models exist
ls dbt/models/gold/dimensions/*.sql | wc -l
# Expected: 5 models

ls dbt/models/gold/facts/*.sql | wc -l
# Expected: 3 models

ls dbt/models/gold/aggregates/*.sql | wc -l
# Expected: 10 models

# Verify tests pass
cd dbt
dbt test --select gold.*
# Expected: 50+ tests, 95%+ pass rate

# Verify Python scripts decommissioned
git diff --stat HEAD~1 scripts/
# Expected: Large deletions (~30K lines)
```

---

## Validation Checklist (Run After Each Phase)

```bash
# Phase 0
[ ] terraform plan shows expected changes only
[ ] 8 files deleted, file count = 36
[ ] New DynamoDB tables exist
[ ] Glue Catalog database exists

# Phase 1
[ ] No hard-coded S3 paths in code
[ ] DBT debug passes
[ ] First 3 DBT models run successfully

# Phase 2
[ ] 3 reference datasets in S3
[ ] Member registry has >2000 members
[ ] Asset crosswalk has >10K tickers

# Phase 3
[ ] 30K PDFs loaded to Bronze
[ ] Gold tables populated
[ ] Cost <$10
[ ] Data quality 100%

# Phase 4
[ ] API authentication working
[ ] Cache hit rate >80%
[ ] Rate limiting enforced
[ ] Usage tracking operational

# Phase 5
[ ] 18 DBT models created
[ ] 50+ tests passing
[ ] 30K lines Python code removed
[ ] Step Functions use DBT
```

---

## Troubleshooting

### Terraform Issues

```bash
# Issue: terraform plan shows unexpected changes
terraform refresh
terraform plan -out=tfplan

# Issue: state lock
terraform force-unlock <lock-id>

# Issue: resource already exists
terraform import <resource_type>.<name> <resource_id>
```

### DBT Issues

```bash
# Issue: dbt debug fails
dbt debug
# Check profiles.yml, check AWS credentials

# Issue: model won't compile
dbt compile --select <model_name> --debug

# Issue: tests fail
dbt test --select <model_name> --store-failures
dbt show --select <model_name>
```

### API Issues

```bash
# Issue: 401 Unauthorized
# Check API key is valid
aws dynamodb get-item \
  --table-name congress-disclosures-api-keys \
  --key '{"api_key_hash": {"S": "<hash>"}}'

# Issue: 429 Rate Limit
# Check hourly usage
aws dynamodb query \
  --table-name congress-disclosures-api-usage \
  --key-condition-expression "user_id = :uid" \
  --expression-attribute-values '{":uid": {"S": "test_user"}}'

# Issue: Slow responses
# Check cache hit rate
aws cloudwatch get-metric-statistics \
  --namespace PoliticsAPI \
  --metric-name CacheHitRate \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Average
```

### Step Functions Issues

```bash
# Issue: execution failed
EXECUTION_ARN=<your-execution-arn>
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN \
  --max-results 100 \
  | jq '.events[] | select(.type == "TaskFailed")'

# Issue: Lambda timeout
# Check CloudWatch logs
aws logs tail /aws/lambda/<function-name> --follow

# Issue: cost overrun
# Check current spend
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '7 days ago' +%Y-%m-%d),End=$(date -u +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost
```

---

## Emergency Stop

If costs exceed budget or critical error:

```bash
# STOP ALL STEP FUNCTIONS
for arn in $(aws stepfunctions list-state-machines --query 'stateMachines[].stateMachineArn' --output text); do
  for exec in $(aws stepfunctions list-executions --state-machine-arn $arn --status-filter RUNNING --query 'executions[].executionArn' --output text); do
    aws stepfunctions stop-execution --execution-arn $exec
    echo "Stopped: $exec"
  done
done

# PAUSE GLUE CRAWLERS
for crawler in $(aws glue list-crawlers --query 'CrawlerNames[]' --output text); do
  aws glue stop-crawler --name $crawler 2>/dev/null || true
  echo "Stopped: $crawler"
done

# DISABLE EVENTBRIDGE RULES
for rule in $(aws events list-rules --query 'Rules[].Name' --output text); do
  aws events disable-rule --name $rule
  echo "Disabled: $rule"
done

# CHECK CURRENT COSTS
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '24 hours ago' +%Y-%m-%d),End=$(date -u +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost

echo "✓ All automated processes stopped"
```

---

## Agent Checklist (Before Starting Each Phase)

- [ ] Read phase DOD from MASTER_EXECUTION_PLAN.md
- [ ] Verify AWS credentials are valid (`aws sts get-caller-identity`)
- [ ] Verify current directory is project root
- [ ] Create git branch for phase (`git checkout -b phase-X`)
- [ ] Run phase automation script OR execute manual commands
- [ ] Validate phase completion using DOD checks
- [ ] Commit changes with descriptive message
- [ ] Update progress in MASTER_EXECUTION_PLAN.md

---

**Last Updated**: 2025-01-06
**For**: AI Agents (Claude Code, Copilot, etc.)
**Purpose**: Step-by-step automation with validation
