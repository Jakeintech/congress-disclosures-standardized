# GitHub Copilot Instructions

This file provides context-aware instructions for GitHub Copilot when working in this repository.

> **Quick Links for Agents:**
> - 🚀 [Start Here](.github/AGENT_START_HERE.md) - Quick start guide for AI agents
> - 📋 [AI Agent Context](docs/agile/AI_AGENT_CONTEXT.md) - Complete project context (copy-paste for each task)
> - 🔄 [AI Agent Workflow](.github/AI_AGENT_WORKFLOW.md) - Multi-agent coordination protocol
> - 📝 [Task Template](.github/AI_AGENT_TASK_TEMPLATE.md) - Structured task execution template
> - 📚 [CLAUDE.md](CLAUDE.md) - Comprehensive project guide with all commands
> - 🤝 [CONTRIBUTING.md](CONTRIBUTING.md) - Code standards, commit conventions, PR process

## 🤖 For AI Agents (Copilot, Claude, etc.)

**If you're an AI coding agent working on this repository:**

1. **ALWAYS read [AI_AGENT_CONTEXT.md](docs/agile/AI_AGENT_CONTEXT.md) first** - This is your master context document with complete project overview, current sprint status, and critical gotchas.

2. **Follow the structured workflow** defined in [AI_AGENT_WORKFLOW.md](.github/AI_AGENT_WORKFLOW.md):
   - Claim issues properly to avoid conflicts with other agents
   - Use branch naming: `agent/<name>/<STORY-ID>-description`
   - Follow conventional commit format: `<type>(<scope>): [STORY-ID] <description>`
   - Complete the task template checklist before submitting PRs

3. **Token budget awareness**: Stories are estimated in tokens (1 point ≈ 10K tokens). Track your usage and optimize by reading context files before coding to avoid backtracking.

4. **Quality gates**: All PRs must pass:
   - Unit tests (`pytest tests/unit/`)
   - Linting (`black`, `flake8`, `mypy`)
   - Coverage ≥80%
   - Security checks (no secrets, no SQL injection)
   - Legal compliance (5 U.S.C. § 13107)

5. **When in doubt**, reference existing implementations in `ingestion/lambdas/` for patterns.

## Project Overview

This is a **serverless data pipeline** for ingesting, extracting, and standardizing US Congress financial disclosures. The pipeline processes 15+ years of PDF filings from the House Clerk website, extracting structured transaction data, assets, and compliance information into a queryable data lake.

**Core Technology Stack:**
- **Cloud**: AWS (Lambda, S3, SQS, Step Functions, DynamoDB)
- **Infrastructure**: Terraform 1.5+
- **Language**: Python 3.11
- **Data**: Parquet, DuckDB, Pandas, PyArrow
- **Testing**: pytest, Black, flake8, mypy
- **CI/CD**: GitHub Actions

## Architecture: Bronze → Silver → Gold

The pipeline follows a **medallion architecture** with three data layers:

### Bronze Layer (Raw/Immutable)
- **Location**: `s3://congress-disclosures-standardized/bronze/house/financial/`
- **Contents**: Byte-for-byte preservation of source data
- **Key Files**: Original ZIP files, XML indices, individual PDFs
- **Important**: S3 object metadata tracks extraction state to prevent duplicate processing

### Silver Layer (Normalized/Queryable)
- **Location**: `s3://congress-disclosures-standardized/silver/house/financial/`
- **Format**: Parquet tables + gzipped text
- **Tables**: filings, documents, text, objects (structured extractions)

### Gold Layer (Query-Facing/Aggregated)
- **Location**: `s3://congress-disclosures-standardized/gold/house/financial/`
- **Structure**: Star schema with dimensions, facts, and pre-computed aggregates

## Data Flow

The pipeline follows this orchestration pattern:

```
Manual/Cron Trigger
    ↓
house_fd_ingest_zip (downloads YEARFD.zip, uploads to Bronze, queues PDFs)
    ↓
house_fd_index_to_silver (parses XML, writes Silver tables, queues extraction)
    ↓
SQS Queue (5K-15K messages) → house_fd_extract_document (parallel, 10 concurrent)
    ↓ (extracts text via pypdf → OCR fallback)
house_fd_extract_structured_code (code-based extraction by filing type)
    ↓ (outputs structured JSON to Silver)
Gold Scripts (aggregate_data, compute metrics, build fact tables)
```

