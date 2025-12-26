# STORY-037: Configure CI/CD Test Pipeline

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 2 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** DevOps engineer
**I want** automated testing in CI/CD
**So that** every PR runs full test suite

## Acceptance Criteria
- **GIVEN** GitHub Actions workflow
- **WHEN** PR is created
- **THEN** Runs unit tests (required)
- **AND** Runs integration tests (if AWS creds available)
- **AND** Reports coverage to Codecov
- **AND** Blocks merge if coverage < 80%

## Technical Tasks
- [ ] Update `.github/workflows/test.yml`
- [ ] Add unit test job
- [ ] Add integration test job (conditional)
- [ ] Configure coverage reporting
- [ ] Add coverage threshold check
- [ ] Test workflow with sample PR

## Implementation
```yaml
name: Tests
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: pytest tests/unit/ --cov --cov-report=xml
      - name: Check coverage
        run: |
          COVERAGE=$(python -c "import xml.etree.ElementTree as ET; tree = ET.parse('coverage.xml'); print(float(tree.getroot().attrib['line-rate']) * 100)")
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "Coverage $COVERAGE% is below 80%"
            exit 1
          fi
```

## Estimated Effort: 2 hours
**Target**: Jan 3, 2026
