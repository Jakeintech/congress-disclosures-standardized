import sys
import os
import unittest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Import modules to test
import compute_agg_member_trading_stats
import compute_agg_stock_activity
import compute_agg_sector_activity
import compute_agg_trading_volume_timeseries
import compute_agg_congressional_alpha
import compute_agg_conflict_detection
import compute_agg_portfolio_reconstruction
import compute_agg_timing_heatmap
import compute_agg_sector_analysis

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


class TestTradingVolumeTimeseries(unittest.TestCase):
    """Tests for compute_agg_trading_volume_timeseries module."""
    
    def setUp(self):
        self.sample_transactions = pd.DataFrame([
            {
                'member_key': '1',
                'transaction_type': 'Purchase',
                'amount_low': 1000.0,
                'amount_high': 15000.0,
                'transaction_date_key': 20250101,
                'ticker': 'AAPL'
            },
            {
                'member_key': '1',
                'transaction_type': 'Sale',
                'amount_low': 1000.0,
                'amount_high': 15000.0,
                'transaction_date_key': 20250108,
                'ticker': 'AAPL'
            },
            {
                'member_key': '2',
                'transaction_type': 'Purchase',
                'amount_low': 50000.0,
                'amount_high': 100000.0,
                'transaction_date_key': 20250115,
                'ticker': 'MSFT'
            }
        ])
        
        self.sample_members = pd.DataFrame([
            {'member_key': '1', 'party': 'D'},
            {'member_key': '2', 'party': 'R'}
        ])
    
    def test_compute_daily_timeseries(self):
        ts = compute_agg_trading_volume_timeseries.compute_timeseries(
            self.sample_transactions.copy(), 
            self.sample_members, 
            granularity='daily'
        )
        
        self.assertFalse(ts.empty)
        self.assertEqual(ts['granularity'].iloc[0], 'daily')
        self.assertIn('total_volume', ts.columns)
        self.assertIn('buy_volume', ts.columns)
        self.assertIn('sell_volume', ts.columns)
        self.assertIn('net_flow', ts.columns)
    
    def test_compute_weekly_timeseries(self):
        ts = compute_agg_trading_volume_timeseries.compute_timeseries(
            self.sample_transactions.copy(), 
            self.sample_members, 
            granularity='weekly'
        )
        
        self.assertFalse(ts.empty)
        self.assertEqual(ts['granularity'].iloc[0], 'weekly')
    
    def test_compute_monthly_timeseries(self):
        ts = compute_agg_trading_volume_timeseries.compute_timeseries(
            self.sample_transactions.copy(), 
            self.sample_members, 
            granularity='monthly'
        )
        
        self.assertFalse(ts.empty)
        self.assertEqual(ts['granularity'].iloc[0], 'monthly')
        # All transactions in January, so 1 period
        self.assertEqual(len(ts), 1)
    
    def test_empty_input(self):
        ts = compute_agg_trading_volume_timeseries.compute_timeseries(
            pd.DataFrame(), self.sample_members, 'daily'
        )
        self.assertTrue(ts.empty)


