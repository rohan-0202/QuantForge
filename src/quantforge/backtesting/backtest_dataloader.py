from quantforge.strategies.data_requirement import DataRequirement
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.strategies.abstract_strategy import StrategyInputData
import pandas as pd
from quantforge.db.db_util import get_historical_data, get_options_data
from datetime import timedelta


def load_requirement_data(
    data_requirement: DataRequirement, lookback_days: int, tradeable_item: TradeableItem
) -> pd.DataFrame:
    """
    Load the data for the given data requirement and tradeable item.
    """
    ticker = tradeable_item.id

    if data_requirement == DataRequirement.TICKER:
        return get_historical_data(ticker_symbol=ticker, days=lookback_days)
    elif data_requirement == DataRequirement.OPTIONS:
        return get_options_data(ticker_symbol=ticker, days=lookback_days)
    else:
        raise NotImplementedError(
            f"Data requirement {data_requirement} not implemented"
        )


def load_data(
    data_requirements: list[DataRequirement], lookback_days: int, portfolio: Portfolio
) -> StrategyInputData:
    """
    Load the data for the given data requirements and portfolio.

    This method combines the functionality of loading data for each requirement and
    each tradeable item in the portfolio.
    """
    data: StrategyInputData = {}
    # lookbackdays is really the day the portfolio starts - the lookbackdays
    lookback_days = portfolio.start_date - timedelta(days=lookback_days)
    for tradeable_item in portfolio.tradeable_items:
        tradeable_item_data = {}

        for data_requirement in data_requirements:
            # Load data for the specific requirement and tradeable item
            # Implementation pending
            tradeable_item_data[data_requirement] = load_requirement_data(
                data_requirement, lookback_days, tradeable_item
            )

        data[tradeable_item] = tradeable_item_data

    return data
