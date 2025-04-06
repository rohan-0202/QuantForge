import unittest
import pytest
from quantforge.strategies.trading_signal import TradingSignalType, TradingSignal


class TestTradingSignalType(unittest.TestCase):
    """Test cases for the TradingSignalType enumeration."""

    def test_enum_values(self):
        """Verify that the enum has the expected values."""
        self.assertTrue(hasattr(TradingSignalType, "BUY"))
        self.assertTrue(hasattr(TradingSignalType, "SELL"))
        self.assertTrue(hasattr(TradingSignalType, "HOLD"))

    def test_enum_uniqueness(self):
        """Verify that all enum values are unique."""
        values = [TradingSignalType.BUY, TradingSignalType.SELL, TradingSignalType.HOLD]
        self.assertEqual(len(values), len(set(values)))


class TestTradingSignal(unittest.TestCase):
    """Test cases for the TradingSignal class."""

    def test_valid_buy_signal(self):
        """Test creation of a valid BUY signal."""
        signal = TradingSignal(TradingSignalType.BUY, 0.8)
        self.assertEqual(signal.signal_type, TradingSignalType.BUY)
        self.assertEqual(signal.signal_strength, 0.8)

    def test_valid_sell_signal(self):
        """Test creation of a valid SELL signal."""
        signal = TradingSignal(TradingSignalType.SELL, -0.7)
        self.assertEqual(signal.signal_type, TradingSignalType.SELL)
        self.assertEqual(signal.signal_strength, -0.7)

    def test_valid_hold_signal(self):
        """Test creation of a valid HOLD signal."""
        signal = TradingSignal(TradingSignalType.HOLD, 0.5)
        self.assertEqual(signal.signal_type, TradingSignalType.HOLD)
        self.assertEqual(signal.signal_strength, 0.5)

    def test_buy_signal_validation(self):
        """Test BUY signal validation constraints."""
        # Test upper bound
        signal = TradingSignal(TradingSignalType.BUY, 1.0)
        self.assertEqual(signal.signal_strength, 1.0)

        # Test invalid upper bound
        with pytest.raises(
            AssertionError, match="Buy signal strength must be between 0 and 1"
        ):
            TradingSignal(TradingSignalType.BUY, 1.5)

        # Test invalid lower bound
        with pytest.raises(
            AssertionError, match="Buy signal strength must be between 0 and 1"
        ):
            TradingSignal(TradingSignalType.BUY, 0)

    def test_sell_signal_validation(self):
        """Test SELL signal validation constraints."""
        # Test lower bound
        signal = TradingSignal(TradingSignalType.SELL, -1.0)
        self.assertEqual(signal.signal_strength, -1.0)

        # Test invalid lower bound
        with pytest.raises(
            AssertionError, match="Sell signal strength must be between -1 and 0"
        ):
            TradingSignal(TradingSignalType.SELL, -1.5)

        # Test invalid upper bound
        with pytest.raises(
            AssertionError, match="Sell signal strength must be between -1 and 0"
        ):
            TradingSignal(TradingSignalType.SELL, 0)

    def test_hold_signal_validation(self):
        """Test HOLD signal validation constraints."""
        # Test bounds
        signal_min = TradingSignal(TradingSignalType.HOLD, 0)
        signal_max = TradingSignal(TradingSignalType.HOLD, 1.0)
        self.assertEqual(signal_min.signal_strength, 0)
        self.assertEqual(signal_max.signal_strength, 1.0)

        # Test invalid bound
        with pytest.raises(
            AssertionError, match="Hold signal strength must be between 0 and 1"
        ):
            TradingSignal(TradingSignalType.HOLD, 1.5)

    def test_getter_methods(self):
        """Test the getter methods of TradingSignal."""
        buy_signal = TradingSignal(TradingSignalType.BUY, 0.75)
        sell_signal = TradingSignal(TradingSignalType.SELL, -0.75)

        self.assertEqual(buy_signal.get_signal_type(), TradingSignalType.BUY)
        self.assertEqual(buy_signal.get_signal_strength(), 0.75)

        self.assertEqual(sell_signal.get_signal_type(), TradingSignalType.SELL)
        self.assertEqual(sell_signal.get_signal_strength(), -0.75)

    def test_immutability(self):
        """Test that the TradingSignal object is immutable."""
        signal = TradingSignal(TradingSignalType.BUY, 0.8)
        with pytest.raises(AttributeError):
            signal.signal_type = TradingSignalType.SELL
        with pytest.raises(AttributeError):
            signal.signal_strength = 0.2


if __name__ == "__main__":
    unittest.main()
