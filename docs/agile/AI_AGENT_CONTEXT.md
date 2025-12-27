# AI Agent Master Context - Congress Disclosures Project

**Purpose**: This document provides complete project context for AI agents. Copy this entire document as context when starting work on any story.

**Last Updated**: 2025-12-26
**Epic**: EPIC-001 Unified Data Platform Migration
**Current Sprint**: Sprint 3 (Dec 27, 2025 - Jan 3, 2026)

---

## 🎯 Project Overview

### What This Project Does

The **Congress Disclosures Standardized** project is a serverless data pipeline that:
1. Ingests US Congress financial disclosures (15+ years of PDFs)
2. Extracts structured transaction data using code-based extraction (no AWS Textract)
3. Standardizes data into a queryable data lake (Bronze → Silver → Gold)
4. Provides analytics via REST API and web dashboard

**Tech Stack**:
- **Infrastructure**: AWS Lambda, S3, SQS, Step Functions, API Gateway, Terraform
- **Data Processing**: Python 3.11, DuckDB v1.1.3, Pandas, PyArrow
- **Frontend**: Next.js 16, TypeScript, React, shadcn/ui
- **CI/CD**: GitHub Actions, auto-deploy to main branch

### Business Value

- **Cost Savings**: $47,820/year (prevent $4K/month EventBridge runaway costs)
- **Reliability**: 99%+ success rate (vs. current ~85%)
- **Performance**: 10x faster processing (4 hours vs. 41 hours)
- **Legal Compliance**: 5 U.S.C. § 13107 (transparency, research, news purposes only)

---

## 📊 Current Project Status

### Sprint Progress

| Metric | Value |
|--------|-------|
| **Overall Progress** | 31% (51/167 points) |
| **Stories Complete** | 15/55 (27%) |
| **Current Sprint** | Sprint 3 (Week 2 of 4) |
| **Sprint Velocity** | 43 pts/sprint (from Sprint 2) |
| **Target Completion** | Jan 11, 2026 |

### Recently Completed

**Sprint 2: Gold Layer Lambdas** (Dec 16, 2025) - ✅ **COMPLETE**:
- 8 Lambda functions deployed (dimensions, facts, aggregates)
- DuckDB v1.1.3 integrated
- 2 endpoints end-to-end tested
- All analytics endpoints operational

**Phase 0: Emergency Hotfixes** (Dec 19-26, 2025) - 🔄 **85% COMPLETE**:
- ✅ Fixed Transactions page loading issues
- ✅ Upgraded DuckDB to v1.1.3 (21 failing endpoints now working)
- 🔄 Health endpoint Lambda created (API Gateway integration pending)

### Current Sprint 3 Focus

**Goal**: Integration, testing, and production readiness

**Active Work**:
- State machine orchestration
- Quality checks integration
- Contract testing
- Performance optimization
- Documentation updates

---

## 🏗️ Architecture

### Data Pipeline: Bronze → Silver → Gold

```
┌─────────────┐
│   BRONZE    │  Raw/Immutable
│  (S3 PDFs)  │  - Year-partitioned ZIPs
└─────┬───────┘  - Individual PDFs with metadata
      │
      ↓ (Extraction: pypdf + Tesseract OCR)
┌─────────────┐
│   SILVER    │  Normalized/Queryable
│  (Parquet)  │  - filings/, documents/, text/, objects/
└─────┬───────┘  - Structured JSON extractions
      │
      ↓ (Aggregation: DuckDB + Pandas)
┌─────────────┐
│    GOLD     │  Analytics-Ready
│  (Parquet)  │  - dimensions/ (SCD Type 2)
└─────────────┘  - facts/ (star schema)
                 - aggregates/ (KPIs)
```

### S3 Bucket Structure

```
s3://congress-disclosures-standardized/
├── bronze/house/financial/
│   ├── year=2025/
│   │   ├── raw_zip/2025FD.zip
│   │   ├── index/2025FD.xml
│   │   └── filing_type=P/pdfs/20026590.pdf
│   └── ...
│
├── silver/house/financial/
│   ├── filings/  (Parquet)
│   ├── documents/  (Parquet)
│   ├── text/extraction_method=direct_text/  (gzipped)
│   └── objects/filing_type=type_p/  (JSON)
│
└── gold/house/financial/
    ├── dimensions/
    │   ├── dim_members.parquet
    │   ├── dim_assets.parquet
    │   └── dim_dates.parquet
    ├── facts/
    │   ├── fact_transactions.parquet
    │   └── fact_filings.parquet
    └── aggregates/
        ├── trending_stocks.parquet
        └── member_stats.parquet
```

