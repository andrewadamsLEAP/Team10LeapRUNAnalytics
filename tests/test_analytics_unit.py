from unittest.mock import Mock, patch, MagicMock
import unittest
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import analytics


class AnalyticsUnitTests(unittest.TestCase):
    """Unit tests for analytics functions with mocked database"""

    def setUp(self):
        """Set up test data"""
        self.mock_conn = MagicMock()

    @patch('analytics.get_connection')
    @patch('analytics.pd.read_sql')
    def test_get_kpi_metrics_returns_dict_with_all_kpi_fields(self, mock_read_sql, mock_get_conn):
        """Test that get_kpi_metrics returns dict with all required KPI fields"""
        mock_get_conn.return_value = self.mock_conn

        # Mock database responses for each query
        mock_read_sql.side_effect = [
            # Total trades
            pd.DataFrame({'count': [1250]}),
            # Total volume
            pd.DataFrame({'total': [5234000.50]}),
            # Avg trade value
            pd.DataFrame({'avg': [4187.20]}),
            # Total clients
            pd.DataFrame({'count': [125]}),
            # Active clients (last 30 days)
            pd.DataFrame({'count': [89]}),
            # Top 5 active clients
            pd.DataFrame({
                'client_id': [5, 3, 12, 7, 1],
                'first_name': ['John', 'Jane', 'Mike', 'Sarah', 'Bob'],
                'last_name': ['Doe', 'Smith', 'Johnson', 'Williams', 'Brown'],
                'trade_count': [145, 98, 87, 76, 65],
                'volume': [450000.00, 380000.00, 320000.00, 290000.00, 250000.00]
            }),
            # Inactive clients
            pd.DataFrame({'count': [36]})
        ]

        result = analytics.get_kpi_metrics(days=30)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertIn('total_trades', result)
        self.assertIn('total_volume', result)
        self.assertIn('avg_trade_value', result)
        self.assertIn('total_clients', result)
        self.assertIn('active_clients', result)
        self.assertIn('active_clients_percentage', result)
        self.assertIn('top_active_clients', result)
        self.assertIn('inactive_clients', result)

    @patch('analytics.get_connection')
    @patch('analytics.pd.read_sql')
    def test_get_kpi_metrics_calculates_correct_values(self, mock_read_sql, mock_get_conn):
        """Test that KPI values are calculated correctly"""
        mock_get_conn.return_value = self.mock_conn

        mock_read_sql.side_effect = [
            pd.DataFrame({'count': [1250]}),
            pd.DataFrame({'total': [5234000.50]}),
            pd.DataFrame({'avg': [4187.20]}),
            pd.DataFrame({'count': [125]}),
            pd.DataFrame({'count': [100]}),
            pd.DataFrame({
                'client_id': [1],
                'first_name': ['John'],
                'last_name': ['Doe'],
                'trade_count': [50],
                'volume': [100000.00]
            }),
            pd.DataFrame({'count': [25]})
        ]

        result = analytics.get_kpi_metrics(days=30)

        self.assertEqual(result['total_trades'], 1250)
        self.assertEqual(result['total_volume'], 5234000.50)
        self.assertEqual(result['avg_trade_value'], 4187.20)
        self.assertEqual(result['total_clients'], 125)
        self.assertEqual(result['active_clients'], 100)
        self.assertEqual(result['active_clients_percentage'], 80.0)
        self.assertEqual(result['inactive_clients'], 25)

    @patch('analytics.get_connection')
    @patch('analytics.pd.read_sql')
    def test_get_instrument_metrics_returns_list(self, mock_read_sql, mock_get_conn):
        """Test that get_instrument_metrics returns list of instruments"""
        mock_get_conn.return_value = self.mock_conn
        
        mock_read_sql.return_value = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'instrument_name': ['Apple Inc.', 'Microsoft Corporation', 'Alphabet Inc.'],
            'asset_type': ['STOCK', 'STOCK', 'STOCK'],
            'trade_count': [10, 8, 5],
            'total_quantity': [100, 80, 50],
            'total_volume': [25000.00, 20000.00, 15000.00],
            'avg_trade_value': [2500.00, 2500.00, 3000.00],
            'min_price': [150.00, 300.00, 140.00],
            'max_price': [160.00, 310.00, 150.00],
            'unique_traders': [5, 4, 3]
        })
        
        result = analytics.get_instrument_metrics(days=30)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['ticker'], 'AAPL')
        self.assertEqual(result[0]['trade_count'], 10)

    @patch('analytics.get_connection')
    @patch('analytics.pd.read_sql')
    def test_get_timeseries_metrics_returns_list(self, mock_read_sql, mock_get_conn):
        """Test that get_timeseries_metrics returns time-series data"""
        mock_get_conn.return_value = self.mock_conn
        
        mock_read_sql.return_value = pd.DataFrame({
            'period': pd.to_datetime(['2026-09-01', '2026-09-02', '2026-09-03']),
            'trade_count': [50, 55, 48],
            'total_volume': [125000.00, 135000.00, 120000.00],
            'avg_trade_value': [2500.00, 2454.55, 2500.00],
            'active_clients': [10, 12, 10],
            'instruments_traded': [8, 9, 7]
        })
        
        result = analytics.get_timeseries_metrics(days=30, granularity='daily')
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['trade_count'], 50)

    @patch('analytics.get_connection')
    @patch('analytics.pd.read_sql')
    def test_get_client_segments_returns_dict(self, mock_read_sql, mock_get_conn):
        """Test that get_client_segments returns summary and detailed data"""
        mock_get_conn.return_value = self.mock_conn
        
        # Mock initial query for client data
        mock_read_sql.return_value = pd.DataFrame({
            'client_id': [1, 2, 3, 4, 5],
            'first_name': ['John', 'Jane', 'Mike', 'Sarah', 'Bob'],
            'last_name': ['Doe', 'Smith', 'Johnson', 'Williams', 'Brown'],
            'trade_count': [10, 20, 5, 15, 1],
            'total_volume': [25000.00, 8000.00, 3000.00, 20000.00, 2000.00],
            'avg_trade_value': [2500.00, 400.00, 600.00, 1333.33, 2000.00],
            'instruments_traded': [5, 3, 2, 4, 1],
            'last_trade_date': pd.to_datetime(['2026-09-20', '2026-09-19', '2026-08-15', '2026-09-21', '2026-09-01'])
        })
        
        result = analytics.get_client_segments(days=30)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertIn('summary', result)
        self.assertIn('detailed', result)
        self.assertIsInstance(result['summary'], list)
        self.assertIsInstance(result['detailed'], list)

    @patch('analytics.get_connection')
    @patch('analytics.pd.read_sql')
    def test_get_instrument_details_returns_dict(self, mock_read_sql, mock_get_conn):
        """Test that get_instrument_details returns instrument, traders, and trends"""
        mock_get_conn.return_value = self.mock_conn
        
        # Mock instrument metrics
        metrics_df = pd.DataFrame({
            'ticker': ['AAPL'],
            'company_name': ['Apple Inc.'],
            'asset_type': ['STOCK'],
            'trade_count': [10],
            'total_quantity': [100],
            'total_volume': [25000.00],
            'avg_trade_value': [2500.00],
            'min_price': [240.00],
            'max_price': [250.00],
            'unique_traders': [5]
        })
        
        # Mock top traders
        traders_df = pd.DataFrame({
            'client_id': [1, 2, 3],
            'first_name': ['John', 'Jane', 'Mike'],
            'last_name': ['Doe', 'Smith', 'Johnson'],
            'trade_count': [4, 3, 2],
            'volume': [10000.00, 8000.00, 5000.00]
        })
        
        # Mock daily trend
        trend_df = pd.DataFrame({
            'date': pd.to_datetime(['2026-09-20', '2026-09-21']),
            'trade_count': [5, 5],
            'daily_volume': [12500.00, 12500.00]
        })
        
        mock_read_sql.side_effect = [metrics_df, traders_df, trend_df]
        
        result = analytics.get_instrument_details(ticker='AAPL', days=30)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertIn('instrument', result)
        self.assertIn('top_traders', result)
        self.assertIn('daily_trend', result)
        self.assertEqual(result['instrument']['ticker'], 'AAPL')
        self.assertIsInstance(result['top_traders'], list)
        self.assertIsInstance(result['daily_trend'], list)

    @patch('analytics.get_connection')
    @patch('analytics.pd.read_sql')
    def test_get_kpi_metrics_handles_null_volume(self, mock_read_sql, mock_get_conn):
        """Test that null volume is handled as 0"""
        mock_get_conn.return_value = self.mock_conn

        mock_read_sql.side_effect = [
            pd.DataFrame({'count': [0]}),
            pd.DataFrame({'total': [None]}),
            pd.DataFrame({'avg': [None]}),
            pd.DataFrame({'count': [0]}),
            pd.DataFrame({'count': [0]}),
            pd.DataFrame({
                'client_id': [],
                'first_name': [],
                'last_name': [],
                'trade_count': [],
                'volume': []
            }),
            pd.DataFrame({'count': [0]})
        ]

        result = analytics.get_kpi_metrics(days=30)

        self.assertEqual(result['total_volume'], 0)
        self.assertEqual(result['avg_trade_value'], 0)

    @patch('analytics.get_connection')
    @patch('analytics.pd.read_sql')
    def test_get_kpi_metrics_active_clients_percentage_zero_division(self, mock_read_sql, mock_get_conn):
        """Test that active_clients_percentage handles zero total clients"""
        mock_get_conn.return_value = self.mock_conn

        mock_read_sql.side_effect = [
            pd.DataFrame({'count': [0]}),
            pd.DataFrame({'total': [0]}),
            pd.DataFrame({'avg': [0]}),
            pd.DataFrame({'count': [0]}),  # Zero total clients
            pd.DataFrame({'count': [0]}),
            pd.DataFrame({
                'client_id': [],
                'first_name': [],
                'last_name': [],
                'trade_count': [],
                'volume': []
            }),
            pd.DataFrame({'count': [0]})
        ]

        result = analytics.get_kpi_metrics(days=30)

        self.assertEqual(result['active_clients_percentage'], 0)

    @patch('analytics.get_connection')
    @patch('analytics.pd.read_sql')
    def test_get_kpi_metrics_returns_top_5_active_clients(self, mock_read_sql, mock_get_conn):
        """Test that top 5 active clients are returned with correct structure"""
        mock_get_conn.return_value = self.mock_conn

        top_clients_df = pd.DataFrame({
            'client_id': [5, 3, 12, 7, 1],
            'first_name': ['John', 'Jane', 'Mike', 'Sarah', 'Bob'],
            'last_name': ['Doe', 'Smith', 'Johnson', 'Williams', 'Brown'],
            'trade_count': [145, 98, 87, 76, 65],
            'volume': [450000.00, 380000.00, 320000.00, 290000.00, 250000.00]
        })

        mock_read_sql.side_effect = [
            pd.DataFrame({'count': [1250]}),
            pd.DataFrame({'total': [5234000.50]}),
            pd.DataFrame({'avg': [4187.20]}),
            pd.DataFrame({'count': [125]}),
            pd.DataFrame({'count': [89]}),
            top_clients_df,
            pd.DataFrame({'count': [36]})
        ]

        result = analytics.get_kpi_metrics(days=30)

        self.assertEqual(len(result['top_active_clients']), 5)
        self.assertEqual(result['top_active_clients'][0]['client_id'], 5)
        self.assertEqual(result['top_active_clients'][0]['first_name'], 'John')
        self.assertEqual(result['top_active_clients'][0]['volume'], 450000.00)

    @patch('analytics.get_connection')
    @patch('analytics.pd.read_sql')
    def test_get_kpi_metrics_exception_handling(self, mock_read_sql, mock_get_conn):
        """Test that exceptions are caught and None is returned"""
        mock_get_conn.return_value = self.mock_conn
        mock_read_sql.side_effect = Exception("Database connection failed")

        result = analytics.get_kpi_metrics(days=30)

        self.assertIsNone(result)
        self.mock_conn.close.assert_called_once()

    @patch('analytics.get_connection')
    @patch('analytics.pd.read_sql')
    def test_get_kpi_metrics_connection_always_closed(self, mock_read_sql, mock_get_conn):
        """Test that database connection is always closed"""
        mock_get_conn.return_value = self.mock_conn

        mock_read_sql.side_effect = [
            pd.DataFrame({'count': [100]}),
            pd.DataFrame({'total': [1000.00]}),
            pd.DataFrame({'avg': [10.00]}),
            pd.DataFrame({'count': [50]}),
            pd.DataFrame({'count': [40]}),
            pd.DataFrame({'client_id': [], 'first_name': [], 'last_name': [], 
                         'trade_count': [], 'volume': []}),
            pd.DataFrame({'count': [10]})
        ]

        result = analytics.get_kpi_metrics(days=30)

        self.mock_conn.close.assert_called_once()

    @patch('analytics.get_connection')
    @patch('analytics.pd.read_sql')
    def test_get_kpi_metrics_with_different_date_ranges(self, mock_read_sql, mock_get_conn):
        """Test that KPIs work with different date ranges"""
        mock_get_conn.return_value = self.mock_conn

        mock_read_sql.side_effect = [
            pd.DataFrame({'count': [500]}),
            pd.DataFrame({'total': [1000000.00]}),
            pd.DataFrame({'avg': [2000.00]}),
            pd.DataFrame({'count': [100]}),
            pd.DataFrame({'count': [50]}),
            pd.DataFrame({'client_id': [], 'first_name': [], 'last_name': [], 
                         'trade_count': [], 'volume': []}),
            pd.DataFrame({'count': [50]})
        ]

        result = analytics.get_kpi_metrics(days=90)

        self.assertIsNotNone(result)
        self.assertEqual(result['total_trades'], 500)


if __name__ == "__main__":
    unittest.main()