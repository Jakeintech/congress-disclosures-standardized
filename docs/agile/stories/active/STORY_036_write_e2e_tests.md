# STORY-036: Write 10+ E2E Tests

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 3 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** QA engineer
**I want** end-to-end tests for full workflows
**So that** we verify user-facing functionality

## Acceptance Criteria
- **GIVEN** E2E test suite
- **WHEN** I run `pytest tests/e2e/`
- **THEN** 10+ tests execute
- **AND** Tests full pipeline + API + website
- **AND** All tests passing

## Technical Tasks
- [ ] Write full pipeline execution test (2 tests)
- [ ] Write API endpoint tests (3 tests)
- [ ] Write Playwright website tests (5 tests)
- [ ] Configure test data
- [ ] Add E2E to CI/CD

## Test Structure
```
tests/e2e/
├── test_full_pipeline.py (2 tests)
├── test_api_endpoints.py (3 tests)
└── playwright/
    ├── test_dashboard.py (2 tests)
    ├── test_members_page.py (2 tests)
    └── test_transactions_page.py (1 test)
```

## Estimated Effort: 3 hours
**Target**: Jan 3, 2026
