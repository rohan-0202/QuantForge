import pandas as pd
from dataclasses import dataclass
from quantforge.signals.macd.macd_params import MacdParams
import ta


@dataclass(frozen=True)
class MacdResult:
    valid: bool
    macd_line: float
    signal_line: float
    histogram: float
    # Optional: Add crossover flags if needed
    # bullish_crossover: bool
    # bearish_crossover: bool

    @classmethod
    def invalid(cls) -> "MacdResult":
        """Return a bulletproof invalid MACD result instance"""
        return cls(valid=False, macd_line=0.0, signal_line=0.0, histogram=0.0)


def calculate_macd(data: pd.Series, params: MacdParams) -> MacdResult:
    """Calculate the MACD (Moving Average Convergence Divergence).

    Args:
        data: A pandas Series of close prices.
        params: An instance of MacdParams containing the periods.

    Returns:
        An instance of MacdResult containing the calculated MACD values.
    """
    # Ensure enough data points for MACD calculation
    # The ta library's MACD requires roughly slow_period + signal_period data points
    # to produce non-NaN values. Add a small buffer for safety.
    required_length = params.slow_period + params.signal_period
    if data.empty or len(data) < required_length:
        return MacdResult.invalid()

    # Calculate MACD using the ta library
    macd_indicator = ta.trend.MACD(
        close=data,
        window_slow=params.slow_period,
        window_fast=params.fast_period,
        window_sign=params.signal_period,
        fillna=False
    )

    macd_line = macd_indicator.macd()
    signal_line = macd_indicator.macd_signal()
    histogram = macd_indicator.macd_diff() # Histogram is MACD line - Signal line

    # Check if the latest values are valid
    if (
        macd_line.empty or signal_line.empty or histogram.empty or
        pd.isna(macd_line.iloc[-1]) or
        pd.isna(signal_line.iloc[-1]) or
        pd.isna(histogram.iloc[-1])
    ):
        return MacdResult.invalid()

    latest_macd = macd_line.iloc[-1]
    latest_signal = signal_line.iloc[-1]
    latest_histogram = histogram.iloc[-1]

    # Optional: Calculate crossovers
    # bullish_crossover = latest_macd > latest_signal and macd_line.iloc[-2] <= signal_line.iloc[-2]
    # bearish_crossover = latest_macd < latest_signal and macd_line.iloc[-2] >= signal_line.iloc[-2]

    return MacdResult(
        valid=True,
        macd_line=latest_macd,
        signal_line=latest_signal,
        histogram=latest_histogram,
        # bullish_crossover=bullish_crossover,
        # bearish_crossover=bearish_crossover,
    ) 