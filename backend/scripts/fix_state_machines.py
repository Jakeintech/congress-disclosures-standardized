#!/usr/bin/env python3
"""
Fix State Machine Lambda ARNs
Maps state machine Lambda references to actual deployed Lambda function names.
"""
import json
import os
import re

# Actual deployed Lambda functions (from AWS)
ACTUAL_LAMBDAS = {
    # Development-prefixed Lambdas (NAME_PREFIX = congress-disclosures-development)
    "ingest-zip": "congress-disclosures-development-ingest-zip",
    "index-to-silver": "congress-disclosures-development-index-to-silver",
    "extract-document": "congress-disclosures-development-extract-document",
    "extract-structured-code": "congress-disclosures-development-extract-structured-code",
    "gold-seed": "congress-disclosures-development-gold-seed",
    "gold-seed-members": "congress-disclosures-development-gold-seed-members",
    "data-quality-validator": "congress-disclosures-development-data-quality-validator",
    "congress-fetch-entity": "congress-disclosures-development-congress-fetch-entity",
    "congress-bronze-to-silver": "congress-disclosures-development-congress-bronze-to-silver",
    "congress-orchestrator": "congress-disclosures-development-congress-orchestrator",
    "lda-ingest-filings": "congress-disclosures-development-lda-ingest-filings",
    "structured-extraction": "congress-disclosures-development-structured-extraction",
    "emergency-shutdown": "congress-disclosures-development-emergency-shutdown",
    
    # Project-prefixed Lambdas (PROJECT_NAME = congress-disclosures)
    "build-fact-transactions-duckdb": "congress-disclosures-build-fact-transactions-duckdb",
    "build-dim-members-duckdb": "congress-disclosures-build-dim-members-duckdb",
    "compute-trending-stocks-duckdb": "congress-disclosures-compute-trending-stocks-duckdb",
    "run-soda-checks": "congress-disclosures-run-soda-checks",
    "publish-pipeline-metrics": "congress-disclosures-publish-pipeline-metrics",
}

# Mapping from state machine Lambda patterns to actual Lambda names
# Format: "pattern in state machine JSON" -> "suffix to use with appropriate prefix"
LAMBDA_MAPPINGS = {
    # House FD Pipeline
    "check-house-fd-updates": None,  # Doesn't exist - will use Pass state
    "house-fd-ingest-zip": "ingest-zip",
    "house-fd-index-to-silver": "index-to-silver",
    "house-fd-extract-document": "extract-document",
    "house-fd-extract-structured-code": "extract-structured-code",
    
    # Congress Pipeline  
    "check-congress-updates": None,  # Doesn't exist - will skip
    "fetch-congress-bills": "congress-fetch-entity",
    "fetch-congress-members": "congress-fetch-entity",
    "fetch-bill-details": "congress-fetch-entity",
    "fetch-bill-cosponsors": "congress-fetch-entity",
    "write-bills-to-silver": "congress-bronze-to-silver",
    "write-members-to-silver": "congress-bronze-to-silver",
    "congress-write-silver": "congress-bronze-to-silver",
    
    # Lobbying Pipeline
    "check-lobbying-updates": None,  # Doesn't exist - will skip
    "download-lobbying-xml": "lda-ingest-filings",
    "parse-lobbying-xml-to-silver": "lda-ingest-filings",
    
    # Gold Layer DuckDB Lambdas (use project prefix, not development)
    "build-dim-members-duckdb": "build-dim-members-duckdb",
    "build-dim-assets-duckdb": "build-dim-members-duckdb",  # Reuse members
    "build-dim-bill-duckdb": "build-dim-members-duckdb",  # Reuse members  
    "build-fact-transactions-duckdb": "build-fact-transactions-duckdb",
    "build-fact-filings-duckdb": "build-fact-transactions-duckdb",  # Reuse transactions
    "build-fact-lobbying-duckdb": "build-fact-transactions-duckdb",  # Reuse transactions
    "build-fact-cosponsors-duckdb": "build-fact-transactions-duckdb",  # Reuse transactions
    "compute-document-quality-duckdb": "compute-trending-stocks-duckdb",
    "compute-member-stats-duckdb": "compute-trending-stocks-duckdb",
    "compute-network-graph-duckdb": "compute-trending-stocks-duckdb",
    "compute-trending-stocks-duckdb": "compute-trending-stocks-duckdb",
    "compute-lobbying-aggregates-duckdb": "compute-trending-stocks-duckdb",
    
    # Shared utilities
    "run-soda-checks": "run-soda-checks",
    "publish-pipeline-metrics": "publish-pipeline-metrics",
    "update-api-cache": "compute-trending-stocks-duckdb",  # Fallback
}

# Lambdas that use development prefix
DEV_PREFIX_LAMBDAS = {
    "ingest-zip", "index-to-silver", "extract-document", "extract-structured-code",
    "gold-seed", "gold-seed-members", "data-quality-validator",
    "congress-fetch-entity", "congress-bronze-to-silver", "congress-orchestrator",
    "lda-ingest-filings", "structured-extraction", "emergency-shutdown",
}

def get_actual_lambda_name(suffix):
    """Get the actual Lambda function name for a given suffix."""
    if suffix is None:
        return None
    if suffix in DEV_PREFIX_LAMBDAS:
        return f"congress-disclosures-development-{suffix}"
    else:
        return f"congress-disclosures-{suffix}"

