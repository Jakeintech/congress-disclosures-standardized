"""
Anomaly Detector.
"""

from typing import Dict, List, Any
from . import Validator

class AnomalyDetector(Validator):
    def validate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues = []
        
        transactions = data.get('transactions', [])
        
        # Rule: Too many transactions
        if len(transactions) > 100:
            issues.append({
                'code': 'HIGH_TRANSACTION_COUNT',
                'message': f"Unusually high transaction count: {len(transactions)}",
                'severity': 'warning',
                'field': 'transactions'
            })
            
        # Rule: Duplicate trades (same date, asset, amount, type)
        seen_trades = set()
        for i, tx in enumerate(transactions):
            # Create a signature
            sig = (
                tx.get('transaction_date'),
                tx.get('asset_name'),
                tx.get('amount_min'),
                tx.get('transaction_type')
            )
            
            if sig in seen_trades:
                issues.append({
                    'code': 'DUPLICATE_TRANSACTION',
                    'message': "Potential duplicate transaction",
                    'severity': 'warning',
                    'field': f"transactions[{i}]"
                })
            else:
                seen_trades.add(sig)
                
        # Rule: Generic asset names
        generic_names = ['stock', 'bond', 'fund', 'asset', 'investment']
        for i, tx in enumerate(transactions):
            asset = tx.get('asset_name', '').lower()
            if asset in generic_names:
                issues.append({
                    'code': 'GENERIC_ASSET_NAME',
                    'message': f"Generic asset name detected: {asset}",
                    'severity': 'warning',
                    'field': f"transactions[{i}].asset_name"
                })
                
        return issues
