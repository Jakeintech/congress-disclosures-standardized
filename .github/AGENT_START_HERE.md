# 🤖 AI AGENT - START HERE

**You've been asked to "work on the next task"**. This guide tells you exactly what to do.

---

## ⚡ QUICK START (5 commands)

```bash
# 1. Find the next task
gh issue list --label "sprint-3" --label "agent-task" \
  --state open --sort created --limit 5

# 2. Claim a task (replace NUMBER with issue number)
gh issue comment NUMBER --body "@me claiming this task"

# 3. Read the full story
# (Issue body has link to story file - read that file)

# 4. Create branch
git checkout -b agent/claude/STORY-XXX-short-description

# 5. Start working
# Follow: .github/AI_AGENT_TASK_TEMPLATE.md
```

---

## 📋 STEP-BY-STEP WORKFLOW

### Step 1: Find Your Task (2 min)

**Find current sprint tasks**:
```bash
gh issue list \
  --label "sprint-3" \
  --state open \
  --sort created \
  --json number,title,labels \
  --jq '.[] | "#\(.number): \(.title) - Points: \(.labels[] | select(.name | startswith("points-")) | .name)"'
```

**Find high-priority tasks**:
```bash
gh issue list \
  --label "P0-critical" \
  --state open \
  --limit 5
```

**Find tasks ready for agents**:
```bash
gh issue list \
  --label "agent-task" \
  --label "sprint-3" \
  --state open \
  --limit 10
```

**Pick the first one** or **ask user which task to work on**.

---

### Step 2: Read Full Context (5 min)

**View the issue**:
```bash
gh issue view NUMBER
```

**The issue contains**:
- ✅ Story ID (STORY-XXX)
- ✅ Epic, Sprint, Points, Priority
- ✅ User Story (As a.../I want.../So that...)
- ✅ Acceptance Criteria (checklist)
- ✅ Technical Tasks (implementation steps)
- ✅ Dependencies (other stories)
- ✅ **Link to full story file** (in "Links" section)

**Read the full story file**:
```bash
# Issue links to: docs/agile/stories/active/STORY_XXX_description.md
cat docs/agile/stories/active/STORY_028_unified_state_machine.md
```

**Read these guides** (CRITICAL):
1. **`.github/AI_AGENT_TASK_TEMPLATE.md`** - Your execution template
2. **`docs/agile/AI_AGENT_CONTEXT.md`** - Full project context (MUST READ)
3. **`.github/AI_AGENT_WORKFLOW.md`** - Multi-agent workflow

---

### Step 3: Claim the Task (30 sec)

```bash
# Claim by commenting
gh issue comment NUMBER --body "@me - Starting work on this task"

# Or just assign yourself
gh issue edit NUMBER --add-assignee @me
```

This prevents other agents from working on same task.

---

### Step 4: Create Branch (30 sec)

**Branch naming convention**:
```
agent/<your-name>/<story-id>-short-description
```

**Examples**:
```bash
# For STORY-028: Design Unified State Machine JSON
git checkout -b agent/claude/story-028-unified-state-machine

# For STORY-033: Create run_soda_checks Lambda
git checkout -b agent/claude/story-033-soda-checks-lambda

# For STORY-034: Write 70+ Unit Tests
git checkout -b agent/claude/story-034-unit-tests
```

**Create the branch**:
```bash
git checkout enhancement  # Start from enhancement branch
git pull
git checkout -b agent/YOUR_NAME/STORY-XXX-description
```

---

### Step 5: Execute Task (Main Work)

**Follow this template exactly**: `.github/AI_AGENT_TASK_TEMPLATE.md`

**Phases** (with token estimates):

#### Phase 1: Setup & Planning (~2K tokens)
- [ ] Read story file completely
- [ ] Read technical architecture docs
- [ ] Identify files to modify
- [ ] Plan implementation approach
- [ ] Verify dependencies are met

#### Phase 2: Implementation (60-70% of tokens)
- [ ] Write code following project patterns
- [ ] Follow coding standards (PEP 8, type hints, docstrings)
- [ ] Check security (no SQL injection, XSS, secrets)
- [ ] Use existing libraries/patterns
- [ ] Keep functions focused and testable

**Token allocation by story points**:
- 1 point: ~10K tokens total (~6K for implementation)
- 2 points: ~20K tokens total (~12K for implementation)
- 3 points: ~30K tokens total (~18K for implementation)
- 5 points: ~50K tokens total (~30K for implementation)
- 8 points: ~80K tokens total (~48K for implementation)

#### Phase 3: Testing (~5-10K tokens)
```bash
# Run tests
pytest tests/unit/test_your_feature.py -v

# Check coverage
pytest --cov=ingestion/lib --cov-report=term-missing

# Integration tests (if needed)
pytest tests/integration/ -v
```

