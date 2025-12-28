#!/bin/bash
#
# Setup GitHub Milestones for Agile Sprint Tracking
#
# Purpose: Creates 4 milestones for EPIC-001 sprints with correct due dates
#          and descriptions.
#
# Usage:
#   ./scripts/setup_github_milestones.sh
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - Appropriate permissions on repository
#
# Notes:
#   - Creates milestones if they don't exist
#   - Updates existing milestones with correct dates/descriptions
#   - Sprint 2 will be marked as closed (already complete)
#   - Idempotent: Safe to run multiple times
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

# Get milestone number by title
get_milestone_number() {
    local title="$1"
    gh api repos/:owner/:repo/milestones --jq ".[] | select(.title == \"$title\") | .number" 2>/dev/null || echo ""
}

# Create or update milestone
create_or_update_milestone() {
    local title="$1"
    local due_date="$2"
    local description="$3"
    local state="${4:-open}"  # open or closed

    local milestone_number=$(get_milestone_number "$title")

    if [ -n "$milestone_number" ]; then
        # Update existing milestone
        gh api \
            --method PATCH \
            "repos/:owner/:repo/milestones/$milestone_number" \
            -f title="$title" \
            -f state="$state" \
            -f description="$description" \
            -f due_on="$due_date" &>/dev/null && \
            log_success "Updated: $title (Milestone #$milestone_number, State: $state)" || \
            log_warning "Failed to update: $title"
    else
        # Create new milestone
        gh api \
            --method POST \
            repos/:owner/:repo/milestones \
            -f title="$title" \
            -f state="$state" \
            -f description="$description" \
            -f due_on="$due_date" &>/dev/null && \
            log_success "Created: $title (State: $state)" || \
            log_warning "Failed to create: $title"
    fi
}

