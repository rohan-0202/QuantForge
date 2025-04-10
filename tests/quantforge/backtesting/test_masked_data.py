import unittest
import pandas as pd
import numpy as np
from datetime import date

from quantforge.backtesting.masked_data import create_masked_data
from quantforge.strategies.data_requirement import DataRequirement
from quantforge.db.df_columns import TIMESTAMP, LAST_UPDATED


class TestMaskedData(unittest.TestCase):
    def setUp(self):
        # Create test dates
        self.cutoff_date = date(2023, 1, 15)
        self.before_dates = [
            date(2023, 1, 10),
            date(2023, 1, 5),
            date(2022, 12, 20),
        ]
        self.after_dates = [
            date(2023, 1, 20),
            date(2023, 2, 1),
        ]

        # Convert to pandas timestamps in UTC (matching db_util.py's format)
        self.before_timestamps = [pd.Timestamp(d, tz="UTC") for d in self.before_dates]
        self.after_timestamps = [pd.Timestamp(d, tz="UTC") for d in self.after_dates]
        all_timestamps = self.before_timestamps + self.after_timestamps

        # TICKER data with timestamp index in UTC (matching db_util.fetch_historical_ticker_data)
        ticker_data = {
            "open": np.random.rand(len(all_timestamps)),
            "high": np.random.rand(len(all_timestamps)),
            "low": np.random.rand(len(all_timestamps)),
            "close": np.random.rand(len(all_timestamps)),
            "volume": np.random.randint(1000, 10000, len(all_timestamps)),
        }
        self.ticker_data = pd.DataFrame(
            ticker_data, index=pd.DatetimeIndex(all_timestamps, name=TIMESTAMP)
        )

        # OPTIONS data with last_updated column in UTC (matching db_util.fetch_historical_options_data)
        options_data = {
            "option_type": ["call"] * len(all_timestamps),
            "strike": [100] * len(all_timestamps),
            "last_price": np.random.rand(len(all_timestamps)),
            "bid": np.random.rand(len(all_timestamps)),
            "ask": np.random.rand(len(all_timestamps)),
            "volume": np.random.randint(1000, 10000, len(all_timestamps)),
            "open_interest": np.random.randint(1000, 10000, len(all_timestamps)),
            "implied_volatility": np.random.rand(len(all_timestamps)),
            LAST_UPDATED: all_timestamps,
        }
        self.options_data = pd.DataFrame(options_data)

        # Invalid TICKER data without proper index
        self.invalid_ticker_data = pd.DataFrame(
            {"close": np.random.rand(len(all_timestamps)), "some_date": all_timestamps}
        )

        # Invalid OPTIONS data without last_updated column
        self.invalid_options_data = pd.DataFrame(
            {
                "strike": [100] * len(all_timestamps),
                "bid": np.random.rand(len(all_timestamps)),
                "ask": np.random.rand(len(all_timestamps)),
            }
        )

        # Other type of data
        self.other_data = pd.DataFrame(
            {
                "feature1": np.random.rand(len(all_timestamps)),
                "feature2": np.random.rand(len(all_timestamps)),
            }
        )

    def test_ticker_data_masking(self):
        """Test masking of TICKER data works correctly"""
        input_data = {"AAPL": {DataRequirement.TICKER: self.ticker_data}}

        masked_data = create_masked_data(input_data, self.cutoff_date)

        # Verify only data before cutoff is included
        result_df = masked_data["AAPL"][DataRequirement.TICKER]
        self.assertEqual(len(result_df), len(self.before_timestamps))
        self.assertTrue(all(idx.date() <= self.cutoff_date for idx in result_df.index))

    def test_options_data_masking(self):
        """Test masking of OPTIONS data works correctly"""
        input_data = {"AAPL": {DataRequirement.OPTIONS: self.options_data}}

        masked_data = create_masked_data(input_data, self.cutoff_date)

        # Verify only data before cutoff is included
        result_df = masked_data["AAPL"][DataRequirement.OPTIONS]
        self.assertEqual(len(result_df), len(self.before_timestamps))
        self.assertTrue(
            all(ts.date() <= self.cutoff_date for ts in result_df[LAST_UPDATED])
        )

    def test_multiple_data_requirements(self):
        """Test masking works with multiple data requirements for the same ticker"""
        input_data = {
            "AAPL": {
                DataRequirement.TICKER: self.ticker_data,
                DataRequirement.OPTIONS: self.options_data,
            }
        }

        masked_data = create_masked_data(input_data, self.cutoff_date)

        # Verify TICKER data is masked correctly
        ticker_result = masked_data["AAPL"][DataRequirement.TICKER]
        self.assertEqual(len(ticker_result), len(self.before_timestamps))

        # Verify OPTIONS data is masked correctly
        options_result = masked_data["AAPL"][DataRequirement.OPTIONS]
        self.assertEqual(len(options_result), len(self.before_timestamps))

    def test_multiple_tickers(self):
        """Test masking works with multiple tickers"""
        input_data = {
            "AAPL": {DataRequirement.TICKER: self.ticker_data},
            "MSFT": {DataRequirement.OPTIONS: self.options_data},
        }

        masked_data = create_masked_data(input_data, self.cutoff_date)

        # Verify AAPL ticker data is masked correctly
        aapl_result = masked_data["AAPL"][DataRequirement.TICKER]
        self.assertEqual(len(aapl_result), len(self.before_timestamps))

        # Verify MSFT options data is masked correctly
        msft_result = masked_data["MSFT"][DataRequirement.OPTIONS]
        self.assertEqual(len(msft_result), len(self.before_timestamps))

    def test_invalid_ticker_data(self):
        """Test that invalid TICKER data raises an error"""
        input_data = {"AAPL": {DataRequirement.TICKER: self.invalid_ticker_data}}

        with self.assertRaises(ValueError):
            create_masked_data(input_data, self.cutoff_date)

    def test_invalid_options_data(self):
        """Test that invalid OPTIONS data raises an error"""
        input_data = {"AAPL": {DataRequirement.OPTIONS: self.invalid_options_data}}

        with self.assertRaises(ValueError):
            create_masked_data(input_data, self.cutoff_date)

    def test_other_data_requirement(self):
        """Test that other data requirements raise NotImplementedError"""
        input_data = {"AAPL": {"OTHER_TYPE": self.other_data}}

        with self.assertRaises(NotImplementedError):
            create_masked_data(input_data, self.cutoff_date)

    def test_empty_input(self):
        """Test with empty input data"""
        input_data = {}
        masked_data = create_masked_data(input_data, self.cutoff_date)
        self.assertEqual(masked_data, {})

    def test_cutoff_date_equals_max_date(self):
        """Test when cutoff date equals the maximum date in the data"""
        max_date = max(
            timestamp.date()
            for timestamp in (self.before_timestamps + self.after_timestamps)
        )

        input_data = {"AAPL": {DataRequirement.TICKER: self.ticker_data}}

        masked_data = create_masked_data(input_data, max_date)
        result_df = masked_data["AAPL"][DataRequirement.TICKER]

        # All data should be included for this cutoff date
        expected_count = sum(
            1 for ts in self.ticker_data.index if ts.date() <= max_date
        )
        self.assertEqual(len(result_df), expected_count)


if __name__ == "__main__":
    unittest.main()
