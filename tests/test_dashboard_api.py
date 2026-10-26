"""Dashboard contract tests; database access is mocked unless explicitly requested."""
import os
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
from fastapi.testclient import TestClient

from analytics_statistics import analytics, api, stock_statistics as stats


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)

    def test_average_cost_with_sell_then_buy(self):
        quantity, average = stats._average_cost([
            dict(quantity=10, price=100, order_type='BUY'),
            dict(quantity=5, price=200, order_type='SELL'),
            dict(quantity=5, price=200, order_type='BUY'),
        ])
        self.assertEqual(quantity, 10)
        self.assertEqual(average, 150)

    def test_incomplete_history_is_not_fabricated(self):
        self.assertEqual(stats._average_cost([
            dict(quantity=1, price=100, order_type='SELL')]), (None, None))

    @patch.object(stats, 'get_warehouse_connection')
    @patch.object(stats.pd, 'read_sql')
    def test_holdings_valuation_and_incomplete_basis(self, read, connection):
        read.side_effect = [pd.DataFrame([
            dict(ticker='AAPL', quantity=5, asset_type='STOCK', current_price=120,
                 price_timestamp='2026-10-23'),
            dict(ticker='BTC', quantity=1, asset_type='CRYPTO', current_price=None,
                 price_timestamp=None),
        ]), pd.DataFrame([
            dict(ticker='AAPL', quantity=10, price=100, order_type='BUY'),
            dict(ticker='AAPL', quantity=5, price=110, order_type='SELL'),
        ])]
        rows = stats.get_client_holdings(3)
        self.assertEqual(rows[0]['unrealized_gain'], 100)
        self.assertEqual(rows[0]['market_value'], 600)
        self.assertIsNone(rows[1]['unrealized_gain'])
        self.assertEqual(rows[1]['category'], 'bitcoin')
        self.assertEqual(read.call_args_list[0].kwargs['params'], (3,))
        self.assertEqual(read.call_args_list[1].kwargs['params'], (3,))
        connection.return_value.close.assert_called_once()

    @patch.object(stats, 'get_client_holdings')
    def test_top_five_sorted_and_unpriced_excluded(self, holdings):
        holdings.return_value = [dict(ticker=str(i), unrealized_gain=i) for i in range(7)]
        holdings.return_value += [dict(ticker='missing', unrealized_gain=None)]
        result = stats.get_top_client_holdings(3)
        self.assertEqual([h['unrealized_gain'] for h in result['holdings']], [6, 5, 4, 3, 2])
        self.assertEqual(result['excluded_tickers'], ['missing'])

    @patch.object(stats, 'get_client_holdings')
    def test_allocation_percentages_and_missing_quotes(self, holdings):
        holdings.return_value = [
            dict(ticker='AAPL', category='stock', market_value=600),
            dict(ticker='BTC', category='bitcoin', market_value=300),
            dict(ticker='ETH', category='crypto', market_value=100),
            dict(ticker='MISSING', category='stock', market_value=None),
        ]
        result = stats.get_client_allocation(3)
        self.assertEqual([r['percentage'] for r in result['allocation']], [60, 10, 30, 0])
        self.assertEqual(result['unpriced_tickers'], ['MISSING'])

    def test_filter_values_are_bound_and_end_date_inclusive(self):
        sql, params = analytics._order_conditions(
            ticker="X'; DROP TABLE orders;--", client_id=3,
            start_date=date(2026, 10, 1), end_date=date(2026, 10, 23))
        self.assertNotIn('DROP', sql)
        self.assertIn(date(2026, 10, 24), params)
        self.assertIn(3, params)

    @patch.object(api, 'get_top_client_holdings', return_value={'holdings': []})
    def test_client_scope_passed(self, holdings):
        result = self.client.get('/api/analytics/clients/3/holdings/top-gainers')
        self.assertEqual(result.status_code, 200)
        holdings.assert_called_once_with(3)
        self.assertEqual(result.headers['cache-control'], 'no-store')

    @patch.object(api, 'get_client_allocation')
    def test_allocation_json_and_png(self, allocation):
        allocation.return_value = dict(total_market_value=100, unpriced_tickers=[],
            allocation=[dict(category='stock', market_value=100, percentage=100)])
        for suffix in ('', '/graph'):
            response = self.client.get('/api/analytics/clients/3/allocation' + suffix)
            self.assertEqual(response.status_code, 200)
            if suffix:
                self.assertTrue(response.content.startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertEqual(response.headers['content-type'], 'image/png')
        allocation.return_value = dict(total_market_value=0, unpriced_tickers=[], allocation=[])
        self.assertEqual(self.client.get('/api/analytics/clients/3/allocation/graph').status_code, 200)

    @patch.object(api, 'get_order_status_metrics')
    def test_order_status_chart(self, status):
        status.return_value = [dict(cancelled_orders=2, pending_orders=3, fulfilled_orders=5)]
        response = self.client.get('/api/analytics/clients/3/order-status/graph?days=7')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'\x89PNG'))
        status.assert_called_once_with(days=7, client_id=3)
        status.return_value = []
        self.assertEqual(self.client.get('/api/analytics/clients/3/order-status/graph').status_code, 404)

    def test_input_validation(self):
        for path in (
            '/api/analytics/orders?days=0',
            '/api/analytics/orders?client_id=-1',
            '/api/analytics/orders?limit=501',
            '/api/analytics/trends?granularity=yearly',
            '/api/analytics/clients/0/allocation',
        ):
            self.assertEqual(self.client.get(path).status_code, 422, path)
        self.assertEqual(self.client.get(
            '/api/analytics/orders?start_date=2026-10-23&end_date=2026-10-01').status_code, 400)

    @patch.object(api, 'calculate_stock_metrics', return_value=None)
    def test_stock_missing_data_remains_404(self, metrics):
        self.assertEqual(self.client.get('/stock_statistics/AAPL').status_code, 404)

    @patch.object(stats, 'get_warehouse_connection')
    @patch.object(stats.pd, 'read_sql', return_value=pd.DataFrame())
    def test_price_query_matches_warehouse_timestamp(self, read, connection):
        stats.fetch_prices_by_ticker_and_date('AAPL', pd.Timestamp('2026-10-23'))
        self.assertIn('recorded_at AS quote_timestamp', read.call_args.args[0])
        self.assertIn('recorded_at >= %s', read.call_args.args[0])
        self.assertEqual(read.call_args.kwargs['params'][0], 'AAPL')

    @patch.object(api, 'get_filtered_orders', return_value={'orders': [], 'total_orders': 0})
    def test_filtered_orders(self, orders):
        response = self.client.get('/api/analytics/orders?ticker=AAPL&client_id=3&limit=10&offset=5')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(orders.call_args.kwargs['client_id'], 3)
        self.assertEqual(orders.call_args.kwargs['ticker'], 'AAPL')
        self.assertEqual(orders.call_args.kwargs['offset'], 5)

    @patch.object(api, 'get_trading_volume_metrics', return_value={'total_trading_volume': 100})
    def test_volume_defaults_to_fulfilled(self, volume):
        self.assertEqual(self.client.get('/api/analytics/trading-volume').status_code, 200)
        self.assertEqual(volume.call_args.kwargs['order_status'], 'FULFILLED')

    @patch.object(api, 'get_client_activity_trend', return_value=[])
    def test_client_activity(self, trend):
        self.assertEqual(self.client.get('/api/analytics/client-activity?granularity=weekly').status_code, 200)
        self.assertEqual(trend.call_args.kwargs['granularity'], 'weekly')

    @patch.object(api, 'get_instrument_metrics')
    def test_existing_instrument_endpoint_ranks_activity(self, instruments):
        instruments.return_value = [dict(ticker='AAPL', trade_count=2), dict(ticker='BTC', trade_count=5)]
        response = self.client.get('/api/analytics/by-instrument?sort_by=trade_count&limit=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data'][0]['ticker'], 'BTC')

    @patch.object(api, 'get_timeseries_metrics')
    def test_existing_trends_and_graph_with_filters(self, trend):
        trend.return_value = [dict(period='2026-10-23', trade_count=2, total_volume=100)]
        for suffix in ('', '/graph'):
            response = self.client.get('/api/analytics/trends' + suffix + '?ticker=AAPL&client_id=3')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(trend.call_args.kwargs['client_id'], 3)
        trend.return_value = []
        self.assertEqual(self.client.get('/api/analytics/trends').json()['data'], [])


