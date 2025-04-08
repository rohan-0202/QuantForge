from quantforge.backtesting.backtest_config import BacktestConfig
import click
import json
import logging
from quantforge.strategies.strategy_factory import StrategyFactory
from quantforge.backtesting.backtest_dataloader import load_data

logger = logging.getLogger(__name__)


def run_backtest(config: BacktestConfig):
    """
    Run a backtest using a configuration file.

    Args:
        config (BacktestConfig): The backtest configuration.
    """
    # Ensure we can load the strategy. Use the strategy factory to load the strategy.
    strategy = StrategyFactory.create_strategy(config.strategy_name)

    # now get the data requirements of the strategy
    data_requirements, lookback_days = strategy.get_data_requirements()

    # now given the data requirements and the tradaable items in the portfolio,
    # load the appropriate data
    _ = load_data(data_requirements, lookback_days, config.initial_portfolio)


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

    backtest_config = BacktestConfig(**config_data)
    run_backtest(backtest_config)


if __name__ == "__main__":
    main()