#### Phase 4: Code Quality (~2K tokens)
```bash
# Format code
black ingestion/ scripts/ tests/

# Lint
flake8 ingestion/ scripts/

# Type check
mypy ingestion/

# Or run all checks
make check-all
```

#### Phase 5: Documentation (~3-5K tokens)
- [ ] Update docstrings
- [ ] Update ARCHITECTURE.md (if needed)
- [ ] Update CLAUDE.md (if architecture changed)
- [ ] Add inline comments for complex logic

#### Phase 6: Commit & Push (~1-2K tokens)
```bash
# Stage changes
git add .

# Commit with conventional format
git commit -m "feat(component): description

- Detailed change 1
- Detailed change 2
- Detailed change 3

Closes #ISSUE_NUMBER

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push branch
git push origin agent/YOUR_NAME/STORY-XXX-description
```

**Conventional Commit Types**:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `refactor:` - Code change that neither fixes bug nor adds feature
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

#### Phase 7: Create PR (~2-3K tokens)
```bash
gh pr create \
  --title "[STORY-XXX] Story Title" \
  --body "$(cat <<EOF
## 📋 Agile Tracking

**Story ID**: STORY-XXX
**Sprint**: Sprint 3
**Story Points**: X
**Estimated Tokens**: XXK
**Actual Tokens**: XXK (check your usage)

## Description

Brief description of changes.

## Changes Made

- Change 1
- Change 2
- Change 3

## Testing

- [ ] Unit tests pass locally
- [ ] Integration tests pass
- [ ] Manual testing completed

## Closes

Closes #ISSUE_NUMBER

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)" \
  --label "sprint-3" \
  --label "points-X"
```

---

### Step 6: Verification Checklist

Before creating PR, verify:

- [ ] **All acceptance criteria met** (check issue)
- [ ] **Tests written and passing**
- [ ] **Code formatted** (`black`, `flake8`, `mypy`)
- [ ] **No secrets committed** (check with `detect-secrets`)
- [ ] **Documentation updated**
- [ ] **Conventional commit format used**
- [ ] **Issue linked in PR** (`Closes #XXX`)

---

## 🧠 CRITICAL CONTEXT TO READ

**Before starting ANY task, read these**:

### 1. Project Context (MUST READ)
**File**: `docs/agile/AI_AGENT_CONTEXT.md`

This contains:
- Project overview (tech stack, architecture)
- Critical gotchas (Lambda timeouts, DuckDB issues, etc.)
- Common patterns (Parquet upsert, SQS partial batch, etc.)
- Environment variables
- Testing approach

**Read this FIRST** - it has critical information that will save you from common mistakes.

### 2. Task Template
**File**: `.github/AI_AGENT_TASK_TEMPLATE.md`

This contains:
- Token estimates by phase
- Complete workflow with examples
- Lambda handler pattern
- Terraform pattern
- Test pattern

### 3. Workflow Guide
**File**: `.github/AI_AGENT_WORKFLOW.md`

This contains:
- Branch naming conventions
- Multi-agent coordination
- Handoff procedures
- Failure recovery

### 4. Architecture
**File**: `CLAUDE.md` (project instructions)

This contains:
- Bronze → Silver → Gold architecture
- Lambda functions map
- Common commands
- Debugging tips

---

## 🎯 FINDING THE "NEXT TASK"

### Priority Order

**1. Current Sprint High Priority**:
```bash
gh issue list --label "sprint-3" --label "P0-critical" --state open
gh issue list --label "sprint-3" --label "P1-high" --state open
```

**2. No Dependencies (Can Start Now)**:
```bash
gh issue list --label "sprint-3" --state open \
  --json number,title,labels \
  --jq '.[] | select(.labels | map(.name) | contains(["dependencies"]) | not) | "#\(.number): \(.title)"'
```

**3. Low Point Value (Quick Wins)**:
```bash
gh issue list --label "points-1" --state open --limit 5
gh issue list --label "points-2" --state open --limit 5
```

**4. Agent-Ready Tasks**:
```bash
gh issue list --label "agent-task" --state open --limit 10
```

### Ask User If Unclear

If multiple tasks have same priority:
```
I found 3 tasks with P1-high priority in Sprint 3:
- #4: Design Unified State Machine JSON (3 points)
- #9: Create run_soda_checks Lambda (5 points)
- #10: Write 70+ Unit Tests (8 points)

Which would you like me to work on?
```

---

## ⚠️ COMMON GOTCHAS (READ THIS)

### 1. Lambda Timeout
- Max 900 seconds (15 min)
- Large operations may timeout
- Solution: Break into smaller chunks or use Step Functions

### 2. DuckDB S3 Connection
```python
# Always use httpfs extension
conn.execute("INSTALL httpfs; LOAD httpfs;")
conn.execute(f"SET s3_region='{region}';")
```

