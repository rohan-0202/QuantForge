import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from quantforge.signals.bollinger_bands.bollinger_bands import (
    BollingerBandsResult,
    calculate_bollinger_bands,
)
from quantforge.signals.bollinger_bands.bollinger_bands_params import (
    BollingerBandsParams,
)


class TestBollingerBandsResult(unittest.TestCase):
    def test_valid_result(self):
        """Test creating a valid BollingerBandsResult"""
        result = BollingerBandsResult(
            valid=True,
            upper_band=110.5,
            middle_band=100.0,
            lower_band=89.5,
            bandwidth=0.21, # (110.5 - 89.5) / 100.0
            percent_b=0.5, # (100.0 - 89.5) / (110.5 - 89.5)
            price_above_upper=False,
            price_below_lower=False,
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.upper_band, 110.5)
        self.assertEqual(result.middle_band, 100.0)
        self.assertEqual(result.lower_band, 89.5)
        self.assertEqual(result.bandwidth, 0.21)
        self.assertEqual(result.percent_b, 0.5)
        self.assertFalse(result.price_above_upper)
        self.assertFalse(result.price_below_lower)

    def test_invalid_result(self):
        """Test creating an invalid BollingerBandsResult sets defaults"""
        result = BollingerBandsResult.invalid()
        self.assertFalse(result.valid)
        self.assertEqual(result.upper_band, 0.0)
        self.assertEqual(result.middle_band, 0.0)
        self.assertEqual(result.lower_band, 0.0)
        self.assertEqual(result.bandwidth, 0.0)
        self.assertEqual(result.percent_b, 0.0)
        self.assertFalse(result.price_above_upper)
        self.assertFalse(result.price_below_lower)

    def test_inconsistent_bands(self):
        """Test inconsistent band values raise ValueError"""
        with self.assertRaises(ValueError):
            # Lower > Middle
            BollingerBandsResult(valid=True, upper_band=110, middle_band=90, lower_band=95, bandwidth=0.2, percent_b=0.5, price_above_upper=False, price_below_lower=False)
        with self.assertRaises(ValueError):
            # Middle > Upper
            BollingerBandsResult(valid=True, upper_band=90, middle_band=95, lower_band=80, bandwidth=0.1, percent_b=0.5, price_above_upper=False, price_below_lower=False)

    def test_negative_bandwidth(self):
        """Test negative bandwidth raises ValueError (though bands should prevent this)"""
        # This scenario is unlikely given band calculation but tests validation
        with self.assertRaises(ValueError):
             BollingerBandsResult(
                valid=True,
                upper_band=100, middle_band=105, lower_band=110, # Inconsistent bands needed
                bandwidth=-0.1, percent_b=0.5, price_above_upper=False, price_below_lower=False
            )

    def test_price_above_upper(self):
        """Test price_above_upper flag"""
        result = BollingerBandsResult(valid=True, upper_band=100, middle_band=90, lower_band=80, bandwidth=0.22, percent_b=1.1, price_above_upper=True, price_below_lower=False)
        self.assertTrue(result.price_above_upper)
        self.assertFalse(result.price_below_lower)

    def test_price_below_lower(self):
        """Test price_below_lower flag"""
        result = BollingerBandsResult(valid=True, upper_band=100, middle_band=90, lower_band=80, bandwidth=0.22, percent_b=-0.1, price_above_upper=False, price_below_lower=True)
        self.assertFalse(result.price_above_upper)
        self.assertTrue(result.price_below_lower)


class TestInvalidMethodBollinger(unittest.TestCase):
    """Tests for the invalid class method on BollingerBandsResult"""

    def test_invalid_method(self):
        """Test the invalid class method returns a properly configured instance"""
        result = BollingerBandsResult.invalid()
        self.assertFalse(result.valid)
        # Check all fields are default/False
        self.assertEqual(result.upper_band, 0.0)
        self.assertEqual(result.middle_band, 0.0)
        self.assertEqual(result.lower_band, 0.0)
        self.assertEqual(result.bandwidth, 0.0)
        self.assertEqual(result.percent_b, 0.0)
        self.assertFalse(result.price_above_upper)
        self.assertFalse(result.price_below_lower)

    def test_invalid_method_immutability(self):
        """Test that invalid results are immutable"""
        result = BollingerBandsResult.invalid()
        with self.assertRaises(AttributeError):
            result.valid = True


