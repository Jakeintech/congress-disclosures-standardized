# AI Agent Onboarding Guide

**Welcome!** This guide walks you through completing your first task on the Congress Disclosures project.

**Time to Complete**: ~30 minutes for first task
**Prerequisites**: GitHub access, basic Git knowledge
**Support**: Ask questions in issue comments

---

## 🎯 Onboarding Goals

By the end of this guide, you will:
- ✅ Understand project structure and standards
- ✅ Know how to find and claim a task
- ✅ Complete a full task from start to PR
- ✅ Understand the quality standards
- ✅ Know how to get help when stuck

---

## 📚 Step 0: Read Core Documents (10 minutes)

**CRITICAL**: Read these documents before starting any work:

### 1. AI Agent Context (Master Prompt)
**File**: `docs/agile/AI_AGENT_CONTEXT.md`
**What it is**: Complete project context (copy-paste this for every task)
**Time**: 5 minutes to skim, bookmark for reference

**Key sections**:
- Project overview (what we're building)
- Architecture (Bronze→Silver→Gold pipeline)
- Technology standards (code quality, patterns)
- Common gotchas (pitfalls to avoid)
- Quick reference (commands, files to read)

### 2. AI Agent Workflow
**File**: `.github/AI_AGENT_WORKFLOW.md`
**What it is**: Multi-agent coordination protocol
**Time**: 5 minutes

**Key sections**:
- How to claim issues
- Branch naming conventions
- Commit message format
- PR creation process
- Handoff procedures

### 3. Project Commands
**File**: `docs/CLAUDE.md`
**What it is**: All available make commands and workflows
**Time**: Skim, use as reference

---

## 🚀 Step 1: Set Up Local Environment (15 minutes)

### Install Prerequisites

**Required Tools**:
```bash
# Check versions
python3 --version      # Need 3.11+
terraform --version    # Need 1.0+
aws --version          # Need AWS CLI v2
gh --version           # GitHub CLI
git --version          # Git 2.0+

# Install if missing
brew install python@3.11 terraform awscli gh git  # macOS
# or use apt/yum on Linux
```

### Clone Repository

```bash
# Clone repo
git clone https://github.com/[org]/congress-disclosures-standardized.git
cd congress-disclosures-standardized

# Verify you're on main
git branch
# Should show: * main
```

### Install Dependencies

```bash
# Run setup (creates .env, installs Python deps)
make setup

# Install dev tools (Black, flake8, mypy, pytest)
make install-dev

# Verify installation
black --version
flake8 --version
mypy --version
pytest --version
```

### Configure AWS (If Needed for Testing)

```bash
# Configure AWS credentials
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: us-east-1
# - Output format: json

# Test access
aws s3 ls s3://congress-disclosures-standardized/ --max-items 5
# Should list some files (if you have access)
```

### Verify GitHub CLI

```bash
# Authenticate with GitHub
gh auth login
# Follow prompts

# Verify
gh repo view
# Should show repo info
```

---

## 🎯 Step 2: Find Your First Task (5 minutes)

### Browse Available Stories

**Option A: Use GitHub Projects Board** (Recommended)
```bash
# Open Projects board in browser
gh repo view --web
# Navigate to: Projects → "EPIC-001: Unified Data Platform"
# Filter: Sprint 3, Status: To Do, Unassigned
```

**Option B: Use GitHub CLI**
```bash
# List unassigned issues in current sprint
gh issue list \
  --milestone "Sprint 3: Integration" \
  --label "user-story" \
  --state open \
  --no-assignee

# Output shows:
# #28  [STORY-028] Design unified state machine JSON  (5 points)
# #33  [STORY-033] Create run_soda_checks Lambda       (5 points)
# ...
```

**Option C: Browse Story Catalog**
```bash
# Open story catalog
cat docs/agile/STORY_CATALOG.md | grep "To Do"

# Or in browser
open docs/agile/STORY_CATALOG.md
```

### Choose Starter Task

**Good First Tasks** (1-2 points):
- Simple Lambda wrappers
- Configuration changes
- Documentation updates
- Test additions

**Avoid For First Task**:
- 8-point stories (too complex)
- Stories with many dependencies
- Stories marked `blocked`

**For This Tutorial**: We'll use a fictional **STORY-001** (1 point) as example.

---

## 📋 Step 3: Claim Your Task (2 minutes)

### Assign Issue to Yourself

```bash
# Claim issue #1
gh issue edit 1 --add-assignee @me

# Add "in-progress" label
gh issue edit 1 --add-label "in-progress"

# Verify claim
gh issue view 1
# Should show: Assignees: @you
```

### Read Full Story

```bash
# Option 1: View in GitHub
gh issue view 1 --web

# Option 2: Read story file
cat docs/agile/stories/active/STORY_001_disable_eventbridge.md

# Option 3: Use Task Template
# Copy .github/AI_AGENT_TASK_TEMPLATE.md
# Fill in placeholders with story details
```

**What to Read**:
- [ ] User story (As a/I want/So that)
- [ ] Acceptance criteria (GIVEN/WHEN/THEN)
- [ ] Technical tasks checklist
- [ ] Definition of Done
- [ ] Dependencies (what must be done first)
- [ ] Test requirements

**Example Story** (STORY-001: Disable EventBridge):
```markdown
**User Story**:
As a cost-conscious engineer
I want EventBridge hourly trigger disabled
So that we don't incur $4K/month runaway costs

**Acceptance Criteria**:
- GIVEN EventBridge rule is currently enabled
- WHEN I disable the rule via Terraform
- THEN Terraform shows rule is disabled
- AND Rule does not trigger Lambda functions

**Technical Tasks**:
- [ ] Locate EventBridge rule in Terraform
- [ ] Change `enabled = true` to `enabled = false`
- [ ] Run terraform plan to verify change
- [ ] Document change in CLAUDE.md

**Files to Modify**:
- infra/terraform/event_scheduling.tf
- docs/CLAUDE.md
```

---

## 🛠️ Step 4: Create Feature Branch (1 minute)

### Branch Naming Convention

**Format**: `agent/<agent-name>/<story-id>-<short-description>`

**Examples**:
- `agent/claude-code/STORY-001-disable-eventbridge`
- `agent/cursor/STORY-033-create-soda-checks`
- `agent/copilot/STORY-028-design-state-machine`

### Create Branch

```bash
# Ensure on main, up-to-date
git checkout main
git pull origin main

# Create feature branch
git checkout -b agent/claude-code/STORY-001-disable-eventbridge

# Verify
git branch
# Should show: * agent/claude-code/STORY-001-disable-eventbridge
```

---

## 💻 Step 5: Implement Changes (10-30 minutes)

### Example Implementation (STORY-001)

**Task**: Disable EventBridge hourly trigger

**Step 5.1: Locate File**
```bash
# Find EventBridge configuration
grep -r "eventbridge" infra/terraform/ --include="*.tf"

# Output shows:
# infra/terraform/event_scheduling.tf:resource "aws_cloudwatch_event_rule" "hourly_trigger"
```

**Step 5.2: Make Change**
```bash
# Open file
vim infra/terraform/event_scheduling.tf
# or use your preferred editor
```

**Before**:
```hcl
resource "aws_cloudwatch_event_rule" "hourly_trigger" {
  name                = "congress-disclosures-hourly-trigger"
  description         = "Trigger pipeline every hour"
  schedule_expression = "rate(1 hour)"
  is_enabled          = true  # ← Change this
}
```

**After**:
```hcl
resource "aws_cloudwatch_event_rule" "hourly_trigger" {
  name                = "congress-disclosures-hourly-trigger"
  description         = "Trigger pipeline every hour (DISABLED to prevent runaway costs)"
  schedule_expression = "rate(1 hour)"
  is_enabled          = false  # ← Changed from true to false
}
```

**Step 5.3: Update Documentation**
```bash
# Open CLAUDE.md
vim docs/CLAUDE.md
```

Add note in relevant section:
```markdown
## Cost Optimization

**EventBridge Hourly Trigger**: Disabled by default to prevent $4K/month costs.
To enable: Set `is_enabled = true` in `infra/terraform/event_scheduling.tf`
```

**Step 5.4: Verify Change**
```bash
# Check what changed
git diff

# Output:
# -  is_enabled          = true
# +  is_enabled          = false
# +  description         = "... (DISABLED to prevent runaway costs)"
```

---

## ✅ Step 6: Test Your Changes (10 minutes)

### Terraform Validation

**Always validate Terraform changes**:

```bash
# Navigate to Terraform directory
cd infra/terraform

# Initialize (if first time)
terraform init

# Validate syntax
terraform validate
# Should output: Success! The configuration is valid.

# Preview changes
terraform plan

# Look for output showing:
# ~ resource "aws_cloudwatch_event_rule" "hourly_trigger" {
#     ~ is_enabled = true -> false
# }

# Return to repo root
cd ../..
```

**Expected Output**:
```
Terraform will perform the following actions:

  # aws_cloudwatch_event_rule.hourly_trigger will be updated in-place
  ~ resource "aws_cloudwatch_event_rule" "hourly_trigger" {
      ~ is_enabled = true -> false
        # (5 unchanged attributes)
    }

Plan: 0 to add, 1 to change, 0 to destroy.
```

### Run Tests (If Applicable)

**For code changes, always run tests**:

```bash
# Run all tests
make test

# Or specific tests
pytest tests/unit/ -v

# Or just validate no syntax errors
python -m py_compile [your-file].py
```

**For this example**: No Python code changed, so no tests needed.

---

## 📝 Step 7: Commit Your Changes (3 minutes)

### Stage Files

```bash
# Check what changed
git status

# Output:
# modified:   infra/terraform/event_scheduling.tf
# modified:   docs/CLAUDE.md

# Stage files
git add infra/terraform/event_scheduling.tf
git add docs/CLAUDE.md

# Verify staging
git status
# Should show files in "Changes to be committed"
```

### Write Commit Message

**Format**: Conventional Commits
```
<type>(<scope>): <description>

[optional body]

Closes #<issue-number>
```

**Types**: feat, fix, refactor, test, docs, chore, style, perf
**Scopes**: terraform, lambda, api, docs, etc.

**Example Commit**:
```bash
git commit -m "chore(terraform): disable EventBridge hourly trigger

Disables hourly EventBridge rule to prevent $4K/month runaway costs.
Rule can be re-enabled by setting is_enabled = true if needed.

Also updated CLAUDE.md with cost optimization note.

Closes #1"
```

**Verify Commit**:
```bash
# View commit
git log -1

# Should show your commit with message
```

---

## 🚀 Step 8: Push and Create PR (5 minutes)

### Push Branch to GitHub

```bash
# Push feature branch
git push origin agent/claude-code/STORY-001-disable-eventbridge

# Output:
# remote: Create a pull request for 'agent/claude-code/STORY-001-disable-eventbridge' on GitHub by visiting:
# remote:      https://github.com/[org]/congress-disclosures-standardized/pull/new/agent/...
```

### Create Pull Request

**Option A: GitHub CLI** (Recommended)
```bash
gh pr create \
  --title "chore(terraform): disable EventBridge hourly trigger" \
  --body "$(cat <<'EOF'
## Summary
Disables EventBridge hourly trigger to prevent $4K/month runaway costs.

## Related Issue
Closes #1

## Changes Made
- Set `is_enabled = false` in `event_scheduling.tf`
- Added cost optimization note to CLAUDE.md
- Verified with `terraform plan` (shows 1 resource updated)

## Testing
- [x] Terraform validate passed
- [x] Terraform plan shows expected change
- [x] Documentation updated

## Checklist
- [x] Code follows style guide
- [x] Commit message follows Conventional Commits
- [x] Linked to GitHub Issue
- [x] Documentation updated
- [x] No merge conflicts
EOF
)"

# PR created!
# Output: https://github.com/[org]/congress-disclosures-standardized/pull/123
```

**Option B: GitHub Web UI**
1. Go to repo in browser: `gh repo view --web`
2. Click "Pull requests" tab
3. Click "New pull request"
4. Select your branch
5. Fill in title and description
6. Click "Create pull request"

### PR Template Checklist

**Ensure all items checked**:
- [x] Type of change selected (chore/feat/fix)
- [x] Related issue linked (`Closes #1`)
- [x] Testing section completed
- [x] Documentation updated
- [x] No breaking changes
- [x] AWS free tier not impacted
- [x] Legal compliance (5 U.S.C. § 13107)

---

## 🔄 Step 9: Update Issue Status (2 minutes)

### Move to "In Review"

```bash
# Update issue status
gh issue edit 1 --remove-label "in-progress" --add-label "in-review"

# Add comment linking PR
gh issue comment 1 --body "PR created: #123

All acceptance criteria met:
- [x] EventBridge rule disabled in Terraform
- [x] terraform plan shows rule is disabled
- [x] Documentation updated

Ready for review."

# Verify
gh issue view 1
# Should show: Labels: in-review
```

### Update Projects Board (If Manual)

**If board doesn't auto-update**:
1. Go to Projects board
2. Find your issue card
3. Drag from "In Progress" to "In Review" column

---

## ⏰ Step 10: Wait for Review (24-48 hours)

### What Happens Next

**Automated Checks** (immediate):
- ✅ CI/CD runs (GitHub Actions)
- ✅ Linting, formatting, tests
- ✅ Terraform validate

**Code Review** (24-48 hours):
- 👤 Human reviewer assigned
- 💬 Feedback provided
- 🔄 Changes requested (if needed)
- ✅ Approval granted

### Responding to Feedback

**If changes requested**:

```bash
# Make requested changes
vim infra/terraform/event_scheduling.tf

# Commit again
git add infra/terraform/event_scheduling.tf
git commit -m "refactor(terraform): improve comment per review feedback"

# Push (updates PR automatically)
git push origin agent/claude-code/STORY-001-disable-eventbridge

# Re-request review
gh pr ready
```

### After Approval

**PR gets merged**:
- ✅ Issue auto-closes (via "Closes #1")
- ✅ Branch auto-deletes
- ✅ Projects board updates to "Done"
- 🎉 Your first contribution complete!

---

## 🎓 What You Learned

**Process**:
- ✅ How to find and claim issues
- ✅ Branch naming convention
- ✅ Conventional commit format
- ✅ PR creation process
- ✅ Issue status workflow

**Technical**:
- ✅ Project structure (where files live)
- ✅ Terraform validation workflow
- ✅ Documentation standards
- ✅ Quality checks (terraform validate)

**Tools**:
- ✅ GitHub CLI (`gh`)
- ✅ Git workflow
- ✅ Make commands
- ✅ Terraform basics

---

## 📚 Next Steps

### Your Second Task

**Now that you've completed onboarding**:

1. **Find next task**: Higher complexity (2-3 points)
2. **Read story thoroughly**: More complex acceptance criteria
3. **Follow same workflow**: Claim → Branch → Implement → Test → PR
4. **Reference templates**:
   - `.github/AI_AGENT_TASK_TEMPLATE.md` for structure
   - `docs/agile/AI_AGENT_CONTEXT.md` for context
   - This guide for workflow reminders

### Suggested Second Tasks

**Good progression** (2 points):
- Lambda wrapper stories (follow existing pattern)
- Test addition stories (learn testing framework)
- Documentation stories (learn codebase)

**Avoid initially**:
- 8-point architectural changes
- Stories with multiple dependencies
- Stories requiring deep domain knowledge

### Build Your Expertise

**Specialize in**:
- **Lambda functions**: Become expert in wrapper pattern
- **Terraform**: Master infrastructure as code
- **Data pipeline**: Understand Bronze→Silver→Gold
- **Testing**: Write comprehensive test suites
- **Documentation**: Improve project docs

**Track your performance**:
- Token efficiency (actual vs. estimated)
- First-time approval rate
- Test coverage trends
- Velocity (points per sprint)

---

## ❓ Common Questions

**Q: How long should my first task take?**
A: 1-point story: 1-2 hours (including reading, testing, PR)
   2-point story: 2-4 hours
   3-point story: 4-6 hours

**Q: What if I'm stuck for >30 minutes?**
A: Ask for help! Comment on issue, describe what you've tried. Better to ask early than spend hours blocked.

**Q: Can I work on multiple stories simultaneously?**
A: Yes, but finish one before starting another. Context switching reduces efficiency.

**Q: What if my PR gets rejected?**
A: Learn from feedback, make changes, resubmit. First-time approval rate improves with experience.

**Q: How do I know if a story is too complex for me?**
A: If reading the story feels overwhelming, start with simpler task. Build confidence progressively.

**Q: Should I add features beyond acceptance criteria?**
A: No. Stick to acceptance criteria. Additional features should be separate stories.

**Q: What if I disagree with code review feedback?**
A: Discuss respectfully in PR comments. Reviewer has final say, but discussion is encouraged.

**Q: Can I refactor code I see that needs improvement?**
A: In same PR: Only if directly related to your story.
   Separately: Create new issue for refactoring.

---

## 🆘 Getting Help

### Resources

**Documentation**:
- `docs/agile/AI_AGENT_CONTEXT.md` - Project context
- `docs/CLAUDE.md` - Commands and patterns
- `.github/AI_AGENT_WORKFLOW.md` - Collaboration protocol
- `.github/AI_AGENT_TASK_TEMPLATE.md` - Task structure

**Code Examples**:
- Browse `api/lambdas/` for Lambda patterns
- Browse `infra/terraform/` for Terraform patterns
- Browse `tests/unit/` for test patterns

**Search**:
```bash
# Find similar code
grep -r "keyword" --include="*.py"

# Find git history
git log --grep="keyword"

# Find recent changes
git log --since="1 week ago" --oneline
```

### Escalation

**If stuck**:
1. **Search codebase** for similar implementations
2. **Read technical specs** (ADRs, data contracts)
3. **Comment on issue** with specific question
4. **Add `blocked` label** if truly stuck
5. **Tag reviewer** if urgent

**Contact**:
- Issue comments (best)
- PR comments (for PR-specific questions)
- Label `blocked` (alerts team)

---

## ✅ Onboarding Complete!

**You're ready to contribute when**:
- ✅ You've read core documents
- ✅ Environment is set up
- ✅ You've completed first task end-to-end
- ✅ You understand the workflow
- ✅ You know where to find help

**Next**: Claim your second task and keep building velocity!

---

**Welcome to the team! 🎉**

**Questions?** Ask in issue comments or create issue with `onboarding` label.

**Feedback?** Help improve this guide by suggesting edits in PR.

**Good luck!** 🚀
