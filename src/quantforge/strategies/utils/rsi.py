import pandas as pd
import numpy as np

def calculate_rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """Calculates the Relative Strength Index (RSI) for a given price series.

    Args:
        prices: A pandas Series containing the price data (e.g., close prices).
        window: The lookback period for calculating RSI (default is 14).

    Returns:
        A pandas Series containing the RSI values, indexed the same as the input prices.
        The initial values corresponding to the lookback window will be NaN.
    """
    if not isinstance(prices, pd.Series):
        raise TypeError("Input 'prices' must be a pandas Series.")
    if not isinstance(window, int) or window <= 0:
        raise ValueError("Input 'window' must be a positive integer.")
    if len(prices) < window:
        # Return a series of NaNs if not enough data
        return pd.Series([float('nan')] * len(prices), index=prices.index)

    # Calculate price differences
    delta = prices.diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Calculate the average gain and loss over the window period
    # Use Exponential Moving Average (EMA) for smoothing, as commonly done for RSI
    # Note: adjust=False is crucial for typical RSI calculation matching TA-Lib etc.
    avg_gain = gain.ewm(com=window - 1, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(com=window - 1, min_periods=window, adjust=False).mean()

    # Calculate Relative Strength (RS)
    rs = avg_gain / avg_loss

    # Calculate RSI
    rsi = 100.0 - (100.0 / (1.0 + rs))

    # Handle edge cases AFTER the main calculation
    # Where avg_loss is zero, RS is infinite, RSI should be 100
    # Be careful not to overwrite legitimate NaNs from the initial window
    rsi.loc[rs == np.inf] = 100.0
    # Where avg_gain is zero (and loss is not), RS is 0, RSI is 0
    # The formula already handles this, but explicit check might be safer depending on float precision
    rsi.loc[avg_gain == 0] = 0.0
    # Ensure that initial NaNs due to insufficient window remain NaN
    # The ewm calculation with min_periods should handle this, but let's be explicit:
    # Recalculate initial NaNs based on the original price series length vs window
    # This step is likely redundant if ewm is used correctly but added for clarity/safety
    initial_nan_count = window - 1
    if len(prices) >= window:
         rsi.iloc[:initial_nan_count] = np.nan
    else: # If less data than window, all should be NaN (already handled at start)
        pass 

    return rsi 