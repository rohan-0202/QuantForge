from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass(frozen=True)
class OHLCData:
    """Type for OHLC price data."""

    open: float
    high: float
    low: float
    close: float
    date: date
    volume: Optional[int] = None

    def __post_init__(self):
        """
        Validates the OHLC data after initialization.

        Ensures:
        - Date is not None
        - At least open price is provided
        """
        assert self.date is not None, "Date must be provided"
        assert self.open >= 0, "Open price must be non-negative"