**Key Execution Patterns:**
- **Step Functions**: Orchestrates complex workflows with parallel processing (MaxConcurrency: 10)
- **Watermarking**: Prevents duplicate processing via SHA256 hashing + DynamoDB
- **Error Handling**: Exponential backoff retries, DLQ integration, SNS alerts
- **Quality Gates**: Soda checks between Bronze→Silver→Gold transitions

## Coding Standards

### Python Style (PEP 8 + Black)
- **Line length**: 88 characters (Black default)
- **Type hints**: ALWAYS use type annotations for function parameters and return types
- **Docstrings**: Use Google style for all public functions, classes, and modules
- **Imports**: Organize in order (stdlib → third-party → local) using isort
- **Error handling**: Use specific exception types, always include logging

**Example:**
```python
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

def extract_text(pdf_path: str, use_ocr: bool = False) -> Dict[str, str]:
    """Extract text from a PDF file.

    Args:
        pdf_path: Path to PDF file
        use_ocr: Whether to use OCR fallback

    Returns:
        Dictionary with 'text', 'confidence_score', 'method'

    Raises:
        FileNotFoundError: If PDF doesn't exist
        S3Error: If S3 upload fails
    """
    try:
        # Implementation here
        logger.info(f"Processing PDF: {pdf_path}")
        return {"text": "", "confidence_score": 0.0, "method": "direct"}
    except FileNotFoundError as e:
        logger.error(f"PDF not found: {pdf_path}")
        raise
```

### Terraform Style
- **Naming**: Use lowercase with underscores (`s3_bucket_name`)
- **Tagging**: ALL resources must have standard tags
- **Variables**: Define in `variables.tf` with clear descriptions
- **Outputs**: Expose important values (ARNs, URLs)

### File Naming Conventions
- Python: `snake_case.py`
- Terraform: `snake_case.tf`
- Documentation: `SCREAMING_SNAKE_CASE.md` for top-level, `lowercase.md` for docs/

## Key Patterns & Best Practices

### Lambda Handler Pattern
When creating Lambda functions, follow this standard pattern:

```python
import json
import logging
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Brief description of what this Lambda does.

    Args:
        event: Lambda event (JSON)
        context: Lambda context

    Returns:
        Response dict with statusCode and body

    Raises:
        ValueError: If required parameters missing
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Validate input
        required_params = ["param1", "param2"]
        for param in required_params:
            if param not in event:
                raise ValueError(f"Missing required parameter: {param}")
        
        # Process
        result = process_event(event)
        
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

### Parquet Upsert Pattern
When updating Parquet tables incrementally:

```python
import pandas as pd

# 1. Read existing records
existing_df = pd.read_parquet(s3_path)
# 2. Remove old records with same keys
existing_clean = existing_df[~existing_df['doc_id'].isin(new_df['doc_id'])]
# 3. Append new records
combined = pd.concat([existing_clean, new_df])
# 4. Write back (atomic replace)
combined.to_parquet(s3_path)
```

### SQS Partial Batch Failure
Always use partial batch failure for SQS processing:

```python
failed_items = []
for record in event['Records']:
    try:
        process(record)
    except Exception as e:
        logger.error(f"Failed to process record: {e}")
        failed_items.append({'itemIdentifier': record['messageId']})
return {'batchItemFailures': failed_items}
```

## Testing Requirements

### Coverage Requirements
- **Minimum coverage**: 80% for new code
- **Critical paths**: 100% coverage (extraction, parsing)
- Run with: `pytest --cov=ingestion --cov-report=html`

### Test Structure
```python
import pytest
from unittest.mock import MagicMock, patch

class TestLambdaHandler:
    """Test suite for function_name Lambda handler"""

    def test_successful_execution(self):
        """Test successful Lambda execution with valid input"""
        # Arrange
        event = {"param1": "value1", "param2": "value2"}
        context = MagicMock()

        # Act
        with patch('module.handler.main') as mock_main:
            mock_main.return_value = {"rows_processed": 100}
            response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["message"] == "Success"
```

### Test Commands
```bash
# Unit tests
pytest tests/unit/ -v

# With coverage
pytest --cov=ingestion tests/

# Integration tests (requires AWS)
pytest tests/integration/ -v

# All quality checks
make check-all
```

## Git Workflow & Conventions

### Branch Naming
Format: `agent/<name>/<STORY-ID>-description` or `feature/<description>`

Examples:
- `agent/copilot/STORY-042-fix-duckdb-nan`
- `feature/add-gold-layer-kpis`

### Commit Message Format (Conventional Commits)
```
<type>(<scope>): [STORY-ID] <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

