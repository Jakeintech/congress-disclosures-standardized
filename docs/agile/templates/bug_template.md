# BUG-XXX: [Bug Title - Brief Description]

**Type**: Bug
**Severity**: [Critical | High | Medium | Low]
**Priority**: [P0-Critical | P1-High | P2-Medium | P3-Low]
**Status**: [New | Investigating | In Progress | Fixed | Verified | Closed]
**Sprint**: [Sprint X - Name, or "Backlog"]
**Story Points**: [1, 2, 3, 5]
**Assignee**: [Name]
**Reporter**: [Name]
**Found In Version**: [Version or commit SHA]
**Target Fix Version**: [Version]
**Created**: [YYYY-MM-DD]
**Updated**: [YYYY-MM-DD]

---

## Bug Summary

**Issue**: [Clear, concise description of the problem]

**Impact**: [Who/what is affected and how severely]

**Environment**:
- Platform: [AWS Lambda, local dev, etc.]
- Region: [us-east-1, etc.]
- OS: [If applicable]
- Python Version: [3.11, etc.]

---

## Severity Classification

### Critical (P0)
- [ ] System is down or completely unusable
- [ ] Data loss or corruption
- [ ] Security vulnerability
- [ ] Financial impact > $100/day

### High (P1)
- [ ] Major feature broken
- [ ] Significant performance degradation
- [ ] Affects multiple users
- [ ] Workaround is difficult

### Medium (P2)
- [ ] Minor feature broken
- [ ] Workaround exists and is reasonable
- [ ] Cosmetic issues with functional impact

### Low (P3)
- [ ] Cosmetic issues only
- [ ] Edge case or rare scenario
- [ ] Enhancement disguised as bug

**This bug is**: [Severity] because [justification]

---

## Steps to Reproduce

### Prerequisites
- [ ] Prerequisite 1 (e.g., "Lambda function deployed")
- [ ] Prerequisite 2 (e.g., "Test data in S3")
- [ ] Prerequisite 3 (e.g., "AWS credentials configured")

### Reproduction Steps
1. Step 1: [Specific action]
2. Step 2: [Specific action]
3. Step 3: [Specific action]
4. Observe: [What happens]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Frequency
- [ ] Always (100%)
- [ ] Frequently (>50%)
- [ ] Sometimes (10-50%)
- [ ] Rarely (<10%)
- [ ] Once

---

## Error Information

### Error Message
```
[Paste full error message here]
```

### Stack Trace
```python
Traceback (most recent call last):
  File "path/to/file.py", line XXX, in function_name
    [relevant stack trace]
[Full error traceback]
```

### Logs
```
[Relevant log entries]
[Include timestamps]
[Include context before/after error]
```

### CloudWatch Log Insights Query
```sql
fields @timestamp, @message
| filter @message like /ERROR/
| filter request_id = "[request-id]"
| sort @timestamp desc
| limit 100
```

---

## Root Cause Analysis

### Investigation Findings
1. **What went wrong**: [Technical explanation]
2. **Why it went wrong**: [Root cause]
3. **When it started**: [Version/commit/date]

### Root Cause
[Detailed explanation of the underlying issue]

### Contributing Factors
- Factor 1: [e.g., "Missing input validation"]
- Factor 2: [e.g., "Race condition in concurrent processing"]
- Factor 3: [e.g., "Insufficient error handling"]

### Why This Wasn't Caught Earlier
- [ ] Missing test coverage
- [ ] Edge case not considered
- [ ] Regression from recent change
- [ ] New scenario not in test suite

---

## Fix Implementation

### Proposed Solution
[Description of the fix]

### Alternative Solutions Considered
1. **Option 1**: [Description]
   - Pros: [Advantages]
   - Cons: [Disadvantages]
   - Decision: [Chosen or rejected, why]

2. **Option 2**: [Description]
   - Pros: [Advantages]
   - Cons: [Disadvantages]
   - Decision: [Chosen or rejected, why]

### Chosen Solution
[Detailed description of selected fix]

**Why This Solution**: [Justification]

---

## Files Affected

### To Be Modified
- [ ] `path/to/file1.py` (line XXX-YYY)
  - Change: [Description]
- [ ] `path/to/file2.py` (line XXX-YYY)
  - Change: [Description]

### To Be Created
- [ ] `tests/unit/test_bugfix_XXX.py`
  - Purpose: [Regression test]

### Configuration Changes
- [ ] `config.yaml` - [Change needed]
- [ ] Environment variables - [New vars]

---

## Testing Plan

### Regression Test
**File**: `tests/unit/test_bug_XXX_regression.py`

```python
def test_bug_XXX_fixed():
    """Regression test for BUG-XXX.

    Reproduces the original bug scenario and verifies
    it no longer occurs.
    """
    # Setup: Reproduce original bug conditions

    # Execute: Trigger the bug scenario

    # Assert: Verify bug is fixed
    assert expected_behavior()
```

