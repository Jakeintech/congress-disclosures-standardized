# AI Agent Workflow & Coordination Protocol

**Project**: Congress Disclosures Standardized
**Epic**: EPIC-001 Unified Data Platform Migration
**Last Updated**: 2025-12-26
**Version**: 1.0

---

## 🎯 Purpose

This document defines how AI agents collaborate on this project, covering:
- How to claim and work on GitHub Issues
- Branch naming conventions for agents
- Multi-agent coordination to prevent conflicts
- Code review and PR protocols
- Handoff procedures between agents
- Failure recovery processes

---

## 📋 Quick Start for AI Agents

### 1. Find Your Assignment

**Option A - Assigned to You**:
```bash
# View your assigned issues
gh issue list --assignee @me --state open

# View specific sprint
gh issue list --milestone "Sprint 3" --assignee @me
```

**Option B - Claim Unassigned Issue**:
```bash
# Find unassigned issues in current sprint
gh issue list --milestone "Sprint 3" --no-assignee --state open

# Claim an issue
gh issue edit ISSUE_NUMBER --add-assignee @me
```

### 2. Read Task Context

**Required Reading** (in order):
1. GitHub Issue description (acceptance criteria)
2. `.github/AI_AGENT_TASK_TEMPLATE.md` (this provides structure)
3. Story file: `/docs/agile/stories/active/STORY_XXX_*.md` (full details)
4. Relevant technical specs (linked in story)

### 3. Create Feature Branch

**Branch Naming Convention**:
```
agent/<agent-identifier>/<story-id>-<short-description>
```

Examples:
```bash
# For Claude Code agent
git checkout -b agent/claude-code/STORY-021-build-fact-transactions

# For Cursor agent
git checkout -b agent/cursor/STORY-034-write-unit-tests

# For Copilot agent
git checkout -b agent/copilot/STORY-045-production-deployment
```

**Rules**:
- Always branch from `main` (unless story specifies otherwise)
- Use lowercase with hyphens
- Include story ID for traceability
- Keep description short (max 50 chars)

### 4. Implement & Test

- Follow `.github/AI_AGENT_TASK_TEMPLATE.md` step-by-step
- Run tests locally before pushing
- Commit frequently with conventional commits
- Update issue status as you progress

### 5. Create Pull Request

```bash
# Push branch
git push origin agent/claude-code/STORY-021-build-fact-transactions

# Create PR
gh pr create \
  --title "feat(gold): add build_fact_transactions Lambda wrapper" \
  --body "$(cat <<'EOF'
## Summary
Creates Lambda wrapper for fact_transactions builder script.

## Related Issue
Closes #21

## Changes
- Add Lambda handler with event validation
- Add Terraform configuration
- Include unit tests (85% coverage)

## Testing
- [x] Unit tests passing
- [x] Manual Lambda invocation tested
- [x] Terraform validate passed
EOF
)"
```

### 6. Complete Handoff

- [ ] Update issue to "In Review" status
- [ ] Move issue on Projects board to "In Review" column
- [ ] Notify in issue comments if special deployment needed
- [ ] Remove "blocked" labels from dependent stories

---

## 🤝 Multi-Agent Coordination

### Claiming Issues

**Protocol**:
1. **Check availability**: Ensure issue is not assigned
2. **Claim atomically**: Use `gh issue edit --add-assignee @me`
3. **Verify claim**: Refresh GitHub to confirm you're listed
4. **Add label**: `gh issue edit --add-label "in-progress"`
5. **Start work**: Create branch and begin

**If issue is already claimed**:
- **DO NOT** work on it
- **DO** find another unassigned issue
- **DO** comment if you believe it's abandoned (no activity >3 days)

### Working on Dependencies

**Scenario**: Story B depends on Story A (not yet complete)

**Options**:
1. **Wait**: Work on different story, come back when Story A complete
2. **Coordinate**: Comment on Story A issue, offer to help
3. **Mock**: Create temporary mocks/stubs, mark with `# TODO: Replace when STORY-A merges`

**Example**:
```python
# TODO: Replace with actual dim_members table when STORY-016 merges
def get_member_dimension_mock(member_name):
    """Temporary mock for testing until dim_members available"""
    return {"member_id": "mock-123", "name": member_name}
```

### Parallel Work Rules

**Safe to work in parallel**:
- ✅ Different Lambda functions
- ✅ Different Terraform modules
- ✅ Different documentation files
- ✅ Independent test files

