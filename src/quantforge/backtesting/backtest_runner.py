from quantforge.backtesting.backtest_config import BacktestConfig
import click
import json
from datetime import datetime, timedelta
from quantforge.strategies.strategy_factory import StrategyFactory
from quantforge.backtesting.backtest_dataloader import load_data
from quantforge.strategies.abstract_strategy import StrategyInputData
from loguru import logger


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
    _: StrategyInputData = load_data(config, strategy, config.initial_portfolio)

    # now that we have loaded the data we can iterate over the days and run the strategy
    # we will start from the first day of the portfolio and go till config.end_date
    # if config.end_date is not provided we will go till the last day of the data
    if config.end_date is None:
        end_date = datetime.now().date()
    else:
        end_date = config.end_date

    # TODO: given the

    current_date = config.initial_portfolio.start_date
    while current_date <= end_date:
        # check if we have data for current_date
        # slice the input_data so that it only shows data till current_date
        # gather the ohlcd data of the next day for each tradeable item
        # call execute of the strategy with the input_data and the ohlcd data
        # update the portfolio with the new positions
        # increment the current_date

        current_date += timedelta(days=1)


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
