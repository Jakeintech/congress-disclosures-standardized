"""
Completeness Validator.
"""

from typing import Dict, List, Any
from . import Validator

class CompletenessValidator(Validator):
    def validate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues = []
        
        # Check required top-level fields
        required_fields = ['filing_type', 'year', 'doc_id']
        for field in required_fields:
            if not data.get(field):
                issues.append({
                    'code': 'MISSING_REQUIRED_FIELD',
                    'message': f"Missing required field: {field}",
                    'severity': 'error',
                    'field': field
                })
                
        # Check transactions if filing type requires them (e.g. PTR)
        filing_type = data.get('filing_type')
        if filing_type == 'P':
            transactions = data.get('transactions', [])
            if not transactions:
                issues.append({
                    'code': 'NO_TRANSACTIONS',
                    'message': "PTR filing has no transactions",
                    'severity': 'warning', # Could be empty PTR?
                    'field': 'transactions'
                })
            else:
                # Check transaction completeness
                for i, tx in enumerate(transactions):
                    if not tx.get('asset_name'):
                        issues.append({
                            'code': 'MISSING_ASSET_NAME',
                            'message': "Transaction missing asset name",
                            'severity': 'error',
                            'field': f"transactions[{i}].asset_name"
                        })
                        
        return issues
