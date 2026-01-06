#!/usr/bin/env python3
"""
Audit all Lambda handler response patterns.

Identifies which handlers use:
- Pattern A (CORRECT): success_response() helper from api.lib
- Pattern B (DEPRECATED): Custom clean_nan() + json.dumps()
- Pattern C (BROKEN): Manual string manipulation (str().replace())
- Unknown patterns

Usage:
    python3 scripts/audit_response_patterns.py [--fix]

Options:
    --fix: Automatically refactor handlers to use Pattern A (dry-run mode, shows diffs)
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


def analyze_handler(file_path: Path) -> Dict[str, any]:
    """
    Analyze a single Lambda handler file.

    Returns:
        Dict with pattern, issues, and recommendations
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        return {
            'pattern': 'ERROR',
            'error': str(e),
            'issues': [],
            'recommendations': []
        }

    issues = []
    recommendations = []
    pattern = 'Unknown'

    # Check for import of success_response
    has_success_response_import = 'from api.lib import' in content and 'success_response' in content

    # Check for usage of success_response()
    uses_success_response = re.search(r'return success_response\(', content)

    # Check for manual JSON dumps
    uses_manual_json = re.search(r'json\.dumps\(', content) and not uses_success_response

    # Check for string manipulation pattern (Pattern C)
    uses_string_replace = re.search(r'str\(.*\)\.replace\(', content) or \
                         re.search(r"\.replace\(['\"]'['\"],\s*['\"]\\\\\?\"['\"]\)", content)

    # Check for custom clean_nan function
    has_local_clean_nan = re.search(r'def clean_nan\(', content)

    # Check for return statements with statusCode
    has_manual_return = re.search(r"return\s+\{[^}]*['\"]statusCode['\"]", content)

    # Determine pattern
    if uses_success_response and has_success_response_import:
        pattern = 'A (CORRECT)'
    elif has_local_clean_nan and uses_manual_json:
        pattern = 'B (DEPRECATED)'
        issues.append("Uses local clean_nan() function instead of api.lib.clean_nan_values")
        issues.append("Uses manual json.dumps() instead of success_response()")
        recommendations.append("Remove local clean_nan() function")
        recommendations.append("Replace json.dumps() with success_response()")
    elif uses_string_replace:
        pattern = 'C (BROKEN)'
        issues.append("Uses brittle string replacement (str().replace()) for JSON serialization")
        issues.append("No NaN value protection")
        recommendations.append("URGENT: Replace string manipulation with success_response()")
    elif uses_manual_json and has_manual_return:
        pattern = 'B/C (MIXED)'
        issues.append("Uses manual json.dumps() and manual return dict")
        recommendations.append("Replace with success_response()")
    elif not has_success_response_import:
        pattern = 'MISSING IMPORTS'
        issues.append("success_response imported but not used, or not imported at all")
        recommendations.append("Add: from api.lib import success_response, error_response")

    # Additional checks
    if has_manual_return and pattern == 'A (CORRECT)':
        # Sometimes both patterns exist (transitional state)
        issues.append("WARNING: File uses both success_response() and manual returns")

    return {
        'pattern': pattern,
        'issues': issues,
        'recommendations': recommendations,
        'has_success_response_import': has_success_response_import,
        'uses_success_response': bool(uses_success_response),
        'has_local_clean_nan': bool(has_local_clean_nan),
        'uses_manual_json': bool(uses_manual_json),
        'uses_string_replace': bool(uses_string_replace)
    }


def audit_all_handlers(lambdas_dir: Path) -> Dict[str, Dict]:
    """
    Audit all handler.py files in the lambdas directory.

    Returns:
        Dict mapping file paths to analysis results
    """
    results = {}

    # Find all handler.py files
    handler_files = list(lambdas_dir.glob('*/handler.py'))

    for handler_file in sorted(handler_files):
        relative_path = handler_file.relative_to(lambdas_dir.parent.parent)
        analysis = analyze_handler(handler_file)
        results[str(relative_path)] = analysis

    return results


def print_summary(results: Dict[str, Dict]):
    """Print a formatted summary of audit results."""

    # Group by pattern
    by_pattern = defaultdict(list)
    for file_path, analysis in results.items():
        by_pattern[analysis['pattern']].append(file_path)

    # Print header
    print(f"\n{BOLD}{'='*80}{RESET}")
    print(f"{BOLD}Lambda Handler Response Pattern Audit{RESET}")
    print(f"{BOLD}{'='*80}{RESET}\n")

    # Print summary statistics
    total = len(results)
    pattern_a = len(by_pattern.get('A (CORRECT)', []))
    pattern_b = len(by_pattern.get('B (DEPRECATED)', []))
    pattern_c = len(by_pattern.get('C (BROKEN)', []))
    other = total - pattern_a - pattern_b - pattern_c

    print(f"{BOLD}Summary:{RESET}")
    print(f"  Total handlers: {total}")
    print(f"  {GREEN}✓ Pattern A (CORRECT):{RESET} {pattern_a} ({pattern_a/total*100:.1f}%)")
    print(f"  {YELLOW}⚠ Pattern B (DEPRECATED):{RESET} {pattern_b} ({pattern_b/total*100:.1f}%)")
    print(f"  {RED}✗ Pattern C (BROKEN):{RESET} {pattern_c} ({pattern_c/total*100:.1f}%)")
    print(f"  {BLUE}? Other/Unknown:{RESET} {other} ({other/total*100:.1f}%)")
    print()

    # Print detailed results by pattern
    for pattern in sorted(by_pattern.keys()):
        files = by_pattern[pattern]

        # Choose color based on pattern
        if 'CORRECT' in pattern:
            color = GREEN
            symbol = '✓'
        elif 'BROKEN' in pattern:
            color = RED
            symbol = '✗'
        elif 'DEPRECATED' in pattern:
            color = YELLOW
            symbol = '⚠'
        else:
            color = BLUE
            symbol = '?'

        print(f"{color}{BOLD}{symbol} Pattern {pattern} ({len(files)} handlers):{RESET}")

        for file_path in files:
            analysis = results[file_path]
            print(f"  {file_path}")

            if analysis.get('issues'):
                for issue in analysis['issues']:
                    print(f"    • {issue}")

            if analysis.get('recommendations'):
                for rec in analysis['recommendations']:
                    print(f"    → {rec}")

        print()

    # Print action items
    print(f"{BOLD}Action Items:{RESET}")
    if pattern_c > 0:
        print(f"  {RED}URGENT:{RESET} Fix {pattern_c} Pattern C (BROKEN) handlers immediately")
    if pattern_b > 0:
        print(f"  {YELLOW}TODO:{RESET} Refactor {pattern_b} Pattern B (DEPRECATED) handlers")
    if pattern_a == total:
        print(f"  {GREEN}✓ All handlers use standardized Pattern A!{RESET}")
    print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Audit Lambda handler response patterns')
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Automatically fix handlers (dry-run mode)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    # Find lambdas directory
    repo_root = Path(__file__).parent.parent
    lambdas_dir = repo_root / 'api' / 'lambdas'

    if not lambdas_dir.exists():
        print(f"Error: Lambdas directory not found: {lambdas_dir}", file=sys.stderr)
        return 1

    # Run audit
    results = audit_all_handlers(lambdas_dir)

    if args.json:
        import json
        print(json.dumps(results, indent=2))
    else:
        print_summary(results)

    # Exit with error code if any handlers use broken patterns
    broken_count = sum(1 for r in results.values() if 'BROKEN' in r['pattern'])
    if broken_count > 0:
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
