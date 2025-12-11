# Pipeline Migration Plan - 7 Week Roadmap

## Executive Summary

**Goal**: Migrate from manual Makefile-based pipeline to automated, production-grade medallion architecture

**Timeline**: 7 weeks (January 13 - March 3, 2025)

**Cost Savings**: $51/month (99.3% reduction)

**Key Deliverables**:
1. Automated orchestration (Step Functions)
2. Incremental processing (DynamoDB watermarks)
3. Data quality gates (Soda Core)
4. API optimization (DuckDB replaces Athena)
5. Complete documentation

---

## Week 1: Orchestration Infrastructure (Jan 13-19)

### Objectives
- Define Step Functions state machines for all pipelines
- Create Terraform infrastructure
- Set up EventBridge cron triggers
- Deploy and test basic orchestration

### Tasks

#### Day 1-2: Step Functions Design
- [ ] Create `state_machines/house_fd_pipeline.json`
  - States: CheckNewFilings → IngestZip → IndexToSilver → ExtractDocuments (Map) → TransformToGold → ValidateQuality → UpdateCache
  - Error handling: Retry with exponential backoff, catch to SNS alert
  - Parallel execution: Map state for document extraction (10 concurrent)

- [ ] Create `state_machines/congress_pipeline.json`
  - States: FetchBills → FetchDetails (Map) → TransformToSilver → BuildDimensions → ComputeCorrelations
  - Rate limiting: 5K requests/hour (Congress.gov API limit)

- [ ] Create `state_machines/lobbying_pipeline.json`
  - States: CheckNewFilings → DownloadXML → ParseToSilver → TransformToGold

- [ ] Create `state_machines/cross_dataset_correlation.json`
  - Triggered by: House FD pipeline completion event
  - States: BuildBillTradeCorrelations → BuildNetworkGraph → UpdateAggregates

#### Day 3-4: Terraform Infrastructure
- [ ] Create `infra/terraform/step_functions.tf`
  ```hcl
  resource "aws_sfn_state_machine" "house_fd_pipeline" {
    name     = "${var.project_name}-house-fd-pipeline"
    role_arn = aws_iam_role.step_functions_role.arn
    definition = file("${path.module}/../../state_machines/house_fd_pipeline.json")
  }

  resource "aws_cloudwatch_event_rule" "house_fd_hourly" {
    name                = "${var.project_name}-house-fd-hourly"
    schedule_expression = "rate(1 hour)"
  }

  resource "aws_cloudwatch_event_target" "trigger_house_fd" {
    rule      = aws_cloudwatch_event_rule.house_fd_hourly.name
    arn       = aws_sfn_state_machine.house_fd_pipeline.arn
    role_arn  = aws_iam_role.eventbridge_step_functions.arn
  }
  ```

- [ ] Create `infra/terraform/dynamodb.tf` (watermarks table)
  ```hcl
  resource "aws_dynamodb_table" "pipeline_watermarks" {
    name           = "${var.project_name}-pipeline-watermarks"
    billing_mode   = "PAY_PER_REQUEST"
    hash_key       = "table_name"
    range_key      = "watermark_type"

    attribute {
      name = "table_name"
      type = "S"
    }
    attribute {
      name = "watermark_type"
      type = "S"
    }
  }
  ```

- [ ] Create IAM roles and policies
  - Step Functions execution role (invoke Lambda, publish SNS)
  - EventBridge role (start Step Functions)

#### Day 5: Lambda Adaptations
- [ ] Refactor existing Lambdas to work with Step Functions
  - Input: Step Functions task input (JSON)
  - Output: Step Functions task output (JSON)
  - Error handling: Raise exceptions for Step Functions Catch

- [ ] Create `api/lambdas/check_house_fd_updates/handler.py`
  ```python
  def handler(event, context):
      """Check House Clerk website for new filings."""
      current_year = datetime.now().year
      url = f"https://disclosures-clerk.house.gov/..."

      # Check last ingestion watermark
      last_ingested = get_watermark('bronze.house.financial', 'last_year')

      # Scrape for new filings
      new_filings = check_for_updates(url, last_ingested)

      return {
          'has_new_filings': len(new_filings) > 0,
          'new_filings': new_filings,
          'year': current_year
      }
  ```

#### Day 6-7: Testing & Deployment
- [ ] Deploy infrastructure: `make init && make deploy`
- [ ] Test Step Functions manually (AWS Console)
- [ ] Verify EventBridge triggers
- [ ] Monitor CloudWatch Logs for errors