class TestCongressionalAlpha(unittest.TestCase):
    """Tests for compute_agg_congressional_alpha module."""
    
    def setUp(self):
        self.sample_transactions = pd.DataFrame([
            {
                'member_key': 'M001',
                'transaction_type': 'Purchase',
                'amount_low': 15000.0,
                'amount_high': 50000.0,
                'transaction_date_key': 20250101,
                'ticker': 'NVDA',
                'asset_description': 'NVIDIA Corp'
            },
            {
                'member_key': 'M001',
                'transaction_type': 'Purchase',
                'amount_low': 50000.0,
                'amount_high': 100000.0,
                'transaction_date_key': 20250115,
                'ticker': 'AAPL',
                'asset_description': 'Apple Inc'
            },
            {
                'member_key': 'M002',
                'transaction_type': 'Sale',
                'amount_low': 100000.0,
                'amount_high': 250000.0,
                'transaction_date_key': 20250120,
                'ticker': 'MSFT',
                'asset_description': 'Microsoft Corp'
            }
        ])
        
        self.sample_members = pd.DataFrame([
            {'member_key': 'M001', 'full_name': 'Alpha Trader', 'party': 'D', 'state': 'CA'},
            {'member_key': 'M002', 'full_name': 'Beta Trader', 'party': 'R', 'state': 'TX'}
        ])
    
    def test_estimate_trade_return(self):
        # Purchase should show positive alpha
        buy_return = compute_agg_congressional_alpha.estimate_trade_return('Purchase', 30)
        self.assertGreater(buy_return, 0)
        
        # Sale return exists
        sell_return = compute_agg_congressional_alpha.estimate_trade_return('Sale', 30)
        self.assertIsNotNone(sell_return)
    
    def test_compute_member_alpha(self):
        alpha = compute_agg_congressional_alpha.compute_member_alpha(
            self.sample_transactions.copy(),
            self.sample_members
        )
        
        self.assertFalse(alpha.empty)
        self.assertEqual(len(alpha), 2)  # 2 members
        self.assertIn('alpha', alpha.columns)
        self.assertIn('alpha_percentile', alpha.columns)
        self.assertIn('total_trades', alpha.columns)
    
    def test_compute_party_alpha(self):
        party_alpha = compute_agg_congressional_alpha.compute_party_alpha(
            self.sample_transactions.copy(),
            self.sample_members
        )
        
        self.assertFalse(party_alpha.empty)
        self.assertIn('D', party_alpha['party'].values)
        self.assertIn('R', party_alpha['party'].values)
        self.assertIn('alpha', party_alpha.columns)
    
    def test_compute_sector_rotation(self):
        rotation = compute_agg_congressional_alpha.compute_sector_rotation(
            self.sample_transactions.copy()
        )
        
        self.assertFalse(rotation.empty)
        self.assertIn('sector', rotation.columns)
        self.assertIn('rotation_signal', rotation.columns)
        self.assertIn('net_flow', rotation.columns)


class TestConflictDetection(unittest.TestCase):
    """Tests for compute_agg_conflict_detection module."""
    
    def test_classify_industry(self):
        self.assertEqual(
            compute_agg_conflict_detection.classify_industry('Apple Inc.'), 
            'Technology'
        )
        self.assertEqual(
            compute_agg_conflict_detection.classify_industry('Pfizer Inc.'), 
            'Healthcare'
        )
        self.assertEqual(
            compute_agg_conflict_detection.classify_industry('JPMorgan Chase'), 
            'Financials'
        )
        self.assertEqual(
            compute_agg_conflict_detection.classify_industry('Unknown Corp'), 
            'Other'
        )
    
    def test_calculate_conflict_score(self):
        trade_date = datetime(2025, 1, 15)
        bill_date = datetime(2025, 1, 10)  # 5 days before trade
        
        result = compute_agg_conflict_detection.calculate_conflict_score(
            trade_date=trade_date,
            bill_action_date=bill_date,
            trade_industry='Technology',
            bill_industries=['Technology'],
            member_role='sponsor',
            trade_amount=250000.0
        )
        
        self.assertIn('total_score', result)
        self.assertIn('severity', result)
        self.assertGreater(result['total_score'], 0)
        
        # High score expected: recent timing + matching industry + sponsor + large trade
        self.assertGreaterEqual(result['total_score'], 70)
        self.assertIn(result['severity'], ['HIGH', 'CRITICAL'])
    
    def test_conflict_score_low_when_distant(self):
        trade_date = datetime(2025, 1, 15)
        bill_date = datetime(2024, 10, 1)  # Over 90 days before
        
        result = compute_agg_conflict_detection.calculate_conflict_score(
            trade_date=trade_date,
            bill_action_date=bill_date,
            trade_industry='Other',
            bill_industries=['Healthcare'],
            member_role='other',
            trade_amount=5000.0
        )
        
        # Low score expected: distant timing + no industry match + minor role + small trade
        self.assertLess(result['total_score'], 30)


