import pytest
import pandas as pd
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.assetclass import AssetClass
from quantforge.qtypes.ohlc import OHLCData
from quantforge.strategies.data_requirement import DataRequirement
from quantforge.strategies.trading_signal import TradingSignalType
from quantforge.strategies.rsi_strategy import RsiStrategy
from quantforge.strategies.utils import calculate_rsi # Import for potential mocking/verification

# --- Fixtures ---
@pytest.fixture
def mock_portfolio():
    """Creates a mock Portfolio object."""
    portfolio = MagicMock(spec=Portfolio)
    portfolio.cash = 10000.0
    # Mock has_position to return False initially, can be changed in tests
    portfolio.has_position.return_value = False 
    return portfolio

@pytest.fixture
def tradeable_item_a():
    return TradeableItem(id="ITEM_A", asset_class=AssetClass.EQUITY)

@pytest.fixture
def tradeable_item_b():
    return TradeableItem(id="ITEM_B", asset_class=AssetClass.EQUITY)

@pytest.fixture
def sample_data_oversold(tradeable_item_a):
    """Generates sample data where the last RSI value is below 30."""
    # Create price series designed to dip low recently
    prices = [50, 51, 52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 41, 43, 42, 40]
    df = pd.DataFrame({'close': prices}, index=pd.date_range(end=date.today(), periods=len(prices)))
    return {tradeable_item_a: {DataRequirement.TICKER: df}}

@pytest.fixture
def sample_data_overbought(tradeable_item_a):
    """Generates sample data where the last RSI value is above 70."""
    # Create price series designed to rise high recently
    prices = [50, 49, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 59, 58, 60, 62]
    df = pd.DataFrame({'close': prices}, index=pd.date_range(end=date.today(), periods=len(prices)))
    return {tradeable_item_a: {DataRequirement.TICKER: df}}

@pytest.fixture
def sample_data_neutral(tradeable_item_a):
    """Generates sample data where the last RSI value is between 30 and 70."""
    prices = [50, 51, 50, 52, 51, 53, 52, 54, 53, 55, 54, 56, 55, 54, 53, 52, 53, 54, 53, 52]
    df = pd.DataFrame({'close': prices}, index=pd.date_range(end=date.today(), periods=len(prices)))
    return {tradeable_item_a: {DataRequirement.TICKER: df}}
    
@pytest.fixture
def next_day_data_sample(tradeable_item_a, tradeable_item_b):
    """Sample next day OHLC data."""
    next_day = date.today() + timedelta(days=1)
    return {
        tradeable_item_a: OHLCData(date=next_day, open=40.5, high=41.0, low=40.0, close=40.8),
        tradeable_item_b: OHLCData(date=next_day, open=100.0, high=101.0, low=99.5, close=100.5),
    }

