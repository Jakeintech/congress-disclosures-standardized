# GitHub Project Setup - Complete Agile Infrastructure

This document outlines the **complete GitHub agile setup** for scalable project management using GitHub's full capabilities.

## 🎯 Vision

Create a fully automated, scalable agile workflow leveraging:
- **GitHub Projects (v2)** - Kanban board with automation
- **Issue Templates** - Standardized story/task creation
- **Labels** - Comprehensive taxonomy for filtering/routing
- **Milestones** - Sprint tracking with burndown
- **GitHub Actions** - Automated workflows (sprint reports, metrics)
- **Branch Protection** - Quality gates

## 📋 Setup Checklist

### Phase 1: Core Configuration ✅

- [x] Create comprehensive label taxonomy (50 labels)
- [x] Create sprint milestones (4 milestones)
- [x] Fix story-to-issue sync script
- [ ] **Verify labels exist in GitHub**
- [ ] **Verify milestones exist in GitHub**
- [ ] **Add missing labels (points-0, etc.)**

### Phase 2: GitHub Projects Board 🔄

- [ ] Create GitHub Projects (v2) board
- [ ] Configure board views (Kanban, Sprint, Backlog, Roadmap)
- [ ] Set up automation rules (auto-add issues, status sync)
- [ ] Configure custom fields (Story Points, Sprint, Priority)
- [ ] Create saved filters

### Phase 3: Issue Templates 🔄

- [ ] Create story template (.github/ISSUE_TEMPLATE/user_story.yml)
- [ ] Create technical task template
- [ ] Create bug template
- [ ] Create spike template
- [ ] Configure issue template chooser

### Phase 4: Automation & Workflows 🔄

- [ ] GitHub Action: Daily standup report
- [ ] GitHub Action: Sprint burndown update
- [ ] GitHub Action: Auto-close completed stories
- [ ] GitHub Action: Story point validation
- [ ] GitHub Action: Dependency tracking

### Phase 5: Quality Gates 🔄

- [ ] Branch protection rules (main, enhancement)
- [ ] Required PR reviews
- [ ] Required status checks
- [ ] Conventional commit enforcement

---

## 🏷️ Label Taxonomy (Complete)

### 1. Sprint Labels (4)
```yaml
sprint-1:
  color: "1d76db"
  description: "Sprint 1: Foundation (Dec 16-20, 2025)"

sprint-2:
  color: "0e8a16"
  description: "Sprint 2: Gold Layer (Dec 16, 2025) - COMPLETE"

sprint-3:
  color: "fbca04"
  description: "Sprint 3: Integration (Dec 27 - Jan 3, 2026) - CURRENT"

sprint-4:
  color: "d93f0b"
  description: "Sprint 4: Production (Jan 6-11, 2026)"
```

### 2. Story Points (6) **FIXED: Added points-0**
```yaml
points-0:
  color: "ededed"
  description: "0 points - No code changes (config/docs only) - ~0 tokens"

points-1:
  color: "c2e0c6"
  description: "1 point - Trivial change - ~10K tokens"

points-2:
  color: "bfd4f2"
  description: "2 points - Small change - ~20K tokens"

points-3:
  color: "fef2c0"
  description: "3 points - Medium complexity - ~30K tokens"

points-5:
  color: "f9d0c4"
  description: "5 points - Complex change - ~50K tokens"

points-8:
  color: "d4c5f9"
  description: "8 points - Very complex - ~80K tokens"
```

### 3. Priority (4)
```yaml
P0-critical:
  color: "b60205"
  description: "Critical - Blocks progress, fix immediately"

P1-high:
  color: "d93f0b"
  description: "High priority - Important for sprint success"

P2-medium:
  color: "fbca04"
  description: "Medium priority - Should complete if time allows"

P3-low:
  color: "0e8a16"
  description: "Low priority - Nice to have"
```

### 4. Story Type (4)
```yaml
user-story:
  color: "1d76db"
  description: "User story with acceptance criteria"

technical-task:
  color: "5319e7"
  description: "Technical implementation task"

epic:
  color: "3e4b9e"
  description: "Large feature spanning multiple sprints"

spike:
  color: "c5def5"
  description: "Research/investigation task"
```