### Deliverables
- ✅ 4 Step Functions state machines (JSON)
- ✅ Terraform infrastructure (step_functions.tf, dynamodb.tf)
- ✅ EventBridge cron triggers
- ✅ Adapted Lambda functions
- ✅ DynamoDB watermarks table

### Success Metrics
- Step Functions execute successfully end-to-end
- EventBridge triggers on schedule
- CloudWatch Logs show execution history
- No manual intervention required

---

## Week 2: DuckDB Integration (Jan 20-26)

### Objectives
- Create DuckDB Lambda layer
- Rewrite 3 Gold transformation scripts with DuckDB
- Benchmark performance (Pandas vs DuckDB)
- Deploy as Lambda functions

### Tasks

#### Day 1-2: DuckDB Lambda Layer
- [ ] Create `layers/duckdb/requirements.txt`
  ```
  duckdb==0.9.2
  pyarrow==14.0.1
  boto3==1.34.0
  ```

- [ ] Build Lambda layer
  ```bash
  cd layers/duckdb
  mkdir python
  pip install -r requirements.txt -t python/
  zip -r duckdb-layer.zip python/
  aws lambda publish-layer-version \
    --layer-name congress-duckdb \
    --zip-file fileb://duckdb-layer.zip \
    --compatible-runtimes python3.11
  ```

- [ ] Update Terraform to attach layer to Lambdas
  ```hcl
  resource "aws_lambda_function" "build_fact_transactions" {
    ...
    layers = [aws_lambda_layer_version.duckdb.arn]
  }
  ```

#### Day 3-4: Rewrite Gold Scripts

**Script 1: `scripts/gold/build_fact_transactions_duckdb.py`**
```python
import duckdb
import boto3
import os

S3_BUCKET = os.environ['S3_BUCKET_NAME']

def handler(event, context):
    """Build fact_ptr_transactions using DuckDB (incremental)."""
    conn = duckdb.connect(':memory:')
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    conn.execute(f"SET s3_region='{os.environ['AWS_REGION']}';")

    # Get watermark
    last_doc_id = get_watermark('gold.fact_ptr_transactions', 'max_doc_id')

    # Incremental load (only new transactions)
    result = conn.execute(f"""
        CREATE TABLE new_transactions AS
        SELECT
            ROW_NUMBER() OVER () + 1000000 AS transaction_key,
            t.transaction_id,
            t.doc_id,
            m.member_key,
            a.asset_key,
            CAST(REPLACE(CAST(t.transaction_date AS STRING), '-', '') AS INT) AS transaction_date_key,
            t.bioguide_id,
            t.ticker,
            t.transaction_type,
            t.amount_low,
            t.amount_high,
            (t.amount_low + t.amount_high) / 2.0 AS amount_midpoint,
            CURRENT_TIMESTAMP AS gold_ingest_ts
        FROM 's3://{S3_BUCKET}/silver/house/financial/transactions/*.parquet' t
        LEFT JOIN 's3://{S3_BUCKET}/gold/dimensions/dim_member/*.parquet' m
            ON t.bioguide_id = m.bioguide_id AND m.is_current = true
        LEFT JOIN 's3://{S3_BUCKET}/gold/dimensions/dim_asset/*.parquet' a
            ON t.ticker = a.ticker
        WHERE t.doc_id > '{last_doc_id}'
          AND t.transaction_date >= CURRENT_DATE - INTERVAL '2 years'
    """)

    # Export to S3 (append)
    output_path = f"s3://{S3_BUCKET}/gold/facts/fact_ptr_transactions/data_incremental_{context.request_id}.parquet"
    conn.execute(f"""
        COPY new_transactions
        TO '{output_path}'
        (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    # Get row count
    row_count = conn.execute("SELECT COUNT(*) FROM new_transactions").fetchone()[0]

    # Update watermark
    if row_count > 0:
        max_doc_id = conn.execute("SELECT MAX(doc_id) FROM new_transactions").fetchone()[0]
        update_watermark('gold.fact_ptr_transactions', 'max_doc_id', max_doc_id, row_count)

    return {
        'status': 'success',
        'rows_processed': row_count,
        'output_path': output_path
    }

def get_watermark(table_name, watermark_type):
    """Get last processed value from DynamoDB."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('congress-pipeline-watermarks')

    response = table.get_item(
        Key={'table_name': table_name, 'watermark_type': watermark_type}
    )

    return response.get('Item', {}).get('last_processed_value', '0')

def update_watermark(table_name, watermark_type, value, rows_processed):
    """Update watermark in DynamoDB."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('congress-pipeline-watermarks')

    table.put_item(Item={
        'table_name': table_name,
        'watermark_type': watermark_type,
        'last_processed_value': str(value),
        'last_processed_timestamp': datetime.utcnow().isoformat(),
        'rows_processed': rows_processed
    })
```

