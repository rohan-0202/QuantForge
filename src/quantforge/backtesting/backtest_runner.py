from quantforge.backtesting.backtest_config import BacktestConfig
import click
import json
import pprint # Import pprint for better dictionary printing
from datetime import datetime
import pandas as pd # Add pandas import
from quantforge.strategies.strategy_factory import StrategyFactory
from quantforge.backtesting.backtest_dataloader import load_data
from quantforge.strategies.abstract_strategy import StrategyInputData
from quantforge.backtesting.trading_dates import extract_trading_dates
from loguru import logger
from quantforge.backtesting.masked_data import create_masked_data
from quantforge.backtesting.get_ohlc_data import extract_ohlc_data
from quantforge.strategies.abstract_strategy import AbstractStrategy
from quantforge.qtypes.portfolio_metrics import PortfolioMetrics # Import the metrics class
from datetime import date


def backtest_loop(
    filtered_trading_dates: list[date],
    input_data: StrategyInputData,
    strategy: AbstractStrategy,
    portfolio_metrics: PortfolioMetrics # Pass metrics tracker to the loop
) -> None:
    """
    Run a backtest using a configuration file.
    """
    # Iterate through each trading day
    for i, current_date in enumerate(filtered_trading_dates):
        logger.info(f"Processing trading day: {current_date}")

        # --- Calculate and record portfolio value BEFORE today's execution logic ---
        # Get current day's data for valuation (using open prices for consistency)
        current_day_prices_raw = extract_ohlc_data(input_data, strategy.portfolio, current_date)

        current_value = None
        if current_day_prices_raw:
            # Identify items currently held in the portfolio that need pricing
            items_to_price = {
                item
                for item, positions in strategy.portfolio._open_positions_by_tradeable_item.items()
                if positions # Only if there are open positions for this item
            }

            # Extract the 'Open' price for each required item, if available
            current_prices = {
                item: ohlc.open
                for item, ohlc in current_day_prices_raw.items()
                if item in items_to_price and ohlc and hasattr(ohlc, 'open')
            }

            # If no assets are held, value is just cash.
            if not items_to_price:
                current_value = strategy.portfolio.cash
                portfolio_metrics.update(current_date, current_value)
                logger.debug(f"Recorded portfolio value (cash only) for {current_date}: {current_value:.2f}")
            # Else, check if we have prices for ALL currently held assets
            elif items_to_price.issubset(current_prices.keys()):
                try:
                    current_value = strategy.portfolio.portfolio_value(current_prices)
                    portfolio_metrics.update(current_date, current_value)
                    logger.debug(f"Recorded portfolio value for {current_date}: {current_value:.2f}")
                except ValueError as e:
                    logger.warning(f"Could not calculate portfolio value for {current_date}: {e}. Skipping metrics update.")
                except Exception as e:
                    logger.error(f"Unexpected error calculating/updating metrics for {current_date}: {e}")
            else: # Held assets but missing prices for some
                missing_items = items_to_price - current_prices.keys()
                logger.warning(f"Missing price data for held assets on {current_date}: {missing_items}. Skipping metrics update.")

        else:
            # If no price data at all for the day, record cash value if no assets held
            if not any(strategy.portfolio._open_positions_by_tradeable_item.values()):
                 current_value = strategy.portfolio.cash
                 portfolio_metrics.update(current_date, current_value)
                 logger.debug(f"Recorded portfolio value (cash only) for {current_date}: {current_value:.2f}")
            else:
                 logger.warning(f"Missing OHLC data entirely for {current_date}. Cannot determine portfolio value. Skipping metrics update.")


        # --- Existing Logic: Mask data and potentially execute strategy for NEXT day ---
        masked_data = create_masked_data(input_data, current_date)

        # Get next day's data for trade execution
        # If current date is the last trading date, we can't execute trades
        if i < len(filtered_trading_dates) - 1:
            next_date = filtered_trading_dates[i + 1]
            # Ensure next_day_data extraction uses the portfolio state *before* today's execute call
            next_day_data = extract_ohlc_data(input_data, strategy.portfolio, next_date)

            # Execute the strategy for the current date using next day's data
            if next_day_data:  # Only execute if we have next day data
                strategy.execute(masked_data, next_day_data)
            else:
                logger.warning(
                    f"Skipping strategy execution for {current_date} due to missing next day data for {next_date}"
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
        config.strategy_name,
        config.initial_portfolio, # Pass the initial portfolio config
        **(config.strategy_params or {}) 
    )

    # Initialize the PortfolioMetrics tracker
    portfolio_metrics = PortfolioMetrics(strategy.portfolio)

    # now given the data requirements and the tradaable items in the portfolio,
    # load the appropriate data
    input_data: StrategyInputData = load_data(
        config, strategy, strategy.portfolio # Use the portfolio from the strategy instance
    )

    # now that we have loaded the data we can iterate over the days and run the strategy
    # we will start from the first day of the portfolio and go till config.end_date
    # if config.end_date is not provided we will go till the last day of the data
    if config.end_date is None:
        # Find the latest date available across all ticker data if no end date specified
        all_dates = set()
        for item_data in input_data.values():
             for req_data in item_data.values():
                  if isinstance(req_data.index, pd.DatetimeIndex):
                       all_dates.update(req_data.index.date)
        end_date = max(all_dates) if all_dates else datetime.now().date()
        logger.info(f"No end date specified, using latest data date: {end_date}")
    else:
        end_date = config.end_date

    # Extract all trading dates from the input data
    # Ensure trading dates respect the structure of StrategyInputData
    trading_dates = extract_trading_dates(input_data)

    # Filter trading dates to only include dates within our simulation range
    start_date = strategy.portfolio.start_date
    filtered_trading_dates = sorted([
        d for d in trading_dates if start_date <= d <= end_date
    ])

    if not filtered_trading_dates:
        logger.error(f"No trading dates found between {start_date} and {end_date}")
        return

    logger.info(
        f"Running backtest from {start_date} to {end_date} ({len(filtered_trading_dates)} trading days)"
    )

    # Pass the metrics tracker to the loop
    backtest_loop(filtered_trading_dates, input_data, strategy, portfolio_metrics)

    # At this point the portfolio has been updated with all the trading activity
    logger.info(f"Backtest complete.")

    # --- Calculate and Print Final Metrics ---
    # Set risk-free rate (example: 0%) and periods per year (example: 252 for daily)
    risk_free_rate = 0.0
    periods_per_year = 252
    final_metrics = portfolio_metrics.get_final_metrics(risk_free_rate, periods_per_year)

    logger.info("--- Backtest Performance Metrics --- ")
    # Use pprint for formatted output
    pp = pprint.PrettyPrinter(indent=2)
    # Convert metrics dict to string using pformat and log it
    metrics_str = pp.pformat(final_metrics)
    logger.info(f"\n{metrics_str}")

    # Log final portfolio value separately for clarity if needed
    final_portfolio_value = portfolio_metrics.value_history[-1][1] if portfolio_metrics.value_history else strategy.portfolio.cash
    logger.info(f"Final Portfolio Value: {final_portfolio_value:.2f}")


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
    try:
        with open(config, "r") as f:
            config_data = json.load(f)
        logger.info(f"Config data loaded successfully.") # Changed log level

        backtest_config = BacktestConfig.from_dict(config_data)
        run_backtest(backtest_config)
    except json.JSONDecodeError as e:
         logger.error(f"Error decoding JSON configuration file '{config}': {e}")
    except FileNotFoundError:
         logger.error(f"Configuration file not found: '{config}'")
    except Exception as e:
         logger.exception(f"An unexpected error occurred during backtest execution: {e}")


if __name__ == "__main__":
    main()
