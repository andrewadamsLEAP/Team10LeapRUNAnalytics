from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import patch
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
STATISTICS_PATH = ROOT / "stock_statistics.py"
SPEC = spec_from_file_location("project_statistics", STATISTICS_PATH)
statistics_module = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(statistics_module)


class StatisticsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        conn = None
        try:
            conn = statistics_module.get_connection()
            query = """
            SELECT ticker, date_trunc('day', quote_timestamp) AS quote_day
            FROM prices
            ORDER BY quote_timestamp DESC
            LIMIT 1
            """
            latest_row = pd.read_sql(query, conn)
        except Exception as exc:
            raise unittest.SkipTest(f"Database unavailable for integration test: {exc}")
        finally:
            if conn is not None:
                conn.close()

        if latest_row.empty:
            raise unittest.SkipTest("Prices table is empty; integration test skipped")

        cls.ticker = latest_row.iloc[0]["ticker"]
        cls.quote_day = pd.Timestamp(latest_row.iloc[0]["quote_day"])

    def test_calculate_stock_metrics_returns_metrics_from_database(self):
        if self.quote_day.tzinfo is None:
            mocked_now = self.quote_day.tz_localize("America/Chicago") + pd.Timedelta(hours=12)
        else:
            mocked_now = self.quote_day.tz_convert("America/Chicago") + pd.Timedelta(hours=12)

        with patch.object(statistics_module.pd.Timestamp, "now", return_value=mocked_now):
            metrics = statistics_module.calculate_stock_metrics(self.ticker)

        print({"quote_day": str(self.quote_day), "metrics": metrics})

        self.assertIsInstance(metrics, dict)
        self.assertEqual(metrics["ticker"], self.ticker)
        self.assertIn("open", metrics)
        self.assertIn("prev_close", metrics)
        self.assertIn("bid_price", metrics)
        self.assertIn("bid_size", metrics)
        self.assertIn("ask_price", metrics)
        self.assertIn("ask_size", metrics)
        self.assertIn("day_low", metrics)
        self.assertIn("day_high", metrics)
        self.assertIsNotNone(metrics["open"])


if __name__ == "__main__":
    unittest.main()