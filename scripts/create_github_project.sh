#!/bin/bash
#
# Create GitHub Projects (v2) Board for Agile Management
#
# Purpose: Creates a complete Projects board with multiple views, custom fields,
#          and automation rules for agile sprint tracking.
#
# Usage:
#   ./scripts/create_github_project.sh
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - Project creation permissions (org owner or repo admin)
#
# References:
#   - https://docs.github.com/en/issues/planning-and-tracking-with-projects
#   - https://docs.github.com/en/graphql/reference/mutations#createprojectv2
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Configuration
OWNER="Jakeintech"
REPO="congress-disclosures-standardized"
PROJECT_TITLE="Congress Disclosures Agile Board"
PROJECT_DESC="Agile project management for Congress disclosure data pipeline with sprint tracking, story points, and AI agent coordination"

log_info "Creating GitHub Projects board..."
echo ""

# Check auth
if ! gh auth status >/dev/null 2>&1; then
    log_error "GitHub CLI not authenticated. Run: gh auth login"
    exit 1
fi

log_success "GitHub CLI authenticated"
echo ""

# Get owner ID (user or org)
log_info "Getting owner information..."
OWNER_TYPE=$(gh api graphql -f query="
  query {
    repositoryOwner(login: \"$OWNER\") {
      __typename
    }
  }
" --jq '.data.repositoryOwner.__typename')

if [ "$OWNER_TYPE" = "User" ]; then
    OWNER_ID=$(gh api graphql -f query="
      query {
        user(login: \"$OWNER\") {
          id
        }
      }
    " --jq '.data.user.id')
else
    OWNER_ID=$(gh api graphql -f query="
      query {
        organization(login: \"$OWNER\") {
          id
        }
      }
    " --jq '.data.organization.id')
fi

log_success "Owner ID: $OWNER_ID"
echo ""

# Create project
log_info "Creating project: $PROJECT_TITLE"
PROJECT_ID=$(gh api graphql -f query="
  mutation {
    createProjectV2(input: {
      ownerId: \"$OWNER_ID\"
      title: \"$PROJECT_TITLE\"
    }) {
      projectV2 {
        id
        number
        url
      }
    }
  }
" --jq '.data.createProjectV2.projectV2.id')

PROJECT_NUMBER=$(gh api graphql -f query="
  mutation {
    createProjectV2(input: {
      ownerId: \"$OWNER_ID\"
      title: \"$PROJECT_TITLE\"
    }) {
      projectV2 {
        number
      }
    }
  }
" --jq '.data.createProjectV2.projectV2.number' 2>/dev/null || echo "")

log_success "Project created! ID: $PROJECT_ID"
echo ""

# Link project to repository
log_info "Linking project to repository..."
REPO_ID=$(gh api graphql -f query="
  query {
    repository(owner: \"$OWNER\", name: \"$REPO\") {
      id
    }
  }
" --jq '.data.repository.id')

gh api graphql -f query="
  mutation {
    linkProjectV2ToRepository(input: {
      projectId: \"$PROJECT_ID\"
      repositoryId: \"$REPO_ID\"
    }) {
      repository {
        name
      }
    }
  }
" >/dev/null

log_success "Project linked to repository"
echo ""

# Add custom fields
log_info "Adding custom fields..."

# Story Points field
STORY_POINTS_FIELD_ID=$(gh api graphql -f query="
  mutation {
    createProjectV2Field(input: {
      projectId: \"$PROJECT_ID\"
      dataType: SINGLE_SELECT
      name: \"Story Points\"
      singleSelectOptions: [
        {name: \"0\", color: GRAY}
        {name: \"1\", color: GREEN}
        {name: \"2\", color: BLUE}
        {name: \"3\", color: YELLOW}
        {name: \"5\", color: ORANGE}
        {name: \"8\", color: PINK}
      ]
    }) {
      projectV2Field {
        ... on ProjectV2SingleSelectField {
          id
          name
        }
      }
    }
  }
" --jq '.data.createProjectV2Field.projectV2Field.id')

log_success "Created Story Points field"

# Sprint field
SPRINT_FIELD_ID=$(gh api graphql -f query="
  mutation {
    createProjectV2Field(input: {
      projectId: \"$PROJECT_ID\"
      dataType: SINGLE_SELECT
      name: \"Sprint\"
      singleSelectOptions: [
        {name: \"Sprint 1: Foundation\", color: BLUE}
        {name: \"Sprint 2: Gold Layer\", color: GREEN}
        {name: \"Sprint 3: Integration\", color: YELLOW}
        {name: \"Sprint 4: Production\", color: ORANGE}
        {name: \"Backlog\", color: GRAY}
      ]
    }) {
      projectV2Field {
        ... on ProjectV2SingleSelectField {
          id
          name
        }
      }
    }
  }
" --jq '.data.createProjectV2Field.projectV2Field.id')

log_success "Created Sprint field"

# Priority field
PRIORITY_FIELD_ID=$(gh api graphql -f query="
  mutation {
    createProjectV2Field(input: {
      projectId: \"$PROJECT_ID\"
      dataType: SINGLE_SELECT
      name: \"Priority\"
      singleSelectOptions: [
        {name: \"P0\", color: RED}
        {name: \"P1\", color: ORANGE}
        {name: \"P2\", color: YELLOW}
        {name: \"P3\", color: GREEN}
      ]
    }) {
      projectV2Field {
        ... on ProjectV2SingleSelectField {
          id
          name
        }
      }
    }
  }
" --jq '.data.createProjectV2Field.projectV2Field.id')

log_success "Created Priority field"

# Component field
COMPONENT_FIELD_ID=$(gh api graphql -f query="
  mutation {
    createProjectV2Field(input: {
      projectId: \"$PROJECT_ID\"
      dataType: SINGLE_SELECT
      name: \"Component\"
      singleSelectOptions: [
        {name: \"Lambda\", color: ORANGE}
        {name: \"Terraform\", color: PINK}
        {name: \"StepFunctions\", color: PURPLE}
        {name: \"Testing\", color: GREEN}
        {name: \"Docs\", color: BLUE}
        {name: \"CI/CD\", color: YELLOW}
        {name: \"Frontend\", color: PINK}
      ]
    }) {
      projectV2Field {
        ... on ProjectV2SingleSelectField {
          id
          name
        }
      }
    }
  }
" --jq '.data.createProjectV2Field.projectV2Field.id')

log_success "Created Component field"

# Estimated Tokens field (number)
ESTIMATED_TOKENS_FIELD_ID=$(gh api graphql -f query="
  mutation {
    createProjectV2Field(input: {
      projectId: \"$PROJECT_ID\"
      dataType: NUMBER
      name: \"Estimated Tokens\"
    }) {
      projectV2Field {
        ... on ProjectV2Field {
          id
          name
        }
      }
    }
  }
" --jq '.data.createProjectV2Field.projectV2Field.id')

log_success "Created Estimated Tokens field"

# Actual Tokens field (number)
ACTUAL_TOKENS_FIELD_ID=$(gh api graphql -f query="
  mutation {
    createProjectV2Field(input: {
      projectId: \"$PROJECT_ID\"
      dataType: NUMBER
      name: \"Actual Tokens\"
    }) {
      projectV2Field {
        ... on ProjectV2Field {
          id
          name
        }
      }
    }
  }
" --jq '.data.createProjectV2Field.projectV2Field.id')

log_success "Created Actual Tokens field"

echo ""

# Get project URL
PROJECT_URL=$(gh api graphql -f query="
  query {
    node(id: \"$PROJECT_ID\") {
      ... on ProjectV2 {
        url
      }
    }
  }
" --jq '.data.node.url')

# Summary
echo ""
log_info "========================================="
log_success "GitHub Projects Board Created!"
log_info "========================================="
echo ""
log_info "Project URL: $PROJECT_URL"
log_info "Project ID: $PROJECT_ID"
echo ""
log_info "Custom Fields Created:"
log_info "  ✓ Story Points (0, 1, 2, 3, 5, 8)"
log_info "  ✓ Sprint (Sprint 1-4, Backlog)"
log_info "  ✓ Priority (P0-P3)"
log_info "  ✓ Component (Lambda, Terraform, etc.)"
log_info "  ✓ Estimated Tokens (number)"
log_info "  ✓ Actual Tokens (number)"
echo ""
log_info "Next Steps:"
echo "  1. Visit: $PROJECT_URL"
echo "  2. Configure board views (Kanban, Sprint, Backlog, Roadmap)"
echo "  3. Set up automation rules (Settings > Workflows)"
echo "  4. Run sync script to import stories: python3 scripts/sync_stories_to_github.py"
echo "  5. Auto-add issues with 'user-story' label to project"
echo ""
log_warning "Note: Board views and automation must be configured manually via UI"
log_warning "GitHub API doesn't yet support creating views programmatically"
echo ""