class TestCalculateBollingerBands(unittest.TestCase):
    def setUp(self):
        """Set up test data and parameters"""
        # Need enough data for window=20
        self.valid_close = pd.Series(np.linspace(100, 120, 30))
        self.default_params = BollingerBandsParams.default()  # window=20, dev=2
        self.custom_params = BollingerBandsParams(window=10, window_dev=1.5)

    @patch(
        "quantforge.signals.bollinger_bands.bollinger_bands.ta.volatility.BollingerBands"
    )
    def test_empty_data(self, mock_bb_indicator):
        """Test with empty data returns invalid result"""
        result = calculate_bollinger_bands(pd.Series([]), self.default_params)
        self.assertFalse(result.valid)
        mock_bb_indicator.assert_not_called()

    @patch(
        "quantforge.signals.bollinger_bands.bollinger_bands.ta.volatility.BollingerBands"
    )
    def test_insufficient_data(self, mock_bb_indicator):
        """Test with insufficient data returns invalid result"""
        short_close = pd.Series(range(100, 105)) # Only 5 points, need 20
        result = calculate_bollinger_bands(short_close, self.default_params)
        self.assertFalse(result.valid)
        mock_bb_indicator.assert_not_called()

    @patch(
        "quantforge.signals.bollinger_bands.bollinger_bands.ta.volatility.BollingerBands"
    )
    def test_normal_data(self, mock_bb_indicator):
        """Test with normal data returns valid result"""
        mock_instance = mock_bb_indicator.return_value
        # Mock the series returned by the indicator methods
        mock_instance.bollinger_hband.return_value = pd.Series([110.0])
        mock_instance.bollinger_mavg.return_value = pd.Series([100.0])
        mock_instance.bollinger_lband.return_value = pd.Series([90.0])
        mock_instance.bollinger_wband.return_value = pd.Series([20.0]) # Width
        mock_instance.bollinger_pband.return_value = pd.Series([0.5])  # %B

        # Assume latest close price for testing flags
        latest_close = 95.0
        self.valid_close.iloc[-1] = latest_close # Ensure the last element is used

        result = calculate_bollinger_bands(self.valid_close, self.default_params)

        mock_bb_indicator.assert_called_once_with(
            close=self.valid_close,
            window=self.default_params.window,
            window_dev=self.default_params.window_dev,
            fillna=False,
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.upper_band, 110.0)
        self.assertEqual(result.middle_band, 100.0)
        self.assertEqual(result.lower_band, 90.0)
        self.assertEqual(result.bandwidth, 20.0)
        self.assertEqual(result.percent_b, 0.5)
        # Check flags based on mocked values and latest_close=95.0
        self.assertFalse(result.price_above_upper)
        self.assertFalse(result.price_below_lower)

    @patch(
        "quantforge.signals.bollinger_bands.bollinger_bands.ta.volatility.BollingerBands"
    )
    def test_price_above_upper_flag(self, mock_bb_indicator):
        """Test correctly identifies price above upper band"""
        mock_instance = mock_bb_indicator.return_value
        mock_instance.bollinger_hband.return_value = pd.Series([110.0])
        mock_instance.bollinger_mavg.return_value = pd.Series([100.0])
        mock_instance.bollinger_lband.return_value = pd.Series([90.0])
        mock_instance.bollinger_wband.return_value = pd.Series([20.0])
        mock_instance.bollinger_pband.return_value = pd.Series([1.1]) # %B > 1

        latest_close = 115.0 # Price above upper band
        self.valid_close.iloc[-1] = latest_close

        result = calculate_bollinger_bands(self.valid_close, self.default_params)
        self.assertTrue(result.valid)
        self.assertTrue(result.price_above_upper)
        self.assertFalse(result.price_below_lower)

    @patch(
        "quantforge.signals.bollinger_bands.bollinger_bands.ta.volatility.BollingerBands"
    )
    def test_price_below_lower_flag(self, mock_bb_indicator):
        """Test correctly identifies price below lower band"""
        mock_instance = mock_bb_indicator.return_value
        mock_instance.bollinger_hband.return_value = pd.Series([110.0])
        mock_instance.bollinger_mavg.return_value = pd.Series([100.0])
        mock_instance.bollinger_lband.return_value = pd.Series([90.0])
        mock_instance.bollinger_wband.return_value = pd.Series([20.0])
        mock_instance.bollinger_pband.return_value = pd.Series([-0.1]) # %B < 0

        latest_close = 85.0 # Price below lower band
        self.valid_close.iloc[-1] = latest_close

        result = calculate_bollinger_bands(self.valid_close, self.default_params)
        self.assertTrue(result.valid)
        self.assertFalse(result.price_above_upper)
        self.assertTrue(result.price_below_lower)

    @patch(
        "quantforge.signals.bollinger_bands.bollinger_bands.ta.volatility.BollingerBands"
    )
    def test_nan_result_from_ta(self, mock_bb_indicator):
        """Test with NaN result from ta library returns invalid"""
        mock_instance = mock_bb_indicator.return_value
        # Return one NaN series, others valid
        mock_instance.bollinger_hband.return_value = pd.Series([np.nan])
        mock_instance.bollinger_mavg.return_value = pd.Series([100.0])
        mock_instance.bollinger_lband.return_value = pd.Series([90.0])
        mock_instance.bollinger_wband.return_value = pd.Series([20.0])
        mock_instance.bollinger_pband.return_value = pd.Series([0.5])

        result = calculate_bollinger_bands(self.valid_close, self.default_params)
        self.assertFalse(result.valid)

    @patch(
        "quantforge.signals.bollinger_bands.bollinger_bands.ta.volatility.BollingerBands"
    )
    def test_empty_series_from_ta(self, mock_bb_indicator):
        """Test with empty series result from ta library returns invalid"""
        mock_instance = mock_bb_indicator.return_value
        # Return one empty series, others valid
        mock_instance.bollinger_hband.return_value = pd.Series([], dtype=float)
        mock_instance.bollinger_mavg.return_value = pd.Series([100.0])
        mock_instance.bollinger_lband.return_value = pd.Series([90.0])
        mock_instance.bollinger_wband.return_value = pd.Series([20.0])
        mock_instance.bollinger_pband.return_value = pd.Series([0.5])

        result = calculate_bollinger_bands(self.valid_close, self.default_params)
        self.assertFalse(result.valid)


if __name__ == "__main__":
    unittest.main() 