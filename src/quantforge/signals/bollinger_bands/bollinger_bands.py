import pandas as pd
from dataclasses import dataclass
from quantforge.signals.bollinger_bands.bollinger_bands_params import (
    BollingerBandsParams,
)
import ta


@dataclass(frozen=True)
class BollingerBandsResult:
    valid: bool
    upper_band: float
    middle_band: float
    lower_band: float
    bandwidth: float  # (Upper - Lower) / Middle
    percent_b: float  # (Price - Lower) / (Upper - Lower)
    price_above_upper: bool
    price_below_lower: bool

    def __post_init__(self):
        if self.valid:
            if self.lower_band > self.middle_band or self.middle_band > self.upper_band:
                raise ValueError("Band values are inconsistent: Lower > Middle or Middle > Upper")
            # Bandwidth can be zero if bands coincide, but not negative
            if self.bandwidth < 0:
                raise ValueError("Bandwidth cannot be negative")

    @classmethod
    def invalid(cls) -> "BollingerBandsResult":
        """Return a bulletproof invalid Bollinger Bands result instance"""
        return cls(
            valid=False,
            upper_band=0.0,
            middle_band=0.0,
            lower_band=0.0,
            bandwidth=0.0,
            percent_b=0.0,
            price_above_upper=False,
            price_below_lower=False,
        )


def calculate_bollinger_bands(
    close: pd.Series, params: BollingerBandsParams
) -> BollingerBandsResult:
    if close.empty or len(close) < params.window:
        # Return invalid result if not enough data
        return BollingerBandsResult.invalid()

    # Use the ta library to calculate Bollinger Bands
    bb_indicator = ta.volatility.BollingerBands(
        close=close, window=params.window, window_dev=params.window_dev, fillna=False
    )

    # High band
    upper_band_series = bb_indicator.bollinger_hband()
    # Middle band
    middle_band_series = bb_indicator.bollinger_mavg()
    # Low band
    lower_band_series = bb_indicator.bollinger_lband()
    # Bandwidth
    bandwidth_series = bb_indicator.bollinger_wband()
    # %B indicator
    percent_b_series = bb_indicator.bollinger_pband()

    if (
        upper_band_series.empty
        or middle_band_series.empty
        or lower_band_series.empty
        or bandwidth_series.empty
        or percent_b_series.empty
        or pd.isna(upper_band_series.iloc[-1])
        or pd.isna(middle_band_series.iloc[-1])
        or pd.isna(lower_band_series.iloc[-1])
        or pd.isna(bandwidth_series.iloc[-1])
        or pd.isna(percent_b_series.iloc[-1])
    ):
        return BollingerBandsResult.invalid()

    latest_upper = upper_band_series.iloc[-1]
    latest_middle = middle_band_series.iloc[-1]
    latest_lower = lower_band_series.iloc[-1]
    latest_bandwidth = bandwidth_series.iloc[-1]
    latest_percent_b = percent_b_series.iloc[-1]
    latest_close = close.iloc[-1]

    return BollingerBandsResult(
        valid=True,
        upper_band=latest_upper,
        middle_band=latest_middle,
        lower_band=latest_lower,
        bandwidth=latest_bandwidth,
        percent_b=latest_percent_b,
        price_above_upper=latest_close > latest_upper,
        price_below_lower=latest_close < latest_lower,
    ) 