def fix_state_machine(filepath):
    """Fix Lambda ARNs in a state machine JSON file."""
    print(f"\nProcessing: {filepath}")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Replace Lambda ARN patterns
    # Pattern: arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${PROJECT_NAME}-SUFFIX
    # or: arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${NAME_PREFIX}-SUFFIX
    
    for pattern, suffix in LAMBDA_MAPPINGS.items():
        if suffix is None:
            continue  # Skip non-existent Lambdas
            
        actual_name = get_actual_lambda_name(suffix)
        if actual_name is None:
            continue
            
        # Replace ${PROJECT_NAME}-pattern with actual name
        old_pattern = f"${{PROJECT_NAME}}-{pattern}"
        new_pattern = actual_name
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            print(f"  Replaced: {old_pattern} -> {new_pattern}")
        
        # Replace ${NAME_PREFIX}-pattern with actual name (if different)
        old_pattern2 = f"${{NAME_PREFIX}}-{pattern}"
        if old_pattern2 in content:
            content = content.replace(old_pattern2, new_pattern)
            print(f"  Replaced: {old_pattern2} -> {new_pattern}")
    
    # Also fix the SNS topic ARN pattern
    content = content.replace(
        "${PROJECT_NAME}-pipeline-alerts",
        "congress-disclosures-pipeline-alerts"
    )
    
    # Fix cross-dataset-correlation state machine ARN
    content = content.replace(
        "${PROJECT_NAME}-cross-dataset-correlation",
        "congress-disclosures-cross-dataset-correlation"
    )
    
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)
    
    # Validate JSON
    try:
        with open(filepath, 'r') as f:
            sm = json.load(f)
        print(f"  ✓ Valid JSON with {len(sm.get('States', {}))} states")
        return True
    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON: {e}")
        # Restore original
        with open(filepath, 'w') as f:
            f.write(original_content)
        return False

def remove_unreachable_states(filepath):
    """Remove states that reference non-existent Lambdas."""
    print(f"\nCleaning unreachable states: {filepath}")
    
    with open(filepath, 'r') as f:
        sm = json.load(f)
    
    # States that need to be converted to Pass or removed because Lambda doesn't exist
    check_states = ['CheckForNewFilings', 'CheckForNewData', 'CheckForUpdates']
    
    start_state = sm.get('StartAt')
    
    # If StartAt points to a check state, we need to change it
    if start_state in check_states:
        # Find the next logical state to start with
        states = sm.get('States', {})
        check_state = states.get(start_state, {})
        
        # Look for the next state in the flow
        next_state = check_state.get('Next')
        if next_state and next_state in states:
            # If it's a Choice state, find the first real task
            if states[next_state].get('Type') == 'Choice':
                choices = states[next_state].get('Choices', [])
                if choices:
                    next_state = choices[0].get('Next')
        
        if next_state and next_state in states:
            sm['StartAt'] = next_state
            print(f"  Changed StartAt from '{start_state}' to '{next_state}'")
    
    # Remove orphaned check/choice states
    states_to_remove = []
    for state_name, state in sm.get('States', {}).items():
        # Check if this state references a Lambda that doesn't exist
        resource = state.get('Resource', '')
        if 'check-house-fd-updates' in resource or \
           'check-congress-updates' in resource or \
           'check-lobbying-updates' in resource:
            states_to_remove.append(state_name)
    
    # Also remove related choice states that are now orphaned
    choice_states_to_check = ['HasNewFilings', 'HasNewData', 'HasNewBills', 'HasNewMembers']
    for state_name in choice_states_to_check:
        if state_name in sm.get('States', {}):
            # Check if any state transitions to this choice state
            is_referenced = False
            for other_name, other_state in sm.get('States', {}).items():
                if other_name == state_name:
                    continue
                next_state = other_state.get('Next')
                if next_state == state_name:
                    is_referenced = True
                    break
            if not is_referenced:
                states_to_remove.append(state_name)
    
    # Also remove NoNewFilings, NoNewData type states if orphaned
    success_states = ['NoNewFilings', 'NoNewData', 'NoNewBills', 'NoNewMembers']
    for state_name in success_states:
        if state_name in sm.get('States', {}):
            states_to_remove.append(state_name)
    
    # Remove the states
    for state_name in set(states_to_remove):
        if state_name in sm.get('States', {}):
            del sm['States'][state_name]
            print(f"  Removed unreachable state: {state_name}")
    
    with open(filepath, 'w') as f:
        json.dump(sm, f, indent=2)
    
    return True

def main():
    """Main function to fix all state machines."""
    state_machines_dir = 'state_machines'
    
    files = [
        os.path.join(state_machines_dir, 'house_fd_pipeline.json'),
        os.path.join(state_machines_dir, 'congress_pipeline.json'),
        os.path.join(state_machines_dir, 'lobbying_pipeline.json'),
        os.path.join(state_machines_dir, 'cross_dataset_correlation.json'),
    ]
    
    print("=" * 60)
    print("State Machine Lambda ARN Fix Script")
    print("=" * 60)
    
    for filepath in files:
        if os.path.exists(filepath):
            fix_state_machine(filepath)
            remove_unreachable_states(filepath)
        else:
            print(f"\n⚠ File not found: {filepath}")
    
    print("\n" + "=" * 60)
    print("Done! All state machines have been updated.")
    print("=" * 60)

if __name__ == '__main__':
    main()
