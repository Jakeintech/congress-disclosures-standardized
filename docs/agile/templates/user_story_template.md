# STORY-XXX: [Story Title]

**Epic**: [EPIC-XXX Epic Name]
**Sprint**: [Sprint X - Name]
**Story Points**: [1, 2, 3, 5, 8, 13]
**Priority**: [P0-Critical | P1-High | P2-Medium | P3-Low]
**Status**: [To Do | In Progress | In Review | Done]
**Assignee**: [Name]
**Created**: [YYYY-MM-DD]
**Updated**: [YYYY-MM-DD]

---

## User Story

**As a** [role/persona]
**I want** [feature/capability]
**So that** [business value/outcome]

## Business Value

- **[Value Category]**: [Specific measurable benefit]
- **[Value Category]**: [Specific measurable benefit]
- **[Value Category]**: [Specific measurable benefit]

**ROI Estimate**: [Cost savings, time saved, risk mitigation value]

---

## Acceptance Criteria

### Scenario 1: [Primary Happy Path]
- **GIVEN** [initial context/state]
- **WHEN** [action/trigger]
- **THEN** [expected outcome]
- **AND** [additional expected outcomes]

### Scenario 2: [Edge Case or Alternative Path]
- **GIVEN** [initial context/state]
- **WHEN** [action/trigger]
- **THEN** [expected outcome]

### Scenario 3: [Error Handling]
- **GIVEN** [error condition]
- **WHEN** [action that triggers error]
- **THEN** [graceful handling behavior]

---

## Technical Tasks

### Development
- [ ] Task 1: [Specific implementation step]
- [ ] Task 2: [Specific implementation step]
- [ ] Task 3: [Specific implementation step]

### Testing
- [ ] Write unit tests (target: 80%+ coverage)
- [ ] Write integration tests
- [ ] Manual testing checklist completed

### Documentation
- [ ] Update technical documentation
- [ ] Update user-facing documentation
- [ ] Update CLAUDE.md if applicable

### Deployment
- [ ] Terraform changes (if applicable)
- [ ] Environment variables configured
- [ ] Rollback plan documented

---

## Definition of Done

### Code Quality
- [ ] Code complete and committed to feature branch
- [ ] Code follows project style guide (Black, flake8)
- [ ] Type hints added (mypy passing)
- [ ] No linting errors

### Testing
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing (if applicable)
- [ ] Test coverage ≥ 80% for new code
- [ ] Manual testing completed and documented

### Review & Deployment
- [ ] Code review approved by peer
- [ ] All CI/CD checks passing
- [ ] Merged to main branch
- [ ] Deployed to dev/staging environment
- [ ] Smoke tests passing in deployed environment

### Documentation
- [ ] Technical documentation updated
- [ ] API documentation updated (if applicable)
- [ ] CLAUDE.md updated with new commands/workflows
- [ ] Runbook updated (if operational changes)

### Acceptance
- [ ] All acceptance criteria verified
- [ ] Product owner/stakeholder approval
- [ ] No known critical bugs

---

## Dependencies

### Blocked By
- [ ] STORY-XXX: [Story title] - [Reason]
- [ ] STORY-YYY: [Story title] - [Reason]

### Blocks
- [ ] STORY-ZZZ: [Story title] - [Reason]

### External Dependencies
- [ ] AWS service availability
- [ ] Third-party API access
- [ ] Data availability

---

## Test Requirements

### Unit Tests
**File**: `tests/unit/[module]/test_[feature].py`

```python
def test_[scenario_1]():
    """Test [specific behavior]."""
    # Arrange
    # Act
    # Assert
    pass

def test_[scenario_2]():
    """Test [edge case]."""
    pass

def test_[scenario_3]():
    """Test [error handling]."""
    pass
```

**Coverage Target**: ≥ 80%

### Integration Tests
**File**: `tests/integration/test_[feature]_integration.py`

```python
def test_[end_to_end_scenario]():
    """Test full workflow integration."""
    # Setup
    # Execute
    # Verify
    # Cleanup
    pass
```

### Manual Testing Checklist
- [ ] Test Case 1: [Description]
  - Steps: [Step by step]
  - Expected: [Result]
  - Actual: [Result]
- [ ] Test Case 2: [Description]
  - Steps: [Step by step]
  - Expected: [Result]
  - Actual: [Result]

---

## Rollback Plan

### If Deployment Fails
```bash
# Step 1: Revert code changes
git revert [commit-sha]
git push origin main

# Step 2: Revert infrastructure (if Terraform changes)
cd infra/terraform
git checkout main -- [changed-file].tf
terraform apply

# Step 3: Verify system state
[verification commands]
```

### If Production Issues Occur
1. **Immediate**: [Emergency mitigation steps]
2. **Short-term**: [Temporary workaround]
3. **Long-term**: [Proper fix in next sprint]

### Data Recovery
- [ ] Backup location: [S3 path or database snapshot]
- [ ] Recovery procedure: [Step by step]
- [ ] Validation: [How to verify data integrity]

---

## Estimated Effort

- **Development**: [X hours]
- **Testing**: [X hours]
- **Code Review**: [X hours]
- **Documentation**: [X hours]
- **Deployment**: [X hours]
- **Total**: [X hours]

**Story Points Justification**: [Why this story is X points]

---

## Notes & Context

### Technical Context
- [Relevant architectural decisions]
- [Technology choices]
- [Performance considerations]

### Business Context
- [Stakeholder requirements]
- [User feedback that led to this story]
- [Related features or initiatives]

### Risks & Mitigations
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| [Risk description] | High/Med/Low | High/Med/Low | [How to prevent/handle] |

### Research & Spike Findings
- [Any research done before implementation]
- [POC results]
- [Alternative approaches considered]

---

## Acceptance Sign-Off

- [ ] **Developer**: Code complete and tested - [Name] - [Date]
- [ ] **Code Reviewer**: Code review passed - [Name] - [Date]
- [ ] **QA/Tester**: Testing complete - [Name] - [Date]
- [ ] **Product Owner**: Acceptance criteria met - [Name] - [Date]
- [ ] **Tech Lead**: Architecture approved - [Name] - [Date]

---

## Related Links

- **Epic**: [Link to epic]
- **Sprint Board**: [Link to sprint board]
- **Related Stories**: STORY-AAA, STORY-BBB
- **Documentation**: [Link to relevant docs]
- **Pull Request**: [GitHub PR link]
- **Deployed Version**: [Version tag or commit SHA]