# --- Test Class --- 
@pytest.mark.unit
class TestRsiStrategy:

    def test_init_valid(self, mock_portfolio):
        """Tests successful initialization."""
        strategy = RsiStrategy(portfolio=mock_portfolio, rsi_window=10, oversold_threshold=25, overbought_threshold=75)
        assert strategy.name == "RsiStrategy"
        assert strategy.portfolio == mock_portfolio
        assert strategy.rsi_window == 10
        assert strategy.oversold_threshold == 25
        assert strategy.overbought_threshold == 75
        assert strategy.get_data_requirements() == [DataRequirement.TICKER]

    def test_init_invalid_params(self, mock_portfolio):
        """Tests initialization with invalid parameters."""
        with pytest.raises(ValueError, match="RSI window must be an integer greater than 1."):
            RsiStrategy(portfolio=mock_portfolio, rsi_window=1)
        with pytest.raises(ValueError, match="Oversold threshold must be between 0 and 100."):
            RsiStrategy(portfolio=mock_portfolio, oversold_threshold=-10)
        with pytest.raises(ValueError, match="Overbought threshold must be between 0 and 100."):
            RsiStrategy(portfolio=mock_portfolio, overbought_threshold=110)
        with pytest.raises(ValueError, match="Oversold threshold must be less than overbought threshold."):
            RsiStrategy(portfolio=mock_portfolio, oversold_threshold=70, overbought_threshold=30)

    def test_generate_signals_buy(self, mock_portfolio, tradeable_item_a, sample_data_oversold):
        """Tests generating a BUY signal when RSI is oversold."""
        strategy = RsiStrategy(portfolio=mock_portfolio)
        signals = strategy.generate_signals(sample_data_oversold)
        assert len(signals) == 1
        assert tradeable_item_a in signals
        assert signals[tradeable_item_a].signal_type == TradingSignalType.BUY
        assert signals[tradeable_item_a].signal_strength == 1.0

    def test_generate_signals_sell_when_holding(self, mock_portfolio, tradeable_item_a, sample_data_overbought):
        """Tests generating a SELL signal when RSI is overbought AND position is held."""
        mock_portfolio.has_position.return_value = True # Assume we hold the position
        strategy = RsiStrategy(portfolio=mock_portfolio)
        signals = strategy.generate_signals(sample_data_overbought)
        assert len(signals) == 1
        assert tradeable_item_a in signals
        assert signals[tradeable_item_a].signal_type == TradingSignalType.SELL
        assert signals[tradeable_item_a].signal_strength == -1.0
        mock_portfolio.has_position.assert_called_once_with(tradeable_item_a)

    def test_generate_signals_no_sell_when_not_holding(self, mock_portfolio, tradeable_item_a, sample_data_overbought):
        """Tests NO SELL signal when RSI is overbought BUT position is NOT held."""
        mock_portfolio.has_position.return_value = False # Assume we do NOT hold the position
        strategy = RsiStrategy(portfolio=mock_portfolio)
        signals = strategy.generate_signals(sample_data_overbought)
        assert len(signals) == 0 # No signal should be generated
        mock_portfolio.has_position.assert_called_once_with(tradeable_item_a)

    def test_generate_signals_no_signal_neutral(self, mock_portfolio, tradeable_item_a, sample_data_neutral):
        """Tests no signal generation when RSI is in the neutral zone."""
        strategy = RsiStrategy(portfolio=mock_portfolio)
        signals = strategy.generate_signals(sample_data_neutral)
        assert len(signals) == 0

    def test_generate_signals_insufficient_data(self, mock_portfolio, tradeable_item_a):
        """Tests no signal generation with insufficient data for RSI calculation."""
        strategy = RsiStrategy(portfolio=mock_portfolio, rsi_window=14)
        short_data = pd.DataFrame({'close': [1, 2, 3, 4, 5]})
        input_data = {tradeable_item_a: {DataRequirement.TICKER: short_data}}
        signals = strategy.generate_signals(input_data)
        assert len(signals) == 0

    def test_generate_signals_missing_data(self, mock_portfolio, tradeable_item_a):
        """Tests no signal generation if ticker data is missing or invalid."""
        strategy = RsiStrategy(portfolio=mock_portfolio)
        # Case 1: Missing TICKER requirement
        input_data_missing_req = {tradeable_item_a: {DataRequirement.NEWS: pd.DataFrame()}}
        signals = strategy.generate_signals(input_data_missing_req)
        assert len(signals) == 0
        # Case 2: TICKER data is None
        input_data_none = {tradeable_item_a: {DataRequirement.TICKER: None}}
        signals = strategy.generate_signals(input_data_none)
        assert len(signals) == 0
        # Case 3: TICKER data is empty DataFrame
        input_data_empty = {tradeable_item_a: {DataRequirement.TICKER: pd.DataFrame()}}
        signals = strategy.generate_signals(input_data_empty)
        assert len(signals) == 0
        # Case 4: TICKER data has no 'close' column
        input_data_no_close = {tradeable_item_a: {DataRequirement.TICKER: pd.DataFrame({'open': [1,2]})}}
        signals = strategy.generate_signals(input_data_no_close)
        assert len(signals) == 0
        
    def test_allocate_capital_equal_weight(self, mock_portfolio, tradeable_item_a, tradeable_item_b, next_day_data_sample):
        """Tests equal weight capital allocation."""
        strategy = RsiStrategy(portfolio=mock_portfolio)
        buy_signals = {
            tradeable_item_a: MagicMock(signal_type=TradingSignalType.BUY),
            tradeable_item_b: MagicMock(signal_type=TradingSignalType.BUY)
        }
        mock_portfolio.cash = 10000.0
        # Use attribute access
        price_a = next_day_data_sample[tradeable_item_a].open 
        # Use attribute access
        price_b = next_day_data_sample[tradeable_item_b].open 
        cash_per_item = 5000.0
        expected_qty_a = int(cash_per_item // price_a) # 5000 // 40.5 = 123
        expected_qty_b = int(cash_per_item // price_b) # 5000 // 100.0 = 50
        
        allocations = strategy.allocate_capital(buy_signals, next_day_data_sample)
        
        assert len(allocations) == 2
        assert allocations[tradeable_item_a] == expected_qty_a
        assert allocations[tradeable_item_b] == expected_qty_b

    def test_allocate_capital_insufficient_cash(self, mock_portfolio, tradeable_item_a, tradeable_item_b, next_day_data_sample):
        """Tests allocation when total cost exceeds available cash."""
        strategy = RsiStrategy(portfolio=mock_portfolio)
        buy_signals = {tradeable_item_a: MagicMock(signal_type=TradingSignalType.BUY)}
        mock_portfolio.cash = 50.0 # Not enough for even one share
        # Use attribute access
        price_a = next_day_data_sample[tradeable_item_a].open 
        
        allocations = strategy.allocate_capital(buy_signals, next_day_data_sample)
        # In the simple equal weight, it calculates cash_per_item, then quantity.
        # If cash_per_item > price, it calculates a quantity > 0
        # Then it checks total_cost_estimate. For the first item, this check passes.
        # If there were a second item, the check might fail.
        # Let's refine the test case. Add item B.
        buy_signals[tradeable_item_b] = MagicMock(signal_type=TradingSignalType.BUY)
        mock_portfolio.cash = 100 # Enough for A, but maybe not A and B
        # Use attribute access
        price_b = next_day_data_sample[tradeable_item_b].open 
        cash_per_item = 50.0
        qty_a = int(50 // price_a) # 1
        cost_a = qty_a * price_a # 40.5
        # remaining_cash = 100 - 40.5 = 59.5
        qty_b = int(50 // price_b) # 0 -> This means B won't be added anyway
        
        # Test where both could be afforded individually but not together
        mock_portfolio.cash = 120
        cash_per_item = 60
        qty_a = int(60 // price_a) # 1 -> cost 40.5. total_cost_est = 40.5
        qty_b = int(60 // price_b) # 0 -> cost 0. Still only A is allocated.

        # Test where both can be afforded
        mock_portfolio.cash = 150
        cash_per_item = 75
        qty_a = int(75 // price_a) # 1 -> cost 40.5. total_cost_est = 40.5
        qty_b = int(75 // price_b) # 0 -> cost 0. Still only A

        # Let's adjust prices for a better test
        next_day_data_adjusted = {
             tradeable_item_a: OHLCData(date=date.today(), open=40.0, high=1, low=1, close=1),
             tradeable_item_b: OHLCData(date=date.today(), open=50.0, high=1, low=1, close=1),
        }
        mock_portfolio.cash = 70
        cash_per_item = 35
        # Item A: qty = int(35 // 40) = 0. Not allocated.
        # Item B: qty = int(35 // 50) = 0. Not allocated.
        allocations = strategy.allocate_capital(buy_signals, next_day_data_adjusted)
        assert len(allocations) == 0
        
        mock_portfolio.cash = 100
        cash_per_item = 50
        # Item A: qty = int(50 // 40) = 1. cost = 40. total_cost = 40. Add A:1
        # Item B: qty = int(50 // 50) = 1. cost = 50. total_cost + cost = 40 + 50 = 90 <= 100. Add B:1
        allocations = strategy.allocate_capital(buy_signals, next_day_data_adjusted)
        assert len(allocations) == 2
        assert allocations[tradeable_item_a] == 1
        assert allocations[tradeable_item_b] == 1

        mock_portfolio.cash = 80 # Enough for A=40, B=50 individually? No. Enough for A, not B if A is first.
        cash_per_item = 40
        # Item A: qty = int(40 // 40) = 1. cost = 40. total_cost = 40. Add A:1
        # Item B: qty = int(40 // 50) = 0. Skip B.
        allocations = strategy.allocate_capital(buy_signals, next_day_data_adjusted)
        assert len(allocations) == 1
        assert allocations[tradeable_item_a] == 1
        assert tradeable_item_b not in allocations


    def test_allocate_capital_no_buy_signals(self, mock_portfolio, next_day_data_sample):
        """Tests allocation when there are no buy signals."""
        strategy = RsiStrategy(portfolio=mock_portfolio)
        buy_signals = {}
        allocations = strategy.allocate_capital(buy_signals, next_day_data_sample)
        assert len(allocations) == 0

    def test_allocate_capital_missing_price_data(self, mock_portfolio, tradeable_item_a, tradeable_item_b, next_day_data_sample):
        """Tests allocation when price data is missing for one item."""
        strategy = RsiStrategy(portfolio=mock_portfolio)
        buy_signals = {
            tradeable_item_a: MagicMock(signal_type=TradingSignalType.BUY),
            tradeable_item_b: MagicMock(signal_type=TradingSignalType.BUY)
        }
        # Remove item B from next day data
        limited_next_day_data = {tradeable_item_a: next_day_data_sample[tradeable_item_a]}
        mock_portfolio.cash = 10000.0
        # Use attribute access
        price_a = next_day_data_sample[tradeable_item_a].open 
        # Only item A is valid, so it gets all the cash
        expected_qty_a = int(10000.0 // price_a) # 10000 // 40.5 = 246
        
        allocations = strategy.allocate_capital(buy_signals, limited_next_day_data)
        assert len(allocations) == 1
        assert allocations[tradeable_item_a] == expected_qty_a
        assert tradeable_item_b not in allocations
        
    # --- Execute Signals Tests (Basic Examples - More complex scenarios possible) ---

    @patch('quantforge.strategies.rsi_strategy.Transaction')
    def test_execute_buy_signals(self, mock_transaction, mock_portfolio, tradeable_item_a, next_day_data_sample):
        """Tests the execution of buy signals."""
        strategy = RsiStrategy(portfolio=mock_portfolio)
        qty_to_buy = 10
        allocated_quantities = {tradeable_item_a: qty_to_buy}
        # Use attribute access
        buy_price = next_day_data_sample[tradeable_item_a].open
        # Use attribute access
        buy_date = next_day_data_sample[tradeable_item_a].date
        
        mock_portfolio.can_trade.return_value = True
        
        strategy.execute_buy_signals(allocated_quantities, next_day_data_sample)
        
        # Verify transaction object creation
        mock_transaction.assert_called_once_with(
            tradeable_item=tradeable_item_a,
            quantity=qty_to_buy,
            price=buy_price,
            date=buy_date,
            transaction_cost=0.0 
        )
        # Verify portfolio methods were called
        mock_portfolio.can_trade.assert_called_once_with(mock_transaction.return_value)
        mock_portfolio.open_position.assert_called_once_with(mock_transaction.return_value)

    @patch('quantforge.strategies.rsi_strategy.Transaction')
    def test_execute_buy_signals_cannot_trade(self, mock_transaction, mock_portfolio, tradeable_item_a, next_day_data_sample):
        """Tests buy execution when portfolio.can_trade returns False."""
        strategy = RsiStrategy(portfolio=mock_portfolio)
        allocated_quantities = {tradeable_item_a: 10}
        mock_portfolio.can_trade.return_value = False # Simulate insufficient funds
        
        strategy.execute_buy_signals(allocated_quantities, next_day_data_sample)
        
        mock_portfolio.can_trade.assert_called_once()
        mock_portfolio.open_position.assert_not_called() # Should not attempt to open position

    @patch('quantforge.strategies.rsi_strategy.Transaction')
    def test_execute_sell_signals(self, mock_transaction, mock_portfolio, tradeable_item_a, next_day_data_sample):
        """Tests the execution of sell signals."""
        strategy = RsiStrategy(portfolio=mock_portfolio)
        sell_signals = {tradeable_item_a: MagicMock(signal_type=TradingSignalType.SELL)}
        # Use attribute access
        sell_price = next_day_data_sample[tradeable_item_a].open
        # Use attribute access
        sell_date = next_day_data_sample[tradeable_item_a].date

        # Mock the position(s) to be closed
        mock_position = MagicMock()
        mock_position.open_transaction.quantity = 100 # Example quantity
        mock_portfolio.get_open_positions_by_item.return_value = [mock_position]
        
        strategy.execute_sell_signals(sell_signals, next_day_data_sample)
        
        # Verify portfolio methods
        mock_portfolio.get_open_positions_by_item.assert_called_once_with(tradeable_item_a)
        # Verify transaction object creation for the sell
        mock_transaction.assert_called_once_with(
            tradeable_item=tradeable_item_a,
            quantity=-100, # Should be negative of open quantity
            price=sell_price,
            date=sell_date,
            transaction_cost=0.0
        )
        # Verify position closure
        mock_portfolio.close_position.assert_called_once_with(mock_position, mock_transaction.return_value)

    def test_execute_sell_signals_no_position(self, mock_portfolio, tradeable_item_a, next_day_data_sample):
        """Tests sell execution when no position is actually open."""
        strategy = RsiStrategy(portfolio=mock_portfolio)
        sell_signals = {tradeable_item_a: MagicMock(signal_type=TradingSignalType.SELL)}
        mock_portfolio.get_open_positions_by_item.return_value = [] # No open positions
        
        strategy.execute_sell_signals(sell_signals, next_day_data_sample)
        
        mock_portfolio.get_open_positions_by_item.assert_called_once_with(tradeable_item_a)
        mock_portfolio.close_position.assert_not_called() 