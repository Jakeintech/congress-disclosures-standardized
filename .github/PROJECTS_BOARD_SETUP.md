# GitHub Projects Board Setup Guide

This guide walks you through setting up **automated GitHub Projects board** integration for the Congress Disclosures project.

**Time Required**: ~30 minutes one-time setup
**Result**: Fully automated sprint tracking with zero manual updates

---

## Overview

We use **GitHub Projects v2** with automated field population via the `leonsteinhaeuser/project-beta-automations` action.

**What Gets Automated**:
- ✅ Issues automatically added to board when created
- ✅ Story Points populated from `points-X` labels
- ✅ Sprint populated from `sprint-X` labels
- ✅ Priority populated from `PX-XXX` labels
- ✅ Status auto-updates: To Do → In Progress → In Review → Done
- ✅ Works with all 55 existing issues

---

## Prerequisites

Before starting, ensure you have:
- [x] GitHub account with admin access to this repository
- [x] `gh` CLI installed and authenticated
- [x] Permission to create Projects (personal or org level)

---

## Step 1: Create GitHub Projects Board (15 min)

### 1.1 Navigate to Projects

**For Personal Projects**:
```bash
open https://github.com/users/Jakeintech/projects
```

**For Organization Projects** (if using org):
```bash
open https://github.com/orgs/YOUR_ORG/projects
```

### 1.2 Create New Project

1. Click **"New project"** button
2. Choose **"Board"** template (or start from scratch)
3. **Name**: `Congress Disclosures Agile Board`
4. **Description**: `Sprint tracking and task management for Congress disclosures pipeline`
5. Click **"Create project"**

### 1.3 Note Your Project Number

Look at the URL after creation:
```
https://github.com/users/Jakeintech/projects/1
                                            ↑
                                      This number
```

**Save this number** - you'll need it in Step 3.

### 1.4 Add Custom Fields

Click **"⚙️ Settings"** (top right) → **"Custom fields"** → **"+ New field"**

Create these 6 fields:

#### Field 1: Status
- **Name**: `Status`
- **Type**: Single select
- **Options** (in order):
  - Backlog
  - To Do
  - In Progress
  - In Review
  - Done
- **Default**: To Do

#### Field 2: Story Points
- **Name**: `Story Points`
- **Type**: Single select
- **Options**: `0`, `1`, `2`, `3`, `5`, `8`
- **Default**: 0

#### Field 3: Sprint
- **Name**: `Sprint`
- **Type**: Single select
- **Options**:
  - Backlog
  - Sprint 1: Foundation
  - Sprint 2: Gold Layer
  - Sprint 3: Integration
  - Sprint 4: Production
- **Default**: Backlog

#### Field 4: Priority
- **Name**: `Priority`
- **Type**: Single select
- **Options**:
  - P0-critical
  - P1-high
  - P2-medium
  - P3-low
- **Default**: P2-medium

#### Field 5: Estimated Tokens
- **Name**: `Estimated Tokens`
- **Type**: Number
- **Default**: 0

#### Field 6: Actual Tokens
- **Name**: `Actual Tokens`
- **Type**: Number
- **Default**: 0

### 1.5 Create Board Views

GitHub Projects supports multiple views. Create these 5:

#### View 1: Kanban (Default)
- Already created as default
- **Group by**: Status
- **Sort**: Priority (high to low), then Story Points (high to low)

#### View 2: Sprint Board
1. Duplicate Kanban view
2. **Name**: `Sprint Board`
3. **Filter**: `sprint:"Sprint 3: Integration"` (update for current sprint)
4. **Group by**: Status
5. **Sort**: Priority, Story Points

#### View 3: Backlog
1. Duplicate Kanban view
2. **Name**: `Backlog`
3. **Filter**: `sprint:Backlog OR is:open`
4. **Group by**: Sprint
5. **Sort**: Priority, Story Points

#### View 4: By Priority
1. Duplicate Kanban view
2. **Name**: `By Priority`
3. **Group by**: Priority
4. **Sort**: Story Points (high to low)

#### View 5: By Component
1. Duplicate Kanban view
2. **Name**: `By Component`
3. **Filter**: `is:open`
4. **Group by**: Labels (select component-related labels)
5. **Sort**: Priority

---

## Step 2: Grant GitHub Token Project Scope (5 min)

The automation workflow needs a token with `project` scope to update board fields.

