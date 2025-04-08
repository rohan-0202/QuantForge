import unittest
import pandas as pd

from quantforge.backtesting.backtest_dataloader import load_requirement_data
from quantforge.strategies.data_requirement import DataRequirement
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.assetclass import AssetClass
from quantforge.db.df_columns import (
    OPEN,
    HIGH,
    LOW,
    CLOSE,
    STRIKE,
    OPTION_TYPE,  # Options data columns
)


class TestBacktestDataloader(unittest.TestCase):
    def setUp(self):
        self.ticker = "AAPL"  # Using a common stock for testing
        self.tradeable_item = TradeableItem(
            id=self.ticker, asset_class=AssetClass.EQUITY
        )
        self.lookback_days = 30  # Testing with 30 days of history

    def test_load_requirement_data_ticker(self):
        """Test loading historical ticker data."""
        data = load_requirement_data(
            DataRequirement.TICKER, self.lookback_days, self.tradeable_item
        )

        # Verify the data is a DataFrame
        self.assertIsInstance(data, pd.DataFrame)

        # Verify the data is not empty
        self.assertFalse(data.empty)

        # Verify the DataFrame has the expected columns for historical data
        expected_columns = [OPEN, HIGH, LOW, CLOSE]
        for col in expected_columns:
            self.assertIn(col, data.columns)

    def test_load_requirement_data_options(self):
        """Test loading options data."""
        data = load_requirement_data(
            DataRequirement.OPTIONS, self.lookback_days, self.tradeable_item
        )

        # Verify the data is a DataFrame
        self.assertIsInstance(data, pd.DataFrame)
        self.assertFalse(data.empty)

        # Verify the DataFrame has expected columns for options data
        expected_columns = [STRIKE, OPTION_TYPE]
        for col in expected_columns:
            self.assertIn(col, data.columns)

    def test_load_requirement_data_unsupported(self):
        """Test that unsupported data requirements raise NotImplementedError."""

        # Create a custom enum value for testing
        class CustomDataRequirement:
            UNSUPPORTED = "UNSUPPORTED"

        with self.assertRaises(NotImplementedError):
            load_requirement_data(
                CustomDataRequirement.UNSUPPORTED,
                self.lookback_days,
                self.tradeable_item,
            )


if __name__ == "__main__":
    unittest.main()
