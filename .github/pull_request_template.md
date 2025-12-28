## 📋 Agile Tracking

**Story ID**: <!-- STORY-XXX (if applicable) -->
**Sprint**: <!-- Sprint 3, Sprint 4, or Backlog -->
**Story Points**: <!-- 0, 1, 2, 3, 5, or 8 -->
**Estimated Tokens**: <!-- Based on story points -->
**Actual Tokens**: <!-- Fill after completion (check usage in Claude Code) -->

## Description

<!-- Provide a clear and concise description of your changes -->

## Type of Change

<!-- Mark the relevant option(s) with an 'x' -->

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Infrastructure change (Terraform)
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Test addition/improvement

## Related Issues

<!-- Link to related issues using #issue_number -->

Fixes #
Closes #
Related to #

## Changes Made

<!-- Describe the changes in detail. What did you do and why? -->

-
-
-

## Testing

<!-- Describe the tests you ran to verify your changes -->

### Test Configuration

- **Python Version**:
- **Terraform Version**:
- **AWS Region**:

### Tests Run

- [ ] Unit tests pass locally (`pytest tests/unit/`)
- [ ] Integration tests pass (`pytest tests/integration/`)
- [ ] Linting passes (`flake8`, `pylint`, `black --check`)
- [ ] Type checking passes (`mypy`)
- [ ] Terraform plan succeeds (if infrastructure changes)
- [ ] Manual testing completed

### Test Evidence

<!-- Paste relevant test output or screenshots -->

<details>
<summary>Test output</summary>

```
Paste test output here
```

</details>

## Documentation

<!-- Have you updated relevant documentation? -->

- [ ] README.md updated (if user-facing changes)
- [ ] ARCHITECTURE.md updated (if infrastructure/design changes)
- [ ] DEPLOYMENT.md updated (if deployment process changes)
- [ ] Inline code comments added/updated
- [ ] Docstrings added/updated
- [ ] .env.example updated (if new env vars added)

## Security & Compliance

<!-- Confirm no secrets or compliance issues -->

- [ ] No AWS credentials, API keys, or secrets committed
- [ ] No sensitive data in code or comments
- [ ] Changes comply with 5 U.S.C. § 13107 (see [LEGAL_NOTES.md](docs/LEGAL_NOTES.md))
- [ ] .gitignore updated (if needed)

## AWS Free Tier Impact

<!-- Assess impact on AWS costs -->

- [ ] This change stays within AWS free tier limits
- [ ] This change may exceed free tier (explain below)
- [ ] Not applicable (no AWS changes)

<!-- If may exceed free tier, explain cost impact and mitigation -->

## Breaking Changes

<!-- If this is a breaking change, describe the impact and migration path -->

**Does this PR introduce breaking changes?**
- [ ] Yes (describe below)
- [ ] No

<!-- If yes, explain:
- What breaks?
- How should users migrate?
- Is there a deprecation period?
-->

## Screenshots / Logs

<!-- If applicable, add screenshots or relevant logs -->

<details>
<summary>Screenshots/Logs</summary>

<!-- Paste or attach here -->

</details>

## Checklist

<!-- Review before submitting -->

- [ ] My code follows the project's coding standards
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings or errors
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Additional Notes

<!-- Any additional information for reviewers -->