### Filing Types (Critical to Understand)

| Code | Type | Key Data | Extractor |
|------|------|----------|-----------|
| **P** | Periodic Transaction Report (PTR) | Stock trades | `PTRExtractor` |
| **A** | Annual Report | Assets, income | `TypeABAnnualExtractor` |
| **T** | Termination Report | Final assets | `TypeTTerminationExtractor` |
| **X** | Extension Request | Notice | `TypeXExtensionRequestExtractor` |
| **D** | Campaign Notice | Notice | `TypeDCampaignNoticeExtractor` |
| **W** | Withdrawal Notice | Notice | `TypeWWithdrawalNoticeExtractor` |

**Location**: `ingestion/lib/extractors/{type_p_ptr,type_a_b_annual,...}/extractor.py`

---

## 🧰 Technology Standards

### Code Quality

**Python Style**:
- **Formatter**: Black (88-char line length)
- **Linter**: flake8
- **Type Checker**: mypy (strict mode)
- **Import Order**: stdlib → third-party → local

**Required Commands** (must pass before PR):
```bash
black .                    # Format code
flake8 .                   # Lint
mypy .                     # Type check
pytest tests/ -v --cov     # Test with coverage ≥80%
```

**Commit Format** (Conventional Commits):
```
<type>(<scope>): <description>

Types: feat, fix, refactor, test, docs, chore, style, perf
Scopes: gold, silver, bronze, lambda, terraform, api, etc.

Example:
feat(gold): add build_fact_transactions Lambda wrapper
```

### Lambda Pattern

**Standard Handler** (`api/lambdas/[function_name]/handler.py`):
```python
import json
import logging
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    [Function description]

    Args:
        event: Lambda event (JSON)
        context: Lambda context

    Returns:
        Response dict with statusCode and body
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Validate input
        if "param1" not in event:
            raise ValueError("Missing required parameter: param1")

        # Call script
        from scripts.script_name import main
        result = main(param1=event["param1"])

        logger.info(f"Execution successful: {result}")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Success", "result": result})
        }

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}
```

### Terraform Pattern

**Lambda Resource** (`infra/terraform/api_lambdas.tf`):
```hcl
resource "aws_lambda_function" "function_name" {
  function_name = "${var.project_name}-${var.environment}-api-function_name"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_execution_role.arn

  filename         = "${path.module}/../../api/lambdas/function_name/function.zip"
  source_code_hash = filebase64sha256("${path.module}/../../api/lambdas/function_name/function.zip")

  timeout     = 300  # 5 minutes
  memory_size = 2048  # 2GB

  layers = [
    aws_lambda_layer_version.pandas_pyarrow.arn,
    aws_lambda_layer_version.duckdb.arn
  ]

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
    }
  }

  tags = merge(local.common_tags, {
    Name = "function_name"
  })
}
```

### Testing Pattern

**Unit Test** (`tests/unit/[module]/test_[feature].py`):
```python
import pytest
from unittest.mock import MagicMock, patch
from module.handler import lambda_handler

class TestLambdaHandler:
    """Test suite for Lambda handler"""

    def test_successful_execution(self):
        """Test successful execution with valid input"""
        # Arrange
        event = {"param1": "value1"}
        context = MagicMock()

        # Act
        with patch('module.handler.main') as mock_main:
            mock_main.return_value = {"rows": 100}
            response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 200
        assert "Success" in response["body"]

    def test_missing_parameter(self):
        """Test error handling for missing required parameter"""
        event = {}
        context = MagicMock()

        response = lambda_handler(event, context)

        assert response["statusCode"] == 400
        assert "Missing required parameter" in response["body"]
```

---

## 📁 Key Directories & Files

### Must Know Locations

