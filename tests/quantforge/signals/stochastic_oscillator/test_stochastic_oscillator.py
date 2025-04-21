import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from quantforge.signals.stochastic_oscillator.stochastic_oscillator import (
    StochasticOscillatorResult,
    calculate_stochastic_oscillator,
)
from quantforge.signals.stochastic_oscillator.stochastic_oscillator_params import (
    StochasticOscillatorParams,
)


class TestStochasticOscillatorResult(unittest.TestCase):
    def test_valid_result(self):
        """Test creating a valid StochasticOscillatorResult"""
        result = StochasticOscillatorResult(
            valid=True, k_value=75.5, d_value=70.2, oversold=False, overbought=False
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.k_value, 75.5)
        self.assertEqual(result.d_value, 70.2)
        self.assertFalse(result.oversold)
        self.assertFalse(result.overbought)

    def test_invalid_result(self):
        """Test creating an invalid StochasticOscillatorResult sets defaults"""
        result = StochasticOscillatorResult.invalid()
        self.assertFalse(result.valid)
        self.assertEqual(result.k_value, 0.0)
        self.assertEqual(result.d_value, 0.0)
        self.assertFalse(result.oversold)
        self.assertFalse(result.overbought)

    def test_k_value_out_of_range_low(self):
        """Test %K below 0 raises ValueError"""
        with self.assertRaises(ValueError):
            StochasticOscillatorResult(
                valid=True, k_value=-5.0, d_value=10.0, oversold=True, overbought=False
            )

    def test_k_value_out_of_range_high(self):
        """Test %K above 100 raises ValueError"""
        with self.assertRaises(ValueError):
            StochasticOscillatorResult(
                valid=True, k_value=105.0, d_value=90.0, oversold=False, overbought=True
            )

    def test_d_value_out_of_range_low(self):
        """Test %D below 0 raises ValueError"""
        with self.assertRaises(ValueError):
            StochasticOscillatorResult(
                valid=True, k_value=15.0, d_value=-5.0, oversold=True, overbought=False
            )

    def test_d_value_out_of_range_high(self):
        """Test %D above 100 raises ValueError"""
        with self.assertRaises(ValueError):
            StochasticOscillatorResult(
                valid=True, k_value=95.0, d_value=105.0, oversold=False, overbought=True
            )

    def test_contradictory_signals(self):
        """Test that both oversold and overbought cannot be True"""
        with self.assertRaises(ValueError):
            StochasticOscillatorResult(
                valid=True, k_value=50.0, d_value=55.0, oversold=True, overbought=True
            )

    def test_oversold_condition(self):
        """Test oversold condition (%K < threshold) is correctly represented"""
        result = StochasticOscillatorResult(
            valid=True, k_value=15.0, d_value=20.0, oversold=True, overbought=False
        )
        self.assertTrue(result.oversold)
        self.assertFalse(result.overbought)

    def test_overbought_condition(self):
        """Test overbought condition (%K > threshold) is correctly represented"""
        result = StochasticOscillatorResult(
            valid=True, k_value=85.0, d_value=80.0, oversold=False, overbought=True
        )
        self.assertFalse(result.oversold)
        self.assertTrue(result.overbought)


class TestInvalidMethodStochastic(unittest.TestCase):
    """Tests for the invalid class method on StochasticOscillatorResult"""

    def test_invalid_method(self):
        """Test the invalid class method returns a properly configured instance"""
        result = StochasticOscillatorResult.invalid()
        self.assertFalse(result.valid)
        self.assertEqual(result.k_value, 0.0)
        self.assertEqual(result.d_value, 0.0)
        self.assertFalse(result.oversold)
        self.assertFalse(result.overbought)

    def test_invalid_method_immutability(self):
        """Test that invalid results are immutable"""
        result = StochasticOscillatorResult.invalid()
        with self.assertRaises(AttributeError):
            result.valid = True


