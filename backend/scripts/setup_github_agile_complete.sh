#!/bin/bash
#
# Complete GitHub Agile Setup - Master Orchestration Script
#
# Purpose: Runs all setup scripts in the correct order to create a fully
#          configured GitHub agile workflow with Projects, Issues, Labels,
#          Milestones, and Automation.
#
# Usage:
#   ./scripts/setup_github_agile_complete.sh [--dry-run] [--skip-issues]
#
# Options:
#   --dry-run      Show what would be created without actually creating
#   --skip-issues  Skip GitHub Issues creation (useful for testing)
#   --help         Show this help message
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - Python 3.11+ installed
#   - Appropriate GitHub permissions
#
# What This Script Does:
#   1. ✅ Verify prerequisites (gh CLI, auth, permissions)
#   2. ✅ Create/update all GitHub labels (53 labels)
#   3. ✅ Create/verify sprint milestones (4 milestones)
#   4. ✅ Create GitHub Projects (v2) board with custom fields
#   5. ✅ Import all user stories as GitHub Issues (55 issues)
#   6. ✅ Verify setup completeness
#   7. ✅ Display next steps
#

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
DRY_RUN=false
SKIP_ISSUES=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Functions
log_header() {
    echo ""
    echo -e "${BOLD}${BLUE}========================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}========================================${NC}"
    echo ""
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BOLD}Step $1: $2${NC}"
    echo ""
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        exit 1
    fi
    log_success "$1 is installed"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-issues)
            SKIP_ISSUES=true
            shift
            ;;
        --help)
            head -n 30 "$0" | grep "^#" | sed 's/^# //g' | sed 's/^#//g'
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log_header "GitHub Agile Setup - Complete Configuration"

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN MODE - No actual changes will be made"
        echo ""
    fi

    # Step 1: Verify Prerequisites
    log_step "1/6" "Verifying Prerequisites"

    check_command "gh"
    check_command "python3"
    check_command "jq"

    # Check GitHub auth
    if ! gh auth status >/dev/null 2>&1; then
        log_error "GitHub CLI not authenticated. Run: gh auth login"
        exit 1
    fi
    log_success "GitHub CLI authenticated"

    # Check we're in correct directory
    if [ ! -f "$PROJECT_ROOT/CLAUDE.md" ]; then
        log_error "Must run from project root or scripts/ directory"
        exit 1
    fi
    log_success "Running from correct directory: $PROJECT_ROOT"

    # Step 2: Create/Update Labels
    log_step "2/6" "Creating GitHub Labels (53 labels)"

    if [ ! -x "$SCRIPT_DIR/setup_github_labels.sh" ]; then
        chmod +x "$SCRIPT_DIR/setup_github_labels.sh"
    fi

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN: Would run setup_github_labels.sh"
    else
        log_info "Running label setup script..."
        "$SCRIPT_DIR/setup_github_labels.sh"
    fi

    # Step 3: Create/Verify Milestones
    log_step "3/6" "Creating Sprint Milestones (4 milestones)"

    if [ ! -x "$SCRIPT_DIR/setup_github_milestones.sh" ]; then
        chmod +x "$SCRIPT_DIR/setup_github_milestones.sh"
    fi

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN: Would run setup_github_milestones.sh"
    else
        log_info "Running milestone setup script..."
        "$SCRIPT_DIR/setup_github_milestones.sh"
    fi

    # Step 4: Create GitHub Projects Board
    log_step "4/6" "Creating GitHub Projects Board"

    if [ ! -x "$SCRIPT_DIR/create_github_project.sh" ]; then
        chmod +x "$SCRIPT_DIR/create_github_project.sh"
    fi

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN: Would create Projects board"
    else
        # Check if project already exists
        EXISTING_PROJECT=$(gh project list --owner Jakeintech --format json 2>/dev/null | \
            jq -r '.projects[] | select(.title=="Congress Disclosures Agile Board") | .number' || echo "")

        if [ -n "$EXISTING_PROJECT" ]; then
            log_warning "Project 'Congress Disclosures Agile Board' already exists (Project #$EXISTING_PROJECT)"
            log_info "Skipping project creation"
        else
            log_info "Running project creation script..."
            "$SCRIPT_DIR/create_github_project.sh"
        fi
    fi

    # Step 5: Import Stories as GitHub Issues
    log_step "5/6" "Importing User Stories as GitHub Issues (55 issues)"

    if [ "$SKIP_ISSUES" = true ]; then
        log_warning "Skipping issue creation (--skip-issues flag set)"
    else
        cd "$PROJECT_ROOT"

        if [ "$DRY_RUN" = true ]; then
            log_info "Running sync script in dry-run mode..."
            python3 "$SCRIPT_DIR/sync_stories_to_github.py" --dry-run
        else
            log_info "Running sync script..."
            python3 "$SCRIPT_DIR/sync_stories_to_github.py"
        fi
    fi

    # Step 6: Verification & Summary
    log_step "6/6" "Verification & Summary"

    if [ "$DRY_RUN" = false ]; then
        # Count labels
        LABEL_COUNT=$(gh label list --limit 100 --json name 2>/dev/null | jq '. | length' || echo "0")
        log_info "GitHub Labels: $LABEL_COUNT created"

        # Count milestones
        MILESTONE_COUNT=$(gh api repos/:owner/:repo/milestones 2>/dev/null | jq '. | length' || echo "0")
        log_info "GitHub Milestones: $MILESTONE_COUNT created"

        # Count issues
        ISSUE_COUNT=$(gh issue list --limit 100 --json number 2>/dev/null | jq '. | length' || echo "0")
        log_info "GitHub Issues: $ISSUE_COUNT created"

        # Check for project
        PROJECT_NUMBER=$(gh project list --owner Jakeintech --format json 2>/dev/null | \
            jq -r '.projects[] | select(.title=="Congress Disclosures Agile Board") | .number' || echo "")

        if [ -n "$PROJECT_NUMBER" ]; then
            log_success "GitHub Project: #$PROJECT_NUMBER created"
            PROJECT_URL="https://github.com/users/Jakeintech/projects/$PROJECT_NUMBER"
        else
            log_warning "GitHub Project: Not found (may need manual creation)"
            PROJECT_URL=""
        fi
    fi

    # Final Summary
    log_header "Setup Complete!"

    echo -e "${BOLD}✅ GitHub Agile Infrastructure Ready${NC}"
    echo ""
    echo -e "${GREEN}What was created:${NC}"
    echo "  ✓ 53 GitHub labels (sprints, points, priorities, components)"
    echo "  ✓ 4 Sprint milestones (Sprint 1-4)"
    if [ -n "$PROJECT_NUMBER" ]; then
        echo "  ✓ GitHub Projects board with custom fields"
    fi
    if [ "$SKIP_ISSUES" = false ] && [ "$DRY_RUN" = false ]; then
        echo "  ✓ $ISSUE_COUNT GitHub Issues imported from stories"
    fi
    echo ""

    echo -e "${BOLD}📋 Next Steps:${NC}"
    echo ""
    echo "1. Configure Projects Board Views:"
    if [ -n "$PROJECT_URL" ]; then
        echo "   Visit: $PROJECT_URL"
    else
        echo "   Visit: https://github.com/Jakeintech/congress-disclosures-standardized/projects"
    fi
    echo "   - Create Kanban view (Backlog → To Do → In Progress → In Review → Done)"
    echo "   - Create Sprint Board view (filtered by current sprint)"
    echo "   - Create Backlog view (grouped by Epic)"
    echo "   - Create Roadmap view (timeline by sprint)"
    echo ""

    echo "2. Set Up Project Automation:"
    echo "   - Auto-add issues with 'user-story' label"
    echo "   - Auto-move to 'In Progress' when PR linked"
    echo "   - Auto-move to 'Done' when issue closed"
    echo "   - See: .github/GITHUB_PROJECT_SETUP.md"
    echo ""

    echo "3. Configure Branch Protection:"
    echo "   GitHub → Settings → Branches → Add rule for 'main'"
    echo "   - Require pull request reviews (1 approval)"
    echo "   - Require status checks (test-unit, lint)"
    echo "   - Require conventional commits"
    echo ""

    echo "4. Review & Customize:"
    echo "   - Issue templates: .github/ISSUE_TEMPLATE/"
    echo "   - PR template: .github/pull_request_template.md"
    echo "   - Pre-commit hooks: .pre-commit-config.yaml"
    echo "   - GitHub Actions: .github/workflows/"
    echo ""

    echo "5. Start Working on Stories:"
    echo "   - View active stories: gh issue list --label 'sprint-3'"
    echo "   - Claim a story: Comment '@me' on issue"
    echo "   - Follow workflow: .github/AI_AGENT_WORKFLOW.md"
    echo "   - Use template: .github/AI_AGENT_TASK_TEMPLATE.md"
    echo ""

    echo -e "${BOLD}📚 Documentation:${NC}"
    echo "   - Setup Guide: .github/GITHUB_PROJECT_SETUP.md"
    echo "   - Agent Onboarding: .github/AGENT_ONBOARDING.md"
    echo "   - Workflow Guide: .github/AI_AGENT_WORKFLOW.md"
    echo "   - Quick Reference: .github/QUICK_REFERENCE.md (to be created)"
    echo "   - Roadmap: docs/agile/ROADMAP.md (to be created)"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN COMPLETE - No actual changes were made"
        echo "   Run without --dry-run to execute setup"
        echo ""
    fi

    log_success "GitHub Agile Setup Complete! 🎉"
}

# Run main function
main "$@"
