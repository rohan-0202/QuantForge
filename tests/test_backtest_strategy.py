import pytest
import pandas as pd
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, ANY
from click.testing import CliRunner
import sqlite3
import numpy as np

# Module to test
from quantforge.backtest_strategy import Backtest, cli, AVAILABLE_STRATEGIES
# Dependent QuantForge modules
from quantforge.qtypes.portfolio import Portfolio
from quantforge.strategies.abstract_strategy import AbstractStrategy
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.assetclass import AssetClass
from quantforge.qtypes.ohlc import OHLCData
from quantforge.strategies.rsi_strategy import RsiStrategy # Assuming this is one available strategy

# Helper to create dummy data
def create_dummy_raw_data(tickers, start_date, end_date):
    all_data = []
    dates = pd.date_range(start_date, end_date, freq='B') # Business days
    for ticker in tickers:
        ticker_data = pd.DataFrame({
            'open': [100 + i*0.1 + (hash(ticker)%10)*0.1 for i in range(len(dates))],
            'high': [101 + i*0.1 + (hash(ticker)%10)*0.1 for i in range(len(dates))],
            'low': [99 + i*0.1 + (hash(ticker)%10)*0.1 for i in range(len(dates))],
            'close': [100.5 + i*0.1 + (hash(ticker)%10)*0.1 for i in range(len(dates))],
            'volume': [10000 + i*10 for i in range(len(dates))]
        }, index=dates)
        ticker_data['ticker'] = ticker
        all_data.append(ticker_data)
    
    if not all_data:
        return pd.DataFrame()
        
    df = pd.concat(all_data)
    df.index.name = 'timestamp'
    df = df.reset_index()
    df = df.set_index(['ticker', 'timestamp']).sort_index()
    return df

# --- Fixtures --- 
@pytest.fixture
def mock_db_connection(tmp_path):
    """Creates a temporary SQLite DB with dummy data."""
    db_path = tmp_path / "test_stock_data.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE historical_prices (
        ticker TEXT,
        timestamp DATETIME,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        PRIMARY KEY (ticker, timestamp)
    )
    """)
    
    # Insert some dummy data
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 6, 30, tzinfo=timezone.utc)
    dummy_df = create_dummy_raw_data(["TEST1", "TEST2"], start, end)
    dummy_df = dummy_df.reset_index()
    dummy_df['timestamp'] = dummy_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S') # Convert to string for DB
    
    dummy_df.to_sql('historical_prices', conn, if_exists='append', index=False)
        
    conn.commit()
    conn.close()
    return str(db_path)

# --- Backtest Class Tests --- 
@pytest.mark.integration # This test interacts with the filesystem and DB
class TestBacktestIntegration:
    
    @patch('quantforge.backtest_strategy.plt.show') # Prevent plots from blocking tests
    def test_backtest_run_rsi_strategy_basic(self, mock_plot_show, mock_db_connection):
        """Tests a basic run of the Backtest class with RsiStrategy."""
        # Ensure RsiStrategy is available for the test
        if 'rsi_strategy' not in AVAILABLE_STRATEGIES:
            pytest.skip("RsiStrategy not found in AVAILABLE_STRATEGIES")
            
        start_date = datetime(2023, 3, 1, tzinfo=timezone.utc) # Needs > 60 days buffer before this
        end_date = datetime(2023, 6, 30, tzinfo=timezone.utc)
        tickers = ["TEST1", "TEST2"]
        
        backtest = Backtest(
            strategy_class=RsiStrategy, 
            strategy_params={'rsi_window': 14}, # Use default thresholds
            initial_capital=50000.0
        )
        
        metrics = backtest.run(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            db_name=mock_db_connection,
            benchmark_ticker="TEST1"
        )
        
        assert isinstance(metrics, dict)
        assert "error" not in metrics
        assert metrics['start_date'] == start_date
        assert metrics['end_date'] == end_date
        assert metrics['initial_capital'] == 50000.0
        assert metrics['final_portfolio_value'] > 0 # Basic check
        assert 'total_return' in metrics
        assert 'num_trades' in metrics # Check if trade counting worked (might be 0)
        
        # Check if equity history was populated
        assert hasattr(backtest, 'equity_history')
        assert len(backtest.equity_history) > 1
        assert backtest.equity_history[0][1] == 50000.0 # Initial capital check
        
        # Check if benchmark data was populated
        assert backtest.benchmark_data is not None
        assert not backtest.benchmark_data.empty
        assert np.isclose(backtest.benchmark_data.iloc[0], 50000.0) # Starts at initial capital
        
        # Test plotting and printing (basic checks)
        with patch('builtins.print') as mock_print:
            backtest.print_results()
            mock_print.assert_called() # Check if it printed *something*
            results_str = backtest.get_results_as_string()
            assert isinstance(results_str, str)
            assert "BACKTEST RESULTS" in results_str
            
        # This tries to plot, mock_plot_show prevents it hanging
        backtest.plot_results() 
        mock_plot_show.assert_called_once()

    def test_backtest_run_no_data(self, mock_db_connection):
        """Tests backtest run when no data is found in DB."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc) # Date after dummy data
        end_date = datetime(2024, 2, 1, tzinfo=timezone.utc)
        tickers = ["NODATA1"]
        
        backtest = Backtest(strategy_class=RsiStrategy) # Use any available strategy
        metrics = backtest.run(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            db_name=mock_db_connection
        )
        assert "error" in metrics
        assert "No data found" in metrics["error"]
        
    def test_backtest_run_no_trading_days_in_range(self, mock_db_connection):
        """Tests backtest run when data exists but not in the specific simulation range."""
        start_date = datetime(2023, 7, 1, tzinfo=timezone.utc) # After dummy data ends
        end_date = datetime(2023, 7, 10, tzinfo=timezone.utc)
        tickers = ["TEST1"]

        backtest = Backtest(strategy_class=RsiStrategy)
        metrics = backtest.run(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            db_name=mock_db_connection
        )
        assert "error" in metrics
        assert "No trading days found" in metrics["error"]

