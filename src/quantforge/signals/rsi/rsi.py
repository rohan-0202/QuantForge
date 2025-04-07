import pandas as pd
from dataclasses import dataclass
from quantforge.signals.rsi.rsi_params import RsiParams
import ta


@dataclass(frozen=True)
class RsiResult:
    valid: bool
    rsi: float
    oversold: bool
    overbought: bool

    def __post_init__(self):
        if self.valid:
            if self.rsi < 0 or self.rsi > 100:
                raise ValueError("RSI must be between 0 and 100")
            # both oversold and overbought cannot be true
            if self.oversold and self.overbought:
                raise ValueError("oversold and overbought cannot both be true")

    @classmethod
    def invalid(cls) -> "RsiResult":
        """Return a bulletproof invalid RSI result instance"""
        return cls(valid=False, rsi=0.0, oversold=False, overbought=False)


def calculate_rsi(data: pd.Series, params: RsiParams) -> RsiResult:
    if data.empty or len(data) < params.rsi_period:
        # Return invalid result if not enough data
        return RsiResult.invalid()

    # Use the ta library to calculate RSI
    rsi_indicator = ta.momentum.RSIIndicator(
        close=data, window=params.rsi_period, fillna=False
    )
    rsi_series = rsi_indicator.rsi()

    if rsi_series.empty or rsi_series.isna().all() or pd.isna(rsi_series.iloc[-1]):
        return RsiResult.invalid()

    latest_rsi = rsi_series.iloc[-1]

    # Get the thresholds from parameters
    oversold = params.oversold_threshold
    overbought = params.overbought_threshold

    return RsiResult(
        valid=True,
        rsi=latest_rsi,
        oversold=latest_rsi < oversold,
        overbought=latest_rsi > overbought,
    )