**Agile Documentation**:
- `/docs/agile/STORY_CATALOG.md` - All 55 stories overview
- `/docs/agile/stories/active/` - Stories to work on (43 stories)
- `/docs/agile/stories/completed/` - Done stories (12 stories)
- `/docs/agile/sprints/SPRINT_03_INTEGRATION.md` - Current sprint plan
- `/docs/agile/active/CURRENT_STATUS.md` - Real-time progress

**Technical Specifications**:
- `/docs/agile/technical/ARCHITECTURE_DECISION_RECORD.md` - Design decisions (10 ADRs)
- `/docs/agile/technical/DATA_CONTRACTS.md` - Schema definitions
- `/docs/agile/technical/LAMBDA_REQUIREMENTS_SPEC.md` - All 47 Lambda functions
- `/docs/agile/technical/STATE_MACHINE_SPEC.md` - Step Functions workflows
- `/docs/agile/technical/TESTING_STRATEGY.md` - Test patterns

**Project Guides**:
- `/docs/CLAUDE.md` - **Most important** - Commands, patterns, gotchas
- `/.github/AI_AGENT_TASK_TEMPLATE.md` - Task brief template
- `/.github/AI_AGENT_WORKFLOW.md` - Collaboration protocol
- `/CONTRIBUTING.md` - Code style, commit format, PR process

**Code Organization**:
- `/api/lambdas/` - API Gateway Lambda functions (20+)
- `/ingestion/lambdas/` - Pipeline Lambda functions (25+)
- `/ingestion/lib/` - Shared libraries (extractors, utilities)
- `/scripts/` - Gold layer aggregation scripts
- `/infra/terraform/` - Infrastructure as Code
- `/tests/` - Unit and integration tests
- `/website/` - Next.js frontend

---

## ⚠️ Critical Gotchas (Common Pitfalls)

### 1. Lambda Timeout (900s maximum)
**Issue**: Large datasets can exceed 15-minute timeout
**Solution**: Process in batches, use Step Functions Map state for parallelization
**Example**: Process 1,000 rows at a time instead of all 100,000

### 2. DuckDB S3 Connection
**Issue**: DuckDB httpfs extension needs correct S3 path format
**Solution**: Use `s3://bucket/key` format, ensure IAM permissions
**Code**:
```python
import duckdb
con = duckdb.connect(":memory:")
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute("SET s3_region='us-east-1';")
df = con.execute("SELECT * FROM read_parquet('s3://bucket/path/*.parquet')").df()
```

### 3. Terraform State Lock
**Issue**: State locked from previous failed run
**Solution**: Wait 5 minutes or check DynamoDB lock table
**Command**: `terraform force-unlock [LOCK_ID]` (use with caution!)

### 4. Bronze PDF Metadata Tagging
**Issue**: Duplicate processing of expensive OCR operations
**Solution**: Always check `extraction-processed` metadata before queuing
**Code**:
```python
response = s3.head_object(Bucket=bucket, Key=pdf_key)
if response['Metadata'].get('extraction-processed') == 'true':
    return  # Already processed, skip

# After processing:
s3.copy_object(
    CopySource={'Bucket': bucket, 'Key': pdf_key},
    Bucket=bucket, Key=pdf_key,
    Metadata={'extraction-processed': 'true'},
    MetadataDirective='REPLACE'
)
```

### 5. Parquet Upsert Pattern
**Issue**: Can't directly update Parquet files (immutable)
**Solution**: Read, filter, append, write back (atomic replace)
**Code**:
```python
# 1. Read existing
existing_df = pd.read_parquet(s3_path)
# 2. Remove old records
existing_clean = existing_df[~existing_df['id'].isin(new_df['id'])]
# 3. Append new
combined = pd.concat([existing_clean, new_df])
# 4. Write back
combined.to_parquet(s3_path)
```

### 6. Test Data Isolation
**Issue**: Tests modifying shared test data
**Solution**: Use pytest fixtures with `scope="function"`
**Code**:
```python
@pytest.fixture(scope="function")
def test_data():
    """Fresh test data for each test"""
    return {"filing_id": "TEST-001", "transactions": []}
```