**Scopes**: `bronze`, `silver`, `gold`, `extraction`, `ingestion`, `api`, `infra`, `terraform`, `lambda`, `docs`, `test`, `ci`

**Examples:**
```
feat(extraction): [STORY-042] add Textract OCR for image-based PDFs
fix(s3): handle S3 upload failures with exponential backoff
docs(architecture): update S3 bucket layout diagram
test(pdf): add unit tests for text layer detection
```

### Pull Request Process
1. **Title**: Use conventional commit format
2. **Description**: Provide clear context, link to issues
3. **Checklist**: Complete all PR template items
4. **Review**: At least one maintainer approval required
5. **CI/CD**: All checks must pass before merge

## Common Commands

### Setup & Development
```bash
make setup                    # Initial setup (creates .env, installs deps)
make install                  # Install Python dependencies
make install-dev              # Install dev tools (black, flake8, pytest)
```

### Testing & Quality
```bash
make test                     # Run all tests
make test-unit                # Run unit tests only
make test-cov                 # Run tests with coverage
make lint                     # Run flake8 linting
make format                   # Format code with black
make type-check               # Run mypy type checking
make check-all                # Run all checks (format, lint, type, test)
```

### Infrastructure & Deployment
```bash
make init                     # Initialize Terraform
make plan                     # Show infrastructure changes
make deploy                   # Deploy infrastructure (interactive)
make deploy-auto              # Deploy without confirmation (CI)
```

### Lambda Operations
```bash
make package-all              # Package all Lambdas
make quick-deploy-extract     # Deploy extract Lambda (bypasses Terraform)
make logs-extract             # Tail extract Lambda logs
```

### Pipeline Operations
```bash
make run-pipeline             # Smart pipeline (interactive mode)
make ingest-year YEAR=2025    # Ingest specific year
make aggregate-data           # Generate Gold layer aggregates
```

## Critical Gotchas & Warnings

### 1. Lambda Timeout (900s max)
- **Issue**: Large datasets can exceed 15-minute Lambda timeout
- **Solution**: Use pagination, process in batches, or Step Functions Map states
- **Example**: Process 1,000 rows at a time instead of all at once

### 2. DuckDB S3 Connection
- **Issue**: DuckDB httpfs extension requires specific setup
- **Solution**: Always use INSTALL httpfs; LOAD httpfs; before S3 queries
```python
conn.execute("INSTALL httpfs; LOAD httpfs;")
conn.execute(f"SET s3_region='{region}';")
```

### 3. Bronze Metadata State Machine
Before queuing extraction, check if already processed:
```python
response = s3_client.head_object(Bucket=bucket, Key=pdf_key)
if response['Metadata'].get('extraction-processed') == 'true':
    return "skipped"  # Already processed
```

After extraction, tag the PDF:
```python
s3_client.copy_object(
    CopySource={'Bucket': bucket, 'Key': pdf_key},
    Bucket=bucket,
    Key=pdf_key,
    Metadata={'extraction-processed': 'true'},
    MetadataDirective='REPLACE'
)
```

### 4. Test Data Isolation
- **Issue**: Tests modifying shared test data
- **Solution**: Use pytest fixtures with function scope
- **Example**: Use `@pytest.fixture(scope="function")` not `scope="module"`

### 5. Environment Variables
- **Issue**: Forgetting to add new env vars to Lambda config
- **Solution**: Update BOTH `.env.example` AND Terraform `environment.variables`

## Security & Legal Requirements

### Security Rules (NEVER COMMIT)
- ❌ AWS credentials or API keys
- ❌ `.tfvars` files with real values
- ❌ `.env` files with secrets
- ❌ SSH keys, certificates, or passwords

**Pre-commit Security Checks:**
```bash
# Install pre-commit hooks
pre-commit install

# Run security scan
detect-secrets scan

# These run automatically on every commit
```

### Best Practices
- ✅ Use AWS IAM roles instead of hardcoded credentials
- ✅ Store secrets in AWS Secrets Manager or SSM Parameter Store
- ✅ Use `.env.example` to document required variables
- ✅ Scan commits with pre-commit hooks (detect-secrets)
- ✅ Rotate credentials immediately if accidentally committed

### Legal Compliance (5 U.S.C. § 13107)
All code must comply with federal law. Prohibited uses:
- ❌ Commercial purposes (except news/media)
- ❌ Credit rating determination
- ❌ Fundraising or solicitation

Permitted uses:
- ✅ Transparency and research purposes
- ✅ News and media reporting
- ✅ Public accountability

**Important**: Every PR must include a statement confirming legal compliance. Any features that could enable prohibited uses must be rejected.

