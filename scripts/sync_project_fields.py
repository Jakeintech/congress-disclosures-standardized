#!/usr/bin/env python3
"""
Sync GitHub Issue Labels to Project V2 Fields

Purpose: Populates "Story Points", "Sprint", "Priority", and "Component" fields
         on a GitHub Project based on issue labels.

Usage:
    python3 scripts/sync_project_fields.py [--dry-run]
"""

import argparse
import json
import subprocess
import sys
from typing import Dict, List, Optional

# Colors
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'

def log(msg, color=Colors.NC):
    print(f"{color}{msg}{Colors.NC}")

def run_gh_json(args):
    """Run gh command and return JSON"""
    cmd = ['gh'] + args + ['--format', 'json']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"Error running gh {' '.join(args)}: {result.stderr}", Colors.RED)
        sys.exit(1)
    return json.loads(result.stdout)

def run_graphql(query):
    """Run GraphQL query"""
    cmd = ['gh', 'api', 'graphql', '-f', f'query={query}']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"GraphQL Error: {result.stderr}", Colors.RED)
        sys.exit(1)
    return json.loads(result.stdout)

def get_project_fields(project_id):
    """Get all fields and options for a project"""
    query = f'''
    query {{
      node(id: "{project_id}") {{
        ... on ProjectV2 {{
          fields(first: 50) {{
            nodes {{
              ... on ProjectV2FieldCommon {{
                id
                name
                dataType
              }}
              ... on ProjectV2SingleSelectField {{
                id
                name
                dataType
                options {{
                  id
                  name
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    '''
    data = run_graphql(query)
    return data['data']['node']['fields']['nodes']

def get_project_items(project_id):
    """Get all items in the project"""
    # Fetching first 100 items (assuming < 100 for now)
    query = f'''
    query {{
      node(id: "{project_id}") {{
        ... on ProjectV2 {{
          items(first: 100) {{
            nodes {{
              id
              type
              content {{
                ... on Issue {{
                  number
                  title
                  labels(first: 20) {{
                    nodes {{
                      name
                    }}
                  }}
                }}
              }}
              fieldValues(first: 20) {{
                nodes {{
                  ... on ProjectV2ItemFieldSingleSelectValue {{
                    field {{ ... on ProjectV2FieldCommon {{ name }} }}
                    name
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    '''
    data = run_graphql(query)
    return data['data']['node']['items']['nodes']

def update_item_field(project_id, item_id, field_id, option_id, dry_run=False):
    """Update a single select field on an item"""
    if dry_run:
        log(f"  [DRY RUN] Update field {field_id} to option {option_id}", Colors.BLUE)
        return

    query = f'''
    mutation {{
      updateProjectV2ItemFieldValue(
        input: {{
          projectId: "{project_id}"
          itemId: "{item_id}"
          fieldId: "{field_id}"
          value: {{ 
            singleSelectOptionId: "{option_id}"
          }}
        }}
      ) {{
        projectV2Item {{
          id
        }}
      }}
    }}
    '''
    run_graphql(query)
    log(f"  Updated field {field_id}", Colors.GREEN)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--owner', default='Jakeintech')
    args = parser.parse_args()

    log("Starting Project Field Sync...", Colors.BLUE)

    # 1. Find the project
    log("Finding project...", Colors.BLUE)
    projects = run_gh_json(['project', 'list', '--owner', args.owner])
    if not projects:
        log("No projects found!", Colors.RED)
        sys.exit(1)
    
    if 'projects' not in projects or not projects['projects']:
        log("No projects found!", Colors.RED)
        sys.exit(1)
    
    project = projects['projects'][0] # Assume the first one is the target
    project_id = project['id']
    log(f"Targeting Project: {project['title']} (ID: {project_id})", Colors.GREEN)

    # 2. Get Fields Definitions
    log("Fetching field definitions...", Colors.BLUE)
    fields = get_project_fields(project_id)
    
    field_map = {} # Name -> {id, options: {OptionName -> OptionID}}
    
    target_fields = ['Sprint', 'Story Points', 'Priority', 'Component']
    
    for f in fields:
        if f['name'] in target_fields:
            if 'options' in f:
                opt_map = {opt['name']: opt['id'] for opt in f['options']}
                field_map[f['name']] = {'id': f['id'], 'options': opt_map}
            else:
                log(f"Field {f['name']} found but has no options!", Colors.YELLOW)

    log(f"Found fields: {', '.join(field_map.keys())}", Colors.GREEN)

    # 3. Get Items
    log("Fetching project items...", Colors.BLUE)
    items = get_project_items(project_id)
    log(f"Found {len(items)} items", Colors.GREEN)

    # 4. Iterate and Update
    for item in items:
        content = item.get('content')
        if not content or 'number' not in content:
            continue
            
        issue_num = content['number']
        labels = [l['name'] for l in content.get('labels', {}).get('nodes', [])]
        
        log(f"Processing Issue #{issue_num}: {content['title']}")
        
        # --- Map Labels to Fields ---

        # 1. Story Points (points-X -> X)
        for label in labels:
            if label.startswith('points-'):
                points = label.replace('points-', '')
                field = field_map.get('Story Points')
                if field and points in field['options']:
                    update_item_field(project_id, item['id'], field['id'], field['options'][points], args.dry_run)

        # 2. Priority (P0-critical -> P0)
        for label in labels:
            # P0-critical -> P0
            # Matches prefix P0, P1, P2, P3
            for p in ['P0', 'P1', 'P2', 'P3']:
                if label.startswith(p):
                    field = field_map.get('Priority')
                    if field and p in field['options']:
                        update_item_field(project_id, item['id'], field['id'], field['options'][p], args.dry_run)

        # 3. Sprint (sprint-1 -> Sprint 1: Foundation)
        sprint_map = {
            'sprint-1': 'Sprint 1: Foundation',
            'sprint-2': 'Sprint 2: Gold Layer',
            'sprint-3': 'Sprint 3: Integration',
            'sprint-4': 'Sprint 4: Production'
        }
        for label in labels:
            if label in sprint_map:
                sprint_name = sprint_map[label]
                field = field_map.get('Sprint')
                if field and sprint_name in field['options']:
                    update_item_field(project_id, item['id'], field['id'], field['options'][sprint_name], args.dry_run)
        
        # 4. Component (lambda -> Lambda)
        comp_map = {
            'lambda': 'Lambda',
            'terraform': 'Terraform',
            'stepfunctions': 'StepFunctions',
            'testing': 'Testing',
            'documentation': 'Docs',
            'ci-cd': 'CI/CD',
            'frontend': 'Frontend'
        }
        for label in labels:
            if label in comp_map:
                comp_name = comp_map[label]
                field = field_map.get('Component')
                if field and comp_name in field['options']:
                    update_item_field(project_id, item['id'], field['id'], field['options'][comp_name], args.dry_run)

    log("Sync Complete!", Colors.GREEN)

if __name__ == '__main__':
    main()