### 7. Environment Variables
**Issue**: Forgetting to update both `.env.example` and Terraform
**Solution**: Always update both when adding new env var
**Checklist**:
- [ ] Add to `.env.example`
- [ ] Add to Terraform `environment.variables`
- [ ] Document in CLAUDE.md if user-configurable

---

## 🚀 Common Commands (from CLAUDE.md)

### Setup
```bash
make setup          # Initial setup (creates .env, installs deps)
make install        # Install Python dependencies
make install-dev    # Install dev tools
```

### Terraform
```bash
make init           # Initialize Terraform
make plan           # Show infrastructure changes
make deploy         # Deploy infrastructure (interactive)
make deploy-auto    # Deploy without confirmation (CI)
```

### Lambda Development
```bash
make package-all              # Package all Lambdas
make package-api              # Package API Lambdas
make quick-deploy-[function]  # Package + deploy single Lambda
```

### Testing
```bash
make test                # Run all tests
make test-unit           # Unit tests only
make test-integration    # Integration tests (requires AWS)
make test-cov            # Tests with coverage report
make check-all           # Format, lint, type-check, test
```

### Code Quality
```bash
make lint            # flake8 linting
make format          # Black formatting
make format-check    # Check formatting without modifying
make type-check      # mypy type checking
```

### Pipeline Operations
```bash
make ingest-year YEAR=2025   # Ingest specific year
make run-pipeline            # Smart pipeline (interactive)
make aggregate-data          # Generate Gold layer
```

---

## 📋 Your Role as AI Agent

### What You'll Do

1. **Claim GitHub Issues**: Find unassigned stories in current sprint
2. **Read Context**: Use this document + task template + story file
3. **Implement**: Write code following patterns and standards
4. **Test**: Write tests (≥80% coverage), run quality checks
5. **Document**: Update docs, add comments for complex logic
6. **Submit PR**: Create pull request with conventional commit format
7. **Handoff**: Update issue status, unblock dependent stories

### Workflow Summary

```
1. Find Issue
   ↓
2. Read Story + Context Files
   ↓
3. Create Branch (agent/[name]/STORY-XXX-description)
   ↓
4. Implement + Test
   ↓
5. Run Quality Checks (black, flake8, mypy, pytest)
   ↓
6. Commit (conventional format)
   ↓
7. Push + Create PR
   ↓
8. Update Issue to "In Review"
```

### Success Criteria

**Your PR will be approved when**:
- ✅ All acceptance criteria from story met
- ✅ All DoD (Definition of Done) items completed
- ✅ Tests passing (≥80% coverage)
- ✅ Code quality checks passing (black, flake8, mypy)
- ✅ No merge conflicts
- ✅ Documentation updated (if needed)
- ✅ PR template checklist completed

### Token Estimation Guide

**Story Points → Token Estimate**:
- 1 point: ~10K tokens (simple Lambda wrapper, config change)
- 2 points: ~20K tokens (Lambda + tests + Terraform)
- 3 points: ~30K tokens (Complex Lambda + integration tests)
- 5 points: ~50K tokens (Multi-component feature)
- 8 points: ~80K tokens (Large refactor or architectural change)