class TestCalculateStochasticOscillator(unittest.TestCase):
    def setUp(self):
        """Set up test data and parameters"""
        # Need enough data for k=14, smooth_k=3, d=3 => 14+3+3-2 = 18 points minimum
        self.valid_close = pd.Series(range(100, 120))
        self.valid_high = self.valid_close + 1
        self.valid_low = self.valid_close - 1
        self.default_params = StochasticOscillatorParams.default()  # k=14, d=3, smooth_k=3
        self.custom_params = StochasticOscillatorParams(
            k_period=5,
            d_period=2,
            smooth_k=2,
            oversold_threshold=10,
            overbought_threshold=90,
        )

    @patch(
        "quantforge.signals.stochastic_oscillator.stochastic_oscillator.ta.momentum.StochasticOscillator"
    )
    def test_empty_data(self, mock_stoch_indicator):
        """Test with empty data returns invalid result"""
        result = calculate_stochastic_oscillator(
            pd.Series([]), pd.Series([]), pd.Series([]), self.default_params
        )
        self.assertFalse(result.valid)
        mock_stoch_indicator.assert_not_called()

    @patch(
        "quantforge.signals.stochastic_oscillator.stochastic_oscillator.ta.momentum.StochasticOscillator"
    )
    def test_insufficient_data(self, mock_stoch_indicator):
        """Test with insufficient data returns invalid result"""
        short_close = pd.Series(range(100, 105)) # Only 5 points, need 18
        short_high = short_close + 1
        short_low = short_close - 1
        result = calculate_stochastic_oscillator(
            short_high, short_low, short_close, self.default_params
        )
        self.assertFalse(result.valid)
        mock_stoch_indicator.assert_not_called()

    @patch(
        "quantforge.signals.stochastic_oscillator.stochastic_oscillator.ta.momentum.StochasticOscillator"
    )
    def test_normal_data(self, mock_stoch_indicator):
        """Test with normal data returns valid result"""
        mock_instance = mock_stoch_indicator.return_value
        mock_k_series = pd.Series([50.0])
        mock_d_series = pd.Series([45.0])
        mock_instance.stoch.return_value = mock_k_series
        mock_instance.stoch_signal.return_value = mock_d_series

        result = calculate_stochastic_oscillator(
            self.valid_high, self.valid_low, self.valid_close, self.default_params
        )

        mock_stoch_indicator.assert_called_once_with(
            high=self.valid_high,
            low=self.valid_low,
            close=self.valid_close,
            window=self.default_params.k_period,
            smooth_window=self.default_params.smooth_k,
            fillna=False,
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.k_value, 50.0)
        self.assertEqual(result.d_value, 45.0)
        self.assertFalse(result.oversold)
        self.assertFalse(result.overbought)

    @patch(
        "quantforge.signals.stochastic_oscillator.stochastic_oscillator.ta.momentum.StochasticOscillator"
    )
    def test_oversold_condition(self, mock_stoch_indicator):
        """Test correctly identifies oversold condition"""
        mock_instance = mock_stoch_indicator.return_value
        mock_instance.stoch.return_value = pd.Series([15.0]) # %K < 20
        mock_instance.stoch_signal.return_value = pd.Series([18.0])

        result = calculate_stochastic_oscillator(
            self.valid_high, self.valid_low, self.valid_close, self.default_params
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.k_value, 15.0)
        self.assertTrue(result.oversold)
        self.assertFalse(result.overbought)

    @patch(
        "quantforge.signals.stochastic_oscillator.stochastic_oscillator.ta.momentum.StochasticOscillator"
    )
    def test_overbought_condition(self, mock_stoch_indicator):
        """Test correctly identifies overbought condition"""
        mock_instance = mock_stoch_indicator.return_value
        mock_instance.stoch.return_value = pd.Series([85.0]) # %K > 80
        mock_instance.stoch_signal.return_value = pd.Series([82.0])

        result = calculate_stochastic_oscillator(
            self.valid_high, self.valid_low, self.valid_close, self.default_params
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.k_value, 85.0)
        self.assertFalse(result.oversold)
        self.assertTrue(result.overbought)

    @patch(
        "quantforge.signals.stochastic_oscillator.stochastic_oscillator.ta.momentum.StochasticOscillator"
    )
    def test_custom_thresholds(self, mock_stoch_indicator):
        """Test with custom thresholds"""
        mock_instance = mock_stoch_indicator.return_value
        mock_instance.stoch.return_value = pd.Series([15.0]) # Between default (20/80) but oversold for custom (10/90)
        mock_instance.stoch_signal.return_value = pd.Series([18.0])

        result = calculate_stochastic_oscillator(
            self.valid_high, self.valid_low, self.valid_close, self.custom_params
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.k_value, 15.0)
        # With custom thresholds (10/90), 15 is neither oversold nor overbought
        self.assertFalse(result.oversold)
        self.assertFalse(result.overbought)

        # Test value that IS oversold with custom thresholds
        mock_instance.stoch.return_value = pd.Series([5.0]) # < 10
        result = calculate_stochastic_oscillator(
            self.valid_high, self.valid_low, self.valid_close, self.custom_params
        )
        self.assertTrue(result.oversold)
        self.assertFalse(result.overbought)


    @patch(
        "quantforge.signals.stochastic_oscillator.stochastic_oscillator.ta.momentum.StochasticOscillator"
    )
    def test_nan_k_result(self, mock_stoch_indicator):
        """Test with NaN %K result from ta library returns invalid"""
        mock_instance = mock_stoch_indicator.return_value
        mock_instance.stoch.return_value = pd.Series([np.nan])
        mock_instance.stoch_signal.return_value = pd.Series([45.0])

        result = calculate_stochastic_oscillator(
            self.valid_high, self.valid_low, self.valid_close, self.default_params
        )
        self.assertFalse(result.valid)

    @patch(
        "quantforge.signals.stochastic_oscillator.stochastic_oscillator.ta.momentum.StochasticOscillator"
    )
    def test_nan_d_result(self, mock_stoch_indicator):
        """Test with NaN %D result from ta library returns invalid"""
        mock_instance = mock_stoch_indicator.return_value
        mock_instance.stoch.return_value = pd.Series([50.0])
        mock_instance.stoch_signal.return_value = pd.Series([np.nan])

        result = calculate_stochastic_oscillator(
            self.valid_high, self.valid_low, self.valid_close, self.default_params
        )
        self.assertFalse(result.valid)

    @patch(
        "quantforge.signals.stochastic_oscillator.stochastic_oscillator.ta.momentum.StochasticOscillator"
    )
    def test_empty_k_series(self, mock_stoch_indicator):
        """Test with empty %K series from ta library returns invalid"""
        mock_instance = mock_stoch_indicator.return_value
        mock_instance.stoch.return_value = pd.Series([], dtype=float)
        mock_instance.stoch_signal.return_value = pd.Series([45.0])

        result = calculate_stochastic_oscillator(
            self.valid_high, self.valid_low, self.valid_close, self.default_params
        )
        self.assertFalse(result.valid)

    @patch(
        "quantforge.signals.stochastic_oscillator.stochastic_oscillator.ta.momentum.StochasticOscillator"
    )
    def test_empty_d_series(self, mock_stoch_indicator):
        """Test with empty %D series from ta library returns invalid"""
        mock_instance = mock_stoch_indicator.return_value
        mock_instance.stoch.return_value = pd.Series([50.0])
        mock_instance.stoch_signal.return_value = pd.Series([], dtype=float)

        result = calculate_stochastic_oscillator(
            self.valid_high, self.valid_low, self.valid_close, self.default_params
        )
        self.assertFalse(result.valid)


if __name__ == "__main__":
    unittest.main() 