### 5. Status (5)
```yaml
blocked:
  color: "d93f0b"
  description: "Blocked by dependencies or external factors"

in-progress:
  color: "fbca04"
  description: "Currently being worked on"

in-review:
  color: "0075ca"
  description: "Pull request submitted, awaiting review"

needs-handoff:
  color: "d876e3"
  description: "Needs handoff between agents/developers"

agent-task:
  color: "7057ff"
  description: "Task ready for AI agent to claim"
```

### 6. Component (7)
```yaml
lambda:
  color: "ff9900"
  description: "AWS Lambda function changes"

terraform:
  color: "623ce4"
  description: "Infrastructure as code changes"

stepfunctions:
  color: "e99695"
  description: "AWS Step Functions state machine"

testing:
  color: "1abc9c"
  description: "Test implementation or coverage"

docs:
  color: "0075ca"
  description: "Documentation updates"

ci-cd:
  color: "2ecc71"
  description: "CI/CD pipeline changes"

frontend:
  color: "f9d0c4"
  description: "Website frontend changes"
```

### 7. Data Layer (3)
```yaml
bronze-layer:
  color: "cd7f32"
  description: "Raw data ingestion layer"

silver-layer:
  color: "c0c0c0"
  description: "Normalized data layer"

gold-layer:
  color: "ffd700"
  description: "Analytics/aggregation layer"
```

### 8. Workflow (4)
```yaml
dependencies:
  color: "d876e3"
  description: "Has dependencies on other stories"

breaking-change:
  color: "d93f0b"
  description: "Breaking API or schema change"

needs-qa:
  color: "fbca04"
  description: "Requires manual QA testing"

backlog:
  color: "ededed"
  description: "Backlog - not assigned to sprint"
```

### 9. Quality (3)
```yaml
bug:
  color: "d73a4a"
  description: "Bug or defect"

technical-debt:
  color: "795548"
  description: "Code refactoring or cleanup"

performance:
  color: "ff6b6b"
  description: "Performance optimization"
```

### 10. Maintenance (2)
```yaml
security:
  color: "b60205"
  description: "Security-related change"

monitoring:
  color: "0e8a16"
  description: "Logging, monitoring, or observability"
```

### 11. Special (3)
```yaml
good-first-issue:
  color: "7057ff"
  description: "Good for newcomers or AI agents"

help-wanted:
  color: "008672"
  description: "Extra attention needed"

wontfix:
  color: "ffffff"
  description: "Will not be implemented"
```

**Total: 53 labels** (including points-0 fix)

---

## 🎯 Milestones

### Sprint 1: Foundation
- **State**: CLOSED
- **Dates**: Dec 16-20, 2025
- **Description**: Cost optimization, watermarking, pipeline fixes
- **Stories**: STORY-001 through STORY-016 (merged into Sprint 2)

### Sprint 2: Gold Layer
- **State**: CLOSED
- **Dates**: Dec 16, 2025
- **Description**: Aggregations, analytics, member dimensions
- **Stories**: STORY-017 through STORY-027
- **Completion**: 100%

### Sprint 3: Integration
- **State**: OPEN (CURRENT)
- **Dates**: Dec 27, 2025 - Jan 3, 2026
- **Description**: Congress API, lobbying data, cross-dataset correlation
- **Stories**: STORY-028 through STORY-041
- **Progress**: 17% (2/12 complete)

### Sprint 4: Production
- **State**: OPEN
- **Dates**: Jan 6-11, 2026
- **Description**: Production deployment, documentation, monitoring
- **Stories**: STORY-042 through STORY-055
- **Progress**: 0% (planned)

---

## 📊 GitHub Projects Board Configuration

### Board: Congress Disclosures Agile Board

#### View 1: Kanban (Default)
**Columns**:
- 📋 Backlog (status: none, no sprint)
- 📝 To Do (has sprint, status: none)
- 🔄 In Progress (status: in-progress)
- 👀 In Review (status: in-review)
- ✅ Done (state: closed)

**Automation**:
- Auto-add new issues with `user-story` or `technical-task` label
- Auto-move to "In Progress" when PR linked
- Auto-move to "In Review" when PR ready for review
- Auto-move to "Done" when issue closed

