# Contributing to Congress Financial Disclosures

Thank you for considering contributing to this project! This pipeline makes congressional financial data more accessible and transparent, and community contributions help improve it for everyone.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Security & Secrets](#security--secrets)
- [AI Agent Workflow](#ai-agent-workflow)
- [Managing Sprints & Tasks](#managing-sprints--tasks)

## Code of Conduct

This project adheres to a Code of Conduct (see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the [existing issues](https://github.com/Jakeintech/congress-disclosures-standardized/issues) to avoid duplicates.

When creating a bug report, include:
- **Clear title**: Summarize the issue in one line
- **Description**: Detailed explanation of the problem
- **Steps to reproduce**: Exact steps to trigger the bug
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Environment**: AWS region, Python version, Terraform version
- **Logs**: Relevant CloudWatch logs or error messages

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear title**: Describe the enhancement concisely
- **Provide context**: Explain why this enhancement would be useful
- **Describe alternatives**: What other approaches did you consider?
- **Link to resources**: Reference similar features in other projects

### Your First Code Contribution

Unsure where to start? Look for issues labeled:
- `good-first-issue`: Simple issues perfect for beginners
- `help-wanted`: Issues where we need community help
- `documentation`: Improvements to docs

### Pull Requests

1. Fork the repo and create your branch from `main`
2. Make your changes following our [coding standards](#coding-standards)
3. Add tests for any new functionality
4. Update documentation (README, Architecture docs, etc.)
5. Ensure all tests pass
6. Submit a pull request

### AI Agent Workflow

AI agents working on this project should follow the **Agentic Agile Workflow** to ensure high-quality, traceable contributions.

#### 🎯 Workflow Steps
1. **Onboarding**: Read [.github/AGENT_ONBOARDING.md](file:///.github/AGENT_ONBOARDING.md) for your first task.
2. **Task Planning**: Use [.github/AI_AGENT_TASK_TEMPLATE.md](file:///.github/AI_AGENT_TASK_TEMPLATE.md) to structure your implementation plan.
3. **Coordination**: Reference [.github/AI_AGENT_WORKFLOW.md](file:///.github/AI_AGENT_WORKFLOW.md) when collaborating with other agents.
4. **Context**: Use `docs/agile/AI_AGENT_CONTEXT.md` to maintain consistent project knowledge.

#### 🌿 Branch Naming Convention
Branches MUST follow this format to enable automated tracking:
`agent/<name>/STORY-XXX-description`

- **Example**: `agent/claudia/STORY-028-unified-state-machine`
- **Prefix**: `agent/`
- **Name**: Your identity (e.g., `claudia`, `jake`)
- **ID**: The user story ID (e.g., `STORY-042`)
- **Description**: Short kebab-case description

### Managing Sprints & Tasks

We use **GitHub Projects (v2)** for all agile tracking.

- **Board**: [Congress Disclosures Agile Board](https://github.com/users/Jakeintech/projects)
- **Status Tracking**: Issues move automatically based on linked Pull Requests.
- **Story Points**: We use Fibonacci sequence (0, 1, 2, 3, 5, 8).
- **Tokens**: AI agent estimates are tracked in tokens (1pt = 10k context).

## Development Setup

### Prerequisites

- **Python 3.11+** with pip
- **Terraform 1.5+**
- **AWS CLI** configured with credentials
- **Make** (optional but recommended)
- **Git**

### Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Jakeintech/congress-disclosures-standardized.git
   cd congress-disclosures-standardized
   ```

2. **Set up Python virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r ingestion/requirements.txt
   pip install -r requirements-dev.txt  # Testing dependencies
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your local AWS configuration
   # NEVER commit .env to Git!
   ```

5. **Initialize Terraform** (optional, for infrastructure changes):
   ```bash
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

We use standard Python tooling:

```bash
# Format code
black ingestion/

# Lint
flake8 ingestion/
pylint ingestion/

# Type checking
mypy ingestion/
```

## Pull Request Process

### Before Submitting

- [ ] Code follows our [coding standards](#coding-standards)
- [ ] All tests pass (`pytest tests/`)
- [ ] New tests added for new functionality
- [ ] Documentation updated (if applicable)
- [ ] No secrets or credentials in code
- [ ] Terraform `plan` succeeds (for infrastructure changes)
- [ ] Commit messages are clear and descriptive
- [ ] Pre-commit hooks passed locally

### Pre-commit Hooks

This project uses `pre-commit` to enforce quality gates (linting, formatting, secret detection).

#### Setup
1. Install pre-commit:
   ```bash
   pip install pre-commit
   ```
2. Install the hooks:
   ```bash
   pre-commit install
   pre-commit install --hook-type commit-msg
   ```

#### Usage
Hooks run automatically on `git commit`. To run manually on all files:
```bash
pre-commit run --all-files
```

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

## Commit Guidelines

We follow the **Conventional Commits** specification to maintain a clean, readable commit history and enable automated changelog generation.

### Commit Message Format

```
<type>(<scope>): [STORY-XXX] <subject>

<body>

<footer>
```

- **Subject**: Must include the story ID in brackets, e.g., `[STORY-042]`.
- **Type**: See below.

### Commit Types

Use one of these types for every commit:

- **feat**: New feature for the user (not a build script feature)
  - `feat(extraction): add Textract OCR for image-based PDFs`
  - `feat(silver): implement house_fd_documents Parquet table`

- **fix**: Bug fix for the user (not a fix to a build script)
  - `fix(pdf): handle corrupt PDF files gracefully`
  - `fix(s3): retry S3 uploads on network errors`

- **docs**: Documentation changes only
  - `docs(architecture): update S3 bucket layout diagram`
  - `docs(readme): add self-hosting instructions`

- **style**: Formatting, missing semicolons, etc.; no code change
  - `style(python): format code with black`
  - `style(terraform): fix indentation in iam.tf`

- **refactor**: Code change that neither fixes a bug nor adds a feature
  - `refactor(extraction): extract PDF logic into separate module`
  - `refactor(s3): simplify upload retry logic`

- **test**: Adding or improving tests
  - `test(pdf): add unit tests for text layer detection`
  - `test(integration): add end-to-end ingestion test`

- **chore**: Build process, dependency updates, tooling
  - `chore(deps): update boto3 to 1.28.0`
  - `chore(ci): add GitHub Actions workflow`

- **perf**: Performance improvements
  - `perf(extraction): optimize PDF text extraction speed`
  - `perf(lambda): reduce Lambda cold start time`

### Scope

The scope should indicate what part of the codebase you're changing:

- `bronze`, `silver`, `gold`: Data lake layers
- `extraction`, `pdf`, `textract`: Extraction components
- `ingestion`, `lambda`: Ingestion pipeline
- `terraform`, `infra`: Infrastructure
- `s3`, `sqs`, `iam`: AWS services
- `docs`, `readme`, `architecture`: Documentation
- `test`, `ci`: Testing and CI/CD

### Subject

- Use imperative mood: "add feature" not "added feature" or "adds feature"
- Don't capitalize the first letter
- No period at the end
- Keep under 50 characters

### Body (Optional)

- Explain **what** and **why**, not **how**
- Wrap at 72 characters
- Leave one blank line between subject and body

### Footer (Optional)

- Reference issues: `Closes #123`, `Fixes #456`, `Related to #789`
- Breaking changes: `BREAKING CHANGE: <description>`

### Examples

**Good commits:**

```
feat(extraction): add AWS Textract integration for image PDFs

Implements Textract DetectDocumentText API for PDFs without embedded
text layers. Falls back to pypdf for text-based PDFs. Adds error
handling for Textract throttling and timeout scenarios.

Closes #42
```

```
fix(s3): handle S3 upload failures with exponential backoff

Adds retry logic with exponential backoff for S3 PutObject operations.
Retries up to 3 times with delays of 1s, 2s, 4s. Logs failures to
CloudWatch for monitoring.

Fixes #15
```

```
docs: add deployment guide for self-hosting

Complete step-by-step guide for deploying infrastructure to personal
AWS accounts. Includes prerequisites, cost estimates, and
troubleshooting section.
```

```
chore(deps): update dependencies to latest versions

- boto3: 1.26.0 -> 1.28.0
- pypdf: 3.0.0 -> 3.15.0
- pyarrow: 12.0.0 -> 13.0.0

No breaking changes in these updates.
```

**Bad commits (avoid these):**

```
❌ Update files
❌ Fix bug
❌ WIP
❌ Fixed the thing that was broken
❌ feat: Added new feature for extracting PDFs and also updated docs
```

### When to Commit

- Commit early and often (logical units of work)
- One commit per logical change
- Don't mix refactoring with feature changes
- Every commit should leave the codebase in a working state

### Commit Before Opening PR

Before opening a pull request:
1. Review your commit history: `git log --oneline`
2. Squash WIP/fix commits if needed: `git rebase -i HEAD~n`
3. Ensure each commit has a clear, descriptive message
4. Each commit should pass tests independently (if possible)

### Helpful Git Aliases

Add these to your `~/.gitconfig`:

```ini
[alias]
  # Show commit log with graph
  lg = log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit

  # Commit with conventional commit message
  cz = !git-cz  # Requires commitizen: npm install -g commitizen cz-conventional-changelog

  # Amend last commit without changing message
  amend = commit --amend --no-edit

  # Show files changed in last commit
  changed = diff-tree --no-commit-id --name-only -r HEAD
```

## Coding Standards

### Python Style

Follow **PEP 8** with these specifics:

- **Line length**: 88 characters (Black default)
- **Imports**: Organized with `isort`
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
- **Type hints**: Always use type annotations
  ```python
  def extract_text(pdf_path: str) -> Dict[str, str]:
      ...
  ```
- **Docstrings**: Use Google style
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
  ```

### Terraform Style

- **Naming**: Use lowercase with underscores (`s3_bucket_name`)
- **Tagging**: All resources must have standard tags:
  ```hcl
  tags = merge(
    var.common_tags,
    {
      Name = "house-fd-ingest-zip"
      Component = "ingestion"
    }
  )
  ```
- **Variables**: Define in `variables.tf` with descriptions
- **Outputs**: Expose important values (ARNs, URLs)
- **Modules**: Use modules for repeated patterns

### File Naming

- Python: `snake_case.py`
- Terraform: `snake_case.tf`
- Documentation: `SCREAMING_SNAKE_CASE.md` for top-level, `lowercase.md` for docs/

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

## Documentation

### When to Update Docs

Update documentation when you:
- Add a new feature
- Change infrastructure (update `docs/ARCHITECTURE.md`)
- Modify deployment process (update `docs/DEPLOYMENT.md`)
- Add environment variables (update `.env.example`)
- Change legal requirements (update `docs/LEGAL_NOTES.md`)

### Documentation Standards

- Use **Markdown** for all docs
- Include code examples where relevant
- Keep line length under 100 characters
- Use diagrams for complex flows (Mermaid or ASCII)
- Link to external resources (AWS docs, legal statutes)

## Security & Secrets

### Critical Rules

**NEVER commit**:
- AWS credentials or API keys
- `.tfvars` files with real values
- `.env` files with secrets
- SSH keys, certificates, or passwords

### Best Practices

1. **Use AWS IAM roles** instead of hardcoded credentials
2. **Store secrets in AWS Secrets Manager** or SSM Parameter Store
3. **Use `.env.example`** to document required variables
4. **Scan commits** with git-secrets or similar tools
5. **Rotate credentials** if accidentally committed (even if removed later)

### If You Accidentally Commit a Secret

1. **Immediately rotate the credential** (revoke the old one)
2. **Rewrite Git history** to remove the secret:
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch path/to/secret" \
     --prune-empty --tag-name-filter cat -- --all
   ```
3. **Force push** (coordinate with maintainers)
4. **Notify maintainers** in your PR or via issue

## Legal Compliance

All contributions must comply with **5 U.S.C. § 13107** (see [docs/LEGAL_NOTES.md](docs/LEGAL_NOTES.md)).

Prohibited:
- Using data for commercial purposes (except news/media)
- Credit rating determination
- Fundraising or solicitation

By contributing, you agree that your contributions:
- Are for transparency, research, or news purposes
- Will not be used for prohibited purposes
- Are licensed under the MIT License

## Questions?

- **General questions**: Open a [GitHub Discussion](https://github.com/Jakeintech/congress-disclosures-standardized/discussions)
- **Bug reports**: Open an [Issue](https://github.com/Jakeintech/congress-disclosures-standardized/issues)
- **Security concerns**: Email [SECURITY@example.com] (do not open public issues)

## Recognition

Contributors are recognized in:
- GitHub contributors page
- Release notes for their contributions
- `CONTRIBUTORS.md` file (if significant contributions)

Thank you for making congressional financial data more transparent and accessible!

---

**License**: By contributing, you agree that your contributions will be licensed under the MIT License.
