import pytest
from quantforge.signals.stochastic_oscillator.stochastic_oscillator_params import (
    StochasticOscillatorParams,
)


@pytest.mark.unit
class TestStochasticOscillatorParams:
    """Tests for the StochasticOscillatorParams class."""

    def test_initialization_valid_params(self):
        """Test StochasticOscillatorParams initialization with valid parameters."""
        params = StochasticOscillatorParams(
            k_period=14,
            d_period=3,
            smooth_k=3,
            oversold_threshold=20,
            overbought_threshold=80,
        )
        assert params.k_period == 14
        assert params.d_period == 3
        assert params.smooth_k == 3
        assert params.oversold_threshold == 20
        assert params.overbought_threshold == 80

    def test_default_params(self):
        """Test StochasticOscillatorParams default constructor provides expected values."""
        params = StochasticOscillatorParams.default()
        assert params.k_period == 14
        assert params.d_period == 3
        assert params.smooth_k == 3
        assert params.oversold_threshold == 20
        assert params.overbought_threshold == 80

    def test_immutability(self):
        """Test StochasticOscillatorParams is immutable (frozen dataclass)."""
        params = StochasticOscillatorParams.default()
        with pytest.raises(AttributeError):
            params.k_period = 10

    def test_validation_k_period(self):
        """Test validation for k_period parameter."""
        with pytest.raises(ValueError, match="k_period must be greater than 0"):
            StochasticOscillatorParams.default()._replace(k_period=0) # Use default replace for brevity
        with pytest.raises(ValueError, match="k_period must be greater than 0"):
            StochasticOscillatorParams.default()._replace(k_period=-5)

    def test_validation_d_period(self):
        """Test validation for d_period parameter."""
        with pytest.raises(ValueError, match="d_period must be greater than 0"):
            StochasticOscillatorParams.default()._replace(d_period=0)
        with pytest.raises(ValueError, match="d_period must be greater than 0"):
            StochasticOscillatorParams.default()._replace(d_period=-1)

    def test_validation_smooth_k(self):
        """Test validation for smooth_k parameter."""
        with pytest.raises(ValueError, match="smooth_k must be greater than 0"):
            StochasticOscillatorParams.default()._replace(smooth_k=0)
        with pytest.raises(ValueError, match="smooth_k must be greater than 0"):
            StochasticOscillatorParams.default()._replace(smooth_k=-2)

    def test_validation_oversold_threshold(self):
        """Test validation for oversold_threshold parameter."""
        with pytest.raises(ValueError, match="oversold_threshold must be between 0 and 100"):
            StochasticOscillatorParams.default()._replace(oversold_threshold=-1)
        with pytest.raises(ValueError, match="oversold_threshold must be between 0 and 100"):
            StochasticOscillatorParams.default()._replace(oversold_threshold=101)

    def test_validation_overbought_threshold(self):
        """Test validation for overbought_threshold parameter."""
        with pytest.raises(ValueError, match="overbought_threshold must be between 0 and 100"):
            StochasticOscillatorParams.default()._replace(overbought_threshold=-1)
        with pytest.raises(ValueError, match="overbought_threshold must be between 0 and 100"):
            StochasticOscillatorParams.default()._replace(overbought_threshold=101)

    def test_validation_threshold_order(self):
        """Test validation that oversold must be less than overbought."""
        with pytest.raises(ValueError, match="oversold_threshold must be less than overbought_threshold"):
            StochasticOscillatorParams.default()._replace(oversold_threshold=80, overbought_threshold=80)
        with pytest.raises(ValueError, match="oversold_threshold must be less than overbought_threshold"):
            StochasticOscillatorParams.default()._replace(oversold_threshold=90, overbought_threshold=80)

    # Add a helper method to replace fields in frozen dataclass for tests
    @staticmethod
    def _replace(self, **changes):
        import dataclasses
        return dataclasses.replace(self, **changes)

# Monkey patch the _replace method onto the class for easier testing
StochasticOscillatorParams._replace = TestStochasticOscillatorParams._replace 