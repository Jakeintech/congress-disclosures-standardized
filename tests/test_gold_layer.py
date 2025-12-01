import sys
import os
import unittest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Import modules to test
import compute_agg_member_trading_stats
import compute_agg_stock_activity
import compute_agg_sector_activity

class TestMemberTradingStats(unittest.TestCase):
    def setUp(self):
        self.sample_transactions = pd.DataFrame([
            {
                'member_key': '1',
                'transaction_type': 'Purchase',
                'amount_low': 1000.0,
                'amount_high': 15000.0,
                'transaction_date_key': 20250101,
                'ticker': 'AAPL',
                'asset_description': 'Apple Inc.'
            },
            {
                'member_key': '1',
                'transaction_type': 'Sale',
                'amount_low': 1000.0,
                'amount_high': 15000.0,
                'transaction_date_key': 20250102,
                'ticker': 'AAPL',
                'asset_description': 'Apple Inc.'
            },
            {
                'member_key': '2',
                'transaction_type': 'Purchase',
                'amount_low': 50000.0,
                'amount_high': 100000.0,
                'transaction_date_key': 20250105,
                'ticker': 'MSFT',
                'asset_description': 'Microsoft Corp.'
            }
        ])

        self.sample_members = pd.DataFrame([
            {'member_key': '1', 'full_name': 'Member One', 'party': 'D', 'state_district': 'CA-01'},
            {'member_key': '2', 'full_name': 'Member Two', 'party': 'R', 'state_district': 'TX-02'}
        ])

    def test_compute_stats_basic(self):
        stats = compute_agg_member_trading_stats.compute_member_trading_stats(self.sample_transactions, self.sample_members)
        
        self.assertFalse(stats.empty)
        self.assertEqual(len(stats), 2)
        
        # Check Member 1
        m1 = stats[stats['member_key'] == '1'].iloc[0]
        self.assertEqual(m1['total_trades'], 2)
        self.assertEqual(m1['buy_count'], 1)
        self.assertEqual(m1['sell_count'], 1)
        self.assertEqual(m1['total_volume'], 16000.0) # (8000 + 8000)
        
        # Check Member 2
        m2 = stats[stats['member_key'] == '2'].iloc[0]
        self.assertEqual(m2['total_trades'], 1)
        self.assertEqual(m2['total_volume'], 75000.0)

    def test_missing_columns_handled(self):
        # Dataframe missing amount_midpoint and transaction_date (should be derived)
        df = pd.DataFrame([
            {
                'member_key': '1',
                'transaction_type': 'Purchase',
                'amount_low': 1000.0,
                'amount_high': 15000.0,
                'transaction_date_key': 20250101
            }
        ])
        
        stats = compute_agg_member_trading_stats.compute_member_trading_stats(df, self.sample_members)
        self.assertFalse(stats.empty)
        self.assertEqual(stats.iloc[0]['total_volume'], 8000.0)
        self.assertEqual(stats.iloc[0]['first_transaction_date'], '2025-01-01')

    def test_empty_input(self):
        stats = compute_agg_member_trading_stats.compute_member_trading_stats(pd.DataFrame(), self.sample_members)
        self.assertTrue(stats.empty)
        self.assertIn('total_volume', stats.columns)

class TestStockActivity(unittest.TestCase):
    def test_compute_activity(self):
        df = pd.DataFrame([
            {
                'ticker': 'AAPL',
                'transaction_type': 'Purchase',
                'amount_low': 1000.0,
                'amount_high': 15000.0,
                'member_key': '1',
                'transaction_date_key': 20250101,
                'asset_description': 'Apple'
            },
            {
                'ticker': 'AAPL',
                'transaction_type': 'Sale',
                'amount_low': 1000.0,
                'amount_high': 15000.0,
                'member_key': '2',
                'transaction_date_key': 20250102,
                'asset_description': 'Apple'
            }
        ])
        
        stats = compute_agg_stock_activity.compute_stock_activity(df)
        self.assertEqual(len(stats), 1)
        row = stats.iloc[0]
        self.assertEqual(row['ticker'], 'AAPL')
        self.assertEqual(row['total_volume'], 16000.0)
        self.assertEqual(row['net_flow'], 0.0) # 8000 buy - 8000 sell
        self.assertEqual(row['unique_traders'], 2)

class TestSectorActivity(unittest.TestCase):
    def test_derive_sector(self):
        # Test heuristic
        self.assertEqual(compute_agg_sector_activity.derive_sector({'asset_description': 'Apple Inc.'}), 'Technology')
        self.assertEqual(compute_agg_sector_activity.derive_sector({'asset_description': 'Pfizer'}), 'Healthcare')
        self.assertEqual(compute_agg_sector_activity.derive_sector({'asset_description': 'Unknown'}), 'Other')

    def test_compute_activity(self):
        df = pd.DataFrame([
            {
                'ticker': 'AAPL',
                'transaction_type': 'Purchase',
                'amount_low': 1000.0,
                'amount_high': 15000.0,
                'member_key': '1',
                'transaction_date_key': 20250101,
                'asset_description': 'Apple Inc.',
                'asset_key': 'mock_asset_key_1'
            }
        ])
        
        stats = compute_agg_sector_activity.compute_sector_activity(df)
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats.iloc[0]['sector'], 'Technology')
        self.assertEqual(stats.iloc[0]['total_volume'], 8000.0)

if __name__ == "__main__":
    unittest.main()
