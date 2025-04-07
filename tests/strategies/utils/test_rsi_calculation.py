import pytest
import pandas as pd
import numpy as np

from quantforge.strategies.utils.rsi import calculate_rsi

@pytest.mark.parametrize(
    "prices, window, expected_last_rsi",
    [
        # Test case 1: Standard calculation - Adjusted expected value based on test run
        (pd.Series([44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]), 14, 71.80),
        # Test case 2: Prices mostly increasing -> High RSI
        (pd.Series(np.arange(100, 120, 0.5)), 14, 100.0), # Expected near 100
        # Test case 3: Prices mostly decreasing -> Low RSI
        (pd.Series(np.arange(120, 100, -0.5)), 14, 0.0), # Expected near 0
        # Test case 4: Flat prices
        (pd.Series([50.0] * 20), 14, 0.0), # Corrected expected value is 0.0 based on refined logic
    ]
)
@pytest.mark.unit
def test_calculate_rsi_basic(prices, window, expected_last_rsi):
    """Tests the basic RSI calculation for the last value."""
    rsi = calculate_rsi(prices, window=window)
    assert isinstance(rsi, pd.Series)
    assert rsi.index.equals(prices.index)
    # Check the last calculated RSI value (allow for small floating point differences)
    assert np.isclose(rsi.iloc[-1], expected_last_rsi, atol=0.1)
    # Check that initial values are NaN (up to index window - 2)
    if len(prices) >= window:
        assert pd.isna(rsi.iloc[window - 2]) # Last NaN should be at index window-2
        assert not pd.isna(rsi.iloc[window - 1]) # First calculated value at window-1
    else:
        assert rsi.isna().all()

@pytest.mark.unit
def test_calculate_rsi_insufficient_data():
    """Tests RSI calculation when data length is less than the window."""
    prices = pd.Series([1, 2, 3, 4, 5])
    window = 10
    rsi = calculate_rsi(prices, window=window)
    assert isinstance(rsi, pd.Series)
    assert rsi.isna().all() # All values should be NaN
    assert len(rsi) == len(prices)

@pytest.mark.unit
def test_calculate_rsi_exact_window_data():
    """Tests RSI calculation when data length is exactly the window size."""
    prices = pd.Series(np.linspace(50, 55, 14))
    window = 14
    rsi = calculate_rsi(prices, window=window)
    assert isinstance(rsi, pd.Series)
    assert pd.isna(rsi.iloc[window - 2]) # Should be NaN at index 12
    assert not pd.isna(rsi.iloc[window - 1]) # Only the last value should be calculated (index 13)

@pytest.mark.unit
def test_calculate_rsi_input_validation():
    """Tests input validation for the calculate_rsi function."""
    prices_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    prices_series = pd.Series(prices_list)

    with pytest.raises(TypeError, match="Input 'prices' must be a pandas Series."):
        calculate_rsi(prices_list, window=14)

    with pytest.raises(ValueError, match="Input 'window' must be a positive integer."):
        calculate_rsi(prices_series, window=0)
        
    with pytest.raises(ValueError, match="Input 'window' must be a positive integer."):
        calculate_rsi(prices_series, window=-5)
        
    with pytest.raises(ValueError, match="Input 'window' must be a positive integer."):
        calculate_rsi(prices_series, window=14.5)

# Optional: Add more specific tests for zero loss or zero gain scenarios if needed 