import pytest
from datetime import date

from quantforge.qtypes.assetclass import AssetClass
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.transaction import Transaction


@pytest.mark.unit
class TestPortfolioInitialization:
    """Unit tests for Portfolio class initialization and properties."""

    @pytest.fixture
    def tradeable_items(self):
        """Return a list of tradeable items for testing."""
        return [
            TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY),
            TradeableItem(id="MSFT", asset_class=AssetClass.EQUITY),
            TradeableItem(id="BTC", asset_class=AssetClass.CRYPTOCURRENCY),
        ]

    @pytest.fixture
    def start_date(self):
        """Return a date for testing."""
        return date(2023, 1, 1)

    def test_valid_initialization(self, tradeable_items, start_date):
        """Test that a Portfolio can be properly initialized with valid parameters."""
        initial_cash = 100000.0
        portfolio = Portfolio(
            initial_cash=initial_cash,
            allowed_tradeable_items=tradeable_items,
            start_date=start_date,
        )

        assert portfolio.cash == initial_cash
        assert portfolio.allowed_tradeable_items == tradeable_items
        assert portfolio.allow_margin is False
        assert portfolio.allow_short is False

    def test_initialization_with_options(self, tradeable_items, start_date):
        """Test portfolio initialization with margin and short selling options."""
        initial_cash = 50000.0
        portfolio = Portfolio(
            initial_cash=initial_cash,
            allowed_tradeable_items=tradeable_items,
            start_date=start_date,
            allow_margin=True,
            allow_short=True,
        )

        assert portfolio.cash == initial_cash
        assert portfolio.allowed_tradeable_items == tradeable_items
        assert portfolio.allow_margin is True
        assert portfolio.allow_short is True

    def test_initialization_negative_cash(self, tradeable_items, start_date):
        """Test that initialization with negative cash raises ValueError."""
        with pytest.raises(ValueError, match="Initial cash cannot be negative."):
            Portfolio(
                initial_cash=-10000.0,
                allowed_tradeable_items=tradeable_items,
                start_date=start_date,
            )

    def test_initialization_zero_cash(self, tradeable_items, start_date):
        """Test that initialization with zero cash raises ValueError."""
        with pytest.raises(ValueError, match="Initial cash cannot be negative."):
            Portfolio(
                initial_cash=0.0,
                allowed_tradeable_items=tradeable_items,
                start_date=start_date,
            )

    def test_initialization_empty_tradeable_items(self, start_date):
        """Test that initialization with empty tradeable items raises ValueError."""
        with pytest.raises(
            ValueError, match="Allowed tradeable items cannot be empty."
        ):
            Portfolio(
                initial_cash=10000.0, allowed_tradeable_items=[], start_date=start_date
            )

    def test_initialization_invalid_tradeable_items(self, start_date):
        """Test that initialization with invalid tradeable items raises ValueError."""
        with pytest.raises(
            ValueError,
            match="All allowed tradeable items must be instances of TradeableItem.",
        ):
            Portfolio(
                initial_cash=10000.0,
                allowed_tradeable_items=["AAPL", "MSFT"],  # Not TradeableItem instances
                start_date=start_date,
            )

    def test_has_position_initially_false(self, tradeable_items, start_date):
        """Test that a new portfolio has no positions."""
        portfolio = Portfolio(
            initial_cash=10000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=start_date,
        )

        for item in tradeable_items:
            assert portfolio.has_position(item) is False

    def test_realized_profit_loss_initially_zero(self, tradeable_items, start_date):
        """Test that a new portfolio has zero realized profit/loss."""
        portfolio = Portfolio(
            initial_cash=10000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=start_date,
        )

        assert portfolio.realized_profit_loss == 0.0

    def test_initial_portfolio_value(self, tradeable_items, start_date):
        """Test that a new portfolio's value equals initial cash."""
        initial_cash = 10000.0
        portfolio = Portfolio(
            initial_cash=initial_cash,
            allowed_tradeable_items=tradeable_items,
            start_date=start_date,
        )

        # Create a prices dictionary with some arbitrary prices
        prices = {
            tradeable_items[0]: 150.0,  # AAPL
            tradeable_items[1]: 250.0,  # MSFT
            tradeable_items[2]: 30000.0,  # BTC
        }

        # Since we have no positions, portfolio value should equal cash
        assert portfolio.portfolio_value(prices) == initial_cash


@pytest.mark.unit
class TestPortfolioOperations:
    """Unit tests for Portfolio operations like opening and closing positions."""

    @pytest.fixture
    def apple_stock(self):
        """Return an Apple stock tradeable item."""
        return TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def tradeable_items(self, apple_stock):
        """Return a list of tradeable items for testing."""
        return [
            apple_stock,
            TradeableItem(id="MSFT", asset_class=AssetClass.EQUITY),
            TradeableItem(id="BTC", asset_class=AssetClass.CRYPTOCURRENCY),
        ]

    @pytest.fixture
    def portfolio(self, tradeable_items):
        """Return a portfolio for testing."""
        return Portfolio(
            initial_cash=100000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
        )

    def test_basic_buy_and_sell_workflow(self, portfolio, apple_stock):
        """Test a basic workflow of buying and selling a stock."""
        # Initial state check
        assert portfolio.cash == 100000.0
        assert not portfolio.has_position(apple_stock)
        assert portfolio.realized_profit_loss == 0.0

        # Create a buy transaction
        buy_date = date(2023, 1, 10)
        buy_price = 150.0
        quantity = 10
        buy_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=quantity,
            price=buy_price,
            date=buy_date,
        )

        # Open a position (buy)
        position = portfolio.open_position(buy_transaction)

        # Verify position was opened correctly
        assert portfolio.has_position(apple_stock)
        assert portfolio.cash == 100000.0 - (buy_price * quantity)
        assert position.open_transaction == buy_transaction
        assert not position.is_closed

        # Create prices dictionary for portfolio valuation
        current_prices = {apple_stock: buy_price}
        portfolio_value_after_buy = portfolio.portfolio_value(current_prices)
        # Portfolio value should be the same as initial cash (100000.0)
        # The cash decreased by (buy_price * quantity) but we gained stock worth (buy_price * quantity)
        assert portfolio_value_after_buy == 100000.0  # Total value remains the same

        # Create a sell transaction at a higher price
        sell_date = date(2023, 2, 15)
        sell_price = 175.0
        sell_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-quantity,  # Negative quantity for selling
            price=sell_price,
            date=sell_date,
        )

        # Close the position (sell)
        closed_position = portfolio.close_position(position, sell_transaction)

        # Verify position was closed correctly
        assert not portfolio.has_position(apple_stock)
        expected_profit = quantity * (sell_price - buy_price)
        assert portfolio.realized_profit_loss == expected_profit
        expected_cash = 100000.0 - (buy_price * quantity) + (sell_price * quantity)
        assert portfolio.cash == expected_cash
        assert closed_position.is_closed

        # Verify portfolio value after selling
        assert portfolio.portfolio_value(current_prices) == expected_cash