#### View 2: Sprint Board
**Filter**: Current sprint only
**Group by**: Status
**Sort by**: Priority (P0 → P3), then Story Points (8 → 1)
**Fields**: Story Points, Assignee, Priority, Sprint

#### View 3: Backlog
**Filter**: No sprint assigned OR sprint = future
**Group by**: Epic
**Sort by**: Priority
**Fields**: Story Points, Priority, Dependencies

#### View 4: Roadmap (Timeline)
**View type**: Roadmap
**Date field**: Sprint dates
**Group by**: Sprint
**Show**: All open issues

#### View 5: By Component
**Group by**: Component label
**Filter**: Open issues only
**Fields**: Sprint, Story Points, Assignee

### Custom Fields

```yaml
Story Points:
  type: single_select
  options: [0, 1, 2, 3, 5, 8]

Sprint:
  type: single_select
  options:
    - Sprint 1: Foundation
    - Sprint 2: Gold Layer
    - Sprint 3: Integration
    - Sprint 4: Production
    - Backlog

Priority:
  type: single_select
  options: [P0, P1, P2, P3]

Component:
  type: single_select
  options: [Lambda, Terraform, StepFunctions, Testing, Docs, CI/CD, Frontend]

Estimated Tokens:
  type: number
  description: "Token estimate based on story points"

Actual Tokens:
  type: number
  description: "Actual tokens used (from PR)"
```

---

## 🎫 Issue Templates

### Template 1: User Story (.github/ISSUE_TEMPLATE/user_story.yml)

```yaml
name: User Story
description: Create a new user story for agile development
title: "[STORY-XXX] "
labels: ["user-story", "agent-task"]
assignees: []

body:
  - type: markdown
    attributes:
      value: |
        ## User Story Template
        Complete all sections below. See [AI Agent Task Template](.github/AI_AGENT_TASK_TEMPLATE.md) for implementation guidance.

  - type: dropdown
    id: epic
    attributes:
      label: Epic
      options:
        - EPIC-001: Foundation & Infrastructure
        - EPIC-002: Data Quality & Monitoring
        - EPIC-003: Advanced Analytics
    validations:
      required: true

  - type: dropdown
    id: sprint
    attributes:
      label: Sprint
      options:
        - Sprint 3: Integration
        - Sprint 4: Production
        - Backlog
    validations:
      required: true

  - type: dropdown
    id: points
    attributes:
      label: Story Points
      description: Complexity estimate (1=trivial, 8=very complex)
      options:
        - "0"
        - "1"
        - "2"
        - "3"
        - "5"
        - "8"
    validations:
      required: true

  - type: dropdown
    id: priority
    attributes:
      label: Priority
      options:
        - P0 - Critical
        - P1 - High
        - P2 - Medium
        - P3 - Low
    validations:
      required: true

  - type: textarea
    id: user_story
    attributes:
      label: User Story
      description: "Format: As a [role], I want [feature], so that [benefit]"
      placeholder: |
        **As a** data engineer
        **I want** automated quality checks
        **So that** I can trust the data pipeline
    validations:
      required: true

  - type: textarea
    id: acceptance_criteria
    attributes:
      label: Acceptance Criteria
      description: "Testable conditions for completion"
      placeholder: |
        - [ ] Criterion 1
        - [ ] Criterion 2
        - [ ] Criterion 3
    validations:
      required: true

  - type: textarea
    id: technical_tasks
    attributes:
      label: Technical Tasks
      description: "Implementation steps"
      placeholder: |
        1. Task 1
        2. Task 2
        3. Task 3
    validations:
      required: false

  - type: textarea
    id: dependencies
    attributes:
      label: Dependencies
      description: "List STORY-XXX dependencies"
      placeholder: |
        - STORY-001 (required)
        - STORY-015 (optional)
    validations:
      required: false

  - type: checkboxes
    id: components
    attributes:
      label: Components
      options:
        - label: Lambda
        - label: Terraform
        - label: Step Functions
        - label: Testing
        - label: Documentation
        - label: CI/CD
        - label: Frontend
```

### Template 2: Technical Task

Similar structure but simplified (no user story section, focus on technical implementation)

### Template 3: Bug Report

Standard bug template with reproduction steps, expected vs actual behavior

### Template 4: Spike

