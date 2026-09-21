from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
STATISTICS_PATH = ROOT / "stock_statistics.py"
SPEC = spec_from_file_location("project_statistics", STATISTICS_PATH)
statistics_module = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(statistics_module)


class StatisticsUnitTests(unittest.TestCase):
    def setUp(self):
        self.prices_df = pd.DataFrame(
            [
                {
                    "quote_timestamp": "2026-09-18T09:31:00-05:00",
                    "price": Decimal("101.25"),
                    "bid_price": Decimal("101.10"),
                    "bid_size": 150,
                    "ask_price": Decimal("101.30"),
                    "ask_size": 200,
                },
                {
                    "quote_timestamp": "2026-09-18T15:59:00-05:00",
                    "price": Decimal("103.50"),
                    "bid_price": Decimal("103.40"),
                    "bid_size": 120,
                    "ask_price": Decimal("103.55"),
                    "ask_size": 90,
                },
                {
                    "quote_timestamp": "2026-09-18T12:15:00-05:00",
                    "price": Decimal("99.95"),
                    "bid_price": Decimal("99.90"),
                    "bid_size": 80,
                    "ask_price": Decimal("100.05"),
                    "ask_size": 110,
                },
            ]
        )

    def test_find_open_returns_earliest_price(self):
        result = statistics_module.find_open(self.prices_df)

        self.assertEqual(result, Decimal("101.30"))

    def test_find_close_returns_latest_price(self):
        result = statistics_module.find_close(self.prices_df)

        self.assertEqual(result, Decimal("103.55"))

    def test_find_last_bid_price_and_size_of_day_returns_latest_bid_tuple(self):
        result = statistics_module.find_last_bid_price_and_size_of_day(self.prices_df)

        self.assertEqual(result, (Decimal("103.40"), 120))

    def test_find_last_ask_price_and_size_of_day_returns_latest_ask_tuple(self):
        result = statistics_module.find_last_ask_price_and_size_of_day(self.prices_df)

        self.assertEqual(result, (Decimal("103.55"), 90))

    def test_find_day_range_returns_min_and_max_ask_prices(self):
        result = statistics_module.find_day_range(self.prices_df)

        self.assertEqual(result, (Decimal("100.05"), Decimal("103.55")))

    def test_find_open_returns_none_for_empty_dataframe(self):
        empty_df = pd.DataFrame(columns=["quote_timestamp", "ask_price"])

        result = statistics_module.find_open(empty_df)

        self.assertIsNone(result)

    def test_find_close_returns_none_when_ask_price_missing(self):
        malformed_df = self.prices_df.drop(columns=["ask_price"])

        result = statistics_module.find_close(malformed_df)

        self.assertIsNone(result)

    def test_find_last_bid_price_and_size_of_day_returns_none_tuple_when_columns_missing(self):
        malformed_df = self.prices_df.drop(columns=["bid_price", "bid_size"])

        result = statistics_module.find_last_bid_price_and_size_of_day(malformed_df)

        self.assertEqual(result, (None, None))

    def test_find_last_ask_price_and_size_of_day_returns_none_tuple_for_empty_dataframe(self):
        empty_df = pd.DataFrame(columns=["quote_timestamp", "ask_price", "ask_size"])

        result = statistics_module.find_last_ask_price_and_size_of_day(empty_df)

        self.assertEqual(result, (None, None))

    def test_find_day_range_returns_none_tuple_when_ask_price_missing(self):
        malformed_df = self.prices_df.drop(columns=["ask_price"])

        result = statistics_module.find_day_range(malformed_df)

        self.assertEqual(result, (None, None))

    def test_fetch_instruments_data_returns_json_records(self):
        mock_conn = Mock()
        instruments_df = pd.DataFrame([{"instrument_id": 1, "ticker": "AAPL"}])

        with patch.object(statistics_module, "get_connection", return_value=mock_conn), patch.object(
            statistics_module.pd, "read_sql", return_value=instruments_df
        ):
            result = statistics_module.fetch_instruments_data()

        self.assertEqual(result, instruments_df.to_json(orient="records"))
        mock_conn.close.assert_called_once()

    def test_fetch_user_transactions_passes_client_id_and_returns_json(self):
        mock_conn = Mock()
        transactions_df = pd.DataFrame([{"transaction_id": 10, "first_name": "Ada", "amount": 12.5}])

        with patch.object(statistics_module, "get_connection", return_value=mock_conn), patch.object(
            statistics_module.pd, "read_sql", return_value=transactions_df
        ) as mock_read_sql:
            result = statistics_module.fetch_user_transactions(3)

        self.assertEqual(result, transactions_df.to_json(orient="records"))
        mock_read_sql.assert_called_once()
        self.assertEqual(mock_read_sql.call_args.kwargs["params"], (3,))
        mock_conn.close.assert_called_once()

    def test_fetch_prices_data_returns_json_records(self):
        mock_conn = Mock()
        prices_df = pd.DataFrame([{"ticker": "AAPL", "ask_price": Decimal("332.72")}])

        with patch.object(statistics_module, "get_connection", return_value=mock_conn), patch.object(
            statistics_module.pd, "read_sql", return_value=prices_df
        ):
            result = statistics_module.fetch_prices_data()

        self.assertEqual(result, prices_df.to_json(orient="records"))
        mock_conn.close.assert_called_once()

    def test_fetch_prices_by_ticker_and_date_returns_dataframe_for_day_window(self):
        mock_conn = Mock()
        prices_df = pd.DataFrame([{"ticker": "AAPL", "ask_price": Decimal("332.72")}])
        timestamp = pd.Timestamp("2026-09-18 14:42:32", tz="America/Chicago")

        with patch.object(statistics_module, "get_connection", return_value=mock_conn), patch.object(
            statistics_module.pd, "read_sql", return_value=prices_df
        ) as mock_read_sql:
            result = statistics_module.fetch_prices_by_ticker_and_date("AAPL", timestamp)

        self.assertTrue(result.equals(prices_df))
        self.assertEqual(mock_read_sql.call_args.kwargs["params"][0], "AAPL")
        self.assertEqual(
            mock_read_sql.call_args.kwargs["params"][1],
            pd.Timestamp("2026-09-18 00:00:00", tz="America/Chicago"),
        )
        self.assertEqual(
            mock_read_sql.call_args.kwargs["params"][2],
            pd.Timestamp("2026-09-19 00:00:00", tz="America/Chicago"),
        )
        mock_conn.close.assert_called_once()

    def test_calculate_stock_metrics_returns_none_when_today_prices_missing(self):
        with patch.object(statistics_module, "fetch_prices_by_ticker_and_date", side_effect=[None, None]):
            result = statistics_module.calculate_stock_metrics("AAPL")

        self.assertIsNone(result)

    def test_calculate_stock_metrics_propagates_helper_failures_as_none_fields(self):
        today_prices = self.prices_df.copy()
        yesterday_prices = self.prices_df.copy()

        with patch.object(
            statistics_module,
            "fetch_prices_by_ticker_and_date",
            side_effect=[today_prices, yesterday_prices],
        ), patch.object(statistics_module, "find_open", return_value=None), patch.object(
            statistics_module, "find_close", return_value=None
        ), patch.object(
            statistics_module, "find_last_bid_price_and_size_of_day", return_value=(None, None)
        ), patch.object(
            statistics_module, "find_last_ask_price_and_size_of_day", return_value=(None, None)
        ), patch.object(statistics_module, "find_day_range", return_value=(None, None)):
            result = statistics_module.calculate_stock_metrics("AAPL")

        self.assertEqual(
            result,
            {
                "ticker": "AAPL",
                "open": None,
                "prev_close": None,
                "bid_price": None,
                "bid_size": None,
                "ask_price": None,
                "ask_size": None,
                "day_low": None,
                "day_high": None,
            },
        )


if __name__ == "__main__":
    unittest.main()