import unittest
from unittest import mock  # noqa
from datetime import date
import pandas as pd

from quantforge.backtesting.backtest_dataloader import load_requirement_data, load_data
from quantforge.backtesting.backtest_config import BacktestConfig
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.strategies.data_requirement import DataRequirement
from quantforge.qtypes.assetclass import AssetClass
from quantforge.strategies.simple_ticker_strategy import SimpleTickerDataStrategy


class CustomTickerStrategy(SimpleTickerDataStrategy):
    """Custom strategy extending SimpleTickerDataStrategy with configurable data requirements."""

    def __init__(self, portfolio: Portfolio, data_requirements=None, lookback_days=30):
        super().__init__(portfolio)
        self._data_requirements = data_requirements or [DataRequirement.TICKER]
        self._lookback_days = lookback_days

    def get_data_requirements(self):
        return self._data_requirements, self._lookback_days


class TestBacktestDataloader(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.aapl = TradeableItem("AAPL", asset_class=AssetClass.EQUITY)
        self.msft = TradeableItem("MSFT", asset_class=AssetClass.EQUITY)
        self.start_date = date(2023, 1, 1)
        self.end_date = date(2023, 1, 31)

    def test_load_requirement_data_ticker(self):
        """Test loading ticker data for a single stock."""
        df = load_requirement_data(
            DataRequirement.TICKER, self.aapl, self.start_date, self.end_date
        )

        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        # Check common ticker data columns
        self.assertTrue(
            all(col in df.columns for col in ["open", "high", "low", "close", "volume"])
        )

    @unittest.mock.patch(
        "quantforge.backtesting.backtest_dataloader.fetch_historical_options_data"
    )
    def test_load_requirement_data_options(self, mock_fetch_options):
        """Test loading options data for a single stock using a mock."""
        # Create a mock DataFrame to return
        mock_options_df = pd.DataFrame(
            {
                "strike": [100, 110, 120],
                "call_price": [5.0, 3.0, 1.5],
                "put_price": [2.0, 4.0, 6.0],
                "expiration_date": ["2023-02-01", "2023-02-01", "2023-02-01"],
            }
        )
        mock_fetch_options.return_value = mock_options_df

        df = load_requirement_data(
            DataRequirement.OPTIONS, self.aapl, self.start_date, self.end_date
        )

        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        # Check options data was correctly returned from mock
        self.assertTrue("strike" in df.columns)
        self.assertTrue(any(col in df.columns for col in ["call_price", "put_price"]))

    def test_load_requirement_data_invalid(self):
        """Test with invalid data requirement."""
        with self.assertRaises(NotImplementedError):
            load_requirement_data(
                "INVALID_REQUIREMENT", self.aapl, self.start_date, self.end_date
            )

    def test_load_data_single_stock_ticker(self):
        """Test loading data for a portfolio with a single stock and ticker requirement."""
        portfolio = Portfolio(
            start_date=self.start_date,
            allowed_tradeable_items=[self.aapl],
            initial_cash=10000,
        )

        strategy = CustomTickerStrategy(portfolio, [DataRequirement.TICKER])
        config = BacktestConfig(
            initial_portfolio=portfolio,
            strategy_name="CustomTickerStrategy",
            end_date=self.end_date,
        )

        data = load_data(config, strategy, portfolio)

        self.assertIsInstance(data, dict)
        self.assertIn(self.aapl, data)
        self.assertIn(DataRequirement.TICKER, data[self.aapl])
        self.assertIsInstance(data[self.aapl][DataRequirement.TICKER], pd.DataFrame)
        self.assertFalse(data[self.aapl][DataRequirement.TICKER].empty)

    def test_load_data_multiple_stocks_ticker(self):
        """Test loading data for a portfolio with multiple stocks."""
        portfolio = Portfolio(
            start_date=self.start_date,
            allowed_tradeable_items=[self.aapl, self.msft],
            initial_cash=10000,
        )

        strategy = CustomTickerStrategy(portfolio, [DataRequirement.TICKER])
        config = BacktestConfig(
            initial_portfolio=portfolio,
            strategy_name="CustomTickerStrategy",
            end_date=self.end_date,
        )

        data = load_data(config, strategy, portfolio)

        self.assertIsInstance(data, dict)
        self.assertIn(self.aapl, data)
        self.assertIn(self.msft, data)

        for ticker in [self.aapl, self.msft]:
            self.assertIn(DataRequirement.TICKER, data[ticker])
            self.assertIsInstance(data[ticker][DataRequirement.TICKER], pd.DataFrame)
            self.assertFalse(data[ticker][DataRequirement.TICKER].empty)

    @unittest.mock.patch(
        "quantforge.backtesting.backtest_dataloader.fetch_historical_options_data"
    )
    def test_load_data_multiple_requirements(self, mock_fetch_options):
        """Test loading data with multiple requirements (ticker and options)."""
        # Create a mock DataFrame to return for options data
        mock_options_df = pd.DataFrame(
            {
                "strike": [100, 110, 120],
                "call_price": [5.0, 3.0, 1.5],
                "put_price": [2.0, 4.0, 6.0],
                "expiration_date": ["2023-02-01", "2023-02-01", "2023-02-01"],
            }
        )
        mock_fetch_options.return_value = mock_options_df

        portfolio = Portfolio(
            start_date=self.start_date,
            allowed_tradeable_items=[self.aapl],
            initial_cash=10000,
        )

        strategy = CustomTickerStrategy(
            portfolio, [DataRequirement.TICKER, DataRequirement.OPTIONS]
        )
        config = BacktestConfig(
            initial_portfolio=portfolio,
            strategy_name="CustomTickerStrategy",
            end_date=self.end_date,
        )

        data = load_data(config, strategy, portfolio)

        self.assertIsInstance(data, dict)
        self.assertIn(self.aapl, data)
        self.assertIn(DataRequirement.TICKER, data[self.aapl])
        self.assertIn(DataRequirement.OPTIONS, data[self.aapl])

        self.assertIsInstance(data[self.aapl][DataRequirement.TICKER], pd.DataFrame)
        self.assertIsInstance(data[self.aapl][DataRequirement.OPTIONS], pd.DataFrame)
        self.assertFalse(data[self.aapl][DataRequirement.TICKER].empty)
        self.assertFalse(data[self.aapl][DataRequirement.OPTIONS].empty)

    def test_load_data_custom_lookback(self):
        """Test loading data with a custom lookback period."""
        portfolio = Portfolio(
            start_date=self.start_date,
            allowed_tradeable_items=[self.aapl],
            initial_cash=10000,
        )

        # Use a 60-day lookback period
        lookback_days = 60
        strategy = CustomTickerStrategy(
            portfolio, [DataRequirement.TICKER], lookback_days=lookback_days
        )
        config = BacktestConfig(
            initial_portfolio=portfolio,
            strategy_name="CustomTickerStrategy",
            end_date=self.end_date,
        )

        data = load_data(config, strategy, portfolio)

        # Check that we have data
        self.assertIsInstance(data[self.aapl][DataRequirement.TICKER], pd.DataFrame)
        self.assertFalse(data[self.aapl][DataRequirement.TICKER].empty)

        # The actual number of days will vary due to weekends/holidays, so we can't precisely
        # check the exact number of days, but we can verify it's a reasonable size
        df_length = len(data[self.aapl][DataRequirement.TICKER])
        self.assertGreater(df_length, 30)  # Should be more than just January's data

    def test_load_data_custom_dates(self):
        """Test loading data with custom start and end dates."""
        custom_start = date(2022, 10, 1)
        custom_end = date(2023, 3, 31)

        portfolio = Portfolio(
            start_date=custom_start,
            allowed_tradeable_items=[self.aapl],
            initial_cash=10000,
        )

        strategy = CustomTickerStrategy(portfolio, [DataRequirement.TICKER])
        config = BacktestConfig(
            initial_portfolio=portfolio,
            strategy_name="CustomTickerStrategy",
            end_date=custom_end,
        )

        data = load_data(config, strategy, portfolio)

        # Check that we have data
        self.assertIsInstance(data[self.aapl][DataRequirement.TICKER], pd.DataFrame)
        self.assertFalse(data[self.aapl][DataRequirement.TICKER].empty)

        # The data should span a reasonable date range
        df = data[self.aapl][DataRequirement.TICKER]
        if not df.empty and hasattr(df.index, "min") and hasattr(df.index, "max"):
            date_range = df.index.max() - df.index.min()
            # Should be a substantial amount of data (at least a month)
            self.assertGreater(date_range.days, 30)


if __name__ == "__main__":
    unittest.main()