**Script 2: `scripts/gold/build_dim_members_duckdb.py`**
- SCD Type 2 logic: detect changes in party, district, committees
- Insert new rows with updated valid_from, expire old rows with valid_to

**Script 3: `scripts/gold/compute_trending_stocks_duckdb.py`**
- Rolling window aggregations (7d, 30d, 90d)
- Sentiment score calculation

#### Day 5: Benchmarking
- [ ] Run Pandas version and DuckDB version side-by-side
- [ ] Measure:
  - Execution time (expect 10-100x speedup)
  - Memory usage
  - Output correctness (row counts, checksums)

- [ ] Document results in `docs/BENCHMARKS.md`

#### Day 6-7: Lambda Deployment
- [ ] Package scripts as Lambda functions
- [ ] Update Terraform: `infra/terraform/lambdas_gold.tf`
- [ ] Deploy: `terraform apply`
- [ ] Test in Step Functions

### Deliverables
- ✅ DuckDB Lambda layer
- ✅ 3 rewritten Gold scripts (DuckDB)
- ✅ Performance benchmarks
- ✅ Deployed Lambda functions

### Success Metrics
- DuckDB scripts 10x+ faster than Pandas
- Incremental processing verified (watermarks work)
- Output matches existing Gold tables (validation)

---

## Week 3: Data Quality Framework (Jan 27 - Feb 2)

### Objectives
- Install Soda Core in Lambda layer
- Write 30+ data quality checks (YAML)
- Create `run_soda_checks` Lambda function
- Integrate quality gates into Step Functions

### Tasks

#### Day 1-2: Soda Core Lambda Layer
- [ ] Create `layers/soda_core/requirements.txt`
  ```
  soda-core-duckdb==3.1.0
  duckdb==0.9.2
  pyyaml==6.0
  ```

- [ ] Build and publish layer
  ```bash
  cd layers/soda_core
  mkdir python
  pip install -r requirements.txt -t python/
  zip -r soda-core-layer.zip python/
  aws lambda publish-layer-version \
    --layer-name congress-soda-core \
    --zip-file fileb://soda-core-layer.zip \
    --compatible-runtimes python3.11
  ```

#### Day 3-4: Write Quality Checks

**File structure**:
```
soda/
  checks/
    silver_filings.yml
    silver_transactions.yml
    silver_assets.yml
    silver_bills.yml
    gold_fact_transactions.yml
    gold_fact_filings.yml
    gold_aggregates.yml
  configuration.yml
```

**Example: `soda/checks/silver_transactions.yml`**
```yaml
checks for silver.transactions:
  # Schema validation
  - schema:
      fail when required column missing:
        - doc_id
        - transaction_date
        - asset_name
        - transaction_type
        - amount_low
      fail when wrong type:
        transaction_date: date
        amount_low: decimal

  # Referential integrity
  - values in (doc_id) must exist in silver.filings (doc_id):
      name: Transactions must reference valid filings

  # Data validity
  - invalid_count(transaction_date) = 0:
      valid min: 2008-01-01
      valid max: ${TODAY}
      name: Transaction dates in valid range

  - invalid_count(transaction_type) = 0:
      valid values: ['Purchase', 'Sale', 'Exchange']

  - invalid_count(amount_low) = 0:
      valid min: 1001
      valid max: 50000000
      name: Amount ranges are realistic

  # Freshness
  - freshness(silver_ingest_ts) < 2h:
      name: Silver layer updated within 2 hours

  # Anomaly detection
  - anomaly score for row_count < 3:
      name: Row count within 3 std devs of historical

  - anomaly score for avg(amount_low) < 3:
      name: Average trade size is normal

  # Duplicates
  - duplicate_count(transaction_id) = 0:
      name: No duplicate transaction IDs

  # Missing values
  - missing_count(ticker) < 100:
      name: Most transactions have tickers
```

**Total checks to write**:
- Silver layer: 15 checks
- Gold facts: 10 checks
- Gold aggregates: 5 checks
- **Total: 30+ checks**