### Manual Testing Checklist
- [ ] Test original reproduction steps → Should NOT reproduce bug
- [ ] Test related functionality → Should still work
- [ ] Test edge cases → Should handle gracefully
- [ ] Test error scenarios → Should fail gracefully

### Automated Tests Added
- [ ] Unit test for bug scenario
- [ ] Integration test (if applicable)
- [ ] Performance test (if performance bug)

---

## Definition of Done

### Fix Complete
- [ ] Root cause identified and documented
- [ ] Fix implemented
- [ ] Code reviewed and approved
- [ ] All existing tests passing
- [ ] New regression test added and passing

### Testing Complete
- [ ] Manual testing completed
- [ ] Automated tests added
- [ ] No new bugs introduced (regression testing)
- [ ] Performance validated (if applicable)

### Documentation
- [ ] Root cause documented
- [ ] Fix documented
- [ ] Runbook updated (if operational fix)
- [ ] Known issues list updated

### Deployment
- [ ] Fix deployed to dev/staging
- [ ] Fix verified in staging
- [ ] Fix deployed to production
- [ ] Monitoring confirms issue resolved

---

## Rollback Plan

### If Fix Causes New Issues
```bash
# Immediate rollback
git revert [commit-sha]
git push origin main

# Redeploy previous version
[deployment commands]
```

### Contingency
- **Plan B**: [Alternative workaround if fix doesn't work]
- **Emergency Contact**: [Who to notify if issues persist]

---

## Impact Analysis

### User Impact
- **Users Affected**: [Number or percentage]
- **Business Impact**: [Revenue, reputation, compliance]
- **Workaround Available**: [Yes/No - Description]

### System Impact
- **Performance**: [Any performance implications]
- **Data**: [Any data integrity concerns]
- **Dependencies**: [Other systems affected]

### Timeline
- **Bug Introduced**: [Date/version]
- **Bug Discovered**: [Date]
- **Time to Fix**: [Hours/days]
- **Downtime**: [If any]

---

## Prevention Strategy

### How to Prevent This in Future

#### Code Changes
- [ ] Add input validation
- [ ] Add error handling
- [ ] Add logging for debugging

#### Testing Improvements
- [ ] Add test case for this scenario
- [ ] Improve test coverage for [module]
- [ ] Add integration test

#### Process Improvements
- [ ] Update code review checklist
- [ ] Add to regression test suite
- [ ] Update development guidelines

#### Monitoring Improvements
- [ ] Add CloudWatch alarm for [metric]
- [ ] Add logging for [scenario]
- [ ] Create dashboard widget for [monitoring]

---

## Related Bugs & Issues

### Duplicate Bugs
- BUG-YYY: [Duplicate or related issue]

### Related Bugs
- BUG-ZZZ: [Similar issue in different component]

### Caused By
- STORY-AAA: [Feature that introduced this bug]
- CHANGE-BBB: [Change that caused regression]

### Blocks
- STORY-CCC: [Can't complete this story until bug fixed]

---

## Monitoring & Verification

### How to Verify Fix
```bash
# Commands to verify bug is fixed
[verification commands]
```

### Metrics to Monitor
- [ ] Error rate: Should decrease to near 0%
- [ ] Latency: Should return to normal
- [ ] Success rate: Should return to 99%+

### CloudWatch Alarms
- [ ] Alarm name: [Threshold]
- [ ] Should not trigger after fix deployed

---

## Communication Plan

### Internal Communication
- [ ] Notify team in Slack/Teams
- [ ] Update stakeholders
- [ ] Post-mortem scheduled (if critical)

### External Communication (if applicable)
- [ ] Customer notification needed: Yes/No
- [ ] Status page update: Yes/No
- [ ] Support ticket updates: [List tickets]

### Post-Mortem (if P0/P1)
- [ ] Schedule post-mortem meeting
- [ ] Document lessons learned
- [ ] Create action items
- [ ] Update runbooks

---

## Estimated Effort

| Activity | Time Estimate |
|----------|--------------|
| Investigation | [X hours] |
| Fix Implementation | [X hours] |
| Testing | [X hours] |
| Code Review | [X hours] |
| Documentation | [X hours] |
| Deployment | [X hours] |
| **Total** | **[X hours]** |

**Story Points**: [X] (Fibonacci scale)

---

## Sign-Off

- [ ] **Developer**: Fix implemented - [Name] - [Date]
- [ ] **Code Reviewer**: Code approved - [Name] - [Date]
- [ ] **QA**: Testing verified - [Name] - [Date]
- [ ] **Reporter**: Bug confirmed fixed - [Name] - [Date]
- [ ] **Product Owner**: Accepted - [Name] - [Date]

---

## Related Links

- **Pull Request**: [GitHub PR link]
- **CloudWatch Logs**: [Link to relevant logs]
- **Monitoring Dashboard**: [Link]
- **Original Report**: [Ticket/email/Slack link]
- **Post-Mortem**: [Link to post-mortem doc]

---

## Notes

### Additional Context
[Any other relevant information]

### Screenshots
[Attach screenshots if applicable]

### Workaround (Temporary)
[If a workaround exists while fix is being developed]
