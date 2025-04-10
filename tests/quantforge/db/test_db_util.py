import unittest
from datetime import date, datetime
import pandas as pd

from quantforge.db.db_util import (
    fetch_historical_options_data,
    fetch_historical_ticker_data,
)


class TestDbUtil(unittest.TestCase):
    def test_fetch_historical_options_data_returns_dataframe(self):
        # Test with a date range that should contain data
        start_date = date(2023, 1, 1)
        end_date = datetime.now().date()
        df = fetch_historical_options_data("AAPL", start_date, end_date)

        # Verify it returns a DataFrame
        self.assertIsInstance(df, pd.DataFrame)

        # Verify it has the expected columns
        expected_columns = [
            "option_type",
            "strike",
            "last_price",
            "bid",
            "ask",
            "volume",
            "open_interest",
            "implied_volatility",
            "last_updated",
        ]
        self.assertTrue(all(column in df.columns for column in expected_columns))

        # Verify expiration_date is the index
        self.assertEqual(df.index.name, "expiration_date")

    def test_fetch_historical_options_data_date_range(self):
        # Test with a specific date range
        start_date = date(2023, 1, 1)
        end_date = datetime.now().date()
        df = fetch_historical_options_data("MSFT", start_date, end_date)

        # Verify all data is within the date range (using last_updated column)
        self.assertTrue(all(pd.to_datetime(df["last_updated"]).dt.date >= start_date))
        self.assertTrue(all(pd.to_datetime(df["last_updated"]).dt.date <= end_date))

    def test_fetch_historical_options_data_no_data(self):
        # Test with a date range that should not contain data (far past)
        start_date = date(1990, 1, 1)
        end_date = date(1990, 12, 31)

        # Should raise ValueError
        with self.assertRaises(ValueError):
            fetch_historical_options_data("AAPL", start_date, end_date)

    def test_fetch_historical_ticker_data_returns_dataframe(self):
        # Test with a date range that should contain data
        start_date = date(2023, 1, 1)
        end_date = datetime.now().date()
        df = fetch_historical_ticker_data("AAPL", start_date, end_date)

        # Verify it returns a DataFrame
        self.assertIsInstance(df, pd.DataFrame)

        # Verify it has the expected columns
        expected_columns = ["open", "high", "low", "close", "volume"]
        self.assertTrue(all(column in df.columns for column in expected_columns))

        # Verify timestamp is the index
        self.assertEqual(df.index.name, "timestamp")

    def test_fetch_historical_ticker_data_date_range(self):
        # Test with a specific date range
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        df = fetch_historical_ticker_data("MSFT", start_date, end_date)

        # Verify all data is within the date range
        self.assertTrue(all(df.index.date >= start_date))
        self.assertTrue(all(df.index.date <= end_date))

    def test_fetch_historical_ticker_data_no_data(self):
        # Test with a date range that should not contain data (far past)
        start_date = date(1800, 1, 1)
        end_date = date(1800, 12, 31)

        # Should raise ValueError
        with self.assertRaises(ValueError):
            fetch_historical_ticker_data("AAPL", start_date, end_date)


if __name__ == "__main__":
    unittest.main()