#### Day 5: Lambda Function

**Create `api/lambdas/run_soda_checks/handler.py`**:
```python
from soda.scan import Scan
import duckdb
import json
import os

def handler(event, context):
    """Run Soda Core data quality checks."""
    checks_path = event['checks_path']  # e.g., 'soda/checks/silver_transactions.yml'

    # Initialize DuckDB connection
    conn = duckdb.connect(':memory:')
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    conn.execute(f"SET s3_region='{os.environ['AWS_REGION']}';")

    # Create Soda scan
    scan = Scan()
    scan.set_data_source_name("s3_data_lake")
    scan.add_duckdb_connection(conn)

    # Add checks
    scan.add_sodacl_yaml_file(checks_path)

    # Run scan
    scan.execute()

    # Get results
    results = {
        'checks_passed': scan.get_checks_passed_count(),
        'checks_failed': scan.get_checks_failed_count(),
        'checks_warned': scan.get_checks_warned_count(),
        'scan_results': scan.get_scan_results()
    }

    # Fail if any checks failed
    if results['checks_failed'] > 0:
        raise Exception(f"Data quality checks failed: {results['checks_failed']} failures")

    return results
```

#### Day 6-7: Step Functions Integration
- [ ] Add quality check states to all pipelines
  ```json
  {
    "TransformToGold": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:::function:build-fact-transactions",
      "Next": "ValidateGoldQuality"
    },
    "ValidateGoldQuality": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:::function:run-soda-checks",
      "Parameters": {
        "checks_path": "soda/checks/gold_fact_transactions.yml"
      },
      "Catch": [{
        "ErrorEquals": ["States.TaskFailed"],
        "ResultPath": "$.error",
        "Next": "SendQualityAlert"
      }],
      "Next": "UpdateAPICache"
    },
    "SendQualityAlert": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:us-east-1:...:pipeline-alerts",
        "Subject": "Data Quality Check Failed",
        "Message.$": "$.error.Cause"
      },
      "End": true
    }
  }
  ```

- [ ] Deploy and test quality gates
- [ ] Verify alerts trigger on check failures

### Deliverables
- ✅ Soda Core Lambda layer
- ✅ 30+ data quality checks (YAML)
- ✅ `run_soda_checks` Lambda function
- ✅ Quality gates in all Step Functions
- ✅ SNS alerts configured

### Success Metrics
- All checks pass on current data
- Quality gates block bad data from propagating
- Alerts sent on failures within 5 minutes

---

## Week 4: API Handler Migration (Feb 3-9)

### Objectives
- Audit all API handlers (eliminate Athena usage)
- Rewrite handlers to use DuckDB
- Benchmark API latency improvements
- Deploy and test

### Tasks

#### Day 1: Audit Current Handlers
- [ ] List all API handlers using Athena:
  ```bash
  grep -r "athena" api/lambdas/
  ```
- [ ] Identify handlers with expensive queries (>$1/month)
- [ ] Prioritize by cost savings potential

#### Day 2-4: Rewrite Handlers

**Pattern**: Connection pooling for warm Lambda reuse

**Example: `api/lambdas/get_member_trades/handler.py`**
```python
import duckdb
import json
import os

# Global connection (reused across warm invocations)
_conn = None

def get_connection():
    """Get or create DuckDB connection (connection pooling)."""
    global _conn
    if _conn is None:
        _conn = duckdb.connect(':memory:')
        _conn.execute("INSTALL httpfs; LOAD httpfs;")
        _conn.execute(f"SET s3_region='{os.environ['AWS_REGION']}';")
    return _conn

def handler(event, context):
    """GET /v1/members/{bioguide_id}/trades"""
    bioguide_id = event['pathParameters']['bioguide_id']
    query_params = event.get('queryStringParameters') or {}
    limit = min(int(query_params.get('limit', 100)), 500)

    conn = get_connection()

    # Query Gold Parquet directly (predicate pushdown to S3)
    result = conn.execute(f"""
        SELECT
            t.transaction_date,
            t.ticker,
            t.asset_name,
            t.transaction_type,
            t.amount_low,
            t.amount_high,
            t.amount_midpoint,
            m.full_name,
            m.party,
            m.state
        FROM 's3://{os.environ['S3_BUCKET_NAME']}/gold/facts/fact_ptr_transactions/*.parquet' t
        JOIN 's3://{os.environ['S3_BUCKET_NAME']}/gold/dimensions/dim_member/*.parquet' m
            ON t.bioguide_id = m.bioguide_id
        WHERE t.bioguide_id = ?
        ORDER BY t.transaction_date DESC
        LIMIT ?
    """, [bioguide_id, limit]).fetchdf()

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'public, max-age=3600'
        },
        'body': json.dumps({
            'bioguide_id': bioguide_id,
            'trades': result.to_dict('records')
        }, default=str)
    }
```