class TestPortfolioReconstruction(unittest.TestCase):
    """Tests for compute_agg_portfolio_reconstruction module."""
    
    def test_classify_sector(self):
        self.assertEqual(
            compute_agg_portfolio_reconstruction.classify_sector('Microsoft Corporation'),
            'Technology'
        )
        self.assertEqual(
            compute_agg_portfolio_reconstruction.classify_sector('Exxon Mobil'),
            'Energy'
        )
    
    def test_calculate_confidence_score(self):
        score, factors = compute_agg_portfolio_reconstruction.calculate_confidence_score(
            trade_count=25,
            last_trade_date=datetime.now() - timedelta(days=15),
            avg_range_precision=1.5,
            years_of_history=2.5
        )
        
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)
        self.assertIsInstance(factors, str)
        
        # Good score expected with these parameters
        self.assertGreater(score, 60)
    
    def test_portfolio_reconstruction_basic(self):
        transactions = pd.DataFrame([
            {
                'member_key': 'M001',
                'transaction_type': 'Purchase',
                'amount_low': 50000.0,
                'amount_high': 100000.0,
                'transaction_date_key': 20240101,
                'ticker': 'AAPL',
                'asset_description': 'Apple Inc'
            },
            {
                'member_key': 'M001',
                'transaction_type': 'Purchase',
                'amount_low': 100000.0,
                'amount_high': 250000.0,
                'transaction_date_key': 20240601,
                'ticker': 'MSFT',
                'asset_description': 'Microsoft'
            },
            {
                'member_key': 'M001',
                'transaction_type': 'Sale',
                'amount_low': 15000.0,
                'amount_high': 50000.0,
                'transaction_date_key': 20250101,
                'ticker': 'AAPL',
                'asset_description': 'Apple Inc'
            }
        ])
        
        members = pd.DataFrame([
            {'member_key': 'M001', 'full_name': 'Test Member', 'party': 'D'}
        ])
        
        portfolios, holdings = compute_agg_portfolio_reconstruction.reconstruct_portfolio(
            transactions.copy(), members
        )
        
        self.assertFalse(portfolios.empty)
        self.assertEqual(len(portfolios), 1)  # 1 member
        self.assertIn('estimated_portfolio_value', portfolios.columns)
        self.assertIn('confidence_score', portfolios.columns)


class TestTimingHeatmap(unittest.TestCase):
    """Tests for compute_agg_timing_heatmap module."""
    
    def setUp(self):
        # Create transactions across different days of week
        self.sample_transactions = pd.DataFrame([
            {'member_key': '1', 'transaction_type': 'Purchase', 'amount_low': 1000.0, 
             'amount_high': 15000.0, 'transaction_date_key': 20250106},  # Monday
            {'member_key': '1', 'transaction_type': 'Purchase', 'amount_low': 1000.0, 
             'amount_high': 15000.0, 'transaction_date_key': 20250107},  # Tuesday
            {'member_key': '2', 'transaction_type': 'Sale', 'amount_low': 50000.0, 
             'amount_high': 100000.0, 'transaction_date_key': 20250108},  # Wednesday
            {'member_key': '2', 'transaction_type': 'Purchase', 'amount_low': 15000.0, 
             'amount_high': 50000.0, 'transaction_date_key': 20250110},  # Friday
        ])
    
    def test_compute_day_of_week_heatmap(self):
        heatmap = compute_agg_timing_heatmap.compute_day_of_week_heatmap(
            self.sample_transactions.copy()
        )
        
        self.assertFalse(heatmap.empty)
        self.assertIn('day_name', heatmap.columns)
        self.assertIn('total_volume', heatmap.columns)
        self.assertIn('pct_of_volume', heatmap.columns)
        self.assertIn('deviation', heatmap.columns)
    
    def test_compute_month_of_year_heatmap(self):
        heatmap = compute_agg_timing_heatmap.compute_month_of_year_heatmap(
            self.sample_transactions.copy()
        )
        
        self.assertFalse(heatmap.empty)
        self.assertIn('month_name', heatmap.columns)
        # All transactions in January
        self.assertEqual(heatmap.iloc[0]['month_name'], 'Jan')
    
    def test_compute_year_over_year(self):
        yoy = compute_agg_timing_heatmap.compute_year_over_year(
            self.sample_transactions.copy()
        )
        
        self.assertFalse(yoy.empty)
        self.assertIn('year', yoy.columns)
        self.assertIn('yoy_volume_growth', yoy.columns)