# Main execution
main() {
    log_info "Starting GitHub milestones setup for EPIC-001..."
    echo ""

    check_prerequisites
    echo ""

    log_info "Creating/updating sprint milestones..."
    echo ""

    # ==========================================
    # SPRINT 1: FOUNDATION
    # ==========================================
    # Status: Merged into Sprint 2 (mark as closed)
    # Original dates: Dec 16-20, 2025
    # ==========================================

    create_or_update_milestone \
        "Sprint 1: Foundation" \
        "2025-12-20T23:59:59Z" \
        "Sprint 1: Foundation and Cost Optimization

**Status**: ⚠️ Merged into Sprint 2
**Planned**: Dec 16-20, 2025
**Actual**: Work absorbed into Sprint 2 (1-day sprint)

**Original Goals**:
- Fix EventBridge hourly trigger ($4K/month cost leak)
- Implement watermarking (House FD, Congress, Lobbying)
- Fix GitHub Actions to trigger Step Functions
- Update documentation

**Stories**: 16 stories, 41 points
**Outcome**: Consolidated with Sprint 2 for efficiency

See Sprint 2 for actual delivery." \
        "closed"

    # ==========================================
    # SPRINT 2: GOLD LAYER
    # ==========================================
    # Status: COMPLETE (mark as closed)
    # Planned: Dec 23-27, 2025
    # Actual: Completed Dec 16, 2025 (1-day sprint!)
    # ==========================================

    create_or_update_milestone \
        "Sprint 2: Gold Layer" \
        "2025-12-27T23:59:59Z" \
        "Sprint 2: Gold Layer Lambda Wrappers

**Status**: ✅ COMPLETE
**Planned**: Dec 23-27, 2025
**Actual**: Dec 16, 2025 (1-day sprint - exceptional velocity!)

**Goals Achieved**:
- Created 8 Gold layer Lambda function wrappers
- Integrated DuckDB v1.1.3 with PyArrow 18.1.0
- Built dimension tables (members, assets, bills)
- Built fact tables (transactions, filings, lobbying)
- Built aggregate tables (trending stocks, member stats)
- End-to-end tested 2 endpoints

**Deliverables**:
- 8 Lambda functions deployed
- All analytics endpoints operational
- 2 endpoints tested end-to-end
- Complete Terraform configuration

**Stories**: 12 stories, 43 points
**Velocity**: 43 points in 1 day (exceptional)

See: docs/agile/sprints/completed/SPRINT_02_REPORT.md" \
        "closed"

    # ==========================================
    # SPRINT 3: INTEGRATION
    # ==========================================
    # Status: IN PROGRESS (current sprint)
    # Dates: Dec 27, 2025 - Jan 3, 2026
    # ==========================================

    create_or_update_milestone \
        "Sprint 3: Integration" \
        "2026-01-03T23:59:59Z" \
        "Sprint 3: Integration, Testing & Quality

**Status**: 🔄 IN PROGRESS (Current Sprint)
**Dates**: Dec 27, 2025 - Jan 3, 2026
**Progress**: 17% complete (8/46 points)

**Goals**:
- Design and implement unified state machine orchestration
- Integrate quality checks (Soda) into pipeline
- Build remaining dimension tables (lobbyists, dates)
- Build remaining fact tables (cosponsors, amendments)
- Write comprehensive unit tests
- Add contract testing (Schemathesis)

**Focus Areas**:
- State machine design (Bronze → Silver → Gold flow)
- Quality gates between layers
- Error handling and retry logic
- Performance optimization
- Documentation updates

**Stories**: 16 stories, 46 points (revised from 52)
**Includes**: Phase 0 emergency work (8 points completed)

**Key Deliverables**:
- Unified Step Functions state machine
- Soda quality check integration
- Full test coverage for Gold layer
- Production-ready error handling

See: docs/agile/sprints/SPRINT_03_INTEGRATION.md" \
        "open"

    # ==========================================
    # SPRINT 4: PRODUCTION
    # ==========================================
    # Status: PLANNED (not yet started)
    # Dates: Jan 6-11, 2026
    # ==========================================

    create_or_update_milestone \
        "Sprint 4: Production" \
        "2026-01-11T23:59:59Z" \
        "Sprint 4: Production Readiness & Launch

**Status**: 📋 PLANNED
**Dates**: Jan 6-11, 2026
**Target**: Epic completion and production launch

**Goals**:
- Deploy full observability stack (monitoring, logging, tracing)
- Create CloudWatch dashboards (pipeline, cost)
- Configure alarms and alerts
- Enable X-Ray distributed tracing
- Write operational runbooks
- Complete deployment guides
- Write developer documentation
- Production deployment and validation

**Focus Areas**:
- Monitoring and observability
- Production deployment
- Documentation (operational, deployment, developer)
- End-to-end testing
- Performance validation
- Cost optimization verification

**Stories**: 14 stories, 31 points

**Key Deliverables**:
- CloudWatch dashboards operational
- Alarms configured and tested
- X-Ray tracing enabled
- Complete operational runbook
- Deployment automation verified
- Production system validated

**Success Criteria**:
- All 55 stories complete
- 99%+ pipeline success rate
- <4 hour processing time
- $47,820/year cost savings achieved
- Full observability operational

**Launch Date**: January 11, 2026

See: docs/agile/sprints/SPRINT_04_PRODUCTION.md" \
        "open"

    echo ""

    # ==========================================
    # SUMMARY
    # ==========================================
    log_success "Milestone setup complete!"
    echo ""
    log_info "Summary of milestones:"
    echo ""

    # Display all milestones
    gh milestone list --json number,title,state,dueOn,description | \
        jq -r '.[] | "  [\(.state | ascii_upcase)] \(.title)\n    Due: \(.dueOn)\n    Number: \(.number)\n"'

    echo ""
    log_info "Milestone statistics:"
    local total=$(gh milestone list | wc -l)
    local open=$(gh milestone list --state open | wc -l)
    local closed=$(gh milestone list --state closed | wc -l)

    echo "  • Total milestones: $total"
    echo "  • Open: $open"
    echo "  • Closed: $closed"
    echo ""

    log_info "Sprint timeline:"
    echo "  ✅ Sprint 1: Dec 16-20, 2025 (merged into Sprint 2)"
    echo "  ✅ Sprint 2: Dec 16, 2025 (COMPLETE - 1-day sprint)"
    echo "  🔄 Sprint 3: Dec 27 - Jan 3, 2026 (IN PROGRESS)"
    echo "  📋 Sprint 4: Jan 6-11, 2026 (PLANNED)"
    echo ""

    log_info "Next steps:"
    echo "  1. Verify milestones: gh milestone list"
    echo "  2. Run: python3 scripts/sync_stories_to_github.py"
    echo "  3. Assign stories to appropriate milestones"
    echo "  4. Set up GitHub Projects board"
    echo ""

    log_success "All done! Milestones are ready for use."
}

# Run main function
main

exit 0