**Requires coordination**:
- ⚠️ Same Lambda function
- ⚠️ Same Terraform resource
- ⚠️ Shared library code (`ingestion/lib/`)
- ⚠️ Same data schema (Bronze/Silver/Gold contracts)

**How to coordinate**:
1. Comment on both issues: "Working on STORY-X which may conflict with STORY-Y"
2. Agree on who goes first
3. Second agent rebases after first PR merges

### Handling Merge Conflicts

**If you encounter conflicts**:

```bash
# Fetch latest main
git fetch origin main

# Rebase your branch
git rebase origin/main

# Resolve conflicts in editor
# After resolving:
git add [conflicted-files]
git rebase --continue

# Force push (your feature branch only!)
git push --force origin agent/your-name/STORY-XXX-description
```

**If conflicts are complex**:
- Comment on your PR with conflict details
- Tag the other PR author
- Discuss resolution strategy
- Consider pair-resolving via comments

---

## 🔀 Branch Strategy

### Branch Types

| Type | Pattern | Purpose | Example |
|------|---------|---------|---------|
| **Agent Feature** | `agent/<agent>/<story>-<desc>` | AI agent work | `agent/claude-code/STORY-021-build-fact-transactions` |
| **Human Feature** | `feature/<story>-<desc>` | Human developer work | `feature/STORY-045-production-deployment` |
| **Bugfix** | `fix/<issue>-<desc>` | Bug fixes | `fix/ISSUE-123-lambda-timeout` |
| **Hotfix** | `hotfix/<critical-issue>` | Emergency prod fixes | `hotfix/api-gateway-500-error` |
| **Release** | `release/v<version>` | Release preparation | `release/v1.0.0` |

### Branch Lifecycle

```
main (protected)
  ↓
agent/claude-code/STORY-021-... (feature branch)
  ↓ (work happens)
  ↓ (commits, tests, docs)
  ↓
PR created → Code review → CI/CD passes
  ↓
Merge to main (squash or rebase)
  ↓
Branch deleted automatically
```

### Branch Protection Rules

**`main` branch** (enforced):
- ❌ No direct pushes (must use PR)
- ✅ Require PR review (1 approval)
- ✅ Require CI/CD passing
- ✅ Require up-to-date with main
- ✅ Auto-delete feature branches after merge

---

## 📝 Commit Convention

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Usage | Example |
|------|-------|---------|
| `feat` | New feature | `feat(gold): add trending stocks aggregation` |
| `fix` | Bug fix | `fix(extraction): handle empty PDF text gracefully` |
| `refactor` | Code change (no behavior change) | `refactor(parquet): extract upsert logic to helper` |
| `test` | Add/update tests | `test(lambda): add unit tests for handler validation` |
| `docs` | Documentation only | `docs(readme): update deployment instructions` |
| `chore` | Tooling, dependencies | `chore(deps): upgrade DuckDB to v1.1.3` |
| `style` | Formatting, whitespace | `style(api): run Black formatter` |
| `perf` | Performance improvement | `perf(query): add index on transaction_date` |

### Scopes

Common scopes:
- `gold`, `silver`, `bronze` - Data layer
- `lambda`, `terraform`, `stepfunctions` - Component
- `extraction`, `ingestion`, `api` - Module
- `test`, `docs`, `ci` - Category

### Examples

```bash
# Good commits
git commit -m "feat(gold): add build_fact_transactions Lambda wrapper"
git commit -m "fix(s3): retry on timeout with exponential backoff"
git commit -m "test(extraction): add edge case tests for OCR fallback"
git commit -m "docs(claude): update Lambda deployment commands"

# Bad commits (avoid)
git commit -m "fixed bug"  # Not descriptive, missing type/scope
git commit -m "WIP"  # Work-in-progress should be local only
git commit -m "asdf"  # Meaningless
```

### Multi-line Commits

For complex changes:

```bash
git commit -m "feat(gold): add build_fact_transactions Lambda wrapper

- Create Lambda handler with event validation
- Add Terraform configuration (5min timeout, 2GB memory)
- Implement incremental and full rebuild modes
- Include unit tests with 85% coverage
- Add error handling for S3 failures

Closes #21"
```

---

## 🔍 Code Review Protocol

### For PR Author (Agent)

**Before requesting review**:
- [ ] All tests passing locally
- [ ] Code formatted (Black, flake8, mypy)
- [ ] PR template checklist completed
- [ ] Linked to GitHub Issue (`Closes #XX`)
- [ ] No merge conflicts
- [ ] Self-review completed (read your own diff)