class TestDeepSectorAnalysis(unittest.TestCase):
    """Tests for compute_agg_sector_analysis module."""
    
    def setUp(self):
        self.sample_transactions = pd.DataFrame([
            {
                'member_key': '1', 'member_bioguide_id': 'B001',
                'transaction_type': 'Purchase',
                'amount_low': 50000.0, 'amount_high': 100000.0,
                'transaction_date_key': 20250101, 'ticker': 'AAPL',
                'asset_description': 'Apple Inc'
            },
            {
                'member_key': '2', 'member_bioguide_id': 'B002',
                'transaction_type': 'Purchase',
                'amount_low': 100000.0, 'amount_high': 250000.0,
                'transaction_date_key': 20250115, 'ticker': 'PFE',
                'asset_description': 'Pfizer Inc'
            },
            {
                'member_key': '1', 'member_bioguide_id': 'B001',
                'transaction_type': 'Sale',
                'amount_low': 15000.0, 'amount_high': 50000.0,
                'transaction_date_key': 20250120, 'ticker': 'MSFT',
                'asset_description': 'Microsoft Corp'
            }
        ])
        
        self.sample_members = pd.DataFrame([
            {'member_key': '1', 'member_bioguide_id': 'B001', 'party': 'D'},
            {'member_key': '2', 'member_bioguide_id': 'B002', 'party': 'R'}
        ])
    
    def test_classify_sector(self):
        self.assertEqual(
            compute_agg_sector_analysis.classify_sector('Apple Inc'),
            'Technology'
        )
        self.assertEqual(
            compute_agg_sector_analysis.classify_sector('Pfizer pharma'),
            'Healthcare'
        )
        self.assertEqual(
            compute_agg_sector_analysis.classify_sector('Boeing Aerospace'),
            'Defense & Aerospace'
        )
    
    def test_compute_sector_summary(self):
        summary = compute_agg_sector_analysis.compute_sector_summary(
            self.sample_transactions.copy(),
            self.sample_members
        )
        
        self.assertFalse(summary.empty)
        self.assertIn('sector', summary.columns)
        self.assertIn('total_volume', summary.columns)
        self.assertIn('flow_signal', summary.columns)
        self.assertIn('pct_of_total', summary.columns)
        
        # Check that percentages sum to ~100
        total_pct = summary['pct_of_total'].sum()
        self.assertAlmostEqual(total_pct, 100.0, places=1)
    
    def test_compute_sector_by_party(self):
        party = compute_agg_sector_analysis.compute_sector_by_party(
            self.sample_transactions.copy(),
            self.sample_members
        )
        
        self.assertFalse(party.empty)
        self.assertIn('d_pct', party.columns)
        self.assertIn('r_pct', party.columns)
        self.assertIn('party_lean', party.columns)
    
    def test_compute_top_stocks_by_sector(self):
        top = compute_agg_sector_analysis.compute_top_stocks_by_sector(
            self.sample_transactions.copy()
        )
        
        self.assertFalse(top.empty)
        self.assertIn('sector', top.columns)
        self.assertIn('ticker', top.columns)
        self.assertIn('sector_rank', top.columns)


if __name__ == "__main__":
    unittest.main()

