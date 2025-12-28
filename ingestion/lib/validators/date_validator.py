"""
Date Validator.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
from . import Validator

class DateValidator(Validator):
    def validate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues = []
        today = datetime.now().date()
        
        # Validate filing_date
        filing_date_str = data.get('filing_date')
        if filing_date_str:
            try:
                filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d').date()
                if filing_date > today:
                    issues.append({
                        'code': 'FUTURE_FILING_DATE',
                        'message': f"Filing date {filing_date} is in the future",
                        'severity': 'error',
                        'field': 'filing_date'
                    })
            except ValueError:
                issues.append({
                    'code': 'INVALID_DATE_FORMAT',
                    'message': f"Invalid date format: {filing_date_str}",
                    'severity': 'error',
                    'field': 'filing_date'
                })
                
        # Validate transactions
        transactions = data.get('transactions', [])
        for i, tx in enumerate(transactions):
            tx_date_str = tx.get('transaction_date')
            notif_date_str = tx.get('notification_date')
            
            if tx_date_str:
                try:
                    tx_date = datetime.strptime(tx_date_str, '%Y-%m-%d').date()
                    if tx_date > today:
                        issues.append({
                            'code': 'FUTURE_TRANSACTION_DATE',
                            'message': f"Transaction date {tx_date} is in the future",
                            'severity': 'error',
                            'field': f"transactions[{i}].transaction_date"
                        })
                        
                    if filing_date_str and filing_date and tx_date > filing_date:
                        issues.append({
                            'code': 'TRANSACTION_AFTER_FILING',
                            'message': f"Transaction date {tx_date} is after filing date {filing_date}",
                            'severity': 'error',
                            'field': f"transactions[{i}].transaction_date"
                        })
                except ValueError:
                     issues.append({
                        'code': 'INVALID_DATE_FORMAT',
                        'message': f"Invalid date format: {tx_date_str}",
                        'severity': 'error',
                        'field': f"transactions[{i}].transaction_date"
                    })

            if notif_date_str and tx_date_str:
                try:
                    notif_date = datetime.strptime(notif_date_str, '%Y-%m-%d').date()
                    tx_date = datetime.strptime(tx_date_str, '%Y-%m-%d').date()
                    
                    if notif_date < tx_date:
                        issues.append({
                            'code': 'NOTIFICATION_BEFORE_TRANSACTION',
                            'message': f"Notification date {notif_date} is before transaction date {tx_date}",
                            'severity': 'error',
                            'field': f"transactions[{i}].notification_date"
                        })
                        
                    # 45 day rule check (warning)
                    if (notif_date - tx_date).days > 45:
                         issues.append({
                            'code': 'LATE_NOTIFICATION',
                            'message': f"Notification date is {(notif_date - tx_date).days} days after transaction (limit 45)",
                            'severity': 'warning',
                            'field': f"transactions[{i}].notification_date"
                        })
                except ValueError:
                    pass

        return issues