**PR Description Requirements**:
- Clear summary of changes
- Link to issue
- Testing evidence (test output, screenshots)
- Any special deployment notes

### For Reviewer (Human or Agent)

**Review Checklist**:

**Functionality**:
- [ ] Meets all acceptance criteria from story
- [ ] Edge cases handled
- [ ] Error handling comprehensive
- [ ] No obvious bugs

**Code Quality**:
- [ ] Follows existing patterns
- [ ] No code duplication
- [ ] Names clear and descriptive
- [ ] No commented-out code
- [ ] No TODOs without issue links

**Testing**:
- [ ] Tests cover happy path
- [ ] Tests cover edge cases
- [ ] Tests cover error scenarios
- [ ] Coverage ≥80%

**Documentation**:
- [ ] Docstrings for public functions
- [ ] Comments for complex logic
- [ ] Technical docs updated (if needed)
- [ ] CLAUDE.md updated (if new workflow)

**Security**:
- [ ] No hardcoded secrets
- [ ] No SQL injection vulnerabilities
- [ ] No command injection risks
- [ ] Complies with legal requirements (5 U.S.C. § 13107)

### Review Feedback

**Use GitHub review features**:
- **Comment**: Questions or suggestions
- **Request changes**: Must be addressed before merge
- **Approve**: Ready to merge

**Response time expectations**:
- Human reviewers: Within 24-48 hours
- Agent reviewers: Immediate (if automated)
- Urgent: Tag with `urgent` label, expect <4 hours

### Addressing Feedback

```bash
# Make requested changes
git add [files]
git commit -m "refactor(lambda): extract validation to helper per review"
git push origin agent/claude-code/STORY-021-...

# PR updates automatically
# Re-request review after all changes addressed
gh pr ready  # Marks PR as ready for re-review
```

---

## 🔄 Handoff Between Agents

### Scenario: Agent A starts, Agent B finishes

**Agent A (Starting Agent)**:
1. Claims issue, adds `in-progress` label
2. Creates branch: `agent/agent-a/STORY-XXX-description`
3. Does partial work
4. **If blocked or reassigning**:
   - Push current work to branch
   - Add detailed comment on issue:
     ```markdown
     ## Handoff from Agent A

     **Completed**:
     - [x] Created Lambda handler skeleton
     - [x] Added basic validation

     **Remaining**:
     - [ ] Implement error handling
     - [ ] Write unit tests
     - [ ] Add Terraform config

     **Branch**: `agent/agent-a/STORY-XXX-description`
     **Blockers**: Need dim_members table (STORY-016) to complete
     **Notes**: Test data fixtures in `tests/fixtures/test_transactions.json`
     ```
   - Remove self from assignee
   - Add `needs-handoff` label

**Agent B (Taking Over)**:
1. Read handoff comment thoroughly
2. Assign self to issue
3. Checkout existing branch:
   ```bash
   git fetch origin
   git checkout agent/agent-a/STORY-XXX-description
   ```
4. Review existing code
5. Continue work
6. **Option A**: Continue on same branch
   - Keep branch name (preserves history)
   - Add commit: `chore: agent-b taking over from agent-a handoff`
7. **Option B**: Create new branch
   - `git checkout -b agent/agent-b/STORY-XXX-description`
   - Cherry-pick useful commits
   - Reference original branch in PR

**PR for Handoff Work**:
- Credit both agents:
  ```markdown
  ## Contributors
  - **Agent A** (initial implementation)
  - **Agent B** (completion + testing)
  ```

---

## 🚨 Failure Recovery

### Build Failures

**If CI/CD fails**:

1. **Check GitHub Actions logs**:
   ```bash
   # View workflow runs
   gh run list

   # View specific run
   gh run view RUN_ID
   ```

2. **Common failures**:
   - **Tests failing**: Fix tests, push again
   - **Linting errors**: Run `black . && flake8 .` locally
   - **Type errors**: Run `mypy .` locally
   - **Merge conflicts**: Rebase on main

3. **Fix and retry**:
   ```bash
   # Fix issue locally
   git add [files]
   git commit -m "fix(ci): resolve linting errors"
   git push origin feature-branch

   # CI auto-retries
   ```

### Accidental Push to Main

**If you accidentally push directly to main**:

**DO NOT PANIC**. Protected branches should prevent this, but if it happens:

