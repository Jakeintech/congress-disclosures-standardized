# Architecture Decision Record (ADR)

**Project**: Congress Disclosures Standardized Data Platform
**Last Updated**: 2025-12-14
**Status**: Living Document

---

## Table of Contents

1. [ADR-001: Adopt AWS Step Functions for Pipeline Orchestration](#adr-001)
2. [ADR-002: Unified Pipeline vs Siloed Pipelines](#adr-002)
3. [ADR-003: Bronze-Silver-Gold Medallion Architecture](#adr-003)
4. [ADR-004: Lambda Functions vs Script-Based Processing](#adr-004)
5. [ADR-005: Parquet + S3 vs Managed Database](#adr-005)
6. [ADR-006: Code-Based Extraction vs AWS Textract](#adr-006)
7. [ADR-007: SQS Queue-Based vs Direct Lambda Invocation](#adr-007)
8. [ADR-008: Cost Optimization - Free Tier First](#adr-008)
9. [ADR-009: Incremental Processing with Watermarking](#adr-009)
10. [ADR-010: Testing Strategy - Unit + Integration + E2E](#adr-010)

---

<a name="adr-001"></a>
## ADR-001: Adopt AWS Step Functions for Pipeline Orchestration

**Date**: 2025-12-14
**Status**: ✅ Accepted
**Decision Makers**: Engineering Team
**Context**: Previous orchestration via Python scripts + GitHub Actions

### Context

The existing system used Python scripts (`run_smart_pipeline.py`) for orchestration, which led to:
- ❌ No visual workflow representation
- ❌ Manual error handling in every script
- ❌ Difficult to track execution state
- ❌ No built-in retry logic
- ❌ Hard to debug failures

### Decision

**Adopt AWS Step Functions** as the primary orchestration engine for all data pipelines.

### Rationale

**Pros**:
- ✅ Visual workflow in AWS Console (easy debugging)
- ✅ Built-in error handling and retry logic
- ✅ State persistence (can resume after failures)
- ✅ CloudWatch integration (automatic logging)
- ✅ Support for parallel execution (Map states)
- ✅ Standard timeout and error catching
- ✅ X-Ray tracing for performance analysis
- ✅ Free tier: 4,000 state transitions/month

**Cons**:
- ❌ Additional AWS service dependency
- ❌ JSON-based state machine definitions (verbose)
- ❌ Requires Terraform to deploy
- ❌ More complex local testing

### Alternatives Considered

1. **Keep Python Script Orchestration**
   - Pro: Simpler, works today
   - Con: No scalability, manual error handling
   - **Rejected**: Not production-ready

2. **Apache Airflow (MWAA)**
   - Pro: Industry standard, powerful DAGs
   - Con: Minimum cost $300/month
   - **Rejected**: Exceeds budget

3. **AWS Glue Workflows**
   - Pro: Designed for ETL
   - Con: Expensive, less flexible
   - **Rejected**: Cost and flexibility

### Implementation

- Single unified state machine: `congress_data_platform.json`
- Replaces 4 separate siloed pipelines
- Terraform manages state machine deployment
- GitHub Actions triggers via `aws stepfunctions start-execution`

### Consequences

**Positive**:
- Reliable orchestration with built-in error handling
- Visual debugging capabilities
- Scalable to handle complex workflows

**Negative**:
- Team must learn Step Functions JSON syntax
- Local testing requires SAM or Step Functions Local

**Migration Path**:
- Phase 1: Keep existing Python scripts as Lambda wrappers
- Phase 2: Gradually replace with native Step Functions logic

### Success Metrics

- [ ] Pipeline executes end-to-end without manual intervention
- [ ] Error rate < 1% with automatic retries
- [ ] Execution time < 2 hours for full refresh
- [ ] Cost < $1/month for Step Functions (within free tier)

---

<a name="adr-002"></a>
## ADR-002: Unified Pipeline vs Siloed Pipelines

**Date**: 2025-12-14
**Status**: ✅ Accepted
**Context**: System previously had 4 separate pipelines

### Context

Previous architecture:
- `house_fd_pipeline.json` - House financial disclosures
- `congress_pipeline.json` - Congress.gov bills/members
- `lobbying_pipeline.json` - LDA lobbying data
- `cross_dataset_correlation.json` - Analytics

Issues:
- ❌ No dependency tracking between pipelines
- ❌ Race conditions when pipelines run concurrently
- ❌ Duplicate Gold layer processing
- ❌ Inconsistent data lineage

### Decision

**Create a single unified `congress_data_platform` pipeline** with phases:
1. Phase 1: Bronze Ingestion (parallel across all sources)
2. Phase 2: Silver Transformation (parallel per source)
3. Phase 3: Gold Aggregation (sequential, dependency-aware)
4. Phase 4: Quality & Publish (final validation)

### Rationale

**Single Pipeline Pros**:
- ✅ Clear dependency management
- ✅ Single entry point for execution
- ✅ Consistent error handling
- ✅ Unified monitoring and alerting
- ✅ Better data lineage tracking
- ✅ Prevents duplicate Gold processing

**Siloed Pipelines Pros**:
- ✅ Independent execution per data source
- ✅ Easier to understand (smaller chunks)
- ✅ Failure isolation

### Decision: **Unified Pipeline with Phased Execution**

### Implementation

```
┌─────────────────────────────────────┐
│  Congress Data Platform Pipeline   │
└─────────────────────────────────────┘
           │
    ┌──────┴───────┬────────────┐
    │              │            │
┌───▼───┐     ┌───▼───┐    ┌──▼───┐
│ House │     │Congress│    │ LDA  │
│  FD   │     │.gov    │    │Lobby │
└───┬───┘     └───┬───┘    └──┬───┘
    │              │            │
    └──────┬───────┴────────────┘
           │
      ┌────▼────┐
      │  Gold   │
      │  Layer  │
      └────┬────┘
           │
      ┌────▼────┐
      │ Quality │
      │  & API  │
      └─────────┘
```

### Consequences

**Positive**:
- Data consistency across all layers
- Clear execution order
- Single monitoring dashboard

**Negative**:
- More complex state machine JSON
- All-or-nothing execution (can't run just one source)

**Mitigation**:
- Add input parameters to enable/disable specific sources
- Implement conditional execution based on update detection

### Success Metrics

- [ ] Single execution completes all data sources
- [ ] Gold layer processes only once per run
- [ ] No race conditions or deadlocks
- [ ] Execution time < 2 hours

---

<a name="adr-003"></a>
## ADR-003: Bronze-Silver-Gold Medallion Architecture

**Date**: 2025-12-14
**Status**: ✅ Accepted (Already Implemented)
**Context**: Industry standard data lake pattern

### Decision

Maintain existing **medallion architecture** with three layers:

**Bronze (Raw/Immutable)**:
- Byte-for-byte preservation of source data
- S3: `s3://bucket/bronze/`
- No transformations
- Append-only (never delete)

**Silver (Normalized/Queryable)**:
- Extracted and structured data
- S3 Parquet tables + gzipped text
- Schema validation
- Idempotent upserts

**Gold (Query-Facing/Aggregated)**:
- Fact tables and dimensions
- Pre-computed aggregates
- Star schema design
- Optimized for API queries

### Rationale

✅ **Separation of Concerns**: Each layer has single responsibility
✅ **Data Lineage**: Can trace any Gold value back to Bronze source
✅ **Reprocessing**: Can rebuild Silver/Gold from Bronze without re-ingestion
✅ **Cost Optimization**: Store raw data cheaply, aggregate expensively
✅ **Industry Standard**: Databricks, AWS Lake Formation use this pattern

### Success Metrics

- [ ] Bronze contains 100% of source data
- [ ] Silver transformations are idempotent
- [ ] Gold can be rebuilt from Silver without data loss

---

<a name="adr-004"></a>
## ADR-004: Lambda Functions vs Script-Based Processing

**Date**: 2025-12-14
**Status**: ✅ Accepted (In Progress)
**Context**: Migration from scripts to Lambda-based architecture

### Context

**Current State**: Python scripts in `scripts/` directory
**Problem**: Scripts can't be invoked by Step Functions

### Decision

**Wrap all Gold layer scripts as Lambda functions** while keeping scripts for local development.

### Implementation Pattern

```python
# Lambda handler (new)
def lambda_handler(event, context):
    """Lambda wrapper for build_dim_members script."""
    from scripts import build_dim_members_simple

    result = build_dim_members_simple.main(
        bucket=event['bucket'],
        year=event.get('year')
    )

    return {
        'statusCode': 200,
        'body': result
    }

# Script (existing - keep for local dev)
if __name__ == '__main__':
    main()
```

### Benefits

- ✅ Scripts still runnable locally (`python scripts/build_dim_members_simple.py`)
- ✅ Lambda functions can be invoked by Step Functions
- ✅ Separation of business logic (script) from infrastructure (Lambda)
- ✅ Easy to test: test scripts, not Lambda wrappers

### Success Metrics

- [ ] All 47 Lambda functions created
- [ ] Scripts still work in local environment
- [ ] Step Functions can invoke all Lambdas

---

<a name="adr-005"></a>
## ADR-005: Parquet + S3 vs Managed Database

**Date**: 2025-12-14
**Status**: ✅ Accepted (Already Implemented)
**Context**: Cost optimization for data storage

### Decision

**Use Parquet files in S3** instead of RDS/DynamoDB/Athena for Gold layer storage.

### Rationale

**Cost Comparison** (for 100GB of data):

| Solution | Monthly Cost | Query Speed |
|----------|--------------|-------------|
| **Parquet + S3** | **$2.30** | Medium (download + parse) |
| RDS PostgreSQL | $200+ | Fast (indexed queries) |
| DynamoDB | $50+ | Fast (key-value) |
| Athena | $5 + S3 | Fast (serverless SQL) |

**Decision**: Parquet + S3
- ✅ 100x cheaper than RDS
- ✅ No database size limits
- ✅ Optimized for analytical queries (columnar format)
- ✅ Easy to version (immutable files)
- ⚠️ Slower queries (no indexes)

### Trade-offs Accepted

- **Latency**: Queries take 1-5 seconds vs <100ms in database
- **Concurrency**: No connection pooling
- **Tooling**: Custom code vs SQL

### Mitigation

- Pre-aggregate common queries in Gold layer
- Use API Gateway caching (5 minutes)
- Partition Parquet files by year/month for faster scans

### Success Metrics

- [ ] Storage cost < $5/month
- [ ] API response time < 5 seconds (p99)
- [ ] Zero database management overhead

---

<a name="adr-006"></a>
## ADR-006: Code-Based Extraction vs AWS Textract

**Date**: 2025-12-14
**Status**: ✅ Accepted (Already Implemented)
**Context**: PDF text extraction approach

### Decision

**Use code-based extraction** (pypdf + Tesseract OCR) instead of AWS Textract.

### Cost Analysis

**Processing 50,000 PDFs/year**:

| Solution | Cost per Page | Annual Cost |
|----------|--------------|-------------|
| **pypdf + Tesseract** | **$0.00** | **$0** (compute only) |
| AWS Textract | $1.50/1,000 | $7,500 |

**Lambda Compute Cost**:
- 50,000 PDFs × 30s avg × 1GB memory = 1.5M GB-seconds
- Cost: $25/month (or free with 400K free tier GB-seconds)

### Trade-offs

**Code-Based**:
- ✅ Free (except Lambda compute)
- ⚠️ Lower accuracy on complex layouts (~85% vs 95%)
- ⚠️ Slower processing (30s vs 5s per page)

**Textract**:
- ❌ Expensive ($7,500/year)
- ✅ Higher accuracy (95%+)
- ✅ Faster processing

### Decision Justification

For this project:
- **Most PDFs are simple forms** (not complex layouts)
- **Acceptable accuracy**: 85% is sufficient for trend analysis
- **Budget constraint**: $5-20/month total

### Fallback Plan

If accuracy becomes an issue:
1. Use Textract only for "problem PDFs" flagged by quality checks
2. Estimated cost: $200/year (95% code-based, 5% Textract)

### Success Metrics

- [ ] Extraction accuracy ≥ 80% (validated by Soda checks)
- [ ] Extraction cost < $30/month
- [ ] All PDFs processed within 24 hours

---

<a name="adr-007"></a>
## ADR-007: SQS Queue-Based vs Direct Lambda Invocation

**Date**: 2025-12-14
**Status**: ✅ Accepted (Already Implemented)
**Context**: How to distribute PDF extraction workload

### Decision

**Use SQS queues** for asynchronous PDF extraction instead of direct Lambda invocation from Step Functions Map state.

### Architecture

```
Step Function                SQS Queue              Lambda (10 concurrent)
     │                           │                         │
     ├─ Send 5,000 messages ────→│                         │
     │                           ├─ Message 1 ────────────→│
     │                           ├─ Message 2 ────────────→│
     │                           ├─ Message 3 ────────────→│
     │                           │         ...              │
     └─ Poll until empty ←───────┴─────────────────────────┘
```

### Rationale

**SQS Pros**:
- ✅ Automatic retry on failure
- ✅ Dead letter queue for poison messages
- ✅ Visibility timeout prevents duplicate processing
- ✅ No Step Functions timeout issues (Map state limited to 15 min per item)
- ✅ Cost: $0.40/million messages (5K messages = $0.002)

**Direct Invocation Pros**:
- ✅ Simpler (no queue management)
- ✅ Real-time tracking in Step Functions
- ❌ Timeout issues for slow PDFs
- ❌ No automatic retry

### Implementation

1. Step Function sends messages to SQS
2. Lambda triggered by SQS (batch size: 10)
3. Partial batch failure handling (return failed message IDs)
4. Step Function polls queue until empty

### Success Metrics

- [ ] Queue depth returns to 0 within 4 hours
- [ ] Failed messages go to DLQ (not lost)
- [ ] No duplicate processing (idempotency)

---

<a name="adr-008"></a>
## ADR-008: Cost Optimization - Free Tier First

**Date**: 2025-12-14
**Status**: ✅ Accepted
**Context**: Budget constraint of $5-20/month

### Decision

**Design all architecture choices to maximize AWS free tier usage.**

### Free Tier Limits (Perpetual)

| Service | Free Tier | Our Usage | Cost |
|---------|-----------|-----------|------|
| Lambda Requests | 1M/month | ~500K | $0 |
| Lambda Duration | 400K GB-sec | ~300K | $0 |
| S3 Storage | 5GB | 100GB | $2.18 |
| S3 GET Requests | 2,000/month | 50K | $0.20 |
| S3 PUT Requests | 20,000/month | 10K | $0.05 |
| Step Functions | 4,000 transitions | 2,000 | $0 |
| CloudWatch Logs | 5GB | 3GB | $0 |
| SQS Requests | 1M/month | 100K | $0 |

**Total Estimated**: $2.43/month (within free tier + minimal overage)

### Cost Optimization Strategies

1. **Lambda**:
   - Right-size memory (128MB-1GB)
   - Avoid provisioned concurrency
   - Use ARM architecture (Graviton2) - 20% cheaper

2. **S3**:
   - Lifecycle policy: Delete logs after 7 days
   - Intelligent-Tiering for infrequent data
   - Compress all JSON/text files (gzip)

3. **CloudWatch**:
   - Log retention: 7 days (not 30)
   - Sample logs (not every execution)
   - Use INFO level (not DEBUG)

4. **Step Functions**:
   - Minimize state transitions (combine steps where possible)
   - Use Express Workflows for high-volume (cheaper)

### Success Metrics

- [ ] Monthly cost < $20 (95% of months)
- [ ] Monthly cost < $10 (target average)
- [ ] No cost surprises (CloudWatch alarms at $15)

---

<a name="adr-009"></a>
## ADR-009: Incremental Processing with Watermarking

**Date**: 2025-12-14
**Status**: ⚠️ In Progress (Needs Implementation)
**Context**: Prevent duplicate processing on every run

### Problem

Current `check_house_fd_updates` Lambda always returns `has_new_filings: true`, causing:
- ❌ Reprocessing same data every execution
- ❌ Wasted Lambda invocations
- ❌ Increased S3 costs
- ❌ Slower pipeline execution

### Decision

**Implement watermarking** using S3 object metadata and SHA256 checksums.

### Implementation

**Bronze Watermark**:
```python
# Check if zip already ingested
s3_key = f"bronze/house/financial/year={year}/raw_zip/{year}FD.zip"
try:
    head = s3.head_object(Bucket=bucket, Key=s3_key)
    existing_sha = head['Metadata'].get('sha256')

    # Download only if different
    new_sha = calculate_sha256(url)
    if existing_sha == new_sha:
        return {'has_new_filings': False}
except ClientError:
    # Object doesn't exist, download it
    pass
```

**Silver Watermark**:
```python
# Check if PDF already extracted
pdf_key = f"bronze/.../pdfs/{doc_id}.pdf"
head = s3.head_object(Bucket=bucket, Key=pdf_key)
if head['Metadata'].get('extraction-processed') == 'true':
    return "skipped"
```

**Gold Watermark**:
- Check Silver manifest last_updated timestamp
- Only rebuild Gold if Silver changed

### Success Metrics

- [ ] Incremental runs only process new data
- [ ] Full refresh still processes all data (override parameter)
- [ ] Execution time: 10 minutes (incremental) vs 2 hours (full)

---

<a name="adr-010"></a>
## ADR-010: Testing Strategy - Unit + Integration + E2E

**Date**: 2025-12-14
**Status**: ⚠️ In Progress
**Context**: Insufficient test coverage (15%)

### Decision

**Implement comprehensive testing** with 80% coverage target.

### Testing Pyramid

```
        ╱╲
       ╱E2E╲          10% - Playwright API/website tests
      ╱─────╲
     ╱ Integ ╲        20% - State machine + AWS integration
    ╱─────────╲
   ╱   Unit    ╲      70% - Lambda functions + libraries
  ╱─────────────╲
```

### Test Coverage by Component

| Component | Unit Tests | Integration Tests | E2E Tests |
|-----------|-----------|------------------|-----------|
| Lambda Functions | ✅ Required | ✅ Required | ⚠️ Smoke only |
| State Machines | N/A | ✅ Required | ✅ Full flow |
| Extractors | ✅ Required | ⚠️ Sample PDFs | N/A |
| API | ✅ Logic | ✅ Endpoints | ✅ User flows |

### Success Metrics

- [ ] Overall coverage ≥ 80%
- [ ] All Lambda functions have unit tests
- [ ] At least one E2E test for full pipeline
- [ ] CI fails if coverage drops below 75%

---

## ADR Template

**Use this template for future decisions**:

```markdown
## ADR-XXX: [Decision Title]

**Date**: YYYY-MM-DD
**Status**: [Proposed | Accepted | Rejected | Deprecated]
**Context**: [What problem are we solving?]

### Context
[Detailed background, constraints, requirements]

### Decision
[What we decided to do]

### Rationale
**Pros**:
- Pro 1
- Pro 2

**Cons**:
- Con 1
- Con 2

### Alternatives Considered
1. **Option 1**: [Description] - [Why rejected]
2. **Option 2**: [Description] - [Why rejected]

### Implementation
[How to implement this decision]

### Consequences
**Positive**: [Benefits]
**Negative**: [Costs/trade-offs]

### Success Metrics
- [ ] Metric 1
- [ ] Metric 2
```

---

## Decision Log

| ADR | Date | Status | Impact |
|-----|------|--------|--------|
| ADR-001 | 2025-12-14 | ✅ Accepted | High - Foundation |
| ADR-002 | 2025-12-14 | ✅ Accepted | High - Architecture |
| ADR-003 | 2025-12-14 | ✅ Accepted | High - Data Model |
| ADR-004 | 2025-12-14 | ⚠️ In Progress | High - Implementation |
| ADR-005 | 2025-12-14 | ✅ Accepted | Medium - Cost |
| ADR-006 | 2025-12-14 | ✅ Accepted | Medium - Cost |
| ADR-007 | 2025-12-14 | ✅ Accepted | Medium - Reliability |
| ADR-008 | 2025-12-14 | ✅ Accepted | High - Budget |
| ADR-009 | 2025-12-14 | ⚠️ In Progress | High - Performance |
| ADR-010 | 2025-12-14 | ⚠️ In Progress | High - Quality |

---

**Document Owner**: Engineering Team
**Review Cycle**: Monthly (or when new decisions needed)
**Approval Process**: Team consensus + tech lead sign-off
