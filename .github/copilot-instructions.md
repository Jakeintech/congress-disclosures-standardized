# GitHub Copilot Instructions

This file provides context-aware instructions for GitHub Copilot when working in this repository.

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

### Best Practices
- ✅ Use AWS IAM roles instead of hardcoded credentials
- ✅ Store secrets in AWS Secrets Manager or SSM Parameter Store
- ✅ Use `.env.example` to document required variables
- ✅ Scan commits with pre-commit hooks (detect-secrets)

### Legal Compliance (5 U.S.C. § 13107)
All code must comply with federal law. Prohibited uses:
- ❌ Commercial purposes (except news/media)
- ❌ Credit rating determination
- ❌ Fundraising or solicitation

Permitted uses:
- ✅ Transparency and research purposes
- ✅ News and media reporting
- ✅ Public accountability

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

1. **CLAUDE.md** - Project overview, architecture, common commands
2. **CONTRIBUTING.md** - Coding standards, commit conventions, PR process
3. **.github/AGENT_START_HERE.md** - Quick start guide for agents
4. **.github/AI_AGENT_WORKFLOW.md** - Multi-agent coordination
5. **docs/ARCHITECTURE.md** - Detailed architecture documentation
6. **docs/EXTRACTION_ARCHITECTURE.md** - Extraction pipeline deep dive

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
1. Check existing similar implementations
2. Review technical specs in `docs/agile/technical/`
3. Search codebase: `grep -r "pattern" --include="*.py"`
4. Check git history: `git log --grep="keyword"`
5. Ask in issue comments with specific question

### Resources
- **Documentation**: Start with `CLAUDE.md`
- **Code Examples**: Browse `ingestion/lambdas/` for patterns
- **Test Examples**: Browse `tests/unit/` for test patterns
- **Architecture Decisions**: See `docs/agile/technical/ARCHITECTURE_DECISION_RECORD.md`

---

**Version**: 1.0  
**Last Updated**: 2025-12-29  
**Maintained By**: Project Team

For questions or improvements to these instructions, create an issue with the `documentation` label.