## Do's and Don'ts

### ✅ DO
- Use existing patterns from similar code
- Write tests BEFORE implementation (TDD when possible)
- Log key operations for debugging
- Handle errors gracefully with specific exceptions
- Update documentation as you go
- Commit frequently with descriptive messages
- Ask for help early if blocked
- Use type hints on all functions
- Follow the Bronze → Silver → Gold data flow

### ❌ DON'T
- Hardcode values (use constants or env vars)
- Skip tests ("I'll add them later")
- Commit commented-out code
- Mix refactoring with new features in same PR
- Push directly to `main` (always use feature branches)
- Ignore linting errors
- Delete or modify working code unless absolutely necessary
- Remove existing tests without replacement
- Use `print()` for logging (use `logging` module)

## Key Files & Directories

### Configuration
- `.env.example` - Environment variable template
- `requirements.txt` - Python dependencies
- `pytest.ini` - pytest configuration
- `.flake8` - Linting rules
- `mypy.ini` - Type checking configuration
- `.pre-commit-config.yaml` - Pre-commit hooks

### Source Code
- `ingestion/` - Main ingestion pipeline code
  - `ingestion/lambdas/` - Lambda function handlers
  - `ingestion/lib/` - Shared libraries and utilities
  - `ingestion/lib/extractors/` - PDF extraction code by filing type
- `scripts/` - Pipeline orchestration and Gold layer scripts
- `api/` - API Lambda functions
- `infra/terraform/` - Infrastructure as code

### Tests
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests
- `tests/fixtures/` - Test data and fixtures

### Documentation
- `CLAUDE.md` - Comprehensive project guide (READ THIS FIRST)
- `CONTRIBUTING.md` - Contribution guidelines
- `docs/ARCHITECTURE.md` - Architecture documentation
- `docs/DEPLOYMENT.md` - Deployment guide
- `docs/EXTRACTION_ARCHITECTURE.md` - Extraction pipeline details
- `.github/AGENT_ONBOARDING.md` - Agent onboarding guide
- `.github/AI_AGENT_WORKFLOW.md` - Multi-agent workflow
- `.github/AI_AGENT_TASK_TEMPLATE.md` - Task template

## Quick Reference for Common Tasks

### Adding a New Lambda Function
1. Create handler in `ingestion/lambdas/function_name/handler.py`
2. Follow Lambda Handler Pattern (see above)
3. Add Terraform config in `infra/terraform/lambdas.tf`
4. Add unit tests in `tests/unit/lambdas/test_function_name.py`
5. Update `.env.example` if new env vars needed
6. Update `CLAUDE.md` if new commands added

### Modifying Data Schema
1. Update relevant layer (Bronze/Silver/Gold)
2. Update data contracts in `docs/agile/technical/DATA_CONTRACTS.md`
3. Add migration script if needed
4. Update all downstream dependencies
5. Add integration tests

### Adding a New Dependency
1. Add to `requirements.txt` or layer-specific requirements
2. Update Lambda layer if needed
3. Run `make install` to verify installation
4. Document in commit message why dependency is needed

## Reading List (Priority Order)

When starting work on this project, read these files in order:

### Essential (Read First)
1. **[CLAUDE.md](CLAUDE.md)** - Project overview, architecture, common commands (15 min read)
2. **[CONTRIBUTING.md](CONTRIBUTING.md)** - Coding standards, commit conventions, PR process (10 min read)

### For AI Agents (Required)
3. **[.github/AGENT_START_HERE.md](.github/AGENT_START_HERE.md)** - Quick start guide for agents (5 min read)
4. **[docs/agile/AI_AGENT_CONTEXT.md](docs/agile/AI_AGENT_CONTEXT.md)** - Complete project context to copy-paste (5 min read, reference throughout)
5. **[.github/AI_AGENT_WORKFLOW.md](.github/AI_AGENT_WORKFLOW.md)** - Multi-agent coordination (10 min read)
6. **[.github/AI_AGENT_TASK_TEMPLATE.md](.github/AI_AGENT_TASK_TEMPLATE.md)** - Task execution template (reference during work)

### Deep Dive (As Needed)
7. **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed architecture documentation
8. **[docs/EXTRACTION_ARCHITECTURE.md](docs/EXTRACTION_ARCHITECTURE.md)** - Extraction pipeline deep dive
9. **[docs/agile/STORY_CATALOG.md](docs/agile/STORY_CATALOG.md)** - All user stories overview
10. **[docs/agile/technical/](docs/agile/technical/)** - Technical specifications and ADRs

