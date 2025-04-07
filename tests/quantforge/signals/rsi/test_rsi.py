import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from quantforge.signals.rsi.rsi import RsiResult, calculate_rsi
from quantforge.signals.rsi.rsi_params import RsiParams


class TestRsiResult(unittest.TestCase):
    def test_valid_rsi_result(self):
        """Test creating a valid RsiResult"""
        result = RsiResult(valid=True, rsi=65.5, oversold=False, overbought=False)
        self.assertTrue(result.valid)
        self.assertEqual(result.rsi, 65.5)
        self.assertFalse(result.oversold)
        self.assertFalse(result.overbought)

    def test_invalid_rsi_result(self):
        """Test creating an invalid RsiResult sets appropriate defaults"""
        result = RsiResult.invalid()
        self.assertFalse(result.valid)
        self.assertEqual(result.rsi, 0.0)
        self.assertFalse(result.oversold)
        self.assertFalse(result.overbought)

    def test_rsi_out_of_range_low(self):
        """Test RSI below 0 raises ValueError"""
        with self.assertRaises(ValueError):
            RsiResult(valid=True, rsi=-5.0, oversold=True, overbought=False)

    def test_rsi_out_of_range_high(self):
        """Test RSI above 100 raises ValueError"""
        with self.assertRaises(ValueError):
            RsiResult(valid=True, rsi=105.0, oversold=False, overbought=True)

    def test_contradictory_signals(self):
        """Test that both oversold and overbought cannot be True"""
        with self.assertRaises(ValueError):
            RsiResult(valid=True, rsi=50.0, oversold=True, overbought=True)

    def test_oversold_condition(self):
        """Test oversold condition is correctly represented"""
        result = RsiResult(valid=True, rsi=25.0, oversold=True, overbought=False)
        self.assertTrue(result.oversold)
        self.assertFalse(result.overbought)

    def test_overbought_condition(self):
        """Test overbought condition is correctly represented"""
        result = RsiResult(valid=True, rsi=75.0, oversold=False, overbought=True)
        self.assertFalse(result.oversold)
        self.assertTrue(result.overbought)


class TestInvalidMethod(unittest.TestCase):
    """Tests for the invalid class method on RsiResult"""

    def test_invalid_method(self):
        """Test the invalid class method returns a properly configured instance"""
        result = RsiResult.invalid()
        self.assertFalse(result.valid)
        self.assertEqual(result.rsi, 0.0)
        self.assertFalse(result.oversold)
        self.assertFalse(result.overbought)

    def test_invalid_method_immutability(self):
        """Test that invalid results are immutable"""
        result = RsiResult.invalid()
        with self.assertRaises(AttributeError):
            result.valid = True


