# Manual GitHub Setup Guide - Complete UI Configuration

## 🎯 Overview

This guide covers **manual GitHub UI configuration** that cannot be automated via CLI/API without additional token scopes. Follow these steps to complete the GitHub agile infrastructure.

**Status After Script Execution**:
- ✅ 50+ Labels created
- ✅ 4 Milestones created
- ✅ 55 GitHub Issues created
- ❌ Projects board (requires manual creation - needs 'project' token scope)
- ❌ Wiki setup (optional)
- ❌ Discussions enabled (optional)
- ❌ Branch protection rules (manual configuration recommended)

---

## 📊 Step 1: Create GitHub Projects (v2) Board

### 1.1 Create New Project

1. Go to: https://github.com/users/Jakeintech/projects
2. Click **"New project"** button
3. Select **"Board"** template (NOT "Table" or "Roadmap" - you'll add those views later)
4. Name: `Congress Disclosures Agile Board`
5. Description: `Agile project management for Congress disclosure data pipeline with sprint tracking, story points, and AI agent coordination`
6. Click **"Create project"**

### 1.2 Link Project to Repository

1. In your new project, click **⚙️ Settings** (top right)
2. Under **"Manage access"**, click **"Add repository"**
3. Search for `congress-disclosures-standardized`
4. Click **"Add"**
5. Permission level: **Write** (allows automation to update)

### 1.3 Add Custom Fields

Click **⚙️ Settings** → **"Custom fields"** → **"+ New field"**

**Field 1: Story Points**
- Name: `Story Points`
- Type: `Single select`
- Options:
  - 0 (gray)
  - 1 (green)
  - 2 (blue)
  - 3 (yellow)
  - 5 (orange)
  - 8 (pink)

**Field 2: Sprint**
- Name: `Sprint`
- Type: `Single select`
- Options:
  - Sprint 1: Foundation (blue)
  - Sprint 2: Gold Layer (green)
  - Sprint 3: Integration (yellow)
  - Sprint 4: Production (orange)
  - Backlog (gray)

**Field 3: Priority**
- Name: `Priority`
- Type: `Single select`
- Options:
  - P0 (red)
  - P1 (orange)
  - P2 (yellow)
  - P3 (green)

**Field 4: Component**
- Name: `Component`
- Type: `Single select`
- Options:
  - Lambda (orange)
  - Terraform (pink)
  - StepFunctions (purple)
  - Testing (green)
  - Docs (blue)
  - CI/CD (yellow)
  - Frontend (pink)

**Field 5: Estimated Tokens**
- Name: `Estimated Tokens`
- Type: `Number`

**Field 6: Actual Tokens**
- Name: `Actual Tokens`
- Type: `Number`

### 1.4 Create Board Views

#### View 1: Kanban (Default)

1. Click **"+ New view"** → **"Board"**
2. Name: `Kanban`
3. Group by: `Status`
4. Configure columns:
   - **Backlog**: Filter `no:sprint` OR `sprint:"Backlog"`
   - **To Do**: Has sprint, Status = none
   - **In Progress**: Status = `in-progress`
   - **In Review**: Status = `in-review`
   - **Done**: State = `closed`

#### View 2: Sprint Board

1. Click **"+ New view"** → **"Board"**
2. Name: `Sprint 3 Board`
3. Filter: `label:"sprint-3" is:open`
4. Group by: `Status`
5. Sort by: `Priority` (P0 first), then `Story Points` (8 first)

#### View 3: Backlog

1. Click **"+ New view"** → **"Board"**
2. Name: `Backlog`
3. Filter: `label:"backlog"` OR `no:sprint` OR `is:open`
4. Group by: `Epic` (requires adding Epic field)
5. Sort by: `Priority`

#### View 4: Roadmap

1. Click **"+ New view"** → **"Roadmap"**
2. Name: `Roadmap`
3. Start date: Map to milestone `due_on`
4. Duration: 1 week (sprint length)
5. Group by: `Sprint`
6. Filter: `is:open`

#### View 5: By Component

1. Click **"+ New view"** → **"Board"**
2. Name: `By Component`
3. Filter: `is:open`
4. Group by: `Component`
5. Sort by: `Priority`

### 1.5 Configure Automation Workflows

Click **⚙️ Settings** → **"Workflows"**

**Workflow 1: Auto-add Items**
1. Click **"Edit workflows"**
2. Enable **"Auto-add to project"**
3. Trigger: Issue opened
4. Condition: Label contains `user-story` OR `technical-task` OR `agent-task`
5. Action: Add to project

**Workflow 2: Auto-move to In Progress**
1. Add workflow: **"Item reopened"**
2. Trigger: Pull request linked to issue
3. Action: Set Status to "In Progress"

**Workflow 3: Auto-move to In Review**
1. Add workflow: **"Pull request opened"**
2. Trigger: Pull request marked ready for review
3. Action: Set Status to "In Review"

**Workflow 4: Auto-close**
1. Add workflow: **"Item closed"**
2. Trigger: Issue closed
3. Action: Set Status to "Done"

### 1.6 Add Existing Issues to Project

**Option A: Bulk Add (Recommended)**
1. In project, click **"+ Add items"**
2. Search: `repo:Jakeintech/congress-disclosures-standardized is:issue`
3. Select all issues (or filter by sprint)
4. Click **"Add selected items"**

**Option B: Enable Auto-add**
- Once automation is enabled (step 1.5), new issues will auto-add
- For existing issues, manually add or use bulk add

---

## 🔒 Step 2: Configure Branch Protection

### 2.1 Protect `main` Branch

1. Go to: https://github.com/Jakeintech/congress-disclosures-standardized/settings/branches
2. Click **"Add branch protection rule"**
3. Branch name pattern: `main`

**Configure**:
```
✅ Require a pull request before merging
  ✅ Require approvals (1)
  ✅ Dismiss stale pull request approvals when new commits are pushed
  ✅ Require review from Code Owners (if CODEOWNERS file exists)

✅ Require status checks to pass before merging
  ✅ Require branches to be up to date before merging
  Add status checks:
    - test-unit (if exists in CI)
    - lint (if exists)
    - type-check (if exists)

✅ Require conversation resolution before merging

✅ Require linear history

✅ Include administrators (optional - for stricter enforcement)

❌ Allow force pushes
❌ Allow deletions
```

4. Click **"Create"** or **"Save changes"**

### 2.2 Protect `enhancement` Branch (Optional)

Same as above but with lighter requirements:
```
✅ Require a pull request before merging
  ✅ Require approvals (0) - lighter for development

✅ Require status checks to pass before merging
  Add: test-unit only

❌ Require linear history (allow merge commits for dev)
```

---

## 📖 Step 3: Enable Wiki (Optional)

### 3.1 Enable Wiki

1. Go to: https://github.com/Jakeintech/congress-disclosures-standardized/settings
2. Scroll to **"Features"** section
3. Check **✅ Wikis**
4. Click **"Save"**

### 3.2 Create Wiki Pages

1. Go to: https://github.com/Jakeintech/congress-disclosures-standardized/wiki
2. Click **"Create the first page"**

**Suggested Pages**:
- **Home**: Project overview, quick links
- **Getting Started**: Setup guide for new contributors
- **Architecture**: Link to docs/ARCHITECTURE.md
- **API Documentation**: Link to API docs
- **Deployment**: Link to docs/DEPLOYMENT.md
- **Troubleshooting**: Common issues and solutions
- **FAQ**: Frequently asked questions

---

## 💬 Step 4: Enable Discussions (Optional)

### 4.1 Enable Discussions

1. Go to: https://github.com/Jakeintech/congress-disclosures-standardized/settings
2. Scroll to **"Features"** section
3. Check **✅ Discussions**
4. Click **"Save"**

### 4.2 Configure Discussion Categories

1. Go to: https://github.com/Jakeintech/congress-disclosures-standardized/discussions
2. Click **⚙️ Edit pinned discussions and categories**

**Suggested Categories**:
- 💡 **Ideas**: Feature requests and suggestions
- 🙏 **Q&A**: Questions and answers
- 📣 **Announcements**: Project updates
- 🐛 **Bugs**: Bug discussion (before creating issues)
- 🚀 **Show and tell**: Share your work
- 💬 **General**: General discussion

---

## 📁 Step 5: Configure Repository Settings

### 5.1 General Settings

Go to: https://github.com/Jakeintech/congress-disclosures-standardized/settings

**Features**:
```
✅ Issues
✅ Preserve this repository (if important)
✅ Sponsorships (if accepting donations)
❌ Restrict editing to users in teams with push access only
✅ Allow merge commits (optional)
✅ Allow squash merging ← Recommended for clean history
✅ Allow rebase merging
❌ Always suggest updating pull request branches
✅ Automatically delete head branches
```

**Pull Requests**:
```
✅ Allow squash merging
  ✅ Default to pull request title and description

❌ Allow merge commits (or enable with default message)

✅ Allow rebase merging

✅ Always suggest updating pull request branches
✅ Automatically delete head branches ← Important for cleanup
```

### 5.2 Code Security and Analysis

**Dependabot**:
```
✅ Enable Dependabot alerts
✅ Enable Dependabot security updates
✅ Enable Dependabot version updates
```

**Code Scanning**:
```
✅ Enable CodeQL analysis (click "Set up" and commit workflow)
```

**Secret Scanning**:
```
✅ Enable secret scanning
✅ Enable push protection
```

---

## 🏷️ Step 6: Verify Labels and Milestones

### 6.1 Verify Labels

Go to: https://github.com/Jakeintech/congress-disclosures-standardized/labels

**Should see**:
- 4 Sprint labels (sprint-1, sprint-2, sprint-3, sprint-4)
- 6 Story Points (points-0, points-1, points-2, points-3, points-5, points-8)
- 4 Priority (P0-critical, P1-high, P2-medium, P3-low)
- 5 Status (blocked, in-progress, in-review, needs-handoff, agent-task)
- 7 Components (lambda, terraform, stepfunctions, testing, documentation, ci-cd, frontend)
- Plus workflow, quality, maintenance, data layer labels

**Total**: 50+ labels

### 6.2 Verify Milestones

Go to: https://github.com/Jakeintech/congress-disclosures-standardized/milestones

**Should see**:
1. Sprint 1: Foundation (closed) - 16 issues
2. Sprint 2: Gold Layer (closed) - 12 issues
3. Sprint 3: Integration (open) - 13 issues
4. Sprint 4: Production (open) - 10 issues

### 6.3 Verify Issues

Go to: https://github.com/Jakeintech/congress-disclosures-standardized/issues

**Should see**: 55 issues total
- Sprint 1: 16 issues (STORY-002 through STORY-015, STORY-046, STORY-047, STORY-051, STORY-054)
- Sprint 2: 12 issues (STORY-016 through STORY-027)
- Sprint 3: 13 issues (STORY-028 through STORY-041)
- Sprint 4: 10 issues (STORY-042 through STORY-045, STORY-048 through STORY-050, STORY-055, STORY-056)

---

## 📧 Step 7: Configure Notifications

### 7.1 Watch Repository

1. Go to: https://github.com/Jakeintech/congress-disclosures-standardized
2. Click **Watch** → **All Activity** (top right)
3. This ensures you get notified of all issues, PRs, etc.

### 7.2 Customize Notifications

1. Go to: https://github.com/settings/notifications
2. Configure email/web notifications as desired
3. Recommended:
   - ✅ Pull Request reviews
   - ✅ Pull Request pushes
   - ✅ Comments on Issues and Pull Requests
   - ✅ New Issues
   - ✅ CI Activity (failures)

---

## ✅ Verification Checklist

After completing all steps, verify:

- [ ] GitHub Projects board exists
- [ ] Projects board has 6 custom fields (Story Points, Sprint, Priority, Component, Estimated Tokens, Actual Tokens)
- [ ] Projects board has 5 views (Kanban, Sprint Board, Backlog, Roadmap, By Component)
- [ ] Automation workflows configured (4 workflows)
- [ ] All 55 issues added to Projects board
- [ ] Branch protection on `main` branch enabled
- [ ] Wiki enabled (optional)
- [ ] Discussions enabled (optional)
- [ ] Dependabot enabled
- [ ] Secret scanning enabled
- [ ] 50+ labels exist
- [ ] 4 milestones exist (2 closed, 2 open)
- [ ] 55 GitHub issues exist

---

## 🔗 Quick Links After Setup

**Projects**:
- Projects board: `https://github.com/users/Jakeintech/projects/{NUMBER}`
- Issues: https://github.com/Jakeintech/congress-disclosures-standardized/issues
- Milestones: https://github.com/Jakeintech/congress-disclosures-standardized/milestones
- Labels: https://github.com/Jakeintech/congress-disclosures-standardized/labels

**Settings**:
- Branch protection: https://github.com/Jakeintech/congress-disclosures-standardized/settings/branches
- Actions: https://github.com/Jakeintech/congress-disclosures-standardized/settings/actions
- Secrets: https://github.com/Jakeintech/congress-disclosures-standardized/settings/secrets/actions

**Optional**:
- Wiki: https://github.com/Jakeintech/congress-disclosures-standardized/wiki
- Discussions: https://github.com/Jakeintech/congress-disclosures-standardized/discussions

---

## 📊 What Was Automated vs Manual

### ✅ Automated (via Scripts)
- 50+ GitHub labels
- 4 Sprint milestones
- 55 GitHub Issues from story files
- Story-to-issue mapping file
- Pre-commit hooks configuration
- Issue templates
- PR template

### 🖱️ Manual (This Guide)
- GitHub Projects (v2) board creation
- Projects board views configuration
- Projects automation workflows
- Adding issues to Projects board
- Branch protection rules
- Wiki setup
- Discussions setup
- Repository settings
- Dependabot configuration
- Code scanning setup

---

## 🎓 Why Manual Steps Are Required

**GitHub Token Scopes**:
- Creating Projects (v2) requires `project` scope
- Your current token has: `gist`, `read:org`, `repo`
- To grant `project` scope: https://github.com/settings/tokens
  - Regenerate token with `project` scope added
  - Update `gh auth login` with new token
  - Re-run `./scripts/create_github_project.sh`

**Repository Settings**:
- Many settings (branch protection, features, security) can only be configured via UI for safety
- GitHub intentionally requires manual confirmation for security settings

---

## 📝 Next Steps After Manual Setup

1. **Test the workflow**:
   ```bash
   # Claim an issue
   gh issue view 4
   gh issue comment 4 --body "@me"

   # Create branch
   git checkout -b agent/test/story-028-unified-state-machine

   # Make changes, commit, push
   git commit -m "feat(stepfunctions): design unified state machine JSON"
   git push origin agent/test/story-028-unified-state-machine

   # Create PR
   gh pr create --title "[STORY-028] Design Unified State Machine JSON" \
     --body "Closes #4" \
     --label "sprint-3" --label "points-3"
   ```

2. **Verify Projects automation**:
   - Check issue auto-added to board
   - Check status auto-updated when PR created

3. **Update documentation**:
   - Run remaining documentation tasks
   - Update CONTRIBUTING.md with workflow
   - Update README.md with Projects board link

---

*Last Updated: 2025-12-27*
*See Also*: `.github/GITHUB_PROJECT_SETUP.md`, `.github/AGILE_SETUP_COMPLETE.md`
