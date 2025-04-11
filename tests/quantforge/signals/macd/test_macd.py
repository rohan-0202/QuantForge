import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from quantforge.signals.macd.macd import MacdResult, calculate_macd
from quantforge.signals.macd.macd_params import MacdParams


class TestMacdResult(unittest.TestCase):
    def test_valid_macd_result(self):
        """Test creating a valid MacdResult"""
        result = MacdResult(
            valid=True, macd_line=1.5, signal_line=1.2, histogram=0.3
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.macd_line, 1.5)
        self.assertEqual(result.signal_line, 1.2)
        self.assertEqual(result.histogram, 0.3)

    def test_invalid_macd_result(self):
        """Test creating an invalid MacdResult sets appropriate defaults"""
        result = MacdResult.invalid()
        self.assertFalse(result.valid)
        self.assertEqual(result.macd_line, 0.0)
        self.assertEqual(result.signal_line, 0.0)
        self.assertEqual(result.histogram, 0.0)

    def test_invalid_method_immutability(self):
        """Test that invalid results are immutable"""
        result = MacdResult.invalid()
        with self.assertRaises(AttributeError):
            result.valid = True


class TestCalculateMacd(unittest.TestCase):
    def setUp(self):
        """Set up test data and parameters."""
        # Generate more data points, sufficient for typical MACD (12, 26, 9)
        # Needs at least slow_period + signal_period = 26 + 9 = 35 points
        self.valid_data = pd.Series(np.linspace(10, 50, 50))
        self.default_params = MacdParams.default()
        self.custom_params = MacdParams(
            fast_period=5, slow_period=15, signal_period=5
        )

    @patch("quantforge.signals.macd.macd.ta.trend.MACD")
    def test_empty_data(self, mock_macd_indicator):
        """Test calculate_macd with empty data returns invalid result."""
        empty_data = pd.Series([], dtype=float) # Explicit dtype
        result = calculate_macd(empty_data, self.default_params)
        self.assertFalse(result.valid)
        self.assertEqual(result.macd_line, 0.0)
        mock_macd_indicator.assert_not_called()

    @patch("quantforge.signals.macd.macd.ta.trend.MACD")
    def test_insufficient_data(self, mock_macd_indicator):
        """Test calculate_macd with insufficient data returns invalid result."""
        insufficient_data = pd.Series([1, 2, 3, 4, 5]) # Less than required
        result = calculate_macd(insufficient_data, self.default_params)
        self.assertFalse(result.valid)
        self.assertEqual(result.macd_line, 0.0)
        mock_macd_indicator.assert_not_called()

    @patch("quantforge.signals.macd.macd.ta.trend.MACD")
    def test_normal_data(self, mock_macd_indicator):
        """Test calculate_macd with normal data returns valid result."""
        # Mock the MACD indicator and its methods
        mock_instance = mock_macd_indicator.return_value
        mock_instance.macd.return_value = pd.Series([1.5])
        mock_instance.macd_signal.return_value = pd.Series([1.2])
        mock_instance.macd_diff.return_value = pd.Series([0.3]) # Histogram

        result = calculate_macd(self.valid_data, self.default_params)

        # Verify MACD indicator was called with correct parameters
        mock_macd_indicator.assert_called_once_with(
            close=self.valid_data,
            window_slow=self.default_params.slow_period,
            window_fast=self.default_params.fast_period,
            window_sign=self.default_params.signal_period,
            fillna=False
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.macd_line, 1.5)
        self.assertEqual(result.signal_line, 1.2)
        self.assertEqual(result.histogram, 0.3)

    @patch("quantforge.signals.macd.macd.ta.trend.MACD")
    def test_nan_macd_result(self, mock_macd_indicator):
        """Test calculate_macd with NaN result from ta library returns invalid result."""
        mock_instance = mock_macd_indicator.return_value
        mock_instance.macd.return_value = pd.Series([np.nan])
        mock_instance.macd_signal.return_value = pd.Series([1.2]) # Doesn't matter
        mock_instance.macd_diff.return_value = pd.Series([0.3]) # Doesn't matter

        result = calculate_macd(self.valid_data, self.default_params)

        self.assertFalse(result.valid)
        self.assertEqual(result.macd_line, 0.0)

    @patch("quantforge.signals.macd.macd.ta.trend.MACD")
    def test_nan_signal_result(self, mock_macd_indicator):
        """Test calculate_macd with NaN signal from ta library returns invalid result."""
        mock_instance = mock_macd_indicator.return_value
        mock_instance.macd.return_value = pd.Series([1.5])
        mock_instance.macd_signal.return_value = pd.Series([np.nan])
        mock_instance.macd_diff.return_value = pd.Series([0.3]) # Doesn't matter

        result = calculate_macd(self.valid_data, self.default_params)

        self.assertFalse(result.valid)
        self.assertEqual(result.signal_line, 0.0)

    @patch("quantforge.signals.macd.macd.ta.trend.MACD")
    def test_nan_histogram_result(self, mock_macd_indicator):
        """Test calculate_macd with NaN histogram from ta library returns invalid result."""
        mock_instance = mock_macd_indicator.return_value
        mock_instance.macd.return_value = pd.Series([1.5])
        mock_instance.macd_signal.return_value = pd.Series([1.2])
        mock_instance.macd_diff.return_value = pd.Series([np.nan])

        result = calculate_macd(self.valid_data, self.default_params)

        self.assertFalse(result.valid)
        self.assertEqual(result.histogram, 0.0)

    @patch("quantforge.signals.macd.macd.ta.trend.MACD")
    def test_empty_macd_series(self, mock_macd_indicator):
        """Test calculate_macd with empty MACD series returns invalid result."""
        mock_instance = mock_macd_indicator.return_value
        mock_instance.macd.return_value = pd.Series([], dtype=float)
        mock_instance.macd_signal.return_value = pd.Series([1.2])
        mock_instance.macd_diff.return_value = pd.Series([0.3])

        result = calculate_macd(self.valid_data, self.default_params)

        self.assertFalse(result.valid)

    @patch("quantforge.signals.macd.macd.ta.trend.MACD")
    def test_custom_params(self, mock_macd_indicator):
        """Test calculate_macd with custom parameters."""
        mock_instance = mock_macd_indicator.return_value
        mock_instance.macd.return_value = pd.Series([2.0])
        mock_instance.macd_signal.return_value = pd.Series([1.8])
        mock_instance.macd_diff.return_value = pd.Series([0.2])

        # Calculate required length for custom params
        required_length = self.custom_params.slow_period + self.custom_params.signal_period
        custom_data = pd.Series(np.linspace(10, 30, required_length + 5)) # Ensure enough data

        result = calculate_macd(custom_data, self.custom_params)

        mock_macd_indicator.assert_called_once_with(
            close=custom_data,
            window_slow=self.custom_params.slow_period,
            window_fast=self.custom_params.fast_period,
            window_sign=self.custom_params.signal_period,
            fillna=False
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.macd_line, 2.0)
        self.assertEqual(result.signal_line, 1.8)
        self.assertEqual(result.histogram, 0.2)


if __name__ == "__main__":
    unittest.main() 