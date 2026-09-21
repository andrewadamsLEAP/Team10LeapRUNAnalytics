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