class TestCalculateRsi(unittest.TestCase):
    def setUp(self):
        """Set up test data and parameters"""
        self.valid_data = pd.Series(
            [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
        )
        self.default_params = RsiParams.default()
        self.custom_params = RsiParams(
            rsi_period=5, oversold_threshold=20, overbought_threshold=80
        )

    @patch("quantforge.signals.rsi.rsi.ta.momentum.RSIIndicator")
    def test_empty_data(self, mock_rsi_indicator):
        """Test calculate_rsi with empty data returns invalid result"""
        empty_data = pd.Series([])
        result = calculate_rsi(empty_data, self.default_params)
        self.assertFalse(result.valid)
        self.assertEqual(result.rsi, 0.0)
        # RSI indicator should not be called for empty data
        mock_rsi_indicator.assert_not_called()

    @patch("quantforge.signals.rsi.rsi.ta.momentum.RSIIndicator")
    def test_insufficient_data(self, mock_rsi_indicator):
        """Test calculate_rsi with insufficient data returns invalid result"""
        insufficient_data = pd.Series([1, 2, 3])  # Fewer than default period 14
        result = calculate_rsi(insufficient_data, self.default_params)
        self.assertFalse(result.valid)
        self.assertEqual(result.rsi, 0.0)
        # RSI indicator should not be called for insufficient data
        mock_rsi_indicator.assert_not_called()

    @patch("quantforge.signals.rsi.rsi.ta.momentum.RSIIndicator")
    def test_normal_data(self, mock_rsi_indicator):
        """Test calculate_rsi with normal data returns valid result"""
        # Mock the RSI indicator and its rsi method
        mock_instance = mock_rsi_indicator.return_value
        mock_rsi_series = pd.Series([50.0])
        mock_instance.rsi.return_value = mock_rsi_series

        result = calculate_rsi(self.valid_data, self.default_params)

        # Verify RSI indicator was called with correct parameters
        mock_rsi_indicator.assert_called_once_with(
            close=self.valid_data, window=self.default_params.rsi_period, fillna=False
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.rsi, 50.0)
        self.assertFalse(result.oversold)
        self.assertFalse(result.overbought)

    @patch("quantforge.signals.rsi.rsi.ta.momentum.RSIIndicator")
    def test_oversold_condition(self, mock_rsi_indicator):
        """Test calculate_rsi correctly identifies oversold condition"""
        # Mock low RSI value (oversold)
        mock_instance = mock_rsi_indicator.return_value
        mock_rsi_series = pd.Series([15.0])
        mock_instance.rsi.return_value = mock_rsi_series

        result = calculate_rsi(self.valid_data, self.default_params)

        self.assertTrue(result.valid)
        self.assertEqual(result.rsi, 15.0)
        self.assertTrue(result.oversold)
        self.assertFalse(result.overbought)

    @patch("quantforge.signals.rsi.rsi.ta.momentum.RSIIndicator")
    def test_overbought_condition(self, mock_rsi_indicator):
        """Test calculate_rsi correctly identifies overbought condition"""
        # Mock high RSI value (overbought)
        mock_instance = mock_rsi_indicator.return_value
        mock_rsi_series = pd.Series([85.0])
        mock_instance.rsi.return_value = mock_rsi_series

        result = calculate_rsi(self.valid_data, self.default_params)

        self.assertTrue(result.valid)
        self.assertEqual(result.rsi, 85.0)
        self.assertFalse(result.oversold)
        self.assertTrue(result.overbought)

    @patch("quantforge.signals.rsi.rsi.ta.momentum.RSIIndicator")
    def test_custom_thresholds(self, mock_rsi_indicator):
        """Test calculate_rsi with custom thresholds"""
        # Mock RSI value between default thresholds but outside custom thresholds
        mock_instance = mock_rsi_indicator.return_value
        mock_rsi_series = pd.Series([25.0])
        mock_instance.rsi.return_value = mock_rsi_series

        # With custom thresholds (oversold < 20)
        result = calculate_rsi(self.valid_data, self.custom_params)

        self.assertTrue(result.valid)
        self.assertEqual(result.rsi, 25.0)
        # With custom thresholds, 25 is neither oversold nor overbought
        self.assertFalse(result.oversold)
        self.assertFalse(result.overbought)

    @patch("quantforge.signals.rsi.rsi.ta.momentum.RSIIndicator")
    def test_nan_rsi_result(self, mock_rsi_indicator):
        """Test calculate_rsi with NaN result from ta library returns invalid result"""
        mock_instance = mock_rsi_indicator.return_value
        mock_rsi_series = pd.Series([np.nan])
        mock_instance.rsi.return_value = mock_rsi_series

        result = calculate_rsi(self.valid_data, self.default_params)

        self.assertFalse(result.valid)
        self.assertEqual(result.rsi, 0.0)
        self.assertFalse(result.oversold)
        self.assertFalse(result.overbought)

    @patch("quantforge.signals.rsi.rsi.ta.momentum.RSIIndicator")
    def test_empty_rsi_series(self, mock_rsi_indicator):
        """Test calculate_rsi with empty result from ta library returns invalid result"""
        mock_instance = mock_rsi_indicator.return_value
        mock_rsi_series = pd.Series([])  # Empty series
        mock_instance.rsi.return_value = mock_rsi_series

        result = calculate_rsi(self.valid_data, self.default_params)

        self.assertFalse(result.valid)
        self.assertEqual(result.rsi, 0.0)
        self.assertFalse(result.oversold)
        self.assertFalse(result.overbought)


if __name__ == "__main__":
    unittest.main()