**Handlers to rewrite** (~12 total):
- `get_member_trades`
- `get_trending_stocks`
- `get_top_traders`
- `get_recent_transactions`
- `get_bill_trades`
- `get_network_graph`
- `get_member_stats`
- `get_analytics_dashboard`
- Others...

#### Day 5: Benchmarking
- [ ] Test API latency (cold start + warm invocation)
  - Athena (baseline): ~2-5s
  - DuckDB (target): <500ms warm, <2s cold

- [ ] Test query correctness (same results as Athena)

- [ ] Measure cost savings
  - Athena: $5/TB scanned (~$50/month)
  - DuckDB: $0 (Lambda execution only)

#### Day 6-7: Deployment
- [ ] Deploy updated handlers: `terraform apply`
- [ ] Update API Gateway routes
- [ ] Test all endpoints end-to-end
- [ ] Monitor CloudWatch Logs for errors

### Deliverables
- ✅ 12+ API handlers rewritten with DuckDB
- ✅ Connection pooling implemented
- ✅ Performance benchmarks
- ✅ Deployed to production

### Success Metrics
- API latency <500ms (warm)
- Zero Athena queries (cost = $0)
- All endpoints return correct data
- No regressions in functionality

---

## Week 5-6: Parallel Validation (Feb 10-23)

### Objectives
- Run old and new pipelines in parallel
- Compare outputs (row counts, checksums, sample data)
- Fix discrepancies
- Build confidence for cutover

### Tasks

#### Week 5: Automated Validation

**Create `scripts/validation/compare_pipelines.py`**:
```python
import duckdb
import pandas as pd

def validate_table(table_name, old_path, new_path):
    """Compare old and new table outputs."""
    conn = duckdb.connect(':memory:')
    conn.execute("INSTALL httpfs; LOAD httpfs;")

    # Row counts
    old_count = conn.execute(f"SELECT COUNT(*) FROM '{old_path}'").fetchone()[0]
    new_count = conn.execute(f"SELECT COUNT(*) FROM '{new_path}'").fetchone()[0]

    print(f"{table_name}: Old={old_count}, New={new_count}, Diff={new_count - old_count}")

    # Sample comparison
    old_sample = conn.execute(f"SELECT * FROM '{old_path}' LIMIT 100").fetchdf()
    new_sample = conn.execute(f"SELECT * FROM '{new_path}' LIMIT 100").fetchdf()

    # Compare schemas
    assert old_sample.columns.tolist() == new_sample.columns.tolist(), "Schema mismatch"

    # Compare values (fuzzy match for floating point)
    for col in old_sample.columns:
        if old_sample[col].dtype in ['float64', 'float32']:
            assert old_sample[col].sub(new_sample[col]).abs().max() < 0.01, f"Values differ in {col}"
        else:
            assert old_sample[col].equals(new_sample[col]), f"Values differ in {col}"

    print(f"✅ {table_name} validation passed")

# Run for all Gold tables
validate_table('fact_ptr_transactions',
               's3://.../gold_old/facts/fact_ptr_transactions/*.parquet',
               's3://.../gold/facts/fact_ptr_transactions/*.parquet')

validate_table('dim_member',
               's3://.../gold_old/dimensions/dim_member/*.parquet',
               's3://.../gold/dimensions/dim_member/*.parquet')

# ... repeat for all tables
```

#### Week 6: Manual Review
- [ ] Spot-check data in AWS Console (S3, DynamoDB)
- [ ] Review CloudWatch metrics (pipeline duration, error rates)
- [ ] Test API responses in production
- [ ] User acceptance testing (smoke tests on website)

### Deliverables
- ✅ Automated validation scripts
- ✅ All tables validated (100% match)
- ✅ Discrepancies documented and fixed
- ✅ Sign-off for cutover

---

## Week 7: Final Cutover (Feb 24 - Mar 3)

### Objectives
- Disable old Makefile-based scripts
- Update documentation
- Remove legacy code
- Celebrate launch! 🎉

### Tasks

#### Day 1-2: Cutover Preparation
- [ ] Backup current Gold layer (S3 versioning)
- [ ] Document rollback procedure
- [ ] Create cutover checklist

