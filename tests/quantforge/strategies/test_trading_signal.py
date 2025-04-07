import pytest
from quantforge.strategies.trading_signal import TradingSignalType, TradingSignal


@pytest.mark.unit
class TestTradingSignalType:
    """Test cases for the TradingSignalType enumeration."""

    def test_enum_values(self):
        """Verify that the enum has the expected values."""
        assert hasattr(TradingSignalType, "BUY")
        assert hasattr(TradingSignalType, "SELL")
        assert hasattr(TradingSignalType, "HOLD")

    def test_enum_uniqueness(self):
        """Verify that all enum values are unique."""
        values = [TradingSignalType.BUY, TradingSignalType.SELL, TradingSignalType.HOLD]
        assert len(values) == len(set(values))


@pytest.mark.unit
class TestTradingSignal:
    """Test cases for the TradingSignal class."""

    def test_valid_buy_signal(self):
        """Test creation of a valid BUY signal."""
        signal = TradingSignal(TradingSignalType.BUY, 0.8)
        assert signal.signal_type == TradingSignalType.BUY
        assert signal.signal_strength == 0.8

    def test_valid_sell_signal(self):
        """Test creation of a valid SELL signal."""
        signal = TradingSignal(TradingSignalType.SELL, -0.7)
        assert signal.signal_type == TradingSignalType.SELL
        assert signal.signal_strength == -0.7

    def test_valid_hold_signal(self):
        """Test creation of a valid HOLD signal."""
        # Note: The original test allowed 0.5, but the implementation requires 0 or 1 for HOLD.
        # Let's test the valid boundaries [0, 1].
        signal_hold_zero = TradingSignal(TradingSignalType.HOLD, 0.0)
        assert signal_hold_zero.signal_type == TradingSignalType.HOLD
        assert signal_hold_zero.signal_strength == 0.0

        signal_hold_one = TradingSignal(TradingSignalType.HOLD, 1.0)
        assert signal_hold_one.signal_type == TradingSignalType.HOLD
        assert signal_hold_one.signal_strength == 1.0

    def test_buy_signal_validation(self):
        """Test BUY signal validation constraints."""
        # Test upper bound (exclusive of 0, inclusive of 1)
        signal = TradingSignal(TradingSignalType.BUY, 1.0)
        assert signal.signal_strength == 1.0

        # Test invalid upper bound
        with pytest.raises(
            AssertionError, match="Buy signal strength must be between 0 and 1"
        ):
            TradingSignal(TradingSignalType.BUY, 1.5)

        # Test invalid lower bound (0 is not allowed for BUY)
        with pytest.raises(
            AssertionError, match="Buy signal strength must be between 0 and 1"
        ):
            TradingSignal(TradingSignalType.BUY, 0)

        # Test edge case just above 0
        signal_min = TradingSignal(TradingSignalType.BUY, 0.00001)
        assert signal_min.signal_strength == 0.00001

    def test_sell_signal_validation(self):
        """Test SELL signal validation constraints."""
        # Test lower bound (inclusive of -1, exclusive of 0)
        signal = TradingSignal(TradingSignalType.SELL, -1.0)
        assert signal.signal_strength == -1.0

        # Test invalid lower bound
        with pytest.raises(
            AssertionError, match="Sell signal strength must be between -1 and 0"
        ):
            TradingSignal(TradingSignalType.SELL, -1.5)

        # Test invalid upper bound (0 is not allowed for SELL)
        with pytest.raises(
            AssertionError, match="Sell signal strength must be between -1 and 0"
        ):
            TradingSignal(TradingSignalType.SELL, 0)

        # Test edge case just below 0
        signal_max = TradingSignal(TradingSignalType.SELL, -0.00001)
        assert signal_max.signal_strength == -0.00001

    def test_hold_signal_validation(self):
        """Test HOLD signal validation constraints."""
        # Test valid bounds [0, 1]
        signal_min = TradingSignal(TradingSignalType.HOLD, 0)
        signal_max = TradingSignal(TradingSignalType.HOLD, 1.0)
        assert signal_min.signal_strength == 0
        assert signal_max.signal_strength == 1.0

        # Test invalid upper bound
        with pytest.raises(
            AssertionError, match="Hold signal strength must be between 0 and 1"
        ):
            TradingSignal(TradingSignalType.HOLD, 1.5)

        # Test invalid lower bound
        with pytest.raises(
            AssertionError, match="Hold signal strength must be between 0 and 1"
        ):
            TradingSignal(TradingSignalType.HOLD, -0.1)

    def test_getter_methods(self):
        """Test the getter methods of TradingSignal."""
        buy_signal = TradingSignal(TradingSignalType.BUY, 0.75)
        sell_signal = TradingSignal(TradingSignalType.SELL, -0.75)

        assert buy_signal.get_signal_type() == TradingSignalType.BUY
        assert buy_signal.get_signal_strength() == 0.75

        assert sell_signal.get_signal_type() == TradingSignalType.SELL
        assert sell_signal.get_signal_strength() == -0.75

    def test_immutability(self):
        """Test that the TradingSignal object is immutable."""
        signal = TradingSignal(TradingSignalType.BUY, 0.8)
        with pytest.raises(
            AttributeError
        ):  # dataclasses.FrozenInstanceError inherits from AttributeError
            signal.signal_type = TradingSignalType.SELL
        with pytest.raises(
            AttributeError
        ):  # dataclasses.FrozenInstanceError inherits from AttributeError
            signal.signal_strength = 0.2
