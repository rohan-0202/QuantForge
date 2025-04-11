import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from quantforge.signals.obv.obv import ObvResult, calculate_obv


class TestObvResult(unittest.TestCase):
    def test_valid_obv_result(self):
        """Test creating a valid ObvResult"""
        result = ObvResult(valid=True, obv=10000.0)
        self.assertTrue(result.valid)
        self.assertEqual(result.obv, 10000.0)

    def test_invalid_obv_result(self):
        """Test creating an invalid ObvResult sets appropriate defaults"""
        result = ObvResult.invalid()
        self.assertFalse(result.valid)
        self.assertEqual(result.obv, 0.0)

    def test_invalid_method_immutability(self):
        """Test that invalid results are immutable"""
        result = ObvResult.invalid()
        with self.assertRaises(AttributeError):
            result.valid = True


class TestCalculateObv(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        # Need closing prices and volume
        self.close_data = pd.Series([10, 11, 10.5, 12, 11.5, 13])
        self.volume_data = pd.Series([1000, 1500, 1200, 1800, 1600, 2000])
        self.mismatched_volume = pd.Series([1000, 1500]) # Mismatched length
        self.insufficient_data = pd.Series([10]) # Only one data point

    @patch("quantforge.signals.obv.obv.ta.volume.OnBalanceVolumeIndicator")
    def test_empty_close_data(self, mock_obv_indicator):
        """Test calculate_obv with empty close data returns invalid result."""
        empty_close = pd.Series([], dtype=float)
        result = calculate_obv(empty_close, self.volume_data)
        self.assertFalse(result.valid)
        mock_obv_indicator.assert_not_called()

    @patch("quantforge.signals.obv.obv.ta.volume.OnBalanceVolumeIndicator")
    def test_empty_volume_data(self, mock_obv_indicator):
        """Test calculate_obv with empty volume data returns invalid result."""
        empty_volume = pd.Series([], dtype=float)
        result = calculate_obv(self.close_data, empty_volume)
        self.assertFalse(result.valid)
        mock_obv_indicator.assert_not_called()

    @patch("quantforge.signals.obv.obv.ta.volume.OnBalanceVolumeIndicator")
    def test_mismatched_data_length(self, mock_obv_indicator):
        """Test calculate_obv with mismatched data lengths returns invalid result."""
        result = calculate_obv(self.close_data, self.mismatched_volume)
        self.assertFalse(result.valid)
        mock_obv_indicator.assert_not_called()

    @patch("quantforge.signals.obv.obv.ta.volume.OnBalanceVolumeIndicator")
    def test_insufficient_data(self, mock_obv_indicator):
        """Test calculate_obv with insufficient data ( < 2 points) returns invalid."""
        # Need volume data of the same insufficient length
        insufficient_volume = pd.Series([100])
        result = calculate_obv(self.insufficient_data, insufficient_volume)
        self.assertFalse(result.valid)
        mock_obv_indicator.assert_not_called()

    @patch("quantforge.signals.obv.obv.ta.volume.OnBalanceVolumeIndicator")
    def test_normal_data(self, mock_obv_indicator):
        """Test calculate_obv with normal data returns valid result."""
        # Mock the OBV indicator and its method
        mock_instance = mock_obv_indicator.return_value
        mock_instance.on_balance_volume.return_value = pd.Series([5000.0])

        result = calculate_obv(self.close_data, self.volume_data)

        # Verify OBV indicator was called with correct parameters
        mock_obv_indicator.assert_called_once_with(
            close=self.close_data,
            volume=self.volume_data,
            fillna=False
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.obv, 5000.0)

    @patch("quantforge.signals.obv.obv.ta.volume.OnBalanceVolumeIndicator")
    def test_nan_obv_result(self, mock_obv_indicator):
        """Test calculate_obv with NaN result from ta library returns invalid."""
        mock_instance = mock_obv_indicator.return_value
        mock_instance.on_balance_volume.return_value = pd.Series([np.nan])

        result = calculate_obv(self.close_data, self.volume_data)

        self.assertFalse(result.valid)
        self.assertEqual(result.obv, 0.0)

    @patch("quantforge.signals.obv.obv.ta.volume.OnBalanceVolumeIndicator")
    def test_empty_obv_series(self, mock_obv_indicator):
        """Test calculate_obv with empty series from ta library returns invalid."""
        mock_instance = mock_obv_indicator.return_value
        mock_instance.on_balance_volume.return_value = pd.Series([], dtype=float)

        result = calculate_obv(self.close_data, self.volume_data)

        self.assertFalse(result.valid)
        self.assertEqual(result.obv, 0.0)


if __name__ == "__main__":
    unittest.main() 