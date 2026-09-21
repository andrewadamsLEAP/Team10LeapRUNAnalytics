import unittest
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import analytics


class AnalyticsIntegrationTests(unittest.TestCase):
    """Integration tests for analytics functions with actual database"""

    @classmethod
    def setUpClass(cls):
        """Check if database is available"""
        conn = None
        try:
            conn = analytics.get_connection()
            # Check if required tables exist
            query = "SELECT COUNT(*) as count FROM clients"
            test_df = pd.read_sql(query, conn)
        except Exception as exc:
            raise unittest.SkipTest(f"Database unavailable for integration test: {exc}")
        finally:
            if conn is not None:
                conn.close()

    def test_get_kpi_metrics_returns_valid_data(self):
        """Test that get_kpi_metrics returns valid data from actual database"""
        result = analytics.get_kpi_metrics(days=30)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)

    def test_get_kpi_metrics_all_fields_present(self):
        """Test that all KPI fields are present in response"""
        result = analytics.get_kpi_metrics(days=30)

        required_fields = [
            'total_trades',
            'total_volume',
            'avg_trade_value',
            'total_clients',
            'active_clients',
            'active_clients_percentage',
            'top_active_clients',
            'inactive_clients'
        ]

        for field in required_fields:
            self.assertIn(field, result, f"Missing field: {field}")

    def test_get_kpi_metrics_values_are_numeric(self):
        """Test that numeric KPI fields have correct types"""
        result = analytics.get_kpi_metrics(days=30)

        self.assertIsInstance(result['total_trades'], int)
        self.assertIsInstance(result['total_volume'], (int, float))
        self.assertIsInstance(result['avg_trade_value'], (int, float))
        self.assertIsInstance(result['total_clients'], int)
        self.assertIsInstance(result['active_clients'], int)
        self.assertIsInstance(result['active_clients_percentage'], (int, float))
        self.assertIsInstance(result['inactive_clients'], int)

    def test_get_kpi_metrics_logical_constraints(self):
        """Test that KPI values satisfy logical constraints"""
        result = analytics.get_kpi_metrics(days=30)

        # Active clients should be <= total clients
        self.assertLessEqual(result['active_clients'], result['total_clients'])

        # Inactive clients should be <= total clients
        self.assertLessEqual(result['inactive_clients'], result['total_clients'])

        # Percentage should be 0-100
        self.assertGreaterEqual(result['active_clients_percentage'], 0)
        self.assertLessEqual(result['active_clients_percentage'], 100)

        # Volumes should be non-negative
        self.assertGreaterEqual(result['total_volume'], 0)
        self.assertGreaterEqual(result['avg_trade_value'], 0)

    def test_get_kpi_metrics_top_clients_is_list(self):
        """Test that top active clients is a list of dicts"""
        result = analytics.get_kpi_metrics(days=30)

        self.assertIsInstance(result['top_active_clients'], list)
        self.assertLessEqual(len(result['top_active_clients']), 5)

        if len(result['top_active_clients']) > 0:
            client = result['top_active_clients'][0]
            self.assertIn('client_id', client)
            self.assertIn('first_name', client)
            self.assertIn('last_name', client)
            self.assertIn('trade_count', client)
            self.assertIn('volume', client)

    def test_get_kpi_metrics_different_date_ranges(self):
        """Test that KPIs can be retrieved with different date ranges"""
        result_7_days = analytics.get_kpi_metrics(days=7)
        result_30_days = analytics.get_kpi_metrics(days=30)
        result_90_days = analytics.get_kpi_metrics(days=90)

        self.assertIsNotNone(result_7_days)
        self.assertIsNotNone(result_30_days)
        self.assertIsNotNone(result_90_days)

        # Longer date ranges should have more activity
        self.assertLessEqual(result_7_days['active_clients'], result_90_days['active_clients'])
        self.assertLessEqual(result_7_days['total_trades'], result_90_days['total_trades'])


if __name__ == "__main__":
    unittest.main()
