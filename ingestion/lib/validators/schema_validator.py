"""
JSON Schema Validator.
"""

import jsonschema
import json
import os
from . import Validator

class SchemaValidator(Validator):
    def __init__(self, schema_path: str):
        super().__init__()
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
            
    def validate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues = []
        try:
            jsonschema.validate(instance=data, schema=self.schema)
        except jsonschema.ValidationError as e:
            issues.append({
                'code': 'SCHEMA_VALIDATION_ERROR',
                'message': e.message,
                'severity': 'error',
                'field': '.'.join(str(p) for p in e.path)
            })
        return issues
