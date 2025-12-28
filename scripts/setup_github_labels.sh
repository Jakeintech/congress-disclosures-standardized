#!/bin/bash
#
# Setup GitHub Labels for Agile Project Management
#
# Purpose: Creates comprehensive label set for sprint tracking, story points,
#          priorities, components, and workflow states.
#
# Usage:
#   ./scripts/setup_github_labels.sh
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - Appropriate permissions on repository
#
# Notes:
#   - Idempotent: Safe to run multiple times
#   - Existing labels with same name will be updated (color/description)
#   - Script will NOT delete any existing labels
#

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) not found. Install: brew install gh"
        exit 1
    fi

    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI not authenticated. Run: gh auth login"
        exit 1
    fi

    log_success "Prerequisites met"
}

# Create or update label
create_label() {
    local name="$1"
    local color="$2"
    local description="$3"

    # Check if label exists
    if gh label list --search "$name" | grep -q "^$name"; then
        # Update existing label
        gh label edit "$name" \
            --color "$color" \
            --description "$description" 2>/dev/null && \
            log_success "Updated: $name" || \
            log_warning "Failed to update: $name"
    else
        # Create new label
        gh label create "$name" \
            --color "$color" \
            --description "$description" 2>/dev/null && \
            log_success "Created: $name" || \
            log_warning "Failed to create: $name"
    fi
}

