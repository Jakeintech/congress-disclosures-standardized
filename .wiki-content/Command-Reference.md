# Command Reference

Complete reference for all Make commands and scripts in the Congress Financial Disclosures pipeline.

## Table of Contents
- [Setup & Installation](#setup--installation)
- [Terraform Commands](#terraform-commands)
- [Lambda Packaging](#lambda-packaging)
- [Data Operations](#data-operations)
- [Monitoring](#monitoring)
- [Testing](#testing)
- [Website](#website)
- [Utilities](#utilities)

---

## Setup & Installation

### `make setup`
Initial setup - creates .env file, installs dependencies

```bash
make setup
```

### `make install`
Install Python dependencies

```bash
make install
```

### `make install-dev`
Install development tools (black, flake8, pytest)

```bash
make install-dev
```

---

## Terraform Commands

### `make init`
Initialize Terraform

```bash
make init
```

### `make plan`
Show infrastructure changes (dry run)

```bash
make plan
```

### `make deploy`
Deploy infrastructure (interactive, asks for confirmation)

```bash
make deploy
```

### `make deploy-auto`
Deploy without confirmation (for CI/CD)

```bash
make deploy-auto
```

### `make output`
Show Terraform outputs (bucket name, Lambda ARNs, etc.)

```bash
make output
```

---

## Lambda Packaging

### `make package-all`
Package all Lambda functions

```bash
make package-all
```

### `make package-ingest`
Package ingestion Lambda only

```bash
make package-ingest
```

### `make package-extract`
Package extraction Lambda only

```bash
make package-extract
```

### `make package-extract-structured`
Package structured extraction Lambda only

```bash
make package-extract-structured
```

### `make quick-deploy-extract`
Package and deploy extraction Lambda directly (bypasses Terraform)

```bash
make quick-deploy-extract
```

### `make quick-deploy-ingest`
Package and deploy ingestion Lambda directly

```bash
make quick-deploy-ingest
```

### `make deploy-extractors`
Package and deploy structured extraction via Terraform

```bash
make deploy-extractors
```

---

## Data Operations

### Ingestion

#### `make ingest-year YEAR=2025`
Ingest specific year

```bash
make ingest-year YEAR=2025
```

#### `make ingest-current`
Ingest current year

```bash
make ingest-current
```

### Pipeline Orchestration

#### `make run-pipeline`
Run smart pipeline (interactive mode selection)

```bash
make run-pipeline
```

Modes:
- **full**: Purge queue → Ingest (overwrite) → Wait → Aggregate
- **incremental**: Ingest (skip existing) → Wait → Aggregate
- **reprocess**: Re-trigger index-to-silver → Wait → Aggregate
- **aggregate**: Skip ingestion, just run Gold scripts

#### `make pipeline`
Alias for `make run-pipeline`

```bash
make pipeline
```

### Re-processing

#### `make run-silver-pipeline`
Re-extract all Bronze PDFs (full reprocess)

```bash
make run-silver-pipeline
```

#### `make run-silver-test`
Test re-extraction (10 PDFs only)

```bash
make run-silver-test
```

### Aggregation

#### `make aggregate-data`
Generate Gold layer aggregates

```bash
make aggregate-data
```

### Full Reset

#### `make reset-and-run-all`
Nuclear option: Deploy infra → Wipe data → Ingest → Aggregate → Deploy website

```bash
make reset-and-run-all
```

**Warning**: This deletes all data!

---

## Monitoring

### Queue Management

#### `make check-extraction-queue`
Check SQS extraction queue status

```bash
make check-extraction-queue
```

Output:
```
Messages in queue: 156
Messages in flight: 10
Messages delayed: 0
```

#### `make purge-extraction-queue`
Clear all messages from extraction queue

```bash
make purge-extraction-queue
```

**Warning**: This deletes all queued messages. Interactive confirmation required.

#### `make check-dlq`
Check dead letter queue

```bash
make check-dlq
```

#### `make purge-dlq`
Clear DLQ

```bash
make purge-dlq
```

### Logs

#### `make logs-ingest`
Tail ingest Lambda logs

```bash
make logs-ingest
```

#### `make logs-extract`
Tail extract Lambda logs

```bash
make logs-extract
```

#### `make logs-extract-recent`
Show recent extract logs (errors + successes)

```bash
make logs-extract-recent
```

---

## Testing

### `make test`
Run all tests

```bash
make test
```

### `make test-unit`
Run unit tests only

```bash
make test-unit
```

### `make test-integration`
Run integration tests (requires AWS)

```bash
make test-integration
```

### `make test-cov`
Run tests with coverage report

```bash
make test-cov
```

### Quality Checks

#### `make lint`
Run flake8 linting

```bash
make lint
```

#### `make format`
Format code with black

```bash
make format
```

#### `make format-check`
Check formatting without modifying files

```bash
make format-check
```

#### `make type-check`
Run mypy type checking

```bash
make type-check
```

#### `make check-all`
Run all checks (format, lint, type, test)

```bash
make check-all
```

#### `make check-contrib`
Quick check before PR (format-check, lint, test-unit)

```bash
make check-contrib
```

---

## Website

### `make deploy-website`
Regenerate analytics and deploy website to S3

```bash
make deploy-website
```

### `make update-pipeline-status`
Generate pipeline status JSON

```bash
make update-pipeline-status
```

### `make upload-pipeline-status`
Upload status to S3

```bash
make upload-pipeline-status
```

---

## Utilities

### `make verify-aws`
Verify AWS credentials

```bash
make verify-aws
```

Output:
```
{
    "UserId": "AIDAI...",
    "Account": "464813693153",
    "Arn": "arn:aws:iam::464813693153:user/terraform-deploy"
}
```

### `make validate-pipeline`
Validate pipeline integrity

```bash
make validate-pipeline
```

### `make test-extractions`
Test extraction results by filing type

```bash
make test-extractions
```

### `make clean`
Clean temp files and caches

```bash
make clean
```

### `make clean-packages`
Clean Lambda package directories

```bash
make clean-packages
```

---

## Script Reference

### `scripts/run_smart_pipeline.py`

Master orchestrator for pipeline execution.

**Usage**:
```bash
python3 scripts/run_smart_pipeline.py --mode MODE --year YEAR
```

**Modes**:
- `full`: Full reset and re-ingest
- `incremental`: Incremental update
- `reprocess`: Re-process existing data
- `aggregate`: Run Gold scripts only

**Examples**:
```bash
# Full pipeline for 2025
python3 scripts/run_smart_pipeline.py --mode full --year 2025

# Incremental update (current year)
python3 scripts/run_smart_pipeline.py --mode incremental

# Just rebuild aggregates
python3 scripts/run_smart_pipeline.py --mode aggregate
```

### Common Scripts

**Bronze Layer**:
- `scripts/build_bronze_manifest.py` - Generate Bronze manifest

**Silver Aggregation**:
- `scripts/generate_type_p_transactions.py` - Aggregate PTR transactions
- `scripts/generate_type_a_assets.py` - Aggregate annual report assets
- `scripts/generate_type_t_terminations.py` - Aggregate terminations
- `scripts/rebuild_silver_manifest.py` - Rebuild Silver manifest

**Gold Layer**:
- `scripts/build_dim_members_simple.py` - Build members dimension
- `scripts/build_fact_filings.py` - Build filings fact table
- `scripts/build_fact_ptr_transactions.py` - Build transactions fact

**Aggregates**:
- `scripts/compute_agg_document_quality.py` - Document quality scores
- `scripts/compute_agg_member_trading_stats.py` - Member trading stats
- `scripts/compute_agg_trending_stocks.py` - Trending stocks analysis
- `scripts/compute_agg_network_graph.py` - Network analysis

**Utilities**:
- `scripts/validate_pipeline_integrity.py` - Validate data integrity
- `scripts/generate_pipeline_errors.py` - Generate error report
- `scripts/sync_terraform_outputs.sh` - Sync outputs to .env
- `scripts/sync-api-url.sh` - Sync API URL to website

---

## See Also

- [[Quick-Start-Guide]] - Getting started
- [[Development-Setup]] - Local development
- [[Running-Pipelines]] - Pipeline execution guide
- [[Troubleshooting]] - Common issues

---

**Tip**: Run `make help` to see all available commands with descriptions.
