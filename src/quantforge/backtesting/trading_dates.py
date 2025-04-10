import pandas as pd
from quantforge.strategies.abstract_strategy import StrategyInputData
from quantforge.strategies.data_requirement import DataRequirement


def extract_trading_dates(input_data: StrategyInputData) -> list:
    """
    Extract all unique trading dates from ticker data in input_data.
    Returns a sorted list of all available trading dates.

    Only considers DataRequirement.TICKER data for each tradeable item.
    Assumes the ticker dataframe has a DatetimeIndex (timestamp).
    """
    all_dates = set()

    for _, item_data in input_data.items():
        # Only consider TICKER data requirement
        if DataRequirement.TICKER in item_data:
            ticker_data = item_data[DataRequirement.TICKER]

            # Assuming ticker data has timestamp as index
            if isinstance(ticker_data.index, pd.DatetimeIndex):
                dates = ticker_data.index.date  # Get date part only (not time)
                all_dates.update(dates)

    # Convert set to sorted list
    trading_dates = sorted(list(all_dates))

    return trading_dates
