import pytest
from quantforge.signals.bollinger_bands.bollinger_bands_params import BollingerBandsParams


@pytest.mark.unit
class TestBollingerBandsParams:
    """Tests for the BollingerBandsParams class."""

    def test_initialization_valid_params(self):
        """Test BollingerBandsParams initialization with valid parameters."""
        params = BollingerBandsParams(window=20, window_dev=2)
        assert params.window == 20
        assert params.window_dev == 2

    def test_default_params(self):
        """Test BollingerBandsParams default constructor provides expected values."""
        params = BollingerBandsParams.default()
        assert params.window == 20
        assert params.window_dev == 2

    def test_immutability(self):
        """Test BollingerBandsParams is immutable (frozen dataclass)."""
        params = BollingerBandsParams.default()
        with pytest.raises(AttributeError):
            params.window = 10

    def test_validation_window(self):
        """Test validation for window parameter."""
        with pytest.raises(ValueError, match="window must be greater than 0"):
            BollingerBandsParams(window=0, window_dev=2)
        with pytest.raises(ValueError, match="window must be greater than 0"):
            BollingerBandsParams(window=-5, window_dev=2)

    def test_validation_window_dev(self):
        """Test validation for window_dev parameter."""
        with pytest.raises(ValueError, match="window_dev \\(standard deviations\\) must be greater than 0"):
            BollingerBandsParams(window=20, window_dev=0)
        with pytest.raises(ValueError, match="window_dev \\(standard deviations\\) must be greater than 0"):
            BollingerBandsParams(window=20, window_dev=-1)

    def test_realistic_values(self):
        """Test with realistic Bollinger Bands parameter values."""
        params = BollingerBandsParams(window=50, window_dev=2.5)
        assert params.window == 50
        assert params.window_dev == 2.5 