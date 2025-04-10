from quantforge.strategies.data_requirement import DataRequirement
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.strategies.abstract_strategy import StrategyInputData, AbstractStrategy
import pandas as pd
from quantforge.db.db_util import (
    fetch_historical_ticker_data,
    fetch_historical_options_data,
)
from quantforge.backtesting.backtest_config import BacktestConfig
from datetime import timedelta, datetime, date
from loguru import logger


def load_requirement_data(
    data_requirement: DataRequirement,
    tradeable_item: TradeableItem,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """
    Load the data for the given data requirement and tradeable item.
    """
    ticker = tradeable_item.id

    if data_requirement == DataRequirement.TICKER:
        return fetch_historical_ticker_data(
            ticker_symbol=ticker, start_date=start_date, end_date=end_date
        )
    elif data_requirement == DataRequirement.OPTIONS:
        return fetch_historical_options_data(
            ticker_symbol=ticker, start_date=start_date, end_date=end_date
        )
    else:
        raise NotImplementedError(
            f"Data requirement {data_requirement} not implemented"
        )


def load_data(
    config: BacktestConfig, strategy: AbstractStrategy, portfolio: Portfolio
) -> StrategyInputData:
    """
    Load the data for the given data requirements and portfolio.

    This method combines the functionality of loading data for each requirement and
    each tradeable item in the portfolio.
    """
    # now get the data requirements of the strategy
    data_requirements, lookback_days = strategy.get_data_requirements()
    data: StrategyInputData = {}

    start_date = portfolio.start_date - timedelta(days=lookback_days)
    end_date = config.end_date if config.end_date is not None else datetime.now().date()

    logger.info(f"Loading data for portfolio from {start_date} to {end_date}")
    for tradeable_item in portfolio.allowed_tradeable_items:
        tradeable_item_data = {}
        logger.info(f"Loading data for tradeable item {tradeable_item}")
        for data_requirement in data_requirements:
            # Load data for the specific requirement and tradeable item
            logger.info(
                f"Loading data for data requirement {data_requirement} for tradeable item {tradeable_item} for {start_date} to {end_date}"
            )
            tradeable_item_data[data_requirement] = load_requirement_data(
                data_requirement, tradeable_item, start_date, end_date
            )

        data[tradeable_item] = tradeable_item_data

    return data
