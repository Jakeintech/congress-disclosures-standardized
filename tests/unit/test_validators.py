import pytest
from datetime import datetime, timedelta
import sys
import os

# Add ingestion/lib to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ingestion/lib')))

from validators.date_validator import DateValidator
from validators.amount_validator import AmountValidator
from validators.completeness_validator import CompletenessValidator
from validators.anomaly_detector import AnomalyDetector

class TestValidators:
    
    def test_date_validator(self):
        validator = DateValidator()
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Future filing date
        issues = validator.validate({'filing_date': future_date})
        assert len(issues) == 1
        assert issues[0]['code'] == 'FUTURE_FILING_DATE'
        
        # Transaction after filing
        issues = validator.validate({
            'filing_date': '2025-01-01',
            'transactions': [{'transaction_date': '2025-02-01'}]
        })
        assert len(issues) == 1
        assert issues[0]['code'] == 'TRANSACTION_AFTER_FILING'

    def test_amount_validator(self):
        validator = AmountValidator()
        
        # Negative amount
        issues = validator.validate({
            'transactions': [{'amount_min': -100}]
        })
        assert len(issues) == 1
        assert issues[0]['code'] == 'NEGATIVE_AMOUNT'
        
        # Invalid range
        issues = validator.validate({
            'transactions': [{'amount_min': 1000, 'amount_max': 500}]
        })
        assert len(issues) == 1
        assert issues[0]['code'] == 'INVALID_AMOUNT_RANGE'

    def test_completeness_validator(self):
        validator = CompletenessValidator()
        
        # Missing required field
        issues = validator.validate({'year': 2025})
        assert any(i['code'] == 'MISSING_REQUIRED_FIELD' for i in issues)
        
        # PTR with no transactions
        issues = validator.validate({
            'filing_type': 'P',
            'year': 2025,
            'doc_id': '123',
            'transactions': []
        })
        assert any(i['code'] == 'NO_TRANSACTIONS' for i in issues)

    def test_anomaly_detector(self):
        validator = AnomalyDetector()
        
        # Too many transactions
        issues = validator.validate({
            'transactions': [{'asset_name': 'Stock'}] * 101
        })
        assert any(i['code'] == 'HIGH_TRANSACTION_COUNT' for i in issues)
        
        # Duplicate transactions
        tx = {
            'transaction_date': '2025-01-01',
            'asset_name': 'Apple',
            'amount_min': 1000,
            'transaction_type': 'purchase'
        }
        issues = validator.validate({
            'transactions': [tx, tx]
        })
        assert any(i['code'] == 'DUPLICATE_TRANSACTION' for i in issues)
