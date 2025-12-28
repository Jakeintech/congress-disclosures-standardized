# TASK-XXX: [Technical Task Title]

**Type**: Technical Task
**Parent Story**: [STORY-XXX if applicable, or "Standalone"]
**Sprint**: [Sprint X - Name]
**Story Points**: [1, 2, 3, 5]
**Priority**: [P0-Critical | P1-High | P2-Medium | P3-Low]
**Status**: [To Do | In Progress | In Review | Done]
**Assignee**: [Name]
**Created**: [YYYY-MM-DD]
**Updated**: [YYYY-MM-DD]

---

## Task Description

**Objective**: [Clear, specific technical objective]

**Why This is Needed**: [Technical justification - technical debt, performance, scalability, etc.]

**Scope**: [What's included and what's explicitly NOT included]

---

## Technical Requirements

### Must Have
- [ ] Requirement 1
- [ ] Requirement 2
- [ ] Requirement 3

### Nice to Have
- [ ] Enhancement 1
- [ ] Enhancement 2

### Out of Scope
- Explicitly NOT doing X
- Explicitly NOT doing Y

---

## Implementation Steps

### Step 1: [Preparation/Setup]
```bash
# Commands or setup needed
```
- [ ] Subtask 1.1
- [ ] Subtask 1.2

### Step 2: [Core Implementation]
```python
# Pseudocode or key logic
```
- [ ] Subtask 2.1
- [ ] Subtask 2.2

### Step 3: [Testing]
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance tests

### Step 4: [Documentation]
- [ ] Code comments
- [ ] Technical documentation
- [ ] Runbook updates

---

## Files to Create/Modify

### New Files
- [ ] `path/to/new_file.py` - [Purpose]
- [ ] `tests/unit/test_new_file.py` - [Tests]

### Modified Files
- [ ] `path/to/existing_file.py` - [Changes needed]
  - Line X: [Change description]
  - Function Y: [Modification]

### Configuration Changes
- [ ] `config_file.yaml` - [New settings]
- [ ] `.env.example` - [New environment variables]

---

## Testing Requirements

### Unit Tests
**File**: `tests/unit/[module]/test_[feature].py`

```python
import pytest

def test_[specific_functionality]():
    """Test [what this verifies]."""
    # Arrange

    # Act

    # Assert
    assert expected == actual
```

**Test Cases**:
1. Happy path test
2. Edge case test
3. Error handling test
4. Performance test (if applicable)

### Integration Tests
**File**: `tests/integration/test_[feature]_integration.py`

```python
def test_[integration_scenario]():
    """Test integration with [external system/component]."""
    pass
```

### Performance Benchmarks
- [ ] Latency target: [X ms/seconds]
- [ ] Throughput target: [X ops/second]
- [ ] Memory usage: [< X MB]
- [ ] CPU usage: [< X %]

---

## Definition of Done

### Code
- [ ] Implementation complete
- [ ] Code reviewed and approved
- [ ] No linting errors (flake8, black)
- [ ] Type hints added (mypy passing)
- [ ] No security vulnerabilities (bandit scan)

### Testing
- [ ] Unit tests passing (≥80% coverage)
- [ ] Integration tests passing
- [ ] Manual testing completed
- [ ] Performance benchmarks met

### Documentation
- [ ] Inline code comments for complex logic
- [ ] Docstrings for all public functions/classes
- [ ] Technical documentation updated
- [ ] Architecture diagrams updated (if applicable)

### Deployment
- [ ] Changes deployed to dev
- [ ] Changes deployed to staging
- [ ] Smoke tests passing
- [ ] Rollback procedure tested

---

## Dependencies

### Technical Dependencies
- [ ] Library/package: [name@version]
- [ ] AWS service: [service name + IAM permissions]
- [ ] External API: [API name + credentials]

### Blocking Tasks
- [ ] TASK-XXX: [Description] must be completed first

### Blocked Tasks
- [ ] TASK-YYY: [Description] waiting on this task

---