### 2.1 Generate New Token (or Update Existing)

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token (classic)"** or edit existing token
3. **Note**: `Congress Disclosures Projects Automation`
4. **Expiration**: No expiration (or your preference)
5. **Scopes** - Check these boxes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
   - ✅ `project` ⭐ **THIS IS CRITICAL**
   - ✅ `read:org` (if using organization projects)
6. Click **"Generate token"**
7. **Copy the token immediately** (you won't see it again!)

### 2.2 Save Token as GitHub Secret

1. Go to repository settings:
   ```bash
   open https://github.com/Jakeintech/congress-disclosures-standardized/settings/secrets/actions
   ```

2. Click **"New repository secret"**

3. **Name**: `PROJECTS_TOKEN`

4. **Value**: Paste the token you just copied

5. Click **"Add secret"**

### 2.3 Update Local gh CLI (Optional)

If you want to use `gh` CLI with project scope locally:

```bash
gh auth login
# Follow prompts
# When asked for scopes, include: repo, workflow, project
```

---

## Step 3: Configure Automation Workflow (5 min)

The workflow file `.github/workflows/projects-automation.yml` has already been created.

### 3.1 Update Project ID

Edit the workflow file and replace `project_id: 1` with your actual project number from Step 1.3:

```bash
# Open in your editor
code .github/workflows/projects-automation.yml

# Find this line:
project_id: 1  # TODO: Replace with your actual project number

# Replace with:
project_id: YOUR_NUMBER_FROM_STEP_1_3
```

### 3.2 Verify Custom Field Names Match

Ensure the field names in the workflow match EXACTLY what you created in Step 1.4:

```yaml
"name": "Status",          # Must match exactly
"name": "Story Points",    # Must match exactly
"name": "Sprint",          # Must match exactly
"name": "Priority",        # Must match exactly
```

If you named fields differently, update the workflow accordingly.

### 3.3 Commit and Push

```bash
git add .github/workflows/projects-automation.yml
git commit -m "feat(automation): add Projects board automation workflow

- Auto-adds issues/PRs to Projects board
- Auto-populates Story Points, Sprint, Priority from labels
- Auto-updates Status on assign/PR/close
- Uses leonsteinhaeuser/project-beta-automations@v2.2.1

Related: Sprint 3 automation setup"
git push origin main  # or your current branch
```

---

## Step 4: Add Existing Issues to Board (5 min)

You have 55 existing issues that need to be added to the board.

### Option A: Bulk Add via Workflow Trigger

Trigger the workflow for all existing issues by adding/removing a label:

```bash
# Get all issues
gh issue list --limit 100 --json number --jq '.[].number' | while read issue_num; do
  echo "Processing issue #$issue_num"
  # Add temporary label to trigger workflow
  gh issue edit $issue_num --add-label "needs-board-sync"
  sleep 1  # Rate limit protection
done

# After workflow runs, remove the temporary label
gh issue list --label "needs-board-sync" --json number --jq '.[].number' | while read issue_num; do
  gh issue edit $issue_num --remove-label "needs-board-sync"
done
```

### Option B: Manual Add via Projects UI

1. Go to your Projects board
2. Click **"+ Add items"** at bottom
3. Search: `repo:Jakeintech/congress-disclosures-standardized is:issue is:open`
4. Select all issues
5. Click **"Add selected items"**

The automation will populate fields automatically on next issue update.

### Option C: Add Specific Issues Only

Add just the high-priority issues (sprint 3, 4):

```bash
# Sprint 3 issues
gh issue list --label "sprint-3" --json number --jq '.[].number' | while read issue_num; do
  gh issue edit $issue_num --add-label "on-board"
  sleep 1
done

# Sprint 4 issues
gh issue list --label "sprint-4" --json number --jq '.[].number' | while read issue_num; do
  gh issue edit $issue_num --add-label "on-board"
  sleep 1
done
```

---

## Step 5: Test Automation (5 min)

Verify the automation works end-to-end.

### Test 1: Create New Issue

```bash
gh issue create \
  --title "Test: Board Automation Check" \
  --label "sprint-3,points-2,P2-medium,agent-task" \
  --body "Testing automated Projects board sync.

This issue should automatically:
- ✅ Appear on Projects board
- ✅ Have Story Points = 2
- ✅ Have Sprint = Sprint 3
- ✅ Have Priority = P2-medium
- ✅ Have Status = To Do"
```

**Expected Result**:
- Issue appears on board within ~30 seconds
- All custom fields populated correctly
- Automation posts confirmation comment

### Test 2: Assign Issue

```bash
# Assign to yourself
gh issue edit ISSUE_NUMBER --add-assignee @me
```

**Expected Result**:
- Status changes from "To Do" → "In Progress"

### Test 3: Create PR Linking to Issue

```bash
git checkout -b test/board-automation
echo "test" > test.txt
git add test.txt
git commit -m "test: board automation"
git push origin test/board-automation

gh pr create \
  --title "Test: PR Auto-Update" \
  --body "Closes #ISSUE_NUMBER

Testing that PR creation updates board status." \
  --base main
```

**Expected Result**:
- Issue status changes from "In Progress" → "In Review"

### Test 4: Close Issue

```bash
gh issue close ISSUE_NUMBER
```

**Expected Result**:
- Status changes from "In Review" → "Done"
- Issue remains visible on board (in "Done" column)

---

## Step 6: Enable Built-in Workflows (Optional) (5 min)

GitHub Projects has some built-in automations you can enable.

1. Go to Projects board
2. Click **"⚙️ Settings"** → **"Workflows"**
3. Enable these:

### Auto-add to project
- **Trigger**: Issues, Pull Requests
- **Filter**: `label:agent-task OR label:user-story`
- **Action**: Add to this project

### Auto-archive
- **Trigger**: Item closed
- **Action**: Archive item (keeps history, removes from active views)

---

## Troubleshooting

### Issue: Workflow fails with "Resource not accessible by integration"

**Cause**: Missing `project` scope on token

**Fix**:
1. Verify token has `project` scope (Step 2)
2. Re-save token as `PROJECTS_TOKEN` secret
3. Re-run workflow

### Issue: Fields not populating

**Cause**: Field names don't match exactly

**Fix**:
1. Check exact field names in Projects settings
2. Update workflow YAML to match (case-sensitive!)
3. Field type must also match (`single_select` vs `text`)

### Issue: Items not auto-adding

**Cause**: Missing filter in auto-add workflow

**Fix**:
1. Check Projects → Settings → Workflows
2. Ensure "Auto-add to project" is enabled
3. Filter should match your issue labels

### Issue: "Project not found"

**Cause**: Wrong project ID in workflow

**Fix**:
1. Check project URL: `https://github.com/users/Jakeintech/projects/NUMBER`
2. Update `project_id` in workflow YAML
3. Ensure organization vs user projects setting matches

---

## Maintenance

### Daily: None Required
- Automation runs on every issue/PR event
- No manual intervention needed

### Monthly: Review & Clean Up
- Archive completed issues
- Review sprint assignments
- Update current sprint filter in Sprint Board view

### Quarterly: Token Rotation
- If token expires, regenerate and update secret
- Consider using GitHub App for better security (future)

---

## Next Steps

Now that automation is set up, you can:

1. **Start using the board**:
   - View progress in Kanban view
   - Plan sprints in Sprint Board view
   - Prioritize in Backlog view

2. **Delegate to agents**:
   - Assign issues to AI agents (e.g., @claude-bot user)
   - Status auto-updates as agent works
   - Track progress in real-time

3. **Generate reports** (future enhancement):
   - Sprint velocity (story points completed)
   - Burn-down charts
   - Agent performance metrics

---

## Reference Links

- **Your Projects Board**: https://github.com/users/Jakeintech/projects/1
- **Workflow File**: `.github/workflows/projects-automation.yml`
- **Action Documentation**: https://github.com/leonsteinhaeuser/project-beta-automations
- **GitHub Projects Docs**: https://docs.github.com/en/issues/planning-and-tracking-with-projects

---

## Summary

**What You Built** (30 min setup):
- ✅ GitHub Projects board with 6 custom fields
- ✅ 5 views (Kanban, Sprint, Backlog, Priority, Component)
- ✅ Automated field population from labels
- ✅ Automated status transitions
- ✅ Integrated 55 existing issues
- ✅ Zero ongoing maintenance

**What You Get**:
- Real-time sprint tracking
- Automated task management
- Visual progress dashboards
- Agent workflow integration
- Accurate velocity metrics

**Total Cost**: $0
**Ongoing Effort**: 0 minutes/week

🎉 **You're now set up with production-grade agile automation!**
