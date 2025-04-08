from quantforge.backtesting.backtest_config import BacktestConfig
import click
import json
import logging

logger = logging.getLogger(__name__)


def run_backtest(config: BacktestConfig):
    pass


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