## Architecture Considerations

### Design Decisions
1. **Decision**: [What was decided]
   - **Rationale**: [Why]
   - **Alternatives Considered**: [Other options]
   - **Trade-offs**: [Pros/cons]

### Impact Analysis
- **Performance**: [Expected impact]
- **Scalability**: [How this scales]
- **Cost**: [AWS cost implications]
- **Security**: [Security considerations]
- **Maintainability**: [Long-term maintenance]

### Architectural Patterns Used
- [ ] Factory Pattern
- [ ] Strategy Pattern
- [ ] Repository Pattern
- [ ] [Other pattern]

---

## Rollback Plan

### Quick Rollback (< 5 minutes)
```bash
# Emergency revert commands
git revert [commit-sha]
git push origin main
```

### Infrastructure Rollback
```bash
# Terraform rollback
cd infra/terraform
git checkout main -- [file].tf
terraform apply
```

### Data Rollback
- **Backup Location**: [S3 path or snapshot ID]
- **Recovery Steps**: [Detailed steps]
- **Validation**: [How to verify success]

---

## Monitoring & Observability

### Metrics to Track
- [ ] CloudWatch metric: [metric name] - [threshold]
- [ ] Custom metric: [metric name] - [threshold]
- [ ] Log pattern: [what to search for]

### Alerts to Configure
- [ ] Alert 1: [Condition] → [Action]
- [ ] Alert 2: [Condition] → [Action]

### Dashboards to Update
- [ ] Dashboard name: [Widgets to add]

### Logging Strategy
```python
# Logging pattern
logger.info("Operation started", extra={
    "operation": "task_name",
    "input": input_data,
})
```

---

## Security Considerations

### Authentication & Authorization
- [ ] IAM roles configured correctly
- [ ] Least privilege principle followed
- [ ] Credentials stored in Secrets Manager/SSM

### Data Protection
- [ ] Sensitive data encrypted at rest
- [ ] Sensitive data encrypted in transit
- [ ] No secrets in code or logs

### Compliance
- [ ] GDPR compliance (if applicable)
- [ ] Data retention policies followed
- [ ] Audit logging enabled

### Vulnerability Scanning
```bash
# Security scan commands
bandit -r path/to/code
safety check
```

---

## Estimated Effort

| Activity | Time Estimate |
|----------|--------------|
| Research & Design | [X hours] |
| Implementation | [X hours] |
| Unit Testing | [X hours] |
| Integration Testing | [X hours] |
| Code Review | [X hours] |
| Documentation | [X hours] |
| Deployment | [X hours] |
| **Total** | **[X hours]** |

**Story Points**: [X points] (based on [fibonacci scale] and team velocity)

---

## Success Criteria

### Functional Success
- [ ] Feature works as designed
- [ ] All acceptance criteria met
- [ ] No regressions introduced

### Non-Functional Success
- [ ] Performance targets met
- [ ] Security requirements satisfied
- [ ] Scalability validated
- [ ] Cost within budget

### Quality Success
- [ ] Code coverage ≥ 80%
- [ ] No critical bugs
- [ ] Technical debt minimized

---

## Notes & Context

### Research Findings
- [Link to spike or POC]
- [Key learnings]
- [Surprises or gotchas]

### Technical Debt
- **Created**: [Any shortcuts taken]
- **Repayment Plan**: [When/how to address]

### Future Enhancements
- Enhancement 1: [Description]
- Enhancement 2: [Description]

---

## Sign-Off

- [ ] **Developer**: Implementation complete - [Name] - [Date]
- [ ] **Code Reviewer**: Approved - [Name] - [Date]
- [ ] **Tech Lead**: Architecture approved - [Name] - [Date]
- [ ] **DevOps**: Deployment verified - [Name] - [Date]

---

## Related Links

- **Parent Story**: [STORY-XXX]
- **Pull Request**: [GitHub PR link]
- **Architecture Docs**: [Link]
- **Related Tasks**: TASK-AAA, TASK-BBB
