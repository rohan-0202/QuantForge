import unittest
from unittest.mock import patch, MagicMock, call, ANY
from datetime import date
from quantforge.backtesting.backtest_runner import backtest_loop
from quantforge.strategies.abstract_strategy import StrategyInputData, AbstractStrategy
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.portfolio_metrics import PortfolioMetrics
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.assetclass import AssetClass
from quantforge.qtypes.ohlc import OHLCData


class TestBacktestLoop(unittest.TestCase):
    def setUp(self):
        # Create mock objects for dependencies
        self.mock_strategy = MagicMock(spec=AbstractStrategy)
        self.mock_input_data = MagicMock(spec=StrategyInputData)
        self.mock_portfolio = MagicMock(spec=Portfolio)
        self.mock_metrics = MagicMock(spec=PortfolioMetrics)

        # Setup mock portfolio
        self.mock_portfolio.cash = 10000.0
        self.mock_portfolio._open_positions_by_tradeable_item = {}
        self.mock_portfolio.portfolio_value.return_value = 10000.0
        self.mock_strategy.portfolio = self.mock_portfolio

        # Set up trading dates
        self.trading_dates = [
            date(2023, 1, 1),
            date(2023, 1, 2),
            date(2023, 1, 3),
        ]
        # Mock data for valuation/execution
        self.mock_item = TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)
        self.mock_ohlc_t1 = OHLCData(date=self.trading_dates[0], open=100, high=101, low=99, close=100, volume=1000)
        self.mock_ohlc_t2 = OHLCData(date=self.trading_dates[1], open=101, high=102, low=100, close=101, volume=1100)
        self.mock_ohlc_t3 = OHLCData(date=self.trading_dates[2], open=102, high=103, low=101, close=102, volume=1200)

    @patch("quantforge.backtesting.backtest_runner.create_masked_data")
    @patch("quantforge.backtesting.backtest_runner.extract_ohlc_data")
    def test_backtest_loop_executes_for_each_trading_day_except_last(
        self, mock_extract_ohlc, mock_create_masked
    ):
        # Configure mocks
        mock_masked_data = MagicMock()
        mock_create_masked.return_value = mock_masked_data

        # Mock portfolio holds AAPL
        self.mock_portfolio._open_positions_by_tradeable_item = {self.mock_item: [MagicMock()]}
        self.mock_portfolio.portfolio_value.side_effect = [10100.0, 10200.0, 10300.0]

        # Define side effects for extract_ohlc_data
        # Called for: valuation(t1), execution(t2), valuation(t2), execution(t3), valuation(t3)
        mock_extract_ohlc.side_effect = [
            {self.mock_item: self.mock_ohlc_t1},
            {self.mock_item: self.mock_ohlc_t2},
            {self.mock_item: self.mock_ohlc_t2},
            {self.mock_item: self.mock_ohlc_t3},
            {self.mock_item: self.mock_ohlc_t3},
        ]

        # Run the function
        backtest_loop(self.trading_dates, self.mock_input_data, self.mock_strategy, self.mock_metrics)

        # --- Assertions --- 
        # create_masked_data called for each date
        self.assertEqual(mock_create_masked.call_count, 3)

        # extract_ohlc_data called for valuation and execution
        self.assertEqual(mock_extract_ohlc.call_count, 5)
        valuation_calls = [
            call(self.mock_input_data, self.mock_portfolio, self.trading_dates[0]),
            call(self.mock_input_data, self.mock_portfolio, self.trading_dates[1]),
            call(self.mock_input_data, self.mock_portfolio, self.trading_dates[2]),
        ]
        execution_calls = [
             call(self.mock_input_data, self.mock_portfolio, self.trading_dates[1]),
             call(self.mock_input_data, self.mock_portfolio, self.trading_dates[2]),
        ]
        # Check calls occurred (order might vary slightly depending on implementation details)
        for c in valuation_calls: self.assertIn(c, mock_extract_ohlc.call_args_list)
        for c in execution_calls: self.assertIn(c, mock_extract_ohlc.call_args_list)

        # portfolio_value called for valuation if prices available
        self.assertEqual(self.mock_portfolio.portfolio_value.call_count, 3)
        self.mock_portfolio.portfolio_value.assert_has_calls([
            call({self.mock_item: 100}),
            call({self.mock_item: 101}),
            call({self.mock_item: 102})
        ])

        # metrics.update called for each day with valuation data
        self.assertEqual(self.mock_metrics.update.call_count, 3)
        self.mock_metrics.update.assert_has_calls([
            call(self.trading_dates[0], 10100.0),
            call(self.trading_dates[1], 10200.0),
            call(self.trading_dates[2], 10300.0),
        ])

        # strategy.execute called for each date except the last
        self.assertEqual(self.mock_strategy.execute.call_count, 2)
        self.mock_strategy.execute.assert_has_calls([
            call(mock_masked_data, {self.mock_item: self.mock_ohlc_t2}),
            call(mock_masked_data, {self.mock_item: self.mock_ohlc_t3})
        ])

    @patch("quantforge.backtesting.backtest_runner.create_masked_data")
    @patch("quantforge.backtesting.backtest_runner.extract_ohlc_data")
    def test_backtest_loop_skips_execution_when_next_day_data_missing(
        self, mock_extract_ohlc, mock_create_masked
    ):
        # Configure mocks
        mock_masked_data = MagicMock()
        mock_create_masked.return_value = mock_masked_data
        self.mock_portfolio._open_positions_by_tradeable_item = {self.mock_item: [MagicMock()]}
        self.mock_portfolio.portfolio_value.side_effect = [10100.0, 10200.0, 10300.0]

        # Valuation(t1)=OK, Exec(t2)=MISSING, Val(t2)=OK, Exec(t3)=OK, Val(t3)=OK
        mock_extract_ohlc.side_effect = [
            {self.mock_item: self.mock_ohlc_t1},
            None,
            {self.mock_item: self.mock_ohlc_t2},
            {self.mock_item: self.mock_ohlc_t3},
            {self.mock_item: self.mock_ohlc_t3},
        ]

        # Run the function
        backtest_loop(self.trading_dates, self.mock_input_data, self.mock_strategy, self.mock_metrics)

        # Verify metrics update still called 3 times (valuation independent of execution)
        self.assertEqual(self.mock_metrics.update.call_count, 3)
        self.mock_metrics.update.assert_has_calls([
            call(self.trading_dates[0], 10100.0),
            call(self.trading_dates[1], 10200.0),
            call(self.trading_dates[2], 10300.0),
        ])

        # Verify strategy.execute called only once (for the second day)
        self.assertEqual(self.mock_strategy.execute.call_count, 1)
        self.mock_strategy.execute.assert_called_with(mock_masked_data, {self.mock_item: self.mock_ohlc_t3})

    @patch("quantforge.backtesting.backtest_runner.create_masked_data")
    @patch("quantforge.backtesting.backtest_runner.extract_ohlc_data")
    def test_backtest_loop_skips_metrics_update_when_valuation_data_missing(
        self, mock_extract_ohlc, mock_create_masked
    ):
        # Configure mocks
        mock_masked_data = MagicMock()
        mock_create_masked.return_value = mock_masked_data
        self.mock_portfolio._open_positions_by_tradeable_item = {self.mock_item: [MagicMock()]}
        # Portfolio value will only be calculated on days valuation data exists
        self.mock_portfolio.portfolio_value.side_effect = [10100.0, 10300.0]

        # Val(t1)=OK, Exec(t2)=OK, Val(t2)=MISSING, Exec(t3)=OK, Val(t3)=OK
        mock_extract_ohlc.side_effect = [
            {self.mock_item: self.mock_ohlc_t1},
            {self.mock_item: self.mock_ohlc_t2},
            None,
            {self.mock_item: self.mock_ohlc_t3},
            {self.mock_item: self.mock_ohlc_t3},
        ]

        # Run the function
        backtest_loop(self.trading_dates, self.mock_input_data, self.mock_strategy, self.mock_metrics)

        # Verify metrics update called only twice (skipped for t2)
        self.assertEqual(self.mock_metrics.update.call_count, 2)
        self.mock_metrics.update.assert_has_calls([
            call(self.trading_dates[0], 10100.0),
            call(self.trading_dates[2], 10300.0),
        ])

        # Verify strategy.execute still called twice (execution independent of valuation)
        self.assertEqual(self.mock_strategy.execute.call_count, 2)

    @patch("quantforge.backtesting.backtest_runner.create_masked_data")
    @patch("quantforge.backtesting.backtest_runner.extract_ohlc_data")
    def test_backtest_loop_with_single_trading_day(
        self, mock_extract_ohlc, mock_create_masked
    ):
        # Single trading day
        single_date = [date(2023, 1, 1)]
        self.mock_portfolio._open_positions_by_tradeable_item = {}
        self.mock_portfolio.cash = 9000.0

        # Configure mocks
        mock_masked_data = MagicMock()
        mock_create_masked.return_value = mock_masked_data
        # Only valuation call will happen
        mock_extract_ohlc.side_effect = [{self.mock_item: self.mock_ohlc_t1}]

        # Run the function
        backtest_loop(single_date, self.mock_input_data, self.mock_strategy, self.mock_metrics)

        # Verify create_masked_data called once
        mock_create_masked.assert_called_once_with(self.mock_input_data, single_date[0])

        # Verify extract_ohlc_data called once (for valuation)
        mock_extract_ohlc.assert_called_once_with(self.mock_input_data, self.mock_portfolio, single_date[0])

        # Verify portfolio_value not called (no assets held)
        self.mock_portfolio.portfolio_value.assert_not_called()

        # Verify metrics.update called once with cash value
        self.mock_metrics.update.assert_called_once_with(single_date[0], self.mock_portfolio.cash)

        # Verify strategy.execute not called
        self.mock_strategy.execute.assert_not_called()

    @patch("quantforge.backtesting.backtest_runner.create_masked_data")
    @patch("quantforge.backtesting.backtest_runner.extract_ohlc_data")
    def test_backtest_loop_with_empty_trading_dates(
        self, mock_extract_ohlc, mock_create_masked
    ):
        # Empty trading dates list
        empty_dates = []

        # Run the function
        backtest_loop(empty_dates, self.mock_input_data, self.mock_strategy, self.mock_metrics)

        # Verify no calls
        mock_create_masked.assert_not_called()
        mock_extract_ohlc.assert_not_called()
        self.mock_portfolio.portfolio_value.assert_not_called()
        self.mock_metrics.update.assert_not_called()
        self.mock_strategy.execute.assert_not_called()

    @patch("quantforge.backtesting.backtest_runner.create_masked_data")
    @patch("quantforge.backtesting.backtest_runner.extract_ohlc_data")
    def test_backtest_loop_with_all_missing_next_day_data(
        self, mock_extract_ohlc, mock_create_masked
    ):
        # Configure mocks
        mock_masked_data = MagicMock()
        mock_create_masked.return_value = mock_masked_data
        self.mock_portfolio._open_positions_by_tradeable_item = {self.mock_item: [MagicMock()]}
        self.mock_portfolio.portfolio_value.side_effect = [10100.0, 10200.0, 10300.0]

        # Val(t1)=OK, Exec(t2)=MISSING, Val(t2)=OK, Exec(t3)=MISSING, Val(t3)=OK
        mock_extract_ohlc.side_effect = [
            {self.mock_item: self.mock_ohlc_t1},
            None,
            {self.mock_item: self.mock_ohlc_t2},
            None,
            {self.mock_item: self.mock_ohlc_t3},
        ]

        # Run the function
        backtest_loop(self.trading_dates, self.mock_input_data, self.mock_strategy, self.mock_metrics)

        # Verify metrics update still called 3 times
        self.assertEqual(self.mock_metrics.update.call_count, 3)

        # Verify strategy.execute never called
        self.mock_strategy.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
