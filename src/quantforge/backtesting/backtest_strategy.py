"""
Backtest a strategy.

Given a strategy backtest it with historical data.

Following is our backtesting methodology:

1. We should be able to backtest the strategy with a portfolio of a single stock or multiple stocks.
2. We should be able to backtest the strategy over a specific time period or the entire history of the stock.
3. We should start off the strategy at a point where there is at least 2 months of historical data.
4. We should use the closing price of the stock for the backtesting.
5. So start off the portfolio with 10000 USD.
6. Then feed the strategy historical data and let it execute or not execute the trades.
7. Tick ahead to the next day of the historical data. Update the portfolio and the strategy with the new data.
8. Repeat the process until the end of the historical data.
9. Calculate the performance metrics.
10. Print the performance metrics.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Type, Union

import matplotlib.pyplot as plt
import pandas as pd
import sqlite3
import click  # Import the click library

from quantforge.qtypes.portfolio import Portfolio
from quantforge.strategies.abstract_strategy import AbstractStrategy, StrategyInputData
from quantforge.strategies.data_requirement import DataRequirement
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.assetclass import AssetClass
from quantforge.qtypes.ohlc import OHLCData

# TODO: Decide on common column names or use strings directly
# from common.df_columns import CLOSE, HIGH, LOW, OPEN, TICKER, TIMESTAMP, VOLUME
TICKER = "ticker"  # Using string directly for now
TIMESTAMP = "timestamp"
OPEN = "open"
HIGH = "high"
LOW = "low"
CLOSE = "close"
VOLUME = "volume"


# TODO: Replace tz_util if needed, or ensure timezone handling
def ensure_utc_tz(dt):
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# --- Strategy Discovery (Simplified) ---
# Removed StrategyFactory dependency. We'll handle strategy selection differently.
# Mapping strategy names to classes
AVAILABLE_STRATEGIES = {}
try:
    from quantforge.strategies.rsi_strategy import RsiStrategy

    AVAILABLE_STRATEGIES["rsi_strategy"] = RsiStrategy
except ImportError:
    pass  # Strategy might not exist yet
try:
    from quantforge.strategies.abstract_strategy import (
        SimpleTickerDataStrategy,
    )  # Example, assuming it's usable

    AVAILABLE_STRATEGIES["simple_ticker_strategy"] = SimpleTickerDataStrategy
except ImportError:
    pass


def get_strategy_class(name: str) -> Type[AbstractStrategy]:
    if name.lower() not in AVAILABLE_STRATEGIES:
        raise ValueError(
            f"Strategy '{name}' not found. Available: {', '.join(AVAILABLE_STRATEGIES.keys())}"
        )
    return AVAILABLE_STRATEGIES[name.lower()]


# --- Backtest Class ---
class Backtest:
    """
    A class to backtest QuantForge trading strategies.
    """

    def __init__(
        self,
        strategy_class: Type[AbstractStrategy],  # Use AbstractStrategy
        strategy_params: Optional[Dict] = None,
        initial_capital: float = 10000.0,
        # commission: float = 0.001, # Commission handled by Portfolio/Transaction now? -> Portfolio doesn't handle this directly yet. Assume 0 for now.
        allow_short_selling: bool = False,
        allow_margin_trading: bool = False,
    ):
        self.strategy_class = strategy_class
        self.strategy_params = strategy_params or {}
        self.initial_capital = initial_capital
        # self.commission = commission
        self.allow_short_selling = allow_short_selling
        self.allow_margin_trading = allow_margin_trading

        self.portfolio: Optional[Portfolio] = None  # Use QuantForge Portfolio
        self.strategy: Optional[AbstractStrategy] = None  # Use AbstractStrategy
        self.raw_data: Optional[pd.DataFrame] = None  # Store raw fetched data
        self.tradeable_items_map: Dict[
            str, TradeableItem
        ] = {}  # Map ticker string to TradeableItem
        self.equity_history: List[tuple[datetime, float]] = []  # Manual equity tracking
        self.benchmark_data: Optional[pd.Series] = None  # For benchmark comparison
        self.current_market_prices: Dict[
            TradeableItem, float
        ] = {}  # Store current prices here

    # --- Data Fetching (Placeholder/Simplified) ---
    def _fetch_raw_data(
        self,
        tickers: List[str],
        start_buffer_date: datetime,
        end_date: datetime,
        db_name: str = "stock_data.db",
    ) -> pd.DataFrame:
        """
        Placeholder for fetching raw OHLCV data from the database.
        Should return a DataFrame indexed by [TICKER, TIMESTAMP].
        """
        print(
            f"Attempting to fetch data for {tickers} from {db_name} between {start_buffer_date} and {end_date}"
        )
        # This needs to be implemented based on the actual DB schema
        # Example using sqlite3 assumed schema: historical_prices(ticker, timestamp, open, high, low, close, volume)
        conn = None
        try:
            conn = sqlite3.connect(db_name)
            placeholders = ",".join("?" * len(tickers))
            query = f"""
            SELECT ticker, timestamp, open, high, low, close, volume
            FROM historical_prices
            WHERE ticker IN ({placeholders})
              AND timestamp >= ?
              AND timestamp <= ?
            ORDER BY ticker, timestamp
            """
            params = tickers + [
                start_buffer_date.strftime("%Y-%m-%d %H:%M:%S"),
                end_date.strftime("%Y-%m-%d %H:%M:%S"),
            ]

            # Read data into pandas DataFrame
            df = pd.read_sql_query(query, conn, params=params)

            if df.empty:
                print(
                    "Warning: No data fetched from database for the given tickers and date range."
                )
                return pd.DataFrame()

            # Convert timestamp to datetime objects and set timezone to UTC
            df[TIMESTAMP] = pd.to_datetime(df[TIMESTAMP]).dt.tz_localize(timezone.utc)

            # Set multi-index
            df = df.set_index([TICKER, TIMESTAMP]).sort_index()
            print(f"Successfully fetched {len(df)} rows of data.")
            return df

        except Exception as e:
            print(f"Error fetching data from {db_name}: {e}")
            print(
                "Please ensure the database exists and the 'historical_prices' table has the correct schema:"
            )
            print(
                "  ticker TEXT, timestamp DATETIME, open REAL, high REAL, low REAL, close REAL, volume INTEGER"
            )
            print("Returning empty DataFrame.")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

    # --- Backtest Execution ---
    def run(
        self,
        tickers: Union[str, List[str]],
        start_date: datetime,
        end_date: Optional[datetime] = None,
        db_name: str = "stock_data.db",
        benchmark_ticker: Optional[str] = None,
        # Add buffer for initial calculations (e.g., RSI window)
        data_buffer_days: int = 60,  # ~2 months
    ) -> Dict:
        """
        Run the backtest.
        """
        if isinstance(tickers, str):
            tickers = [tickers]
        if not tickers:
            raise ValueError("At least one ticker must be provided.")

        # Set end date to current date if not provided
        end_date = end_date or datetime.now(timezone.utc)

        # Ensure dates are in UTC timezone
        start_date = ensure_utc_tz(start_date)
        end_date = ensure_utc_tz(end_date)
        start_buffer_date = start_date - timedelta(days=data_buffer_days)

        self.backtest_start_date = start_date  # Actual simulation start
        self.backtest_end_date = end_date

        # Create TradeableItem objects
        self.tradeable_items_map = {
            ticker: TradeableItem(
                id=ticker, asset_class=AssetClass.EQUITY
            )  # Assuming EQUITY
            for ticker in tickers
        }
        allowed_items = list(self.tradeable_items_map.values())

        # Initialize portfolio
        self.portfolio = Portfolio(
            initial_cash=self.initial_capital,
            allowed_tradeable_items=allowed_items,
            start_date=start_date,  # Portfolio start date
            allow_short=self.allow_short_selling,
            allow_margin=self.allow_margin_trading,
        )

        # Initialize strategy
        self.strategy = self.strategy_class(
            portfolio=self.portfolio, **self.strategy_params
        )
        # print(f"Initialized strategy: {self.strategy.name} with params: {self.strategy_params}") # Use RsiStrategy __init__ print

        # Fetch raw data including buffer
        print(f"Fetching data from {start_buffer_date.date()} to {end_date.date()}...")
        self.raw_data = self._fetch_raw_data(
            tickers, start_buffer_date, end_date, db_name
        )

        if self.raw_data.empty:
            print("Cannot run backtest with no data.")
            return {"error": "No data found for the specified tickers and date range."}

        # --- Benchmark Data Preparation (Simplified) ---
        if (
            benchmark_ticker
            and benchmark_ticker
            in self.raw_data.index.get_level_values(TICKER).unique()
        ):
            bench_df = self.raw_data.xs(benchmark_ticker, level=TICKER)[CLOSE]
            # Align benchmark start with portfolio value start
            bench_df = bench_df[bench_df.index >= start_date]
            if not bench_df.empty:
                # Normalize benchmark to initial capital
                self.benchmark_data = (
                    bench_df / bench_df.iloc[0]
                ) * self.initial_capital
            else:
                self.benchmark_data = pd.Series(dtype=float)
        else:
            self.benchmark_data = pd.Series(dtype=float)
            if benchmark_ticker:
                print(
                    f"Warning: Benchmark ticker '{benchmark_ticker}' not found in fetched data."
                )

        # Get unique timestamps within the actual backtest period (simulation period)
        all_timestamps = self.raw_data.index.get_level_values(TIMESTAMP).unique()
        backtest_timestamps = sorted(
            all_timestamps[
                (all_timestamps >= start_date) & (all_timestamps <= end_date)
            ]
        )

        if not backtest_timestamps:
            print(
                f"No trading days found between {start_date.date()} and {end_date.date()} in the fetched data."
            )
            return {"error": "No trading days found for backtest period."}

        print(
            f"Running backtest simulation over {len(backtest_timestamps)} trading days..."
        )
        self.equity_history = []  # Reset equity history

        # Record initial portfolio value
        self.equity_history.append(
            (backtest_timestamps[0] - timedelta(microseconds=1), self.initial_capital)
        )  # Record just before start

        # --- Backtesting Loop ---
        for i, current_ts in enumerate(backtest_timestamps):
            # Get current portfolio value *before* processing today's data/trades for progress printing
            # Use the prices stored from the *previous* iteration
            current_value_for_print = self.portfolio.portfolio_value(
                self.current_market_prices
            )
            if i % 100 == 0 or i == len(backtest_timestamps) - 1:
                print(
                    f"Processing Day {i+1}/{len(backtest_timestamps)}: {current_ts.date()} - Portfolio Value: ${current_value_for_print:,.2f}"
                )

            # 1. Prepare StrategyInputData for the current timestamp
            # This includes data up to and including current_ts from the raw_data buffer
            current_data_slice = self.raw_data[
                self.raw_data.index.get_level_values(TIMESTAMP) <= current_ts
            ]
            input_data: StrategyInputData = {}
            # TODO: Handle multiple data requirements if strategy needs more than TICKER
            required_data_type = DataRequirement.TICKER  # Assuming TICKER for now
            for ticker_str, item_obj in self.tradeable_items_map.items():
                if (
                    ticker_str
                    in current_data_slice.index.get_level_values(TICKER).unique()
                ):
                    ticker_df = current_data_slice.xs(ticker_str, level=TICKER)
                    input_data[item_obj] = {required_data_type: ticker_df}
                # else: Data for this ticker might be missing up to this point

            # 2. Prepare next_day_data for execution price lookup
            next_day_data: dict[TradeableItem, OHLCData] = {}
            if i < len(backtest_timestamps) - 1:
                next_ts = backtest_timestamps[i + 1]
                try:
                    # Get data for all tickers at the next timestamp
                    next_day_slice = self.raw_data.xs(next_ts, level=TIMESTAMP)
                    for ticker_str, item_obj in self.tradeable_items_map.items():
                        if ticker_str in next_day_slice.index:
                            row = next_day_slice.loc[ticker_str]
                            # Create OHLCData object - Ensure NaN handling if needed
                            ohlc = OHLCData(
                                date=next_ts.date(),  # Use date part? Check OHLCData definition
                                open=row[OPEN],
                                high=row[HIGH],
                                low=row[LOW],
                                close=row[CLOSE],
                                # volume=row.get(VOLUME, None) # Check if OHLCData includes volume
                            )
                            next_day_data[item_obj] = ohlc
                except KeyError:
                    # No data available for next_ts for some/all tickers
                    print(f"Warning: No data found for next timestamp {next_ts.date()}")
                except Exception as e:
                    print(f"Error preparing next_day_data for {next_ts.date()}: {e}")

            # 3. Update Portfolio's current prices (needed for valuation)
            # Store these prices within the Backtest object
            current_prices_dict: Dict[TradeableItem, float] = {}
            try:
                latest_data_this_ts = self.raw_data.xs(current_ts, level=TIMESTAMP)
                for ticker_str, item_obj in self.tradeable_items_map.items():
                    if ticker_str in latest_data_this_ts.index:
                        close_price = latest_data_this_ts.loc[ticker_str, CLOSE]
                        if pd.notna(close_price):
                            current_prices_dict[item_obj] = close_price
                # Update the stored prices in the Backtest class
                self.current_market_prices = current_prices_dict
            except KeyError:
                print(
                    f"Warning: No data found for current timestamp {current_ts.date()}"
                )
            except Exception as e:
                print(f"Error updating portfolio prices for {current_ts.date()}: {e}")

            # 4. Execute strategy logic
            try:
                self.strategy.execute(input_data, next_day_data)
            except Exception as e:
                print(
                    f"!!! Error during strategy execution on {current_ts.date()}: {e}"
                )
                import traceback

                traceback.print_exc()  # Print stack trace for debugging

            # 5. Record portfolio value at the end of the day
            # Use the updated current market prices for end-of-day valuation
            current_total_value = self.portfolio.portfolio_value(
                self.current_market_prices
            )
            self.equity_history.append((current_ts, current_total_value))

        print("Backtest simulation finished.")
        # Calculate and return performance metrics
        metrics = self.get_performance_metrics()
        return metrics

    # --- Metrics Calculation (Needs Adaptation) ---
    def get_performance_metrics(self) -> Dict:
        """
        Calculate performance metrics for the backtest.
        NEEDS REWRITING based on tracked equity and Portfolio data.
        """
        if not self.equity_history:
            return {"error": "Backtest has not been run or produced no results."}

        metrics = {}
        metrics["start_date"] = self.backtest_start_date
        metrics["end_date"] = self.backtest_end_date
        metrics["initial_capital"] = self.initial_capital
        metrics["final_portfolio_value"] = (
            self.equity_history[-1][1] if self.equity_history else self.initial_capital
        )

        # Create equity series for calculations
        timestamps, values = zip(*self.equity_history, strict=False)
        equity_series = pd.Series(values, index=pd.to_datetime(timestamps))

        # Simple Total Return
        total_return = (
            metrics["final_portfolio_value"] / metrics["initial_capital"]
        ) - 1
        metrics["total_return"] = total_return

        # TODO: Implement more sophisticated metrics (Annualized Return, Volatility, Sharpe, Sortino, Max Drawdown, etc.)
        # These require daily/periodic returns calculations from the equity_series.
        metrics["annualized_return"] = 0.0  # Placeholder
        metrics["volatility"] = 0.0  # Placeholder
        metrics["sharpe_ratio"] = 0.0  # Placeholder
        metrics["sortino_ratio"] = 0.0  # Placeholder
        metrics["max_drawdown"] = 0.0  # Placeholder
        metrics["calmar_ratio"] = 0.0  # Placeholder

        # Trades (Requires Portfolio to track trades)
        # Assuming portfolio has a list of closed positions or similar
        # metrics['num_trades'] = len(self.portfolio._closed_positions) if hasattr(self.portfolio, '_closed_positions') else 0 # HACK: Accessing private member
        metrics["num_trades"] = (
            len(self.portfolio.get_closed_positions())
            if hasattr(self.portfolio, "get_closed_positions")
            else 0
        )

        return metrics

    # --- Plotting (Needs Adaptation) ---
    def plot_results(self, figsize=(12, 8), show_benchmark=True):
        """
        Plot backtest results. Needs review based on actual equity tracking.
        """
        if not self.equity_history:
            print("No equity history available to plot.")
            return

        try:
            timestamps, equity = zip(*self.equity_history, strict=False)
            equity_series = pd.Series(equity, index=pd.to_datetime(timestamps))

            plt.figure(figsize=figsize)
            plt.plot(
                equity_series.index,
                equity_series.values,
                label=f"{self.strategy.name} Strategy",
            )

            if (
                show_benchmark
                and self.benchmark_data is not None
                and not self.benchmark_data.empty
            ):
                try:
                    # Align benchmark data to equity curve dates
                    aligned_benchmark = self.benchmark_data.reindex(
                        equity_series.index, method="ffill"
                    )
                    # Ensure we only plot where we have strategy data
                    aligned_benchmark = aligned_benchmark.loc[equity_series.index]
                    plt.plot(
                        aligned_benchmark.index,
                        aligned_benchmark.values,
                        label="Buy & Hold Benchmark",
                        linestyle="--",
                    )
                except Exception as e:
                    print(f"Error aligning or plotting benchmark: {e}")

            plt.title(f"{self.strategy.name} Backtest Equity Curve")
            plt.xlabel("Date")
            plt.ylabel("Portfolio Value ($)")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plt.show()

        except Exception as e:
            print(f"Error plotting results: {e}")
            import traceback

            traceback.print_exc()

    # --- Results String (Needs Adaptation) ---
    def get_results_as_string(self) -> Optional[str]:
        """Generate backtest results and stats as a formatted string."""
        if not self.portfolio or not self.strategy or not self.equity_history:
            return "Backtest has not been run or failed."

        metrics = self.get_performance_metrics()
        if "error" in metrics:
            return f"Error retrieving metrics: {metrics['error']}"

        # ... (rest of the string formatting - needs review based on implemented metrics) ...
        # This part needs significant updates once metrics calculation is solid.
        # For now, provide basic info.

        output_lines = []
        separator = "=" * 50

        output_lines.append("\n" + separator)
        output_lines.append(f"BACKTEST RESULTS: {self.strategy.name}")
        output_lines.append(separator)
        output_lines.append(
            f"Period: {metrics['start_date'].date()} to {metrics['end_date'].date()}"
        )
        output_lines.append(f"Initial Capital: ${metrics['initial_capital']:,.2f}")
        output_lines.append(
            f"Final Portfolio Value: ${metrics['final_portfolio_value']:,.2f}"
        )

        profit_loss = metrics["final_portfolio_value"] - metrics["initial_capital"]
        profit_loss_pct = (
            (profit_loss / metrics["initial_capital"] * 100)
            if metrics["initial_capital"] != 0
            else 0
        )
        output_lines.append(
            f"Profit/Loss: ${profit_loss:,.2f} ({profit_loss_pct:.2f}%)"
        )
        output_lines.append(f"Total Return: {metrics.get('total_return', 0.0):.2%}")
        # Add other available metrics placeholders
        output_lines.append(f"Number of Trades: {metrics.get('num_trades', 'N/A')}")

        output_lines.append("\nSTRATEGY PARAMETERS:")
        # Assuming strategy params are stored reasonably
        if hasattr(self.strategy, "rsi_window"):  # Example for RsiStrategy
            output_lines.append(f"  rsi_window: {self.strategy.rsi_window}")
            output_lines.append(
                f"  oversold_threshold: {self.strategy.oversold_threshold}"
            )
            output_lines.append(
                f"  overbought_threshold: {self.strategy.overbought_threshold}"
            )
        # Add more parameter reporting as needed

        output_lines.append("\nFINAL HOLDINGS:")
        # Use portfolio methods/properties if available
        open_positions = (
            self.portfolio.get_all_open_positions()
        )  # Assuming this method exists or can be added
        if not open_positions:
            output_lines.append("  No open positions.")
        else:
            # Use the stored current market prices
            current_prices = self.current_market_prices
            for position in open_positions:
                item = position.open_transaction.tradeable_item
                qty = position.open_transaction.quantity
                current_price = current_prices.get(item, 0)
                value = qty * current_price
                output_lines.append(
                    f"  {item.id}: {qty} shares @ ${current_price:,.2f} (Value: ${value:,.2f})"
                )

        output_lines.append(f"\nFinal Cash: ${self.portfolio.cash:,.2f}")
        output_lines.append(separator)

        # Optional: Add trade summary (Requires portfolio trade tracking)
        # ...

        return "\n".join(output_lines)

    def print_results(self):
        """Print backtest results and stats."""
        results_str = self.get_results_as_string()
        print(results_str)


# --- Click CLI (Adapted) ---
@click.group()
def cli():
    """Backtest QuantForge trading strategies."""
    pass


@cli.command()
def list_strategies():
    """List available QuantForge strategies."""
    if AVAILABLE_STRATEGIES:
        print("Available strategies:")
        for name in AVAILABLE_STRATEGIES.keys():
            print(f"  - {name}")
    else:
        print("No strategies found.")


@cli.command()
@click.option(
    "--strategy",
    required=True,
    type=click.Choice(
        list(AVAILABLE_STRATEGIES.keys()), case_sensitive=False
    ),  # Use discovered strategies
    help="Strategy to use (e.g., 'rsi_strategy')",
)
@click.option(
    "--tickers",  # Renamed from --ticker
    required=True,  # Make tickers required for clarity
    help="Comma-separated list of ticker symbols (e.g., 'AAPL,MSFT')",
)
@click.option(
    "--db-name",
    default="stock_data.db",
    show_default=True,
    help="Database for historical data",
)
@click.option(
    "--months",
    type=int,
    default=12,
    show_default=True,
    help="Number of months to backtest",
)
@click.option(
    "--start-cash",
    type=float,
    default=10000.0,
    show_default=True,
    help="Initial capital",
)
# @click.option("--commission", type=float, default=0.0, show_default=True, help="Commission per trade (Currently not implemented in Portfolio)")
@click.option("--plot", is_flag=True, help="Plot the equity curve")
@click.option(
    "--benchmark", help="Ticker for Buy & Hold benchmark (must be in --tickers)"
)
# Strategy specific parameters (Example for RSI)
# TODO: Find a better way to handle strategy-specific params via Click
@click.option(
    "--rsi-window",
    type=int,
    default=14,
    show_default=True,
    help="RSI window (for rsi_strategy)",
)
@click.option(
    "--rsi-oversold",
    type=float,
    default=30.0,
    show_default=True,
    help="RSI oversold threshold (for rsi_strategy)",
)
@click.option(
    "--rsi-overbought",
    type=float,
    default=70.0,
    show_default=True,
    help="RSI overbought threshold (for rsi_strategy)",
)
def run(
    strategy,
    tickers,
    db_name,
    months,
    start_cash,
    plot,
    benchmark,
    rsi_window,
    rsi_oversold,
    rsi_overbought,
):
    """Run a QuantForge strategy backtest."""

    try:
        strategy_class = get_strategy_class(strategy)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # --- Parameter Handling ---
    # Collect strategy-specific parameters based on selected strategy
    strategy_params = {}
    if strategy.lower() == "rsi_strategy":
        strategy_params["rsi_window"] = rsi_window
        strategy_params["oversold_threshold"] = rsi_oversold
        strategy_params["overbought_threshold"] = rsi_overbought
    # Add more elif blocks for other strategies and their parameters

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=months * 30.4)  # More precise month approx

    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        print("Error: No valid tickers provided.")
        return

    # Validate benchmark ticker
    benchmark_ticker = benchmark.strip().upper() if benchmark else ticker_list[0]
    if benchmark_ticker not in ticker_list:
        print(
            f"Warning: Benchmark ticker '{benchmark_ticker}' is not in the list of tested tickers. Using '{ticker_list[0]}' instead."
        )
        benchmark_ticker = ticker_list[0]

    print("\n--- Starting Backtest ---")
    print(f"Strategy: {strategy_class.__name__}")
    print(f"Parameters: {strategy_params}")
    print(f"Tickers: {', '.join(ticker_list)}")
    print(f"Period: {start_date.date()} to {end_date.date()} ({months} months)")
    print(f"Initial Cash: ${start_cash:,.2f}")
    print(f"Benchmark: {benchmark_ticker}")
    print(f"Database: {db_name}")
    print("-------------------------")

    backtest = Backtest(
        strategy_class=strategy_class,
        strategy_params=strategy_params,
        initial_capital=start_cash,
        # commission=commission, # Not currently used
    )

    try:
        backtest.run(
            tickers=ticker_list,
            start_date=start_date,
            end_date=end_date,
            db_name=db_name,
            benchmark_ticker=benchmark_ticker,
        )
        backtest.print_results()
        if plot:
            print("Generating plot...")
            backtest.plot_results()

    except Exception as e:
        print("\n--- Backtest Failed ---")
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    cli()
