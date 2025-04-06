import pytest
import pandas as pd
from datetime import date, timedelta

from quantforge.qtypes.assetclass import AssetClass
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.transaction import Transaction
from quantforge.strategies.trading_signal import TradingSignal, TradingSignalType
from quantforge.strategies.data_requirement import DataRequirement
from quantforge.strategies.abstract_strategy import StrategyInputData
from quantforge.strategies.simple_ticker_strategy import SimpleTickerDataStrategy
from quantforge.qtypes.ohlc import OHLCData


@pytest.fixture
def apple_stock():
    """Return an Apple stock tradeable item."""
    return TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)


@pytest.fixture
def microsoft_stock():
    """Return a Microsoft stock tradeable item."""
    return TradeableItem(id="MSFT", asset_class=AssetClass.EQUITY)


@pytest.fixture
def tradeable_items(apple_stock, microsoft_stock):
    """Return a list of tradeable items."""
    return [apple_stock, microsoft_stock]


@pytest.fixture
def start_date():
    """Return a start date for portfolio and data."""
    return date(2023, 1, 1)


@pytest.fixture
def portfolio(tradeable_items, start_date):
    """Return a basic portfolio."""
    return Portfolio(
        initial_cash=10000.0,
        allowed_tradeable_items=tradeable_items,
        start_date=start_date,
        allow_margin=False,
        allow_short=False,
    )


@pytest.fixture
def strategy(portfolio):
    """Return an instance of SimpleTickerDataStrategy."""
    return SimpleTickerDataStrategy(portfolio=portfolio)


@pytest.fixture
def sample_ticker_data_up():
    """Return sample ticker data where close increases."""
    return pd.DataFrame(
        {
            "open": [100, 101, 102],
            "high": [103, 104, 105],
            "low": [99, 100, 101],
            "close": [101, 102, 103],  # Increasing close
            "volume": [1000, 1100, 1200],
        }
    )


@pytest.fixture
def sample_ticker_data_down():
    """Return sample ticker data where close decreases."""
    return pd.DataFrame(
        {
            "open": [103, 102, 101],
            "high": [105, 104, 103],
            "low": [101, 100, 99],
            "close": [102, 101, 100],  # Decreasing close
            "volume": [1200, 1100, 1000],
        }
    )


@pytest.fixture
def sample_ticker_data_flat():
    """Return sample ticker data where close is flat."""
    return pd.DataFrame(
        {
            "open": [100, 100, 100],
            "high": [101, 101, 101],
            "low": [99, 99, 99],
            "close": [100, 100, 100],  # Flat close
            "volume": [1000, 1000, 1000],
        }
    )


@pytest.fixture
def next_day_prices(apple_stock, microsoft_stock, start_date):
    """Return sample next day OHLC data as OHLCData objects."""
    next_day = start_date + timedelta(days=10)  # Assume execution date
    return {
        apple_stock: OHLCData(
            date=next_day, open=105.0, high=106.0, low=104.0, close=105.5
        ),
        microsoft_stock: OHLCData(
            date=next_day, open=95.0, high=96.0, low=94.0, close=95.5
        ),
    }