#### Day 3: Cutover Execution
- [ ] Disable EventBridge triggers for old pipeline
- [ ] Archive old scripts: `mv scripts/old_pipeline/ archive/`
- [ ] Update Makefile: Remove old targets, add new ones
  ```makefile
  # New targets
  trigger-house-fd-pipeline:
  	aws stepfunctions start-execution --state-machine-arn ...

  monitor-pipeline:
  	aws stepfunctions list-executions --state-machine-arn ...

  check-quality:
  	aws lambda invoke --function-name run-soda-checks ...
  ```

#### Day 4: Monitoring
- [ ] Monitor Step Functions for 48 hours
- [ ] Check SNS alerts (should be none)
- [ ] Verify API responses
- [ ] Monitor costs (should be near $0)

#### Day 5: Documentation
- [ ] Update `README.md` with new pipeline instructions
- [ ] Update `docs/DEPLOYMENT.md`
- [ ] Create runbook: `docs/RUNBOOK.md` (troubleshooting, common issues)
- [ ] Record demo video (optional)

#### Day 6-7: Cleanup & Celebration
- [ ] Delete old Lambda functions: `terraform destroy -target=...`
- [ ] Archive old Terraform modules
- [ ] Team retrospective (what went well, what to improve)
- [ ] Celebrate! 🎉

### Deliverables
- ✅ Old pipeline decommissioned
- ✅ New pipeline running in production
- ✅ Documentation updated
- ✅ Cost savings verified ($51/month)
- ✅ Team trained on new system

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| DuckDB performance worse than expected | Low | High | Benchmark early (Week 2), fallback to Athena if needed |
| Data quality checks too strict | Medium | Medium | Start with warnings, tune thresholds based on data |
| Step Functions complexity | Medium | Medium | Start simple, add complexity iteratively |
| Migration takes longer than 7 weeks | Medium | Low | Buffer time in Weeks 5-6, can extend if needed |
| Cost overruns | Low | High | Monitor daily, set CloudWatch billing alarms |
| Cutover issues | Low | High | Parallel validation (Weeks 5-6), rollback plan |

---

## Success Criteria

- ✅ **Cost Savings**: Reduce monthly cost from $51 to <$1
- ✅ **Automation**: Zero manual intervention for pipeline execution
- ✅ **Data Quality**: 100% of quality checks passing
- ✅ **Performance**: API latency <500ms (warm), <2s (cold)
- ✅ **Reliability**: 99%+ pipeline success rate
- ✅ **Scalability**: Can handle 10x data volume within free tier
- ✅ **Documentation**: Complete runbooks and architecture docs

---

## Post-Migration (Phase 2)

**Month 2** (March):
- Apache Iceberg migration (ACID transactions, time travel)
- Social media ingestion (Twitter/X API)
- Real-time updates (Kinesis Data Streams)

**Month 3** (April):
- Machine learning (trade prediction models)
- Advanced analytics (sentiment analysis, anomaly detection)
- Data marketplace (OpenAPI monetization)

**Month 6** (July):
- Multi-region replication (DR)
- Performance tuning (sub-100ms API latency)
- Scale to 100x data volume

---

## Appendix

### Terraform Modules
- `infra/terraform/step_functions.tf` - Orchestration
- `infra/terraform/dynamodb.tf` - Watermarks
- `infra/terraform/lambdas_gold.tf` - Transformations
- `infra/terraform/cloudwatch.tf` - Monitoring
- `infra/terraform/sns.tf` - Alerts

### Lambda Functions (New)
- `check_house_fd_updates` - Check for new filings
- `build_fact_transactions_duckdb` - Incremental transform
- `build_dim_members_duckdb` - SCD Type 2
- `compute_trending_stocks_duckdb` - Aggregations
- `run_soda_checks` - Data quality validation
- `update_api_cache` - Pre-compute JSON responses

### Key Documentation
- `docs/MEDALLION_ARCHITECTURE.md` - Complete architecture
- `docs/MIGRATION_PLAN.md` - This document
- `docs/RUNBOOK.md` - Operations guide
- `docs/BENCHMARKS.md` - Performance results

### Contacts
- **Project Lead**: Jake
- **AWS Support**: [AWS Support Portal](https://console.aws.amazon.com/support/)
- **Soda Core Docs**: https://docs.soda.io/
- **DuckDB Docs**: https://duckdb.org/docs/
