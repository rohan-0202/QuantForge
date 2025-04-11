import pytest
from quantforge.signals.macd.macd_params import MacdParams


@pytest.mark.unit
class TestMacdParams:
    """Tests for the MacdParams class."""

    def test_initialization_valid_params(self):
        """Test MacdParams initialization with valid parameters."""
        params = MacdParams(fast_period=12, slow_period=26, signal_period=9)

        assert params.fast_period == 12
        assert params.slow_period == 26
        assert params.signal_period == 9

    def test_default_params(self):
        """Test MacdParams default constructor provides expected values."""
        params = MacdParams.default()

        assert params.fast_period == 12
        assert params.slow_period == 26
        assert params.signal_period == 9

    def test_immutability(self):
        """Test MacdParams is immutable (frozen dataclass)."""
        params = MacdParams(fast_period=12, slow_period=26, signal_period=9)

        with pytest.raises(AttributeError):
            params.fast_period = 10

    def test_validation_fast_period(self):
        """Test validation for fast_period parameter."""
        # Test zero value
        with pytest.raises(ValueError, match="fast_period must be greater than 0"):
            MacdParams(fast_period=0, slow_period=26, signal_period=9)

        # Test negative value
        with pytest.raises(ValueError, match="fast_period must be greater than 0"):
            MacdParams(fast_period=-5, slow_period=26, signal_period=9)

    def test_validation_slow_period(self):
        """Test validation for slow_period parameter."""
        # Test zero value
        with pytest.raises(ValueError, match="slow_period must be greater than 0"):
            MacdParams(fast_period=12, slow_period=0, signal_period=9)

        # Test negative value
        with pytest.raises(ValueError, match="slow_period must be greater than 0"):
            MacdParams(fast_period=12, slow_period=-10, signal_period=9)

    def test_validation_signal_period(self):
        """Test validation for signal_period parameter."""
        # Test zero value
        with pytest.raises(ValueError, match="signal_period must be greater than 0"):
            MacdParams(fast_period=12, slow_period=26, signal_period=0)

        # Test negative value
        with pytest.raises(ValueError, match="signal_period must be greater than 0"):
            MacdParams(fast_period=12, slow_period=26, signal_period=-5)

    def test_validation_fast_less_than_slow(self):
        """Test validation ensuring fast_period is less than slow_period."""
        # Test equal value
        with pytest.raises(ValueError, match="fast_period must be less than slow_period"):
            MacdParams(fast_period=26, slow_period=26, signal_period=9)

        # Test fast > slow
        with pytest.raises(ValueError, match="fast_period must be less than slow_period"):
            MacdParams(fast_period=30, slow_period=26, signal_period=9)

    def test_realistic_values(self):
        """Test with realistic MACD parameter values."""
        # Test typical MACD settings
        params = MacdParams(fast_period=12, slow_period=26, signal_period=9)
        assert params.fast_period == 12
        assert params.slow_period == 26
        assert params.signal_period == 9

        # Test alternative MACD settings
        params = MacdParams(fast_period=5, slow_period=35, signal_period=5)
        assert params.fast_period == 5
        assert params.slow_period == 35
        assert params.signal_period == 5 