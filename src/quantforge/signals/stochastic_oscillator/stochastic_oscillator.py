import pandas as pd
from dataclasses import dataclass
from quantforge.signals.stochastic_oscillator.stochastic_oscillator_params import (
    StochasticOscillatorParams,
)
import ta


@dataclass(frozen=True)
class StochasticOscillatorResult:
    valid: bool
    k_value: float  # %K
    d_value: float  # %D
    oversold: bool
    overbought: bool

    def __post_init__(self):
        if self.valid:
            if not (0 <= self.k_value <= 100):
                raise ValueError("%K must be between 0 and 100")
            if not (0 <= self.d_value <= 100):
                raise ValueError("%D must be between 0 and 100")
            # both oversold and overbought cannot be true
            if self.oversold and self.overbought:
                raise ValueError("oversold and overbought cannot both be true")

    @classmethod
    def invalid(cls) -> "StochasticOscillatorResult":
        """Return a bulletproof invalid Stochastic Oscillator result instance"""
        return cls(
            valid=False, k_value=0.0, d_value=0.0, oversold=False, overbought=False
        )


def calculate_stochastic_oscillator(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    params: StochasticOscillatorParams,
) -> StochasticOscillatorResult:
    required_length = params.k_period + params.smooth_k + params.d_period - 2
    if (
        high.empty
        or low.empty
        or close.empty
        or len(close) < required_length
    ):
        # Return invalid result if not enough data
        return StochasticOscillatorResult.invalid()

    # Use the ta library to calculate Stochastic Oscillator
    stoch_indicator = ta.momentum.StochasticOscillator(
        high=high,
        low=low,
        close=close,
        window=params.k_period,
        smooth_window=params.smooth_k,
        fillna=False,
    )

    k_series = stoch_indicator.stoch()  # %K
    d_series = stoch_indicator.stoch_signal()  # %D (signal line)

    if (
        k_series.empty
        or d_series.empty
        or k_series.isna().all()
        or d_series.isna().all()
        or pd.isna(k_series.iloc[-1])
        or pd.isna(d_series.iloc[-1])
    ):
        return StochasticOscillatorResult.invalid()

    latest_k = k_series.iloc[-1]
    latest_d = d_series.iloc[-1]

    # Get the thresholds from parameters
    oversold = params.oversold_threshold
    overbought = params.overbought_threshold

    # Determine oversold/overbought based on %K
    is_oversold = latest_k < oversold
    is_overbought = latest_k > overbought

    return StochasticOscillatorResult(
        valid=True,
        k_value=latest_k,
        d_value=latest_d,
        oversold=is_oversold,
        overbought=is_overbought,
    ) 