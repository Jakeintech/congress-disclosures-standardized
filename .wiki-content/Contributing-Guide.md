# Contributing Guide

Thank you for considering contributing to the Congress Financial Disclosures project! This guide will help you get started.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Commit Guidelines](#commit-guidelines)
- [AI Agent Workflow](#ai-agent-workflow)

---

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

**Expected Behavior**:
- Be respectful and inclusive
- Welcome diverse perspectives
- Give and receive constructive feedback gracefully
- Focus on what's best for the community

**Unacceptable Behavior**:
- Harassment or discrimination
- Trolling or insulting comments
- Publishing others' private information
- Other conduct inappropriate in a professional setting

---

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, check existing issues to avoid duplicates.

**Good Bug Report Includes**:
- **Clear title**: Summarize the issue in one line
- **Description**: Detailed explanation of the problem
- **Steps to reproduce**: Exact steps to trigger the bug
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Environment**: AWS region, Python version, Terraform version
- **Logs**: Relevant CloudWatch logs or error messages

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues.

**Good Enhancement Suggestion Includes**:
- **Clear title**: Describe the enhancement concisely
- **Context**: Explain why this would be useful
- **Alternatives**: What other approaches did you consider?
- **Resources**: Link to similar features in other projects

### Your First Code Contribution

**Good First Issues**:
- `good-first-issue`: Simple issues perfect for beginners
- `help-wanted`: Issues where we need community help
- `documentation`: Improvements to docs

---

## Development Setup

### Prerequisites

- Python 3.11+
- Terraform 1.5+
- AWS CLI configured
- Git

### Local Setup

```bash
# 1. Clone repository
git clone https://github.com/Jakeintech/congress-disclosures-standardized.git
cd congress-disclosures-standardized

# 2. Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r ingestion/requirements.txt
pip install -r requirements-dev.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your AWS configuration

# 5. Initialize Terraform (optional)
cd infra/terraform
terraform init
```

### Running Tests Locally

```bash
# Unit tests
pytest tests/unit/

# Integration tests (requires AWS credentials)
pytest tests/integration/

# With coverage
pytest --cov=ingestion tests/
```

### Linting and Formatting

```bash
# Format code
black ingestion/

# Lint
flake8 ingestion/
pylint ingestion/

# Type checking
mypy ingestion/
```

---

## Coding Standards

### Python Style (PEP 8 + Black)

**Line length**: 88 characters (Black default)

**Type hints**: Always use type annotations
```python
def extract_text(pdf_path: str, use_ocr: bool = False) -> Dict[str, str]:
    """Extract text from a PDF file."""
    pass
```

**Docstrings**: Use Google style
```python
def process_document(doc_id: str, year: int) -> bool:
    """Process a single financial disclosure document.

    Args:
        doc_id: Document identifier from House index
        year: Filing year (e.g., 2025)

    Returns:
        True if processing succeeded, False otherwise

    Raises:
        ValueError: If doc_id is invalid
        S3Error: If S3 upload fails
    """
    pass
```

**Imports**: Organized with isort
```python
# Standard library
import os
from typing import Dict, List

# Third-party
import boto3
from pypdf import PdfReader

# Local
from lib.s3_utils import upload_file_to_s3
```

### Terraform Style

**Naming**: Use lowercase with underscores (`s3_bucket_name`)

**Tagging**: All resources must have standard tags
```hcl
tags = merge(
  var.common_tags,
  {
    Name = "house-fd-ingest-zip"
    Component = "ingestion"
  }
)
```

**Variables**: Define in `variables.tf` with descriptions

**Outputs**: Expose important values (ARNs, URLs)

### File Naming

- Python: `snake_case.py`
- Terraform: `snake_case.tf`
- Documentation: `SCREAMING_SNAKE_CASE.md` for top-level, `lowercase.md` for docs/

---

## Testing Guidelines

### Unit Tests

Test individual functions in isolation:

```python
# tests/unit/test_pdf_extractor.py
import pytest
from lib.pdf_extractor import detect_has_text_layer

def test_detect_text_layer_with_text():
    """Test detection of PDF with embedded text."""
    result = detect_has_text_layer('tests/fixtures/text_based.pdf')
    assert result is True

def test_detect_text_layer_image_only():
    """Test detection of image-only PDF."""
    result = detect_has_text_layer('tests/fixtures/image_only.pdf')
    assert result is False
```

### Integration Tests

Test end-to-end workflows (requires AWS):

```python
# tests/integration/test_ingestion_pipeline.py
import boto3
import pytest
from lambdas.house_fd_ingest_zip.handler import lambda_handler

@pytest.mark.integration
def test_full_ingestion_2025():
    """Test complete ingestion of 2025 data."""
    event = {"year": 2025}
    result = lambda_handler(event, None)

    assert result['status'] == 'success'
    assert result['pdfs_queued'] > 0
```

### Coverage Requirements

- **Minimum coverage**: 80% for new code
- **Critical paths**: 100% coverage (extraction, parsing)
- Run with: `pytest --cov=ingestion --cov-report=html`

---

## Pull Request Process

### Before Submitting

- [ ] Code follows coding standards
- [ ] All tests pass (`pytest tests/`)
- [ ] New tests added for new functionality
- [ ] Documentation updated (if applicable)
- [ ] No secrets or credentials in code
- [ ] Terraform `plan` succeeds (for infrastructure changes)
- [ ] Commit messages are clear and descriptive
- [ ] Pre-commit hooks passed locally

### PR Checklist

1. **Title**: Use conventional commit format
   - `feat: Add Textract error retry logic`
   - `fix: Handle corrupt PDF files gracefully`
   - `docs: Update deployment guide`
   - `test: Add unit tests for pdf_extractor`

2. **Description**: Provide context
   - What problem does this solve?
   - How does this change address it?
   - Any breaking changes?
   - Link to related issues

3. **Review Process**:
   - At least one maintainer must approve
   - All CI checks must pass
   - Merge conflicts must be resolved

4. **After Merge**:
   - Your branch will be deleted automatically
   - Changes will be deployed in the next release

---

## Commit Guidelines

We follow **Conventional Commits** specification.

### Commit Message Format

```
<type>(<scope>): [STORY-XXX] <subject>

<body>

<footer>
```

### Commit Types

- **feat**: New feature for the user
  - `feat(extraction): add Tesseract OCR for image PDFs`
  
- **fix**: Bug fix for the user
  - `fix(pdf): handle corrupt PDF files gracefully`
  
- **docs**: Documentation changes only
  - `docs(architecture): update S3 bucket layout diagram`
  
- **style**: Formatting, no code change
  - `style(python): format code with black`
  
- **refactor**: Code change that neither fixes a bug nor adds a feature
  - `refactor(extraction): extract PDF logic into module`
  
- **test**: Adding or improving tests
  - `test(pdf): add unit tests for text layer detection`
  
- **chore**: Build process, dependency updates, tooling
  - `chore(deps): update boto3 to 1.28.0`

### Scope

Indicate what part of codebase you're changing:
- `bronze`, `silver`, `gold`: Data lake layers
- `extraction`, `pdf`, `ocr`: Extraction components
- `ingestion`, `lambda`: Ingestion pipeline
- `terraform`, `infra`: Infrastructure
- `s3`, `sqs`, `iam`: AWS services
- `docs`, `readme`: Documentation
- `test`, `ci`: Testing and CI/CD

### Examples

**Good commits:**
```
feat(extraction): add AWS Textract integration for image PDFs

Implements Textract DetectDocumentText API for PDFs without embedded
text layers. Falls back to pypdf for text-based PDFs. Adds error
handling for Textract throttling and timeout scenarios.

Closes #42
```

**Bad commits (avoid):**
```
❌ Update files
❌ Fix bug
❌ WIP
❌ Fixed the thing that was broken
```

---

## AI Agent Workflow

AI agents working on this project should follow the **Agentic Agile Workflow**.

### Workflow Steps

1. **Onboarding**: Read `.github/AGENT_ONBOARDING.md` for your first task
2. **Task Planning**: Use `.github/AI_AGENT_TASK_TEMPLATE.md` to structure implementation
3. **Coordination**: Reference `.github/AI_AGENT_WORKFLOW.md` for collaboration
4. **Context**: Use `docs/agile/AI_AGENT_CONTEXT.md` for project knowledge

### Branch Naming Convention

Branches MUST follow this format:
`agent/<name>/STORY-XXX-description`

**Example**: `agent/claudia/STORY-028-unified-state-machine`

- **Prefix**: `agent/`
- **Name**: Your identity (e.g., `claudia`, `jake`)
- **ID**: The user story ID (e.g., `STORY-042`)
- **Description**: Short kebab-case description

---

## See Also

- [[Quick-Start-Guide]] - Getting started
- [[Development-Setup]] - Detailed setup instructions
- [[Code-Style-Guide]] - Coding standards
- [[Testing-Strategy]] - Testing approach
- [[PR-Process]] - Pull request workflow
- [[Commit-Conventions]] - Commit message standards

---

**Questions?**

- Open a [GitHub Discussion](https://github.com/Jakeintech/congress-disclosures-standardized/discussions)
- Check [GitHub Issues](https://github.com/Jakeintech/congress-disclosures-standardized/issues)

Thank you for making congressional financial data more transparent and accessible!