@unittest.skipUnless(os.environ.get('RUN_DASHBOARD_INTEGRATION') == '1', 'Opt-in warehouse checks')
class DashboardWarehouseTests(unittest.TestCase):
    def test_live_endpoints(self):
        client = TestClient(api.app)
        from shared.database_connections import get_warehouse_connection
        with get_warehouse_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT client_id FROM clients ORDER BY client_id LIMIT 1')
                first = cursor.fetchone()
        self.assertIsNotNone(first, 'Need at least one warehouse client')
        client_id = first[0]
        paths = [
            f'/api/analytics/clients/{client_id}/holdings/top-gainers',
            f'/api/analytics/clients/{client_id}/allocation',
            f'/api/analytics/clients/{client_id}/allocation/graph',
            f'/api/analytics/clients/{client_id}/order-status/graph',
            '/api/analytics/orders', '/api/analytics/orders?offset=100000000',
            '/api/analytics/trading-volume', '/api/analytics/client-activity',
            '/api/analytics/by-instrument?sort_by=trade_count&limit=1',
            '/api/analytics/trends', '/api/analytics/trends/graph',
            f'/api/analytics/order-status?client_id={client_id}',
        ]
        for path in paths:
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 200, response.text[:300])
            response = client.get('/stock_statistics/AAPL')
            self.assertIn(response.status_code, (200, 404), response.text)


if __name__ == '__main__':
    unittest.main()