import pytest
from quantforge.signals.rsi.rsi_params import RsiParams


@pytest.mark.unit
class TestRsiParams:
    """Tests for the RsiParams class."""

    def test_initialization_valid_params(self):
        """Test RsiParams initialization with valid parameters."""
        params = RsiParams(
            rsi_period=14, oversold_threshold=30, overbought_threshold=70
        )

        assert params.rsi_period == 14
        assert params.oversold_threshold == 30
        assert params.overbought_threshold == 70

    def test_default_params(self):
        """Test RsiParams default constructor provides expected values."""
        params = RsiParams.default()

        assert params.rsi_period == 14
        assert params.oversold_threshold == 30
        assert params.overbought_threshold == 70

    def test_immutability(self):
        """Test RsiParams is immutable (frozen dataclass)."""
        params = RsiParams(
            rsi_period=14, oversold_threshold=30, overbought_threshold=70
        )

        with pytest.raises(AttributeError):
            params.rsi_period = 10

    def test_validation_rsi_period(self):
        """Test validation for rsi_period parameter."""
        # Test zero value
        with pytest.raises(ValueError, match="rsi_period must be greater than 0"):
            RsiParams(rsi_period=0, oversold_threshold=30, overbought_threshold=70)

        # Test negative value
        with pytest.raises(ValueError, match="rsi_period must be greater than 0"):
            RsiParams(rsi_period=-5, oversold_threshold=30, overbought_threshold=70)

    def test_validation_oversold_threshold(self):
        """Test validation for oversold_threshold parameter."""
        # Test zero value
        with pytest.raises(
            ValueError, match="oversold_threshold must be greater than 0"
        ):
            RsiParams(rsi_period=14, oversold_threshold=0, overbought_threshold=70)

        # Test negative value
        with pytest.raises(
            ValueError, match="oversold_threshold must be greater than 0"
        ):
            RsiParams(rsi_period=14, oversold_threshold=-10, overbought_threshold=70)

    def test_validation_overbought_threshold(self):
        """Test validation for overbought_threshold parameter."""
        # Test zero value
        with pytest.raises(
            ValueError, match="overbought_threshold must be greater than 0"
        ):
            RsiParams(rsi_period=14, oversold_threshold=30, overbought_threshold=0)

        # Test negative value
        with pytest.raises(
            ValueError, match="overbought_threshold must be greater than 0"
        ):
            RsiParams(rsi_period=14, oversold_threshold=30, overbought_threshold=-10)

    def test_realistic_values(self):
        """Test with realistic RSI parameter values."""
        # Test typical RSI settings
        params = RsiParams(
            rsi_period=14, oversold_threshold=30, overbought_threshold=70
        )
        assert params.rsi_period == 14
        assert params.oversold_threshold == 30
        assert params.overbought_threshold == 70

        # Test custom RSI settings
        params = RsiParams(rsi_period=7, oversold_threshold=20, overbought_threshold=80)
        assert params.rsi_period == 7
        assert params.oversold_threshold == 20
        assert params.overbought_threshold == 80