Research/investigation template with questions to answer, acceptance criteria based on knowledge gained

---

## 🤖 GitHub Actions Workflows

### 1. Daily Standup Report (.github/workflows/daily_standup.yml)

```yaml
name: Daily Standup Report

on:
  schedule:
    - cron: '0 9 * * 1-5'  # 9 AM weekdays
  workflow_dispatch:

jobs:
  standup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate Standup Report
        run: |
          python3 scripts/generate_standup_report.py

      - name: Post to Slack
        if: env.SLACK_WEBHOOK_URL != ''
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK_URL }} \
            -H 'Content-Type: application/json' \
            -d @standup_report.json
```

### 2. Sprint Burndown (.github/workflows/sprint_burndown.yml)

Updates sprint progress metrics daily

### 3. Story Point Validator (.github/workflows/validate_story_points.yml)

Validates that issues have proper labels and story points on PR

### 4. Auto-close Completed (.github/workflows/auto_close_done.yml)

Closes issues when PR merged and all acceptance criteria met

---

## 🔒 Branch Protection Rules

### Branch: `main`

```yaml
required_pull_request_reviews:
  required_approving_review_count: 1
  dismiss_stale_reviews: true
  require_code_owner_reviews: false

required_status_checks:
  strict: true
  contexts:
    - "test-unit"
    - "test-integration"
    - "lint"
    - "type-check"

enforce_admins: false
restrictions: null

required_linear_history: true
allow_force_pushes: false
allow_deletions: false
```

### Branch: `enhancement`

```yaml
required_pull_request_reviews:
  required_approving_review_count: 0  # Lighter for active development

required_status_checks:
  strict: false
  contexts:
    - "test-unit"

enforce_admins: false
```

---

## 📝 Setup Scripts

### Script 1: Complete Label Setup
File: `scripts/setup_github_labels_complete.sh`

Creates all 53 labels including points-0

### Script 2: Milestone Setup with Verification
File: `scripts/setup_github_milestones_verified.sh`

Creates milestones and verifies they exist

### Script 3: Create GitHub Project
File: `scripts/create_github_project.sh`

Uses `gh api` to create Projects board with all views and automations

### Script 4: Setup Issue Templates
File: `scripts/setup_issue_templates.sh`

Copies issue templates to `.github/ISSUE_TEMPLATE/`

### Script 5: Import Stories to Issues
File: `scripts/sync_stories_to_github.py` (already created, needs verification)

---

## 🎯 Execution Plan

### Step 1: Verify & Fix Core Config
```bash
# Verify labels
gh label list

# Verify milestones
gh api repos/:owner/:repo/milestones

# Add missing labels (points-0)
gh label create "points-0" --color "ededed" --description "0 points - No code changes"
```

### Step 2: Create GitHub Projects Board
```bash
# Create project
gh project create --owner Jakeintech --title "Congress Disclosures Agile Board"

# Configure views (manual or via API)
```

### Step 3: Setup Issue Templates
```bash
# Copy templates
cp -r .github/ISSUE_TEMPLATE_EXAMPLES/* .github/ISSUE_TEMPLATE/
git add .github/ISSUE_TEMPLATE/
git commit -m "feat: add issue templates for agile workflow"
```

### Step 4: Import Stories
```bash
# Dry run
python3 scripts/sync_stories_to_github.py --dry-run

# Execute
python3 scripts/sync_stories_to_github.py
```

### Step 5: Configure Automations
```bash
# Add GitHub Actions
git add .github/workflows/
git commit -m "feat: add agile automation workflows"
```

### Step 6: Manual Configuration
- Set up Projects board views (via UI)
- Configure branch protection rules (via UI)
- Add team members/collaborators
- Configure notifications

---

## 📊 Success Metrics

- ✅ All 55 stories imported as GitHub Issues
- ✅ Projects board shows current sprint status
- ✅ Burndown chart updates daily
- ✅ AI agents can claim and complete tasks
- ✅ Conventional commits enforced
- ✅ Pre-commit hooks prevent bad commits
- ✅ Sprint reports auto-generated

---

## 🔗 References

- [GitHub Projects Documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [Issue Templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [GitHub Actions for Projects](https://github.com/actions/add-to-project)
