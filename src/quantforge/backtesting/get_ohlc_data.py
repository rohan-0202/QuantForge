from quantforge.strategies.abstract_strategy import StrategyInputData
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.ohlc import OHLCData
from quantforge.strategies.data_requirement import DataRequirement
from datetime import date
from loguru import logger
from quantforge.db.df_columns import OPEN, HIGH, LOW, CLOSE, VOLUME


def extract_ohlc_data(
    input_data: StrategyInputData, portfolio: Portfolio, data_date: date
) -> dict[TradeableItem, OHLCData]:
    """
    Extract OHLC data for date data_date

    Args:
        input_data: The full input data
        portfolio: The portfolio to extract the data for
        data_date: The date to extract the data for

    Returns:
        Dictionary mapping TradeableItem to OHLCData for the date data_date
    """
    ohlc_data = {}
    for tradeable_item in portfolio.allowed_tradeable_items:
        # Skip if tradeable_item is not in input_data
        if tradeable_item not in input_data:
            logger.warning(f"No data found for {tradeable_item} in input data")
            continue

        # ensure ticker data is available
        if DataRequirement.TICKER not in input_data[tradeable_item]:
            logger.warning(f"No ticker data found for {tradeable_item}")
            continue

        ticker_data = input_data[tradeable_item][DataRequirement.TICKER]
        # get the ohlc data for the date data_date
        date_data = ticker_data[ticker_data.index.date == data_date]
        if date_data.empty:
            logger.warning(f"No data found for {tradeable_item} on {data_date}")
            continue
        ohlc_data[tradeable_item] = OHLCData(
            date=data_date,
            open=date_data[OPEN].iloc[0],
            high=date_data[HIGH].iloc[0],
            low=date_data[LOW].iloc[0],
            close=date_data[CLOSE].iloc[0],
            volume=date_data[VOLUME].iloc[0],
        )

    return ohlc_data
