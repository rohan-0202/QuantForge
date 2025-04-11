import pandas as pd
from dataclasses import dataclass
import ta


@dataclass(frozen=True)
class ObvResult:
    valid: bool
    obv: float

    @classmethod
    def invalid(cls) -> "ObvResult":
        """Return a bulletproof invalid OBV result instance"""
        return cls(valid=False, obv=0.0)


def calculate_obv(close_data: pd.Series, volume_data: pd.Series) -> ObvResult:
    """Calculate the On-Balance Volume (OBV).

    Args:
        close_data: A pandas Series of close prices.
        volume_data: A pandas Series of volume data.

    Returns:
        An instance of ObvResult containing the latest OBV value.
    """
    # Ensure data is not empty and lengths match
    if close_data.empty or volume_data.empty or len(close_data) != len(volume_data):
        return ObvResult.invalid()

    # Basic check: OBV needs at least 2 data points to compare
    if len(close_data) < 2:
        return ObvResult.invalid()

    # Calculate OBV using the ta library
    obv_indicator = ta.volume.OnBalanceVolumeIndicator(
        close=close_data,
        volume=volume_data,
        fillna=False
    )

    obv_series = obv_indicator.on_balance_volume()

    # Check if the latest value is valid
    if obv_series.empty or pd.isna(obv_series.iloc[-1]):
        return ObvResult.invalid()

    latest_obv = obv_series.iloc[-1]

    return ObvResult(
        valid=True,
        obv=latest_obv,
    ) 