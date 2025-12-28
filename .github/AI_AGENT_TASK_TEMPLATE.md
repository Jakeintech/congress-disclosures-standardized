# AI Agent Task Brief: [STORY-XXX]

**Story**: [Link to GitHub Issue #XX]
**Sprint**: [Sprint X - Sprint Name]
**Assigned Agent**: [Agent Name or "Unassigned"]
**Created**: [YYYY-MM-DD HH:MM UTC]
**Estimated Tokens**: [X tokens based on story points - 1pt≈10K, 2pt≈20K, 3pt≈30K, 5pt≈50K, 8pt≈80K tokens]
**Story Points**: [1, 2, 3, 5, or 8]

---

## 📋 Context

### What You Need to Know

- **Epic**: EPIC-001 Unified Data Platform Migration
- **Sprint Goal**: [Copy sprint goal from sprint plan]
- **Business Value**: [Why this story matters]
- **Dependencies**:
  - ✅ **Completed**: [List completed dependencies with links to issues/PRs]
  - ⚠️ **Prerequisites**: [What MUST be done BEFORE starting this task]
  - 📋 **Blocks**: [What stories are waiting for this task to complete]

### Related Work

- **Previous PRs**: [Links to related pull requests]
- **Related Stories**: [STORY-AAA](#), [STORY-BBB](#)
- **Technical Specs**:
  - Architecture Decision: [Link to ADR in `/docs/agile/technical/ARCHITECTURE_DECISION_RECORD.md`]
  - Data Contracts: [Link to relevant schemas in `/docs/agile/technical/DATA_CONTRACTS.md`]
  - Lambda Spec: [Link to function spec in `/docs/agile/technical/LAMBDA_REQUIREMENTS_SPEC.md`]
  - State Machine: [Link to workflow in `/docs/agile/technical/STATE_MACHINE_SPEC.md`]

### Current System State

- **Branch**: `main` (or specify feature branch if building on another story)
- **Last Deploy**: [Date of last deployment]
- **Known Issues**: [Any current bugs or limitations affecting this work]

---

## 🎯 Task Description

### User Story

> **As a** [role/persona]
> **I want** [feature/capability]
> **So that** [business value/outcome]

### Technical Summary

[1-3 sentence technical description of what needs to be built]

**Example**:
> Create a Lambda wrapper for the `build_fact_transactions.py` script that aggregates PTR (Periodic Transaction Report) data from Silver layer and writes to Gold layer fact table. The Lambda should support incremental and full rebuild modes, handle large datasets efficiently, and integrate with Step Functions orchestration.

---

## ✅ Acceptance Criteria

**IMPORTANT**: All criteria must be met for story completion. Use GIVEN/WHEN/THEN format.

### 1. Primary Happy Path
- **GIVEN** [initial state/context]
- **WHEN** [action is performed]
- **THEN** [expected outcome]
- **AND** [additional verification]

**Example**:
> - **GIVEN** Silver layer has 10,000 PTR transactions for 2025
> - **WHEN** Lambda is invoked with `{"year": 2025, "mode": "incremental"}`
> - **THEN** Gold fact table contains all 10,000 transactions with enriched member/asset dimensions
> - **AND** Execution completes in <5 minutes

### 2. Edge Cases
[List 2-3 edge cases that must be handled]

**Example**:
> - **GIVEN** No transactions exist for specified year
> - **WHEN** Lambda executes
> - **THEN** Returns success with 0 rows processed, does not create empty Parquet file

### 3. Error Handling
[Specify how errors should be handled]

**Example**:
> - **GIVEN** S3 bucket is unavailable
> - **WHEN** Lambda attempts to write output
> - **THEN** Raises clear exception, logs error details, sends SNS alert, allows Step Functions retry

### 4. Performance Requirements
[If applicable, specify performance targets]

**Example**:
> - Process ≥1,000 transactions/second
> - Complete within Lambda 15-minute timeout
> - Memory usage <3GB (Lambda has 10GB available)

---

## 📝 Definition of Done Checklist

**Code**:
- [ ] Implementation complete and follows existing patterns
- [ ] Code adheres to style guide (Black, flake8, mypy passing)
- [ ] No hardcoded values (use environment variables or constants)
- [ ] Error handling comprehensive (try/except with specific exceptions)
- [ ] Logging added for key operations (using Python logging module)
- [ ] No secrets or credentials in code

**Testing**:
- [ ] Unit tests written for all functions (≥80% coverage)
- [ ] Integration tests written (if applicable)
- [ ] Manual testing performed against dev environment
- [ ] All tests passing locally: `pytest tests/ -v --cov`
- [ ] Edge cases covered in tests
- [ ] Error scenarios tested

**Infrastructure** (if applicable):
- [ ] Terraform configuration added/updated
- [ ] Terraform validate passes: `terraform validate`
- [ ] Terraform plan reviewed (no unexpected changes)
- [ ] Environment variables documented in `.env.example`
- [ ] IAM permissions updated (if needed)

**Documentation**:
- [ ] Inline code comments for complex logic
- [ ] Function docstrings (Google style)
- [ ] `/docs/CLAUDE.md` updated (if new commands/workflows)
- [ ] Technical docs updated (if architecture changes)
- [ ] README updated (if user-facing changes)

**Git**:
- [ ] Committed to feature branch: `feature/STORY-XXX-short-name`
- [ ] Commit messages follow Conventional Commits format
- [ ] No merge conflicts with `main`
- [ ] Branch pushed to GitHub

**Pull Request**:
- [ ] PR created with title: `feat(scope): short description`
- [ ] PR body references this issue: `Closes #XX`
- [ ] All PR checklist items completed
- [ ] CI/CD checks passing (GitHub Actions green)
- [ ] Code review requested

**Handoff**:
- [ ] Issue status updated to "In Review"
- [ ] Sprint board updated (if manual update needed)
- [ ] Blockers removed from downstream stories
- [ ] Any new dependencies documented

---

## 🗂️ Files to Modify

### Primary Implementation Files

- [ ] `path/to/main/file.py` - **Purpose**: [What changes are needed]
  - **Example**: `api/lambdas/build_fact_transactions/handler.py` - Create Lambda wrapper for fact table builder

- [ ] `path/to/helper/file.py` - **Purpose**: [What changes are needed]
  - **Example**: `ingestion/lib/parquet_writer.py` - Add upsert method for fact tables (may already exist)

### Configuration Files

- [ ] `infra/terraform/[module]/main.tf` - **Purpose**: [Infrastructure changes]
  - **Example**: `infra/terraform/api_lambdas.tf` - Add Lambda function definition

- [ ] `.env.example` - **Purpose**: [If new environment variables added]

- [ ] `requirements.txt` or `layers/[layer]/requirements.txt` - **Purpose**: [If new dependencies]

### Test Files

- [ ] `tests/unit/[module]/test_[feature].py` - **Purpose**: Unit tests
  - **Example**: `tests/unit/api/test_build_fact_transactions.py` - Test Lambda handler logic

- [ ] `tests/integration/test_[feature]_integration.py` - **Purpose**: Integration tests (if applicable)

### Documentation Files (if applicable)

- [ ] `docs/CLAUDE.md` - **Purpose**: [If new commands or workflows]
- [ ] `docs/agile/technical/LAMBDA_REQUIREMENTS_SPEC.md` - **Purpose**: [If new Lambda function]
- [ ] `README.md` - **Purpose**: [If user-facing changes]

---

## 🛠️ Implementation Guidance

### Step-by-Step Approach

#### 1. Setup & Planning (~2K tokens)

```bash
# Ensure you're on main and up-to-date
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/STORY-XXX-short-description

# Read context files (see "Context Files to Read" section below)
```

**Read Before Coding**:
- [ ] Full story in `/docs/agile/stories/[active|completed]/STORY_XXX_*.md`
- [ ] Relevant ADR in `/docs/agile/technical/ARCHITECTURE_DECISION_RECORD.md`
- [ ] Similar code examples (see "Code Patterns" section below)

#### 2. Implementation (Primary token usage - varies by story points)

**Code Patterns to Follow**:

**Lambda Handler Pattern** (if creating Lambda):
```python
# api/lambdas/[function_name]/handler.py
import json
import logging
import os
from typing import Any, Dict

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    [Brief description of what this Lambda does]

    Args:
        event: Lambda event (JSON)
        context: Lambda context

    Returns:
        Response dict with statusCode and body

    Raises:
        ValueError: If required parameters missing
        Exception: For unexpected errors
    """
    try:
        # Log incoming event
        logger.info(f"Received event: {json.dumps(event)}")

        # Validate input
        required_params = ["param1", "param2"]
        for param in required_params:
            if param not in event:
                raise ValueError(f"Missing required parameter: {param}")

        # Import and call script
        from scripts.[script_name] import main
        result = main(
            param1=event["param1"],
            param2=event.get("param2", "default_value")
        )

        # Log success
        logger.info(f"Execution successful: {result}")

        # Return success response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Success",
                "result": result
            })
        }

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }
```

**Terraform Lambda Resource Pattern**:
```hcl
# infra/terraform/api_lambdas.tf
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

**Test Pattern**:
```python
# tests/unit/api/test_function_name.py
import json
import pytest
from unittest.mock import MagicMock, patch
from api.lambdas.function_name.handler import lambda_handler

class TestLambdaHandler:
    """Test suite for function_name Lambda handler"""

    def test_successful_execution(self):
        """Test successful Lambda execution with valid input"""
        # Arrange
        event = {
            "param1": "value1",
            "param2": "value2"
        }
        context = MagicMock()

        # Act
        with patch('api.lambdas.function_name.handler.main') as mock_main:
            mock_main.return_value = {"rows_processed": 100}
            response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["message"] == "Success"
        assert body["result"]["rows_processed"] == 100

    def test_missing_required_parameter(self):
        """Test error handling for missing required parameter"""
        # Arrange
        event = {"param1": "value1"}  # Missing param2
        context = MagicMock()

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Missing required parameter" in body["error"]

    def test_unexpected_error_handling(self):
        """Test graceful handling of unexpected errors"""
        # Arrange
        event = {"param1": "value1", "param2": "value2"}
        context = MagicMock()

        # Act
        with patch('api.lambdas.function_name.handler.main') as mock_main:
            mock_main.side_effect = Exception("Unexpected error")
            response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 500
```

#### 3. Testing (~5-10K tokens depending on test complexity)

**Run Tests Locally**:
```bash
# Unit tests with coverage
pytest tests/unit/api/test_function_name.py -v --cov=api.lambdas.function_name

# All unit tests
pytest tests/unit/ -v --cov

# Integration tests (if applicable)
pytest tests/integration/test_function_name_integration.py -v

# Full test suite
make test
```

**Coverage Requirements**:
- Target: ≥80% coverage
- Check: `pytest --cov=[module] --cov-report=term-missing`

**Manual Testing** (if applicable):
```bash
# Package Lambda
make package-api

# Deploy to dev (if Terraform)
cd infra/terraform
terraform plan
terraform apply  # Only if safe

# Test via AWS CLI
aws lambda invoke \
  --function-name congress-disclosures-development-api-function_name \
  --payload '{"param1":"value1","param2":"value2"}' \
  output.json

# Check output
cat output.json
```

#### 4. Code Quality Checks (~2K tokens)

```bash
# Format code
black api/lambdas/function_name/

# Lint
flake8 api/lambdas/function_name/

# Type check
mypy api/lambdas/function_name/

# Run all checks
make check-all
```

#### 5. Documentation (~3-5K tokens if updates needed)

**Update `/docs/CLAUDE.md`** (if new commands):
```markdown
### Quick Deploy Function Name
```bash
make quick-deploy-function-name  # Package + deploy directly
```
```

**Update Lambda Spec** (if new Lambda):
Add entry to `/docs/agile/technical/LAMBDA_REQUIREMENTS_SPEC.md`

#### 6. Git Commit & Push (~1-2K tokens)

```bash
# Stage changes
git add api/lambdas/function_name/
git add infra/terraform/api_lambdas.tf
git add tests/unit/api/test_function_name.py

# Commit with conventional commit message
git commit -m "feat(gold): add build_fact_transactions Lambda wrapper

- Create Lambda handler for fact table builder script
- Add Terraform configuration with 5min timeout, 2GB memory
- Include unit tests with 85% coverage
- Add error handling and logging

Closes #XX"

# Push to GitHub
git push origin feature/STORY-XXX-short-description
```

#### 7. Create Pull Request (~2-3K tokens)

**PR Title Format**:
```
feat(scope): short description
```

Examples:
- `feat(gold): add build_fact_transactions Lambda wrapper`
- `fix(ingestion): handle S3 timeout errors gracefully`
- `refactor(extraction): simplify PDF text detection logic`

**PR Body Template**:
```markdown
## Summary
[1-2 sentence description of changes]

## Related Issue
Closes #XX

## Changes Made
- [Bullet point 1]
- [Bullet point 2]
- [Bullet point 3]

## Testing
- [x] Unit tests passing (85% coverage)
- [x] Integration tests passing
- [x] Manual testing completed

## Checklist
- [x] Code follows style guide
- [x] Tests written and passing
- [x] Documentation updated
- [x] No merge conflicts
```

---

## 📚 Context Files to Read

### **MUST READ** (Before Starting)

1. **Full Story**: `/docs/agile/stories/[active|completed]/STORY_XXX_*.md`
   - Contains full acceptance criteria, technical tasks, DoD

2. **Project Guide**: `/docs/CLAUDE.md`
   - Project overview, common commands, patterns

3. **Similar Code**: [Link to existing similar implementation]
   - Example: If building Lambda, review another Lambda in `api/lambdas/`

4. **Relevant ADR**: `/docs/agile/technical/ARCHITECTURE_DECISION_RECORD.md`
   - Search for relevant decisions (e.g., "ADR-002: Lambda Wrapper Pattern")

### **OPTIONAL** (If Stuck or Need Clarification)

5. **Lambda Spec**: `/docs/agile/technical/LAMBDA_REQUIREMENTS_SPEC.md`
   - If creating or modifying Lambda function

6. **Data Contracts**: `/docs/agile/technical/DATA_CONTRACTS.md`
   - If touching data schemas (Bronze/Silver/Gold)

7. **State Machine Spec**: `/docs/agile/technical/STATE_MACHINE_SPEC.md`
   - If integrating with Step Functions

8. **Testing Strategy**: `/docs/agile/technical/TESTING_STRATEGY.md`
   - For test design patterns and best practices

9. **Contributing Guide**: `/CONTRIBUTING.md`
   - Code style, commit conventions, PR process

---

## ⚠️ Known Gotchas & Tips

### Common Issues

1. **Lambda Timeout (900s max)**
   - **Issue**: Large datasets can exceed 15-minute Lambda timeout
   - **Solution**: Use pagination, process in batches, or consider Step Functions Map state
   - **Example**: Process 1,000 rows at a time instead of all at once

2. **DuckDB S3 Connection**
   - **Issue**: DuckDB httpfs extension requires correct S3 paths
   - **Solution**: Use format `s3://bucket/key`, ensure IAM permissions, test with small dataset first
   - **Example**: `INSTALL httpfs; LOAD httpfs; SELECT * FROM read_parquet('s3://bucket/path/*.parquet');`

3. **Terraform State Lock**
   - **Issue**: Terraform state locked from previous failed run
   - **Solution**: Check DynamoDB lock table, wait 5 minutes, or force-unlock (caution!)
   - **Example**: `terraform force-unlock [LOCK_ID]` (only if safe)

4. **Test Data Isolation**
   - **Issue**: Tests modifying shared test data
   - **Solution**: Use pytest fixtures, create fresh test data per test
   - **Example**: Use `@pytest.fixture(scope="function")` not `scope="module"`

5. **Environment Variables**
   - **Issue**: Forgetting to add new env vars to Lambda config
   - **Solution**: Update both `.env.example` and Terraform `environment.variables`
   - **Example**: If adding `NEW_VAR`, update both files

### Best Practices

✅ **DO**:
- Use existing patterns from similar code
- Write tests BEFORE implementation (TDD when possible)
- Log key operations for debugging
- Handle errors gracefully with specific exceptions
- Update documentation as you go (don't defer)
- Commit frequently with descriptive messages
- Ask for help early if blocked

❌ **DON'T**:
- Hardcode values (use constants or env vars)
- Skip tests ("I'll add them later")
- Commit commented-out code
- Mix refactoring with new features in same PR
- Push directly to `main` (always use feature branches)
- Ignore linting errors ("I'll fix them later")

---

## 🎯 Success Criteria

### How You Know You're Done

✅ **All acceptance criteria verified** (test each GIVEN/WHEN/THEN)
✅ **All tests passing**: `pytest tests/ -v --cov` shows ≥80% coverage
✅ **Code quality passing**: `black . && flake8 . && mypy .` exit 0
✅ **PR created** with:
   - Title: `feat(scope): description`
   - Body: References this issue `Closes #XX`
   - All PR template checklist items completed
✅ **No merge conflicts** with `main`
✅ **CI/CD passing**: GitHub Actions all green
✅ **Documentation updated** (if applicable)

### Definition of Success (User Perspective)

- [ ] User can achieve the story goal without errors
- [ ] Edge cases handled gracefully
- [ ] Error messages clear and actionable
- [ ] Performance meets requirements
- [ ] Code is maintainable by other developers
- [ ] Future changes won't break easily (good test coverage)

---

## 🔄 Handoff Checklist

**Before Marking "Done", Ensure**:

- [ ] **Code pushed**: Branch exists on GitHub remote
- [ ] **PR created**: Pull request linked to this issue
- [ ] **CI/CD passing**: All GitHub Actions checks green
- [ ] **Review requested**: Auto-assigned or manually requested
- [ ] **Issue updated**: Status set to "In Review", moved to correct column
- [ ] **Blockers removed**: Any downstream stories unblocked
- [ ] **Documentation updated**: Sprint board reflects progress
- [ ] **Handoff notes**: Any special deployment instructions in PR comments

**For Reviewer**:
- Acceptance criteria location: [Link to story file]
- Manual test instructions: [Specific steps to verify functionality]
- Deployment notes: [Any special considerations]

---

## 🆘 Emergency Contacts & Escalation

### If Blocked

1. **Check Dependencies**: Are all prerequisites actually completed?
   - Review issue links in "Dependencies" section
   - Verify PRs merged and deployed

2. **Review Similar Code**: Look for existing implementations
   - Browse `api/lambdas/` for similar Lambda functions
   - Check git history: `git log --all --grep="similar keyword"`

3. **Read Technical Specs**: Deep dive into architecture docs
   - ADRs explain "why" decisions were made
   - Data contracts show exact schemas expected

4. **Search Codebase**: Find patterns and examples
   - `grep -r "pattern" --include="*.py"`
   - Look in `tests/` for test examples

5. **Escalate**: Comment on this GitHub Issue
   - Describe what you've tried
   - Specify what's blocking you
   - Tag with `@mention` if urgent

### Rollback Procedure

**If deployment causes issues**:

```bash
# Step 1: Revert code changes
git revert [commit-sha]
git push origin main

# Step 2: Revert Terraform (if infrastructure changed)
cd infra/terraform
git checkout main -- [changed-file].tf
terraform plan  # Review changes
terraform apply  # Revert infrastructure

# Step 3: Notify team
# - Comment on PR with failure details
# - Update issue with "blocked" label
# - Tag reviewer for assistance
```

### Getting Help

- **Stuck on implementation?** → Review ADRs and similar code
- **Tests failing?** → Check test patterns in existing test files
- **Terraform errors?** → Review existing Terraform modules
- **Unclear requirements?** → Comment on issue, ask for clarification
- **Urgent blocker?** → Tag issue with `blocked` label, mention reviewer

---

## 📊 Metadata (For Tracking)

**Agent Performance Tracking** (To be filled by agent):
- **Start Time**: [YYYY-MM-DD HH:MM UTC]
- **End Time**: [YYYY-MM-DD HH:MM UTC]
- **Actual Tokens Used**: [X tokens] (vs estimated [Y tokens])
- **Token Efficiency**: [X%] (actual/estimated)
- **Blockers Encountered**: [Description or "None"]
- **Tests Added**: [X unit tests, Y integration tests]
- **Lines of Code**: [+XXX, -YYY]
- **Coverage**: [X%]
- **Commits**: [X commits]

**Quality Metrics**:
- **First-time PR approval**: [Yes/No]
- **Code review rounds**: [X]
- **Bugs found in review**: [X]
- **Deployment success**: [Yes/No/Pending]

---

**Template Version**: 1.0
**Last Updated**: 2025-12-26
**Maintained By**: Project Management Team

---

## Quick Reference

**Key Commands**:
```bash
# Setup
git checkout -b feature/STORY-XXX-description

# Quality Checks
make check-all          # Format, lint, type-check, test
pytest tests/ -v --cov  # Run tests with coverage

# Deploy
make package-api        # Package Lambda
terraform plan          # Preview infrastructure changes
terraform apply         # Deploy infrastructure

# Git
git add .
git commit -m "feat(scope): description"
git push origin feature/STORY-XXX-description
```

**Need Help?** Read `.github/AGENT_ONBOARDING.md` for detailed walkthrough.
