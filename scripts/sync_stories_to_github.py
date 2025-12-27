#!/usr/bin/env python3
"""
Sync Story Files to GitHub Issues

Purpose: Parses story markdown files and creates/updates GitHub Issues
         with proper labels, milestones, and acceptance criteria.

Usage:
    python3 scripts/sync_stories_to_github.py [options]

    Options:
        --dry-run       Show what would be created without actually creating
        --update        Update existing issues (default: skip existing)
        --close-done    Close issues for completed stories
        --stories DIR   Path to stories directory (default: docs/agile/stories)
        --mapping FILE  Path to mapping file (default: .github/story_issue_mapping.json)

Prerequisites:
    - GitHub CLI (gh) installed and authenticated
    - Story files in markdown format
    - Labels and milestones already created

Examples:
    # Dry run (see what would be created)
    python3 scripts/sync_stories_to_github.py --dry-run

    # Create issues for all stories
    python3 scripts/sync_stories_to_github.py

    # Update existing issues
    python3 scripts/sync_stories_to_github.py --update

    # Close completed stories
    python3 scripts/sync_stories_to_github.py --close-done
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def log_info(msg: str) -> None:
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")

def log_success(msg: str) -> None:
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")

def log_warning(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")

def log_error(msg: str) -> None:
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}", file=sys.stderr)

class StoryParser:
    """Parse markdown story files"""

    def __init__(self, story_path: Path):
        self.story_path = story_path
        self.content = story_path.read_text()

    def extract_story_id(self) -> Optional[str]:
        """Extract story ID from filename (e.g., STORY_001 from STORY_001_description.md)"""
        match = re.search(r'STORY_(\d+)', self.story_path.name)
        if match:
            return f"STORY-{match.group(1)}"
        return None

    def extract_title(self) -> str:
        """Extract story title from first H1 heading"""
        match = re.search(r'^# (.+)$', self.content, re.MULTILINE)
        if match:
            # Remove STORY-XXX: prefix if present
            title = match.group(1)
            title = re.sub(r'^STORY-\d+:\s*', '', title)
            return title.strip()
        return "Untitled Story"

    def extract_metadata(self) -> Dict[str, str]:
        """Extract metadata from story header"""
        metadata = {}

        # Look for metadata line like: **Epic**: EPIC-001 | **Sprint**: Sprint 2 | **Points**: 5 | **Priority**: P0 | **Status**: To Do
        match = re.search(
            r'\*\*Epic\*\*:\s*([^\|]+)\s*\|\s*\*\*Sprint\*\*:\s*([^\|]+)\s*\|\s*\*\*Points\*\*:\s*(\d+)\s*\|\s*\*\*Priority\*\*:\s*([^\|]+)\s*\|\s*\*\*Status\*\*:\s*([^\n]+)',
            self.content
        )

        if match:
            metadata['epic'] = match.group(1).strip()
            metadata['sprint'] = match.group(2).strip()
            metadata['points'] = match.group(3).strip()
            metadata['priority'] = match.group(4).strip()
            metadata['status'] = match.group(5).strip()

        return metadata

    def extract_user_story(self) -> str:
        """Extract user story (As a/I want/So that)"""
        match = re.search(
            r'## User Story\s*\n\s*\*\*As a\*\*\s+(.+?)\s*\*\*I want\*\*\s+(.+?)\s*\*\*So that\*\*\s+(.+?)(?=\n##|\Z)',
            self.content,
            re.DOTALL
        )
        if match:
            return f"**As a** {match.group(1).strip()}\n**I want** {match.group(2).strip()}\n**So that** {match.group(3).strip()}"
        return ""

    def extract_acceptance_criteria(self) -> str:
        """Extract acceptance criteria section"""
        match = re.search(
            r'## Acceptance Criteria\s*\n(.+?)(?=\n##|\Z)',
            self.content,
            re.DOTALL
        )
        if match:
            return match.group(1).strip()
        return ""

    def extract_technical_tasks(self) -> str:
        """Extract technical tasks section"""
        match = re.search(
            r'## Technical Tasks\s*\n(.+?)(?=\n##|\Z)',
            self.content,
            re.DOTALL
        )
        if match:
            return match.group(1).strip()
        return ""

    def extract_dependencies(self) -> List[str]:
        """Extract dependencies (STORY-XXX references)"""
        dependencies = []
        match = re.search(
            r'## Dependencies\s*\n(.+?)(?=\n##|\Z)',
            self.content,
            re.DOTALL
        )
        if match:
            dep_text = match.group(1)
            # Find all STORY-XXX references
            dependencies = re.findall(r'STORY-\d+', dep_text)
        return list(set(dependencies))  # Remove duplicates

    def parse(self) -> Dict:
        """Parse entire story file"""
        story_id = self.extract_story_id()
        if not story_id:
            raise ValueError(f"Could not extract story ID from {self.story_path}")

        metadata = self.extract_metadata()

        return {
            'story_id': story_id,
            'title': self.extract_title(),
            'epic': metadata.get('epic', 'EPIC-001'),
            'sprint': metadata.get('sprint', 'Unknown'),
            'points': metadata.get('points', '0'),
            'priority': metadata.get('priority', 'P2'),
            'status': metadata.get('status', 'To Do'),
            'user_story': self.extract_user_story(),
            'acceptance_criteria': self.extract_acceptance_criteria(),
            'technical_tasks': self.extract_technical_tasks(),
            'dependencies': self.extract_dependencies(),
            'story_file_path': str(self.story_path.resolve().relative_to(Path.cwd().resolve()))
        }

class GitHubIssueManager:
    """Manage GitHub Issues via CLI"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def run_gh_command(self, args: List[str]) -> Tuple[int, str, str]:
        """Run GitHub CLI command"""
        try:
            result = subprocess.run(
                ['gh'] + args,
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            log_error("GitHub CLI (gh) not found. Install: brew install gh")
            sys.exit(1)

    def check_auth(self) -> bool:
        """Check if GitHub CLI is authenticated"""
        code, _, _ = self.run_gh_command(['auth', 'status'])
        return code == 0

    def get_issue_by_story_id(self, story_id: str) -> Optional[int]:
        """Get issue number by story ID (searches issue titles)"""
        code, stdout, _ = self.run_gh_command([
            'issue', 'list',
            '--state', 'all',
            '--search', f"[{story_id}]",
            '--json', 'number,title'
        ])

        if code == 0 and stdout.strip():
            issues = json.loads(stdout)
            for issue in issues:
                if f"[{story_id}]" in issue['title']:
                    return issue['number']
        return None

    def create_issue_body(self, story: Dict) -> str:
        """Create GitHub Issue body from story data"""
        body_parts = []

        # Story metadata
        body_parts.append(f"**Story ID**: {story['story_id']}")
        body_parts.append(f"**Epic**: {story['epic']}")
        body_parts.append(f"**Sprint**: {story['sprint']}")
        body_parts.append(f"**Story Points**: {story['points']}")
        body_parts.append(f"**Priority**: {story['priority']}")
        body_parts.append("")

        # User story
        if story['user_story']:
            body_parts.append("## User Story")
            body_parts.append("")
            body_parts.append(story['user_story'])
            body_parts.append("")

        # Acceptance criteria
        if story['acceptance_criteria']:
            body_parts.append("## Acceptance Criteria")
            body_parts.append("")
            body_parts.append(story['acceptance_criteria'])
            body_parts.append("")

        # Technical tasks
        if story['technical_tasks']:
            body_parts.append("## Technical Tasks")
            body_parts.append("")
            body_parts.append(story['technical_tasks'])
            body_parts.append("")

        # Dependencies
        if story['dependencies']:
            body_parts.append("## Dependencies")
            body_parts.append("")
            for dep in story['dependencies']:
                body_parts.append(f"- {dep} (will be linked once issues created)")
            body_parts.append("")

        # Links
        body_parts.append("## Links")
        body_parts.append("")
        body_parts.append(f"**Full Story**: [`{story['story_file_path']}`]({story['story_file_path']})")
        body_parts.append(f"**Task Template**: [AI Agent Task Template](.github/AI_AGENT_TASK_TEMPLATE.md)")
        body_parts.append(f"**Context**: [AI Agent Context](docs/agile/AI_AGENT_CONTEXT.md)")
        body_parts.append("")

        # Footer
        body_parts.append("---")
        body_parts.append("*This issue was auto-generated from story file. See story file for complete details.*")

        return "\n".join(body_parts)

    def get_labels_for_story(self, story: Dict) -> List[str]:
        """Generate label list for story"""
        labels = []

        # Story type
        labels.append("user-story")

        # Sprint
        sprint_map = {
            "Sprint 1": "sprint-1",
            "Sprint 2": "sprint-2",
            "Sprint 3": "sprint-3",
            "Sprint 4": "sprint-4"
        }
        sprint_label = sprint_map.get(story['sprint'])
        if sprint_label:
            labels.append(sprint_label)

        # Points
        points = story.get('points', '0')
        labels.append(f"points-{points}")

        # Priority
        priority_map = {
            "P0": "P0-critical",
            "P1": "P1-high",
            "P2": "P2-medium",
            "P3": "P3-low"
        }
        priority_label = priority_map.get(story['priority'])
        if priority_label:
            labels.append(priority_label)

        # Status
        if story['status'].lower() in ['done', 'complete', 'completed']:
            # Don't add status label - issue will be closed instead
            pass
        elif story['dependencies']:
            labels.append("dependencies")

        return labels

    def get_milestone_for_story(self, story: Dict) -> Optional[str]:
        """Get milestone name for story"""
        milestone_map = {
            "Sprint 1": "Sprint 1: Foundation",
            "Sprint 2": "Sprint 2: Gold Layer",
            "Sprint 3": "Sprint 3: Integration",
            "Sprint 4": "Sprint 4: Production"
        }
        return milestone_map.get(story['sprint'])

    def create_issue(self, story: Dict) -> Optional[int]:
        """Create GitHub Issue from story"""
        title = f"[{story['story_id']}] {story['title']}"
        body = self.create_issue_body(story)
        labels = self.get_labels_for_story(story)
        milestone = self.get_milestone_for_story(story)

        if self.dry_run:
            log_info(f"DRY RUN: Would create issue: {title}")
            log_info(f"  Labels: {', '.join(labels)}")
            log_info(f"  Milestone: {milestone}")
            return None

        # Build gh issue create command
        cmd = [
            'issue', 'create',
            '--title', title,
            '--body', body
        ]

        # Add labels
        for label in labels:
            cmd.extend(['--label', label])

        # Add milestone
        if milestone:
            cmd.extend(['--milestone', milestone])

        # Execute
        code, stdout, stderr = self.run_gh_command(cmd)

        if code == 0:
            # Extract issue number from output (URL)
            match = re.search(r'/issues/(\d+)', stdout)
            if match:
                issue_number = int(match.group(1))
                log_success(f"Created issue #{issue_number}: {title}")
                return issue_number
            else:
                log_warning(f"Issue created but couldn't extract number: {title}")
                return None
        else:
            log_error(f"Failed to create issue: {title}")
            log_error(f"Error: {stderr}")
            return None

    def close_issue(self, issue_number: int, story_id: str) -> bool:
        """Close a GitHub Issue"""
        if self.dry_run:
            log_info(f"DRY RUN: Would close issue #{issue_number} ({story_id})")
            return True

        cmd = ['issue', 'close', str(issue_number)]
        code, _, stderr = self.run_gh_command(cmd)

        if code == 0:
            log_success(f"Closed issue #{issue_number} ({story_id})")
            return True
        else:
            log_error(f"Failed to close issue #{issue_number}")
            log_error(f"Error: {stderr}")
            return False

def load_mapping(mapping_file: Path) -> Dict[str, int]:
    """Load story ID to issue number mapping"""
    if mapping_file.exists():
        with open(mapping_file, 'r') as f:
            return json.load(f)
    return {}

def save_mapping(mapping_file: Path, mapping: Dict[str, int]) -> None:
    """Save story ID to issue number mapping"""
    mapping_file.parent.mkdir(parents=True, exist_ok=True)
    with open(mapping_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    log_info(f"Saved mapping to {mapping_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Sync story files to GitHub Issues",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be created without actually creating'
    )
    parser.add_argument(
        '--update',
        action='store_true',
        help='Update existing issues (default: skip existing)'
    )
    parser.add_argument(
        '--close-done',
        action='store_true',
        help='Close issues for completed stories'
    )
    parser.add_argument(
        '--stories',
        type=Path,
        default=Path('docs/agile/stories'),
        help='Path to stories directory (default: docs/agile/stories)'
    )
    parser.add_argument(
        '--mapping',
        type=Path,
        default=Path('.github/story_issue_mapping.json'),
        help='Path to mapping file (default: .github/story_issue_mapping.json)'
    )

    args = parser.parse_args()

    # Header
    log_info("Story to GitHub Issue Sync Tool")
    log_info("================================")
    print()

    # Check GitHub CLI auth
    gh = GitHubIssueManager(dry_run=args.dry_run)
    if not gh.check_auth():
        log_error("GitHub CLI not authenticated. Run: gh auth login")
        sys.exit(1)

    log_success("GitHub CLI authenticated")
    print()

    # Load existing mapping
    mapping = load_mapping(args.mapping)
    log_info(f"Loaded {len(mapping)} existing story-to-issue mappings")
    print()

    # Find all story files
    story_files = []
    for folder in ['active', 'completed']:
        folder_path = args.stories / folder
        if folder_path.exists():
            story_files.extend(folder_path.glob('STORY_*.md'))

    if not story_files:
        log_error(f"No story files found in {args.stories}")
        sys.exit(1)

    log_info(f"Found {len(story_files)} story files")
    print()

    # Process each story
    stats = {
        'created': 0,
        'skipped': 0,
        'updated': 0,
        'closed': 0,
        'errors': 0
    }

    for story_file in sorted(story_files):
        try:
            # Parse story
            parser = StoryParser(story_file)
            story = parser.parse()

            story_id = story['story_id']
            is_done = story['status'].lower() in ['done', 'complete', 'completed']

            # Check if issue already exists
            existing_issue = mapping.get(story_id) or gh.get_issue_by_story_id(story_id)

            if existing_issue:
                if args.close_done and is_done:
                    # Close completed stories
                    if gh.close_issue(existing_issue, story_id):
                        stats['closed'] += 1
                    else:
                        stats['errors'] += 1
                elif args.update:
                    # TODO: Implement update logic
                    log_warning(f"Skipped {story_id}: Update not yet implemented")
                    stats['skipped'] += 1
                else:
                    log_info(f"Skipped {story_id}: Issue #{existing_issue} already exists")
                    stats['skipped'] += 1
            else:
                # Create new issue
                issue_number = gh.create_issue(story)
                if issue_number:
                    mapping[story_id] = issue_number
                    stats['created'] += 1
                else:
                    stats['errors'] += 1

        except Exception as e:
            log_error(f"Error processing {story_file.name}: {str(e)}")
            stats['errors'] += 1

    # Save mapping
    if not args.dry_run:
        save_mapping(args.mapping, mapping)

    # Summary
    print()
    log_info("Summary")
    log_info("=======")
    log_success(f"Created: {stats['created']}")
    log_info(f"Skipped: {stats['skipped']}")
    log_info(f"Updated: {stats['updated']}")
    log_success(f"Closed: {stats['closed']}")
    if stats['errors'] > 0:
        log_error(f"Errors: {stats['errors']}")
    print()

    if args.dry_run:
        log_warning("DRY RUN: No actual changes made")
    else:
        log_success("Sync complete!")

    print()
    log_info("Next steps:")
    print("  1. Review created issues: gh issue list")
    print("  2. Set up GitHub Projects board")
    print("  3. Link dependencies between issues")
    print("  4. Verify labels and milestones are correct")

if __name__ == '__main__':
    main()
