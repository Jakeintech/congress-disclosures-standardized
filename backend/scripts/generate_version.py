#!/usr/bin/env python3
"""
Generate version.json with build metadata for Lambda deployments.

This file is included in every Lambda package to track:
- Git commit hash
- Build timestamp
- Git branch
- Deployment environment

Usage:
    python3 scripts/generate_version.py [--output path/to/version.json]
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_git_hash() -> str:
    """Get current Git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def get_git_hash_short() -> str:
    """Get short Git commit hash (7 characters)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def get_git_branch() -> str:
    """Get current Git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def get_git_dirty() -> bool:
    """Check if Git working directory has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet"],
            capture_output=True
        )
        return result.returncode != 0
    except subprocess.CalledProcessError:
        return False


def get_build_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def generate_version_data() -> dict:
    """Generate complete version metadata."""
    git_hash = get_git_hash()
    git_hash_short = get_git_hash_short()
    git_branch = get_git_branch()
    git_dirty = get_git_dirty()
    build_timestamp = get_build_timestamp()

    # Create version string: v{date}-{short_hash}
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    version_string = f"v{date_str}-{git_hash_short}"

    if git_dirty:
        version_string += "-dirty"

    return {
        "version": version_string,
        "git": {
            "commit": git_hash,
            "commit_short": git_hash_short,
            "branch": git_branch,
            "dirty": git_dirty
        },
        "build": {
            "timestamp": build_timestamp,
            "date": date_str
        },
        "api_version": "v1"
    }


def main():
    """Generate and write version.json file."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate version.json for Lambda deployments"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="version.json",
        help="Output file path (default: version.json)"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output"
    )

    args = parser.parse_args()

    # Generate version data
    version_data = generate_version_data()

    # Write to file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        if args.pretty:
            json.dump(version_data, f, indent=2)
            f.write('\n')
        else:
            json.dump(version_data, f)

    # Also print to stdout for use in scripts
    print(json.dumps(version_data, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
