from quantforge.backtesting.backtest_config import BacktestConfig
import click
import json
from datetime import datetime
from quantforge.strategies.strategy_factory import StrategyFactory
from quantforge.backtesting.backtest_dataloader import load_data
from quantforge.strategies.abstract_strategy import StrategyInputData
from quantforge.backtesting.trading_dates import extract_trading_dates
from loguru import logger
from quantforge.backtesting.masked_data import create_masked_data
from quantforge.backtesting.get_ohlc_data import extract_ohlc_data
from quantforge.strategies.abstract_strategy import AbstractStrategy
from datetime import date
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.ohlc import OHLCData


def extract_prices(data: dict[TradeableItem, OHLCData]) -> dict[TradeableItem, float]:
    if data is None:
        return {}
    return {item: data[item].close for item in data}


def backtest_loop(
    filtered_trading_dates: list[date],
    input_data: StrategyInputData,
    strategy: AbstractStrategy,
) -> None:
    """
    Run a backtest using a configuration file.
    """
    # Iterate through each trading day
    for i, current_date in enumerate(filtered_trading_dates):
        logger.info(f"Processing trading day: {current_date}")

        # Create masked data up to the current date
        masked_data = create_masked_data(input_data, current_date)

        # Get next day's data for trade execution
        # If current date is the last trading date, we can't execute trades
        if i < len(filtered_trading_dates) - 1:
            next_date = filtered_trading_dates[i + 1]
            next_day_data = extract_ohlc_data(input_data, strategy.portfolio, next_date)
            # current_date_data = extract_ohlc_data(
            #     input_data, strategy.portfolio, current_date
            # )
            # prices = extract_prices(current_date_data)
            # if prices:
            #     portfolio_value = strategy.portfolio.portfolio_value(prices)
            #     logger.info(f"Portfolio value on {current_date}: {portfolio_value}")
            # Execute the strategy for the current date
            if next_day_data:  # Only execute if we have next day data
                strategy.execute(masked_data, next_day_data)
            else:
                logger.warning(
                    f"Skipping strategy execution for {current_date} due to missing next day data"
                )
        else:
            logger.info(
                f"Reached last trading day {current_date}, no more trades to execute"
            )


def run_backtest(config: BacktestConfig):
    """
    Run a backtest using a configuration file.

    Args:
        config (BacktestConfig): The backtest configuration.
    """
    # Ensure we can load the strategy. Use the strategy factory to load the strategy.
    strategy = StrategyFactory.create_strategy(
        config.strategy_name, config.initial_portfolio
    )

    # now given the data requirements and the tradaable items in the portfolio,
    # load the appropriate data
    input_data: StrategyInputData = load_data(
        config, strategy, config.initial_portfolio
    )

    # now that we have loaded the data we can iterate over the days and run the strategy
    # we will start from the first day of the portfolio and go till config.end_date
    # if config.end_date is not provided we will go till the last day of the data
    if config.end_date is None:
        end_date = datetime.now().date()
    else:
        end_date = config.end_date

    # Extract all trading dates from the input data
    trading_dates = extract_trading_dates(input_data)

    # Filter trading dates to only include dates within our simulation range
    start_date = config.initial_portfolio.start_date
    filtered_trading_dates = [
        date for date in trading_dates if start_date <= date <= end_date
    ]

    if not filtered_trading_dates:
        logger.error(f"No trading dates found between {start_date} and {end_date}")
        return

    logger.info(
        f"Running backtest from {start_date} to {end_date} ({len(filtered_trading_dates)} trading days)"
    )

    backtest_loop(filtered_trading_dates, input_data, strategy)

    # At this point the portfolio has been updated with all the trading activity
    logger.info(f"Backtest complete. Final portfolio: {strategy.portfolio}")


@click.command()
@click.option(
    "--config",
    required=True,
    type=click.Path(exists=True),
    help="Path to the backtest configuration JSON file",
)
def main(config):
    """
    Run a backtest using a configuration file.

    Args:
        config (str): Path to the backtest configuration JSON file.
    """
    logger.info(f"Running backtest with config file: {config}")
    with open(config, "r") as f:
        config_data = json.load(f)
    logger.info(f"Config data: {config_data}")

    backtest_config = BacktestConfig.from_dict(config_data)
    run_backtest(backtest_config)


if __name__ == "__main__":
    main()