# Main execution
main() {
    log_info "Starting GitHub labels setup..."
    echo ""

    check_prerequisites
    echo ""

    # ==========================================
    # SPRINT LABELS
    # ==========================================
    log_info "Creating Sprint labels..."

    create_label "sprint-1" "0E8A16" "Sprint 1: Foundation (Dec 16-20, 2025)"
    create_label "sprint-2" "0E8A16" "Sprint 2: Gold Layer (Dec 23-27, 2025)"
    create_label "sprint-3" "0E8A16" "Sprint 3: Integration (Dec 30-Jan 3, 2026)"
    create_label "sprint-4" "0E8A16" "Sprint 4: Production (Jan 6-10, 2026)"

    echo ""

    # ==========================================
    # STORY POINTS LABELS
    # ==========================================
    log_info "Creating Story Points labels..."

    create_label "points-0" "EDEDED" "0 story points - No code changes (config/docs only)"
    create_label "points-1" "FBCA04" "1 story point (~10K tokens, 1-2 hours)"
    create_label "points-2" "FBCA04" "2 story points (~20K tokens, 2-4 hours)"
    create_label "points-3" "FBCA04" "3 story points (~30K tokens, 4-6 hours)"
    create_label "points-5" "FBCA04" "5 story points (~50K tokens, 1 day)"
    create_label "points-8" "FBCA04" "8 story points (~80K tokens, 2 days)"

    echo ""

    # ==========================================
    # PRIORITY LABELS
    # ==========================================
    log_info "Creating Priority labels..."

    create_label "P0-critical" "B60205" "Critical priority - blocks release"
    create_label "P1-high" "D93F0B" "High priority - must have"
    create_label "P2-medium" "FBCA04" "Medium priority - should have"
    create_label "P3-low" "0E8A16" "Low priority - nice to have"

    echo ""

    # ==========================================
    # STORY TYPE LABELS
    # ==========================================
    log_info "Creating Story Type labels..."

    create_label "user-story" "5319E7" "User story with acceptance criteria"
    create_label "technical-task" "5319E7" "Technical task (infrastructure, tooling)"
    create_label "epic" "3E4B9E" "Epic (collection of stories)"
    create_label "spike" "BFD4F2" "Spike (research/investigation)"

    echo ""

    # ==========================================
    # STATUS LABELS
    # ==========================================
    log_info "Creating Status labels..."

    create_label "blocked" "D93F0B" "Blocked by dependency or external issue"
    create_label "in-progress" "0E8A16" "Currently being worked on"
    create_label "in-review" "FBCA04" "Code review in progress"
    create_label "needs-handoff" "FEF2C0" "Needs handoff to another agent"
    create_label "agent-task" "D4C5F9" "Assigned to AI agent"

    echo ""

    # ==========================================
    # COMPONENT LABELS
    # ==========================================
    log_info "Creating Component labels..."

    create_label "lambda" "C5DEF5" "AWS Lambda function"
    create_label "terraform" "C5DEF5" "Infrastructure as Code (Terraform)"
    create_label "stepfunctions" "C5DEF5" "AWS Step Functions orchestration"
    create_label "testing" "C5DEF5" "Testing (unit, integration, E2E)"
    create_label "documentation" "0075CA" "Documentation changes"
    create_label "ci-cd" "C5DEF5" "CI/CD pipeline (GitHub Actions)"
    create_label "frontend" "C5DEF5" "Next.js website"

    echo ""

    # ==========================================
    # DATA LAYER LABELS
    # ==========================================
    log_info "Creating Data Layer labels..."

    create_label "bronze-layer" "D4C5F9" "Bronze layer (raw/immutable data)"
    create_label "silver-layer" "D4C5F9" "Silver layer (normalized/queryable)"
    create_label "gold-layer" "D4C5F9" "Gold layer (analytics-ready)"

    echo ""

    # ==========================================
    # WORKFLOW LABELS
    # ==========================================
    log_info "Creating Workflow labels..."

    create_label "good-first-issue" "7057FF" "Good for newcomers or first AI agent task"
    create_label "dependencies" "E99695" "Has dependencies on other stories"
    create_label "breaking-change" "D93F0B" "Breaking change - requires migration"
    create_label "needs-triage" "EDEDED" "Needs triage and prioritization"

    echo ""

    # ==========================================
    # QUALITY LABELS
    # ==========================================
    log_info "Creating Quality labels..."

    create_label "bug" "D73A4A" "Something isn't working"
    create_label "enhancement" "A2EEEF" "New feature or request"
    create_label "refactor" "FEF2C0" "Code refactoring (no behavior change)"
    create_label "performance" "BFDADC" "Performance improvement"
    create_label "security" "B60205" "Security vulnerability or concern"

    echo ""

    # ==========================================
    # MAINTENANCE LABELS
    # ==========================================
    log_info "Creating Maintenance labels..."

    create_label "duplicate" "CFD3D7" "Duplicate issue or PR"
    create_label "wontfix" "FFFFFF" "Will not be fixed"
    create_label "invalid" "E4E669" "Invalid issue"
    create_label "question" "D876E3" "Question about codebase or process"
    create_label "help-wanted" "008672" "Extra attention needed"

    echo ""

    # ==========================================
    # SPECIAL LABELS
    # ==========================================
    log_info "Creating Special labels..."

    create_label "urgent" "B60205" "Urgent - requires immediate attention"
    create_label "process-improvement" "FEF2C0" "Improvement to development process"
    create_label "onboarding" "BFD4F2" "Related to onboarding new agents/developers"
    create_label "legal-compliance" "D4C5F9" "Legal compliance requirement (5 U.S.C. § 13107)"

    echo ""

    # ==========================================
    # SUMMARY
    # ==========================================
    log_success "Label setup complete!"
    echo ""
    log_info "Summary of labels created:"

    local total_labels=$(gh label list | wc -l)
    log_info "Total labels in repository: $total_labels"

    echo ""
    log_info "Label categories:"
    echo "  • Sprint labels: 4 (sprint-1 through sprint-4)"
    echo "  • Story points: 5 (points-1 through points-8)"
    echo "  • Priority: 4 (P0-critical through P3-low)"
    echo "  • Story types: 4 (user-story, technical-task, epic, spike)"
    echo "  • Status: 5 (blocked, in-progress, in-review, needs-handoff, agent-task)"
    echo "  • Components: 7 (lambda, terraform, stepfunctions, testing, docs, ci-cd, frontend)"
    echo "  • Data layers: 3 (bronze-layer, silver-layer, gold-layer)"
    echo "  • Workflow: 4 (good-first-issue, dependencies, breaking-change, needs-triage)"
    echo "  • Quality: 5 (bug, enhancement, refactor, performance, security)"
    echo "  • Maintenance: 5 (duplicate, wontfix, invalid, question, help-wanted)"
    echo "  • Special: 4 (urgent, process-improvement, onboarding, legal-compliance)"
    echo ""
    echo "  TOTAL: 50 labels"

    echo ""
    log_info "Next steps:"
    echo "  1. Run: ./scripts/setup_github_milestones.sh"
    echo "  2. Run: python3 scripts/sync_stories_to_github.py"
    echo "  3. Set up GitHub Projects board manually or via API"

    echo ""
    log_success "All done! Labels are ready for use."
}

# Run main function
main

exit 0
