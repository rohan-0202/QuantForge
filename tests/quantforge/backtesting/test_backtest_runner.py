import unittest
from unittest.mock import patch, MagicMock, call, ANY
from datetime import date
from quantforge.backtesting.backtest_runner import backtest_loop
from quantforge.strategies.abstract_strategy import StrategyInputData, AbstractStrategy


class TestBacktestLoop(unittest.TestCase):
    def setUp(self):
        # Create mock objects for dependencies
        self.mock_strategy = MagicMock(spec=AbstractStrategy)
        self.mock_input_data = MagicMock(spec=StrategyInputData)

        # Set up trading dates
        self.trading_dates = [
            date(2023, 1, 1),
            date(2023, 1, 2),
            date(2023, 1, 3),
        ]

    @patch("quantforge.backtesting.backtest_runner.create_masked_data")
    @patch("quantforge.backtesting.backtest_runner.extract_ohlc_data")
    def test_backtest_loop_executes_for_each_trading_day_except_last(
        self, mock_extract_ohlc, mock_create_masked
    ):
        # Configure mocks
        mock_masked_data = MagicMock()
        mock_create_masked.return_value = mock_masked_data

        mock_next_day_data = MagicMock()
        mock_extract_ohlc.return_value = mock_next_day_data

        # Run the function
        backtest_loop(self.trading_dates, self.mock_input_data, self.mock_strategy)

        # Verify create_masked_data called for each date
        self.assertEqual(mock_create_masked.call_count, 3)
        mock_create_masked.assert_has_calls(
            [
                call(self.mock_input_data, self.trading_dates[0]),
                call(self.mock_input_data, self.trading_dates[1]),
                call(self.mock_input_data, self.trading_dates[2]),
            ]
        )

        # Verify extract_ohlc_data called for next day of each date except the last
        self.assertEqual(mock_extract_ohlc.call_count, 2)
        # Since the mock may have other boolean calls, we'll check just the relevant calls
        self.assertIn(
            call(
                self.mock_input_data,
                self.mock_strategy.portfolio,
                self.trading_dates[1],
            ),
            mock_extract_ohlc.mock_calls,
        )
        self.assertIn(
            call(
                self.mock_input_data,
                self.mock_strategy.portfolio,
                self.trading_dates[2],
            ),
            mock_extract_ohlc.mock_calls,
        )

        # Verify strategy.execute called for each date except the last
        self.assertEqual(self.mock_strategy.execute.call_count, 2)
        # Check that execute is called with the masked data and any next day data
        self.mock_strategy.execute.assert_has_calls(
            [
                call(mock_masked_data, mock_next_day_data),
                call(mock_masked_data, mock_next_day_data),
            ]
        )

    @patch("quantforge.backtesting.backtest_runner.create_masked_data")
    @patch("quantforge.backtesting.backtest_runner.extract_ohlc_data")
    def test_backtest_loop_skips_execution_when_next_day_data_missing(
        self, mock_extract_ohlc, mock_create_masked
    ):
        # Configure mocks
        mock_masked_data = MagicMock()
        mock_create_masked.return_value = mock_masked_data

        # Return None for the first next day data (missing data)
        # and valid data for the second day
        mock_extract_ohlc.side_effect = [None, MagicMock()]

        # Run the function
        backtest_loop(self.trading_dates, self.mock_input_data, self.mock_strategy)

        # Verify create_masked_data called for each date
        self.assertEqual(mock_create_masked.call_count, 3)

        # Verify extract_ohlc_data called for next day of each date except the last
        self.assertEqual(mock_extract_ohlc.call_count, 2)

        # Verify strategy.execute called only once (for the second day with valid data)
        self.assertEqual(self.mock_strategy.execute.call_count, 1)
        # Use ANY to match any mock object since we're only checking call count
        self.mock_strategy.execute.assert_called_with(mock_masked_data, ANY)

    @patch("quantforge.backtesting.backtest_runner.create_masked_data")
    @patch("quantforge.backtesting.backtest_runner.extract_ohlc_data")
    def test_backtest_loop_with_single_trading_day(
        self, mock_extract_ohlc, mock_create_masked
    ):
        # Single trading day
        single_date = [date(2023, 1, 1)]

        # Configure mocks
        mock_masked_data = MagicMock()
        mock_create_masked.return_value = mock_masked_data

        # Run the function
        backtest_loop(single_date, self.mock_input_data, self.mock_strategy)

        # Verify create_masked_data called for the single date
        mock_create_masked.assert_called_once_with(self.mock_input_data, single_date[0])

        # Verify extract_ohlc_data not called (no next day)
        mock_extract_ohlc.assert_not_called()

        # Verify strategy.execute not called (no next day)
        self.mock_strategy.execute.assert_not_called()

    @patch("quantforge.backtesting.backtest_runner.create_masked_data")
    @patch("quantforge.backtesting.backtest_runner.extract_ohlc_data")
    def test_backtest_loop_with_empty_trading_dates(
        self, mock_extract_ohlc, mock_create_masked
    ):
        # Empty trading dates list
        empty_dates = []

        # Run the function
        backtest_loop(empty_dates, self.mock_input_data, self.mock_strategy)

        # Verify no calls to create_masked_data, extract_ohlc_data, or strategy.execute
        mock_create_masked.assert_not_called()
        mock_extract_ohlc.assert_not_called()
        self.mock_strategy.execute.assert_not_called()

    @patch("quantforge.backtesting.backtest_runner.create_masked_data")
    @patch("quantforge.backtesting.backtest_runner.extract_ohlc_data")
    def test_backtest_loop_with_all_missing_next_day_data(
        self, mock_extract_ohlc, mock_create_masked
    ):
        # Configure mocks
        mock_masked_data = MagicMock()
        mock_create_masked.return_value = mock_masked_data

        # Return None for all next day data (all missing)
        mock_extract_ohlc.return_value = None

        # Run the function
        backtest_loop(self.trading_dates, self.mock_input_data, self.mock_strategy)

        # Verify create_masked_data called for each date
        self.assertEqual(mock_create_masked.call_count, 3)

        # Verify extract_ohlc_data called for next day of each date except the last
        self.assertEqual(mock_extract_ohlc.call_count, 2)

        # Verify strategy.execute never called because all next day data is missing
        self.mock_strategy.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