## Step Functions & State Machines

The pipeline uses AWS Step Functions for orchestration:

**State Machines:**
- `house_fd_pipeline` - House Financial Disclosures
- `congress_pipeline` - Congress.gov API data
- `lobbying_pipeline` - Senate LDA lobbying disclosures

**Key Features:**
- Parallel processing with Map states (MaxConcurrency: 10)
- Error handling with exponential backoff retries
- Quality gates (Soda checks) between layers
- Watermarking to prevent duplicate processing

## Help & Support

### If Blocked
1. Check existing similar implementations in the codebase
2. Review technical specs in `docs/agile/technical/`
3. Search codebase: `grep -r "pattern" --include="*.py"`
4. Check git history: `git log --grep="keyword"`
5. Ask in issue comments with specific question
6. **For AI agents**: Check [AI_AGENT_WORKFLOW.md](.github/AI_AGENT_WORKFLOW.md) for handoff procedures

### Resources
- **Documentation**: Start with `CLAUDE.md` (comprehensive guide)
- **Code Examples**: Browse `ingestion/lambdas/` for Lambda patterns
- **Test Examples**: Browse `tests/unit/` for test patterns
- **Architecture Decisions**: See `docs/agile/technical/ARCHITECTURE_DECISION_RECORD.md`
- **AI Agent Resources**:
  - [AI_AGENT_CONTEXT.md](docs/agile/AI_AGENT_CONTEXT.md) - Complete project context
  - [AGENT_ONBOARDING.md](.github/AGENT_ONBOARDING.md) - First-time agent walkthrough
  - [AI_AGENT_TASK_TEMPLATE.md](.github/AI_AGENT_TASK_TEMPLATE.md) - Task execution template
  - [STORY_CATALOG.md](docs/agile/STORY_CATALOG.md) - All user stories overview

### Common Workflows for Copilot

**Starting a new task:**
```bash
# 1. Find and claim an issue
gh issue list --label "agent-task" --state open --limit 5
gh issue edit <NUMBER> --add-assignee @me

# 2. Create branch
git checkout -b agent/copilot/STORY-XXX-description

# 3. Read context
cat docs/agile/AI_AGENT_CONTEXT.md
cat docs/agile/stories/active/STORY_XXX_*.md
```

**Before submitting PR:**
```bash
# Run quality checks
make check-all           # format, lint, type-check, test
pytest --cov=ingestion   # verify coverage ≥80%

# Verify no secrets
detect-secrets scan

# Create PR with conventional commit
git commit -m "feat(scope): [STORY-XXX] description"
gh pr create --fill
```

## Definition of Done (DoD)

Every PR must meet these criteria before merge:

### Code Quality
- [ ] Code follows PEP 8 style guide (88 char line length)
- [ ] All functions have type hints
- [ ] All public functions have Google-style docstrings
- [ ] No commented-out code (use git history instead)
- [ ] No TODOs without linked issues
- [ ] Black formatting applied
- [ ] flake8 linting passes
- [ ] mypy type checking passes

### Testing
- [ ] Unit tests written for new functionality
- [ ] Test coverage ≥80% for new code
- [ ] Critical paths have 100% coverage
- [ ] All tests pass locally (`pytest tests/`)
- [ ] Integration tests pass (if applicable)

### Security
- [ ] No hardcoded secrets or credentials
- [ ] No SQL injection vulnerabilities
- [ ] No command injection risks
- [ ] `detect-secrets` scan passes
- [ ] Legal compliance verified (5 U.S.C. § 13107)

### Documentation
- [ ] Code changes documented in docstrings
- [ ] Complex logic has inline comments
- [ ] README/CLAUDE.md updated if workflow changed
- [ ] `.env.example` updated if new env vars added
- [ ] PR description clearly explains changes

### Git & CI/CD
- [ ] Conventional commit format used
- [ ] Branch named correctly (`agent/<name>/STORY-XXX-description`)
- [ ] Issue linked in PR (`Closes #XXX`)
- [ ] All CI/CD checks passing
- [ ] No merge conflicts
- [ ] Self-review completed

### Acceptance Criteria
- [ ] All story acceptance criteria met
- [ ] Manual testing completed
- [ ] Edge cases considered and handled
- [ ] Error messages are clear and actionable

**For AI Agents**: Track your token usage against estimates. If >20% over budget, document why in PR description.

---

**Version**: 1.1  
**Last Updated**: 2026-01-05  
**Maintained By**: Project Team

For questions or improvements to these instructions, create an issue with the `documentation` label.