**Optimize Tokens**:
- Read context files BEFORE coding (avoid backtracking)
- Use existing patterns (search codebase for similar code)
- Test incrementally (don't write all code then test)
- Reuse helper functions (check `ingestion/lib/`)

---

## 🆘 When You're Stuck

### Escalation Path

1. **Check dependencies**: Are prerequisites actually done?
   - View linked issues in GitHub
   - Verify PRs merged and deployed

2. **Search for patterns**: Look for similar implementations
   - `grep -r "similar_function" --include="*.py"`
   - Browse `/api/lambdas/` for similar Lambda functions
   - Check git history: `git log --grep="keyword"`

3. **Read technical specs**: Deep dive into architecture
   - ADRs explain "why" decisions were made
   - Data contracts show exact schemas
   - Lambda specs show expected inputs/outputs

4. **Comment on issue**: Describe blocker, ask for help
   - "I'm blocked by [X] because [Y]"
   - "I've tried [A, B, C] but encountering [error]"
   - Tag with `@mention` if urgent

5. **Add `blocked` label**: Signals you need help
   - Frees you to work on different story
   - Alerts team to prioritize unblocking

### Common Questions

**Q: Can I modify shared library code?**
A: Yes, but coordinate if other agents might be using it. Add comment on issue.

**Q: Should I create new files or modify existing?**
A: Prefer modifying existing. Only create new if truly needed per story.

**Q: How do I test locally without deploying to AWS?**
A: Use pytest mocks. See existing tests in `tests/unit/` for patterns.

**Q: Can I use a different pattern than existing code?**
A: Stick to existing patterns for consistency. If improvement needed, discuss in issue first.

**Q: What if my PR fails CI/CD?**
A: Check GitHub Actions logs, fix locally, push again. CI auto-retries.

---

## 🎯 Quick Reference

### Files to Read First (For Every Story)

**Priority 1** (Always Read):
1. GitHub Issue description
2. This file (`docs/agile/AI_AGENT_CONTEXT.md`)
3. Story file in `/docs/agile/stories/active/STORY_XXX_*.md`
4. `/docs/CLAUDE.md` (project commands)

**Priority 2** (Read If Relevant):
5. Relevant ADR in `/docs/agile/technical/ARCHITECTURE_DECISION_RECORD.md`
6. Similar code (search codebase)
7. Technical spec (Lambda, Data Contract, State Machine, Testing)

**Priority 3** (Reference When Needed):
8. `/.github/AI_AGENT_TASK_TEMPLATE.md` (task structure)
9. `/.github/AI_AGENT_WORKFLOW.md` (collaboration protocol)
10. `/CONTRIBUTING.md` (style guide)

### Quality Checklist (Before PR)

```bash
# Run these commands in order
black .                           # Format
flake8 .                          # Lint
mypy .                            # Type check
pytest tests/unit/ -v --cov      # Test with coverage

# If all pass:
git add .
git commit -m "feat(scope): description"
git push origin agent/name/STORY-XXX-description
gh pr create --fill
```

### Emergency Commands

```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Discard all local changes
git reset --hard origin/main

# Recover deleted branch
git checkout -b recovered origin/agent/name/STORY-XXX

# Fix merge conflict
git fetch origin main
git rebase origin/main
# [resolve conflicts]
git add [files]
git rebase --continue
```

---

## 📊 Current Sprint 3 Stories (Examples)

**Priority Stories** (Unassigned, ready to claim):
- STORY-028: Design unified state machine JSON (5 pts)
- STORY-029: Implement Bronze ingestion phase (3 pts)
- STORY-030: Implement Silver transformation phase (5 pts)
- STORY-033: Create run_soda_checks Lambda (5 pts)
- STORY-048: Create Soda quality check YAML definitions (5 pts)

**View All**: `/docs/agile/STORY_CATALOG.md` or GitHub Projects board

---

## 🎓 Learning Resources

**Understand Architecture**:
- Read: `/docs/agile/technical/ARCHITECTURE_DECISION_RECORD.md`
- Study: Existing Lambda functions in `/api/lambdas/`
- Review: Bronze/Silver/Gold data flow

**Understand Patterns**:
- Lambda wrapper: Check `/api/lambdas/build_dim_members/handler.py`
- Parquet upsert: Check `/ingestion/lib/parquet_writer.py`
- PDF extraction: Check `/ingestion/lib/extraction/ExtractionPipeline.py`

**Understand Testing**:
- Unit tests: `/tests/unit/api/test_*.py`
- Integration tests: `/tests/integration/test_*_integration.py`
- Fixtures: `/tests/fixtures/`

---

## ✅ Final Checklist Before Starting Work

- [ ] I've read this entire context document
- [ ] I've claimed a GitHub Issue (assigned to me)
- [ ] I've read the full story file
- [ ] I've reviewed relevant technical specs
- [ ] I've searched for similar code patterns
- [ ] I understand acceptance criteria
- [ ] I understand Definition of Done
- [ ] I have token budget for this story (estimated tokens vs. available)
- [ ] I've created feature branch with correct naming
- [ ] I'm ready to implement following standards

---

**Document Version**: 1.0
**Last Updated**: 2025-12-26
**For Questions**: Create issue with `process-improvement` label

**Good luck! Follow the patterns, write tests, and don't hesitate to ask for help. 🚀**
