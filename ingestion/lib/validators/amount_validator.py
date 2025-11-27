"""
Amount Validator.
"""

from typing import Dict, List, Any
from . import Validator

class AmountValidator(Validator):
    def validate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues = []
        
        transactions = data.get('transactions', [])
        for i, tx in enumerate(transactions):
            amount_min = tx.get('amount_min')
            amount_max = tx.get('amount_max')
            
            # Check for negative amounts
            if amount_min is not None and amount_min < 0:
                issues.append({
                    'code': 'NEGATIVE_AMOUNT',
                    'message': f"Negative amount_min: {amount_min}",
                    'severity': 'error',
                    'field': f"transactions[{i}].amount_min"
                })
                
            if amount_max is not None and amount_max < 0:
                issues.append({
                    'code': 'NEGATIVE_AMOUNT',
                    'message': f"Negative amount_max: {amount_max}",
                    'severity': 'error',
                    'field': f"transactions[{i}].amount_max"
                })
                
            # Check range
            if amount_min is not None and amount_max is not None:
                if amount_min > amount_max:
                    issues.append({
                        'code': 'INVALID_AMOUNT_RANGE',
                        'message': f"amount_min ({amount_min}) > amount_max ({amount_max})",
                        'severity': 'error',
                        'field': f"transactions[{i}].amount_min"
                    })
                    
        return issues