### 3. Parquet Upsert Pattern
```python
# Don't just append - upsert!
existing = pd.read_parquet(s3_path)
existing_clean = existing[~existing['id'].isin(new_df['id'])]
combined = pd.concat([existing_clean, new_df])
combined.to_parquet(s3_path)
```

### 4. Test Data Isolation
```python
# Use unique prefixes for test data
TEST_PREFIX = f"test-{uuid.uuid4()}"
```

### 5. Environment Variables
```python
# Always check .env.example for required vars
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
```

**Full list**: `docs/agile/AI_AGENT_CONTEXT.md` section "Critical Gotchas"

---

## 🆘 STUCK OR BLOCKED?

### If Dependencies Missing
1. Check issue for "Dependencies" section
2. Verify prerequisite stories are complete
3. Ask user: "STORY-XXX requires STORY-YYY to be completed first. Should I wait or work on something else?"

### If Requirements Unclear
1. Read full story file (not just issue)
2. Check acceptance criteria - are they testable?
3. Ask user: "The acceptance criteria for STORY-XXX says [X]. Can you clarify what this means specifically?"

### If Tests Failing
1. Don't mark task as complete
2. Debug and fix
3. If blocked, create new issue: "Tests failing for STORY-XXX - [error message]"

### If Hit Token Limit
1. Don't rush remaining work
2. Create handoff issue: "STORY-XXX 80% complete - needs [remaining tasks]"
3. Label with `needs-handoff`
4. Document what's done and what remains

---

## 🔍 VERIFICATION COMMANDS

**Before claiming task**:
```bash
# Check it's not already assigned
gh issue view NUMBER --json assignees

# Check dependencies
gh issue view NUMBER --json body | grep -i "dependencies"
```

**During work**:
```bash
# Run tests frequently
pytest tests/unit/ -v

# Check code quality
make check-all
```

**Before PR**:
```bash
# Verify all tests pass
pytest tests/

# Verify formatting
black --check ingestion/ scripts/ tests/

# Verify no secrets
detect-secrets scan
```

---

## 📊 EXAMPLE WORKFLOW (STORY-028)

```bash
# 1. Find task
gh issue list --label "sprint-3" --state open --limit 5
# Output: #4 [STORY-028] Design Unified State Machine JSON (3 points)

# 2. Read context
gh issue view 4
cat docs/agile/stories/active/STORY_028_unified_state_machine.md
cat docs/agile/AI_AGENT_CONTEXT.md  # MUST READ

# 3. Claim task
gh issue comment 4 --body "@me - Starting work on this"

# 4. Create branch
git checkout enhancement
git pull
git checkout -b agent/claude/story-028-unified-state-machine

# 5. Work on it
# - Read Step Functions docs
# - Design JSON schema
# - Create example state machine
# - Write tests
# - Update documentation

# 6. Commit
git add .
git commit -m "feat(stepfunctions): design unified state machine JSON

- Created base state machine template
- Added error handling states
- Documented all state types
- Added validation examples

Closes #4

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 7. Push & PR
git push origin agent/claude/story-028-unified-state-machine
gh pr create --title "[STORY-028] Design Unified State Machine JSON" \
  --body "..." --label "sprint-3" --label "points-3"
```

---

## ✅ SUCCESS CRITERIA

**You've successfully completed a task when**:
- ✅ All acceptance criteria met
- ✅ Tests written and passing
- ✅ Code quality checks pass
- ✅ Documentation updated
- ✅ PR created and linked to issue
- ✅ Issue auto-closes when PR merges

---

## 🎓 LEARNING RESOURCES

**First Time?**
- Read: `.github/AGENT_ONBOARDING.md` (complete walkthrough of first task)

**Quick Reference**:
- Read: `.github/QUICK_REFERENCE.md` (when created - one-page cheat sheet)

**Deep Dive**:
- Read: `docs/ARCHITECTURE.md` (system architecture)
- Read: `docs/EXTRACTION_ARCHITECTURE.md` (extraction pipeline)

---

## 🎯 TL;DR - ULTRA QUICK START

```bash
# 1. Find task
gh issue list --label "sprint-3" --state open --limit 5

# 2. Read context (CRITICAL - DON'T SKIP)
cat docs/agile/AI_AGENT_CONTEXT.md
cat docs/agile/stories/active/STORY_XXX_*.md

# 3. Claim & branch
gh issue comment NUMBER --body "@me"
git checkout -b agent/claude/story-XXX-description

# 4. Follow template
# Read: .github/AI_AGENT_TASK_TEMPLATE.md
# Implement, test, document

# 5. PR
git commit -m "feat: description\n\nCloses #NUMBER"
git push origin HEAD
gh pr create
```

**That's it!** 🚀

---

**Questions?** Read `.github/AGENT_ONBOARDING.md` for a complete walkthrough of your first task.

**Stuck?** Ask the user for clarification - never guess on requirements!

**Ready?** Run `gh issue list --label "sprint-3" --state open --limit 5` to see your first task! 🎯