# --- CLI Tests --- 
@pytest.mark.unit
class TestCli:

    def test_list_strategies(self):
        """Tests the list-strategies command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['list-strategies'])
        assert result.exit_code == 0
        # Check if known strategies are listed (case-insensitive) 
        assert 'Available strategies:' in result.output
        for strategy_name in AVAILABLE_STRATEGIES.keys():
             assert strategy_name in result.output.lower()
             
    @patch('quantforge.backtest_strategy.Backtest.run')
    @patch('quantforge.backtest_strategy.Backtest.print_results')
    @patch('quantforge.backtest_strategy.Backtest.plot_results')
    def test_run_command_success(self, mock_plot, mock_print, mock_backtest_run, mock_db_connection):
        """Tests the run command basic execution flow with mocking."""
        runner = CliRunner()
        mock_backtest_run.return_value = {'status': 'ok'} # Mock successful run
        
        # Find an available strategy name for the test
        if not AVAILABLE_STRATEGIES:
             pytest.skip("No strategies available to test CLI run command.")
        strategy_name = list(AVAILABLE_STRATEGIES.keys())[0]
        
        result = runner.invoke(cli, [
            'run',
            '--strategy', strategy_name,
            '--tickers', 'AAPL,MSFT',
            '--db-name', mock_db_connection,
            '--months', '6',
            '--start-cash', '12345',
            # Add strategy-specific params if needed for the chosen strategy
            # e.g., '--rsi-window', '20' for rsi_strategy
            '--plot' # Test plotting flag
        ])
        
        assert result.exit_code == 0
        mock_backtest_run.assert_called_once()
        mock_print.assert_called_once()
        mock_plot.assert_called_once()
        
        # Check if args were passed correctly to Backtest.run (simplified check)
        call_args, call_kwargs = mock_backtest_run.call_args
        assert 'tickers' in call_kwargs and call_kwargs['tickers'] == ['AAPL', 'MSFT']
        assert 'db_name' in call_kwargs and call_kwargs['db_name'] == mock_db_connection
        assert 'start_date' in call_kwargs and isinstance(call_kwargs['start_date'], datetime)
        assert 'end_date' in call_kwargs and isinstance(call_kwargs['end_date'], datetime)
        # Check if strategy params were passed to Backtest init (harder to check directly here)
        
    def test_run_command_invalid_strategy(self):
        """Tests the run command with an invalid strategy name."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'run',
            '--strategy', 'invalid_strat_name',
            '--tickers', 'AAPL'
        ])
        assert result.exit_code != 0 # Should fail
        # Check for Click's specific error message for invalid choice
        assert "Invalid value for '--strategy'" in result.output

    def test_run_command_no_tickers(self):
        """Tests the run command without providing tickers."""
        runner = CliRunner()
        # Assuming 'rsi_strategy' exists
        if 'rsi_strategy' not in AVAILABLE_STRATEGIES: pytest.skip("rsi_strategy needed")
        result = runner.invoke(cli, [
            'run',
            '--strategy', 'rsi_strategy' 
            # Missing --tickers 
        ])
        assert result.exit_code != 0 # Should fail because --tickers is required now
        assert "Missing option '--tickers'" in result.output or "No valid tickers provided" in result.output # Depending on Click version / error handling
        
# Add more tests for edge cases, specific strategy parameter handling, etc. 