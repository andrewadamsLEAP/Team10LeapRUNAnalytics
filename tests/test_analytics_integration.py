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

    def test_get_instrument_metrics_returns_valid_data(self):
        """Test that get_instrument_metrics returns valid data from database"""
        result = analytics.get_instrument_metrics(days=30)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_get_instrument_metrics_all_fields_present(self):
        """Test that all instrument metric fields are present"""
        result = analytics.get_instrument_metrics(days=30)

        if len(result) > 0:
            instrument = result[0]
            required_fields = [
                'ticker',
                'asset_type',
                'trade_count',
                'total_quantity',
                'total_volume',
                'avg_trade_value',
                'min_price',
                'max_price',
                'unique_traders'
            ]
            for field in required_fields:
                self.assertIn(field, instrument, f"Missing field: {field}")

    def test_get_instrument_metrics_values_are_numeric(self):
        """Test that numeric instrument metric fields have correct types"""
        result = analytics.get_instrument_metrics(days=30)

        if len(result) > 0:
            instrument = result[0]
            self.assertIsInstance(instrument['trade_count'], (int, float))
            self.assertIsInstance(instrument['total_quantity'], (int, float))
            self.assertIsInstance(instrument['total_volume'], (int, float))
            self.assertIsInstance(instrument['unique_traders'], (int, float))

    def test_get_instrument_metrics_logical_constraints(self):
        """Test that instrument metric values satisfy logical constraints"""
        result = analytics.get_instrument_metrics(days=30)

        for instrument in result:
            # Min price should be <= max price
            if instrument['min_price'] > 0 and instrument['max_price'] > 0:
                self.assertLessEqual(instrument['min_price'], instrument['max_price'])

            # Volumes should be non-negative
            self.assertGreaterEqual(instrument['total_volume'], 0)
            self.assertGreaterEqual(instrument['avg_trade_value'], 0)

            # Trade count and traders should match
            self.assertGreaterEqual(instrument['trade_count'], instrument['unique_traders'])

    def test_get_timeseries_metrics_returns_valid_data(self):
        """Test that get_timeseries_metrics returns valid time-series data"""
        result = analytics.get_timeseries_metrics(days=30, granularity='daily')

        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)

    def test_get_timeseries_metrics_all_fields_present(self):
        """Test that all timeseries metric fields are present"""
        result = analytics.get_timeseries_metrics(days=30, granularity='daily')

        if len(result) > 0:
            entry = result[0]
            required_fields = [
                'period',
                'trade_count',
                'total_volume',
                'avg_trade_value',
                'active_clients',
                'instruments_traded'
            ]
            for field in required_fields:
                self.assertIn(field, entry, f"Missing field: {field}")

    def test_get_timeseries_metrics_with_different_granularities(self):
        """Test that timeseries metrics work with different granularities"""
        daily = analytics.get_timeseries_metrics(days=30, granularity='daily')
        weekly = analytics.get_timeseries_metrics(days=30, granularity='weekly')
        monthly = analytics.get_timeseries_metrics(days=30, granularity='monthly')

        self.assertIsNotNone(daily)
        self.assertIsNotNone(weekly)
        self.assertIsNotNone(monthly)

        # More granular periods should have more entries
        self.assertGreaterEqual(len(daily), len(weekly))
        self.assertGreaterEqual(len(weekly), len(monthly))

    def test_get_timeseries_metrics_chronological_order(self):
        """Test that timeseries data is in chronological order"""
        result = analytics.get_timeseries_metrics(days=30, granularity='daily')

        if len(result) > 1:
            for i in range(len(result) - 1):
                self.assertLessEqual(result[i]['period'], result[i + 1]['period'])

    def test_get_client_segments_returns_valid_data(self):
        """Test that get_client_segments returns valid segmentation data"""
        result = analytics.get_client_segments(days=30)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertIn('summary', result)
        self.assertIn('detailed', result)

    def test_get_client_segments_summary_has_required_fields(self):
        """Test that segment summary has all required fields"""
        result = analytics.get_client_segments(days=30)

        if len(result['summary']) > 0:
            segment = result['summary'][0]
            required_fields = ['segment', 'client_count', 'total_volume', 'total_trades', 'avg_trade_value']
            for field in required_fields:
                self.assertIn(field, segment, f"Missing field: {field}")

    def test_get_client_segments_detailed_has_required_fields(self):
        """Test that detailed client data has all required fields"""
        result = analytics.get_client_segments(days=30)

        if len(result['detailed']) > 0:
            client = result['detailed'][0]
            required_fields = [
                'client_id',
                'first_name',
                'last_name',
                'segment',
                'trade_count',
                'total_volume',
                'avg_trade_value',
                'instruments_traded'
            ]
            for field in required_fields:
                self.assertIn(field, client, f"Missing field: {field}")

    def test_get_client_segments_categorization(self):
        """Test that clients are correctly categorized into segments"""
        result = analytics.get_client_segments(days=30)

        valid_segments = ['Inactive', 'Casual', 'Regular', 'High-Value']
        for client in result['detailed']:
            self.assertIn(client['segment'], valid_segments, f"Invalid segment: {client['segment']}")

    def test_get_instrument_details_returns_valid_data(self):
        """Test that get_instrument_details returns valid detailed data"""
        # First, get a list of available instruments
        instruments = analytics.get_instrument_metrics(days=30)
        
        if len(instruments) > 0:
            ticker = instruments[0]['ticker']
            result = analytics.get_instrument_details(ticker=ticker, days=30)

            self.assertIsNotNone(result)
            self.assertIsInstance(result, dict)
            self.assertIn('instrument', result)
            self.assertIn('top_traders', result)
            self.assertIn('daily_trend', result)

    def test_get_instrument_details_instrument_has_required_fields(self):
        """Test that instrument details have all required fields"""
        instruments = analytics.get_instrument_metrics(days=30)
        
        if len(instruments) > 0:
            ticker = instruments[0]['ticker']
            result = analytics.get_instrument_details(ticker=ticker, days=30)

            instrument = result['instrument']
            required_fields = [
                'ticker',
                'asset_type',
                'trade_count',
                'total_quantity',
                'total_volume',
                'avg_trade_value',
                'min_price',
                'max_price',
                'unique_traders'
            ]
            for field in required_fields:
                self.assertIn(field, instrument, f"Missing field: {field}")

    def test_get_instrument_details_top_traders_structure(self):
        """Test that top traders data is properly structured"""
        instruments = analytics.get_instrument_metrics(days=30)
        
        if len(instruments) > 0:
            ticker = instruments[0]['ticker']
            result = analytics.get_instrument_details(ticker=ticker, days=30)

            self.assertIsInstance(result['top_traders'], list)
            self.assertLessEqual(len(result['top_traders']), 10)

            if len(result['top_traders']) > 0:
                trader = result['top_traders'][0]
                required_fields = ['client_id', 'first_name', 'last_name', 'trade_count', 'volume']
                for field in required_fields:
                    self.assertIn(field, trader, f"Missing field: {field}")

    def test_get_instrument_details_daily_trend_structure(self):
        """Test that daily trend data is properly structured"""
        instruments = analytics.get_instrument_metrics(days=30)
        
        if len(instruments) > 0:
            ticker = instruments[0]['ticker']
            result = analytics.get_instrument_details(ticker=ticker, days=30)

            self.assertIsInstance(result['daily_trend'], list)

            if len(result['daily_trend']) > 0:
                trend = result['daily_trend'][0]
                required_fields = ['date', 'trade_count', 'daily_volume']
                for field in required_fields:
                    self.assertIn(field, trend, f"Missing field: {field}")


if __name__ == "__main__":
    unittest.main()