1. **Revert immediately**:
   ```bash
   git revert HEAD
   git push origin main
   ```

2. **Notify team**:
   - Create issue with `incident` label
   - Document what happened
   - Explain fix

3. **Create proper PR**:
   - Branch from commit before revert
   - Create PR with changes
   - Follow normal review process

### Lost Work

**If branch deleted before PR merged**:

1. **Check GitHub**:
   - Branches are backed up on GitHub
   - View all branches: `gh repo view --web` → Branches tab

2. **Recover**:
   ```bash
   # Fetch all remote branches
   git fetch --all

   # Restore deleted branch
   git checkout -b recovered-branch origin/agent/name/STORY-XXX
   ```

3. **Prevent**:
   - Always push before closing session
   - Don't delete branches until PR merged

### Blocked by Dependency

**If dependency not ready**:

1. **Check dependency status**:
   ```bash
   gh issue view DEPENDENCY_ISSUE_NUMBER
   ```

2. **Options**:
   - **Wait**: Work on different story
   - **Mock**: Create temporary implementation
   - **Help**: Offer to assist on dependency story

3. **Document blocking**:
   - Add comment on your issue
   - Add `blocked` label
   - Link to blocking issue
   - Remove `in-progress` label (frees you for other work)

---

## 📊 Agent Performance Metrics

### Tracked Metrics

**Per Story**:
- Token usage (estimated vs. actual)
- Token efficiency ratio
- Time to completion
- Test coverage achieved
- Code review iterations
- Bugs found in review

**Aggregate (Per Agent)**:
- Total stories completed
- Average token efficiency
- Story point velocity
- First-time approval rate
- Average test coverage
- Specialization areas (which story types/components)

### Optimization

**Improve token efficiency**:
- Read context files before coding (avoid backtracking)
- Use code patterns from similar implementations
- Test incrementally (don't write all code then test)
- Leverage existing helper functions

**Improve review approval rate**:
- Complete all DoD checklist items before PR
- Self-review your diff
- Run all quality checks locally
- Write clear PR descriptions

---

## 📚 Reference

### Quick Commands

```bash
# Find work
gh issue list --milestone "Sprint 3" --no-assignee --state open

# Claim issue
gh issue edit 21 --add-assignee @me --add-label "in-progress"

# Create branch
git checkout -b agent/claude-code/STORY-021-description

# Push work
git push origin agent/claude-code/STORY-021-description

# Create PR
gh pr create --fill

# Update issue status
gh issue edit 21 --add-label "in-review"
gh issue comment 21 --body "PR created: #XX"

# View PR status
gh pr status

# View CI/CD status
gh run list --workflow=ci.yml
```

### Files to Bookmark

- `.github/AI_AGENT_TASK_TEMPLATE.md` - Task brief template
- `.github/AGENT_ONBOARDING.md` - Getting started guide
- `docs/CLAUDE.md` - Project commands and patterns
- `docs/agile/STORY_CATALOG.md` - All stories overview
- `CONTRIBUTING.md` - Code style, commit format
- `.github/pull_request_template.md` - PR checklist

### Getting Help

- **Stuck on task?** → Comment on issue, describe blocker
- **Need clarification?** → Ask in issue comments
- **Found bug in story?** → Comment on issue, suggest fix
- **Conflict with another agent?** → Comment on both issues, coordinate
- **Urgent blocker?** → Add `blocked` label, tag reviewer

---

## 🎯 Success Checklist

**Before marking story "Done"**:

- [ ] All acceptance criteria met
- [ ] All DoD items completed
- [ ] Branch pushed to GitHub
- [ ] PR created and passing CI/CD
- [ ] Code review requested
- [ ] Issue status updated to "In Review"
- [ ] Projects board updated
- [ ] Dependent stories unblocked
- [ ] Handoff notes complete (if applicable)

**PR Merge Criteria**:

- [ ] At least 1 approval
- [ ] All CI/CD checks passing
- [ ] No merge conflicts
- [ ] All review comments addressed
- [ ] No open "Request changes" reviews

**Post-Merge**:

- [ ] Issue closed (auto-closes with "Closes #XX")
- [ ] Branch deleted (auto-deletes)
- [ ] Projects board shows "Done"
- [ ] Velocity metrics updated

---

**Document Version**: 1.0
**Last Updated**: 2025-12-26
**Maintained By**: Project Management Team

For questions or improvements to this workflow, create an issue with the `process-improvement` label.