@pytest.mark.unit
class TestSimpleTickerDataStrategy:
    """Tests for the SimpleTickerDataStrategy implementation."""

    def test_get_data_requirements(self, strategy):
        """Verify the strategy requires TICKER data."""
        assert strategy.get_data_requirements() == [DataRequirement.TICKER]

    def test_generate_buy_signal(self, strategy, apple_stock, sample_ticker_data_up):
        """Test generating a BUY signal when close price increases."""
        input_data: StrategyInputData = {
            apple_stock: {DataRequirement.TICKER: sample_ticker_data_up}
        }
        signals = strategy.generate_signals(input_data)
        assert len(signals) == 1
        assert apple_stock in signals
        assert signals[apple_stock].signal_type == TradingSignalType.BUY
        assert signals[apple_stock].signal_strength == 1.0

    def test_generate_sell_signal(self, strategy, apple_stock, sample_ticker_data_down):
        """Test generating a SELL signal when close price decreases."""
        input_data: StrategyInputData = {
            apple_stock: {DataRequirement.TICKER: sample_ticker_data_down}
        }
        signals = strategy.generate_signals(input_data)
        assert len(signals) == 1
        assert apple_stock in signals
        assert signals[apple_stock].signal_type == TradingSignalType.SELL
        assert signals[apple_stock].signal_strength == -1.0

    def test_generate_no_signal_flat(
        self, strategy, apple_stock, sample_ticker_data_flat
    ):
        """Test generating no signal when close price is flat."""
        input_data: StrategyInputData = {
            apple_stock: {DataRequirement.TICKER: sample_ticker_data_flat}
        }
        signals = strategy.generate_signals(input_data)
        assert len(signals) == 0  # Simple strategy doesn't generate HOLD

    def test_generate_no_signal_insufficient_data(self, strategy, apple_stock):
        """Test generating no signal with insufficient ticker data."""
        short_data = pd.DataFrame({"close": [100]})
        input_data: StrategyInputData = {
            apple_stock: {DataRequirement.TICKER: short_data}
        }
        signals = strategy.generate_signals(input_data)
        assert len(signals) == 0

        empty_data = pd.DataFrame()
        input_data_empty: StrategyInputData = {
            apple_stock: {DataRequirement.TICKER: empty_data}
        }
        signals_empty = strategy.generate_signals(input_data_empty)
        assert len(signals_empty) == 0

        no_close_data = pd.DataFrame({"open": [100, 101]})
        input_data_no_close: StrategyInputData = {
            apple_stock: {DataRequirement.TICKER: no_close_data}
        }
        signals_no_close = strategy.generate_signals(input_data_no_close)
        assert len(signals_no_close) == 0

    def test_generate_signals_multiple_items(
        self,
        strategy,
        apple_stock,
        microsoft_stock,
        sample_ticker_data_up,
        sample_ticker_data_down,
    ):
        """Test generating signals for multiple items with different trends."""
        input_data: StrategyInputData = {
            apple_stock: {DataRequirement.TICKER: sample_ticker_data_up},
            microsoft_stock: {DataRequirement.TICKER: sample_ticker_data_down},
        }
        signals = strategy.generate_signals(input_data)
        assert len(signals) == 2
        assert apple_stock in signals
        assert microsoft_stock in signals
        assert signals[apple_stock].signal_type == TradingSignalType.BUY
        assert signals[microsoft_stock].signal_type == TradingSignalType.SELL

    def test_allocate_capital_no_signals(self, strategy, next_day_prices):
        """Test capital allocation with no buy signals."""
        buy_signals = {}
        allocations = strategy.allocate_capital(buy_signals, next_day_prices)
        assert allocations == {}

    def test_allocate_capital_insufficient_cash(
        self, strategy, apple_stock, next_day_prices
    ):
        """Test capital allocation when cash is zero."""
        strategy.portfolio._cash = 0  # Manually set cash to zero
        buy_signals = {apple_stock: TradingSignal(TradingSignalType.BUY, 1.0)}
        allocations = strategy.allocate_capital(buy_signals, next_day_prices)
        assert allocations == {}
        strategy.portfolio._cash = 10000.0  # Reset cash

    def test_allocate_capital_equal_allocation(
        self, strategy, apple_stock, microsoft_stock, next_day_prices
    ):
        """Test equal capital allocation between two buy signals."""
        buy_signals = {
            apple_stock: TradingSignal(TradingSignalType.BUY, 1.0),
            microsoft_stock: TradingSignal(TradingSignalType.BUY, 1.0),
        }
        initial_cash = strategy.portfolio.cash
        cash_per_item = initial_cash / 2

        apple_price = next_day_prices[apple_stock]["open"]
        msft_price = next_day_prices[microsoft_stock]["open"]

        expected_apple_qty = int(cash_per_item // apple_price)
        expected_msft_qty = int(cash_per_item // msft_price)

        allocations = strategy.allocate_capital(buy_signals, next_day_prices)

        assert len(allocations) == 2
        assert apple_stock in allocations
        assert microsoft_stock in allocations
        assert allocations[apple_stock] == expected_apple_qty
        assert allocations[microsoft_stock] == expected_msft_qty

        total_cost = (expected_apple_qty * apple_price) + (
            expected_msft_qty * msft_price
        )
        assert total_cost <= initial_cash

    def test_allocate_capital_missing_price_data(
        self, strategy, apple_stock, microsoft_stock, next_day_prices
    ):
        """Test allocation when next day price is missing for one item."""
        buy_signals = {
            apple_stock: TradingSignal(TradingSignalType.BUY, 1.0),
            microsoft_stock: TradingSignal(TradingSignalType.BUY, 1.0),
        }
        limited_next_day_prices = {apple_stock: next_day_prices[apple_stock]}

        initial_cash = strategy.portfolio.cash
        apple_price = limited_next_day_prices[apple_stock]["open"]

        expected_apple_qty = int(initial_cash // apple_price)

        allocations = strategy.allocate_capital(buy_signals, limited_next_day_prices)

        assert len(allocations) == 1
        assert apple_stock in allocations
        assert allocations[apple_stock] == expected_apple_qty
        assert microsoft_stock not in allocations

    def test_execute_buy_signals(self, strategy, apple_stock, next_day_prices):
        """Test execution of buy signals."""
        initial_cash = strategy.portfolio.cash
        apple_price = next_day_prices[apple_stock]["open"]
        quantity_to_buy = 10
        allocated_quantities = {apple_stock: quantity_to_buy}

        assert not strategy.portfolio.has_position(apple_stock)

        strategy.execute_buy_signals(allocated_quantities, next_day_prices)

        assert strategy.portfolio.has_position(apple_stock)
        expected_cash = initial_cash - (quantity_to_buy * apple_price)
        assert strategy.portfolio.cash == pytest.approx(expected_cash)
        positions = strategy.portfolio._open_positions_by_tradeable_item.get(
            apple_stock, []
        )
        assert len(positions) == 1
        assert positions[0].open_transaction.quantity == quantity_to_buy
        assert positions[0].open_transaction.price == apple_price

    def test_execute_sell_signals(self, strategy, apple_stock, next_day_prices):
        """Test execution of sell signals for an existing position."""
        buy_price = 100.0
        buy_qty = 20
        buy_date = date(2023, 1, 5)
        open_transaction = Transaction(
            tradeable_item=apple_stock, quantity=buy_qty, price=buy_price, date=buy_date
        )
        _ = strategy.portfolio.open_position(open_transaction)
        initial_cash_after_buy = strategy.portfolio.cash
        assert strategy.portfolio.has_position(apple_stock)

        sell_signals = {apple_stock: TradingSignal(TradingSignalType.SELL, -1.0)}
        sell_price = next_day_prices[apple_stock]["open"]

        strategy.execute_sell_signals(sell_signals, next_day_prices)

        assert not strategy.portfolio.has_position(apple_stock)
        expected_cash = initial_cash_after_buy + (buy_qty * sell_price)
        assert strategy.portfolio.cash == pytest.approx(expected_cash)
        expected_pnl = (sell_price - buy_price) * buy_qty
        assert strategy.portfolio.realized_profit_loss == pytest.approx(expected_pnl)

    def test_execute_sell_signals_no_position(
        self, strategy, apple_stock, next_day_prices
    ):
        """Test executing sell signals when there is no open position."""
        initial_cash = strategy.portfolio.cash
        assert not strategy.portfolio.has_position(apple_stock)

        sell_signals = {apple_stock: TradingSignal(TradingSignalType.SELL, -1.0)}
        strategy.execute_sell_signals(sell_signals, next_day_prices)

        # No change should occur
        assert not strategy.portfolio.has_position(apple_stock)
        assert strategy.portfolio.cash == initial_cash
        assert strategy.portfolio.realized_profit_loss == 0.0

    def test_full_execute_cycle_buy(
        self, strategy, apple_stock, sample_ticker_data_up, next_day_prices
    ):
        """Test the full execute cycle resulting in a buy."""
        input_data: StrategyInputData = {
            apple_stock: {DataRequirement.TICKER: sample_ticker_data_up}
        }
        initial_cash = strategy.portfolio.cash
        apple_price = next_day_prices[apple_stock]["open"]

        assert not strategy.portfolio.has_position(apple_stock)

        strategy.execute(input_data, next_day_prices)

        expected_qty = int(initial_cash // apple_price)
        expected_cash = initial_cash - (expected_qty * apple_price)

        assert strategy.portfolio.has_position(apple_stock)
        assert strategy.portfolio.cash == pytest.approx(expected_cash)
        positions = strategy.portfolio._open_positions_by_tradeable_item.get(
            apple_stock, []
        )
        assert len(positions) == 1
        assert positions[0].open_transaction.quantity == expected_qty

    def test_full_execute_cycle_sell(
        self, strategy, apple_stock, sample_ticker_data_down, next_day_prices
    ):
        """Test the full execute cycle resulting in a sell."""
        buy_price = 100.0
        buy_qty = 10
        buy_date = date(2023, 1, 5)
        open_transaction = Transaction(
            tradeable_item=apple_stock, quantity=buy_qty, price=buy_price, date=buy_date
        )
        _ = strategy.portfolio.open_position(open_transaction)
        initial_cash_after_buy = strategy.portfolio.cash
        assert strategy.portfolio.has_position(apple_stock)

        input_data: StrategyInputData = {
            apple_stock: {DataRequirement.TICKER: sample_ticker_data_down}
        }
        sell_price = next_day_prices[apple_stock]["open"]

        strategy.execute(input_data, next_day_prices)

        expected_cash = initial_cash_after_buy + (buy_qty * sell_price)
        expected_pnl = (sell_price - buy_price) * buy_qty

        assert not strategy.portfolio.has_position(apple_stock)
        assert strategy.portfolio.cash == pytest.approx(expected_cash)
        assert strategy.portfolio.realized_profit_loss == pytest.approx(expected_pnl)

    def test_execute_missing_input_data_item(
        self,
        strategy,
        apple_stock,
        microsoft_stock,
        sample_ticker_data_up,
        next_day_prices,
    ):
        """Test execute when input_data is missing an allowed item (should proceed)."""
        input_data: StrategyInputData = {
            apple_stock: {DataRequirement.TICKER: sample_ticker_data_up}
        }
        initial_cash = strategy.portfolio.cash
        apple_price = next_day_prices[apple_stock]["open"]

        strategy.execute(input_data, next_day_prices)

        expected_qty = int(initial_cash // apple_price)
        expected_cash = initial_cash - (expected_qty * apple_price)

        assert strategy.portfolio.has_position(apple_stock)
        assert not strategy.portfolio.has_position(microsoft_stock)
        assert strategy.portfolio.cash == pytest.approx(expected_cash)

    def test_execute_missing_required_data_type(
        self, strategy, apple_stock, next_day_prices
    ):
        """Test execute when input_data is missing the required TICKER data type (should halt)."""
        input_data: StrategyInputData = {
            apple_stock: {DataRequirement.NEWS: pd.DataFrame()}  # Wrong data type
        }
        initial_cash = strategy.portfolio.cash

        strategy.execute(input_data, next_day_prices)

        assert not strategy.portfolio.has_position(apple_stock)
        assert strategy.portfolio.cash == initial_cash  # Cash unchanged
