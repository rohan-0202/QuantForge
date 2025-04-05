import pytest
from datetime import date

from quantforge.qtypes.assetclass import AssetClass
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.transaction import Transaction
from quantforge.qtypes.portfolio_position import PortfolioPosition


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


@pytest.mark.unit
class TestPortfolioOpenAndClosePosition:
    """Unit tests specifically for the open_position and close_position methods of the Portfolio class."""

    @pytest.fixture
    def apple_stock(self):
        """Return an Apple stock tradeable item."""
        return TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def microsoft_stock(self):
        """Return a Microsoft stock tradeable item."""
        return TradeableItem(id="MSFT", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def tradeable_items(self, apple_stock, microsoft_stock):
        """Return a list of tradeable items for testing."""
        return [
            apple_stock,
            microsoft_stock,
            TradeableItem(id="BTC", asset_class=AssetClass.CRYPTOCURRENCY),
        ]

    @pytest.fixture
    def standard_portfolio(self, tradeable_items):
        """Return a standard portfolio for testing (no margin, no short)."""
        return Portfolio(
            initial_cash=100000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
        )

    @pytest.fixture
    def margin_portfolio(self, tradeable_items):
        """Return a portfolio with margin trading allowed."""
        return Portfolio(
            initial_cash=100000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
            allow_margin=True,
            allow_short=False,
        )

    @pytest.fixture
    def short_portfolio(self, tradeable_items):
        """Return a portfolio with short selling allowed."""
        return Portfolio(
            initial_cash=100000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
            allow_margin=False,
            allow_short=True,
        )

    @pytest.fixture
    def full_portfolio(self, tradeable_items):
        """Return a portfolio with both margin trading and short selling allowed."""
        return Portfolio(
            initial_cash=100000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
            allow_margin=True,
            allow_short=True,
        )

    def test_open_single_position(self, standard_portfolio, apple_stock):
        """Test opening a single position."""
        # Initial state check
        assert standard_portfolio.cash == 100000.0
        assert not standard_portfolio.has_position(apple_stock)

        # Create a buy transaction
        buy_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        # Open a position
        position = standard_portfolio.open_position(buy_transaction)

        # Verify position was opened correctly
        assert standard_portfolio.has_position(apple_stock)
        assert position.open_transaction == buy_transaction
        assert not position.is_closed

        # Check cash was updated correctly: 100000 - (150 * 10 + 9.99) = 98490.01
        expected_cash = 100000.0 - (150.0 * 10 + 9.99)
        assert standard_portfolio.cash == pytest.approx(expected_cash)

    def test_open_multiple_positions_same_item(self, standard_portfolio, apple_stock):
        """Test opening multiple positions for the same tradeable item."""
        # Create first buy transaction
        buy_transaction1 = Transaction(
            tradeable_item=apple_stock,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        # Create second buy transaction
        buy_transaction2 = Transaction(
            tradeable_item=apple_stock,
            quantity=5,
            price=155.0,
            date=date(2023, 1, 15),
            transaction_cost=9.99,
        )

        # Open first position
        position1 = standard_portfolio.open_position(buy_transaction1)

        # Check after first position
        assert standard_portfolio.has_position(apple_stock)
        first_cash = 100000.0 - (150.0 * 10 + 9.99)
        assert standard_portfolio.cash == pytest.approx(first_cash)

        # Open second position
        position2 = standard_portfolio.open_position(buy_transaction2)

        # Check both positions are open and cash was updated
        assert standard_portfolio.has_position(apple_stock)
        assert not position1.is_closed
        assert not position2.is_closed

        second_cash = first_cash - (155.0 * 5 + 9.99)
        assert standard_portfolio.cash == pytest.approx(second_cash)

        # Check that we now have two different positions
        assert position1 != position2

        # Create prices dictionary for portfolio valuation
        current_prices = {apple_stock: 155.0}

        # Portfolio value should equal cash + positions value
        expected_value = second_cash + (10 * 155.0) + (5 * 155.0)
        assert standard_portfolio.portfolio_value(current_prices) == pytest.approx(
            expected_value
        )

    def test_open_positions_different_items(
        self, standard_portfolio, apple_stock, microsoft_stock
    ):
        """Test opening positions for different tradeable items."""
        # Create Apple transaction
        apple_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        # Create Microsoft transaction
        microsoft_transaction = Transaction(
            tradeable_item=microsoft_stock,
            quantity=5,
            price=250.0,
            date=date(2023, 1, 15),
            transaction_cost=9.99,
        )

        # Open Apple position
        standard_portfolio.open_position(apple_transaction)

        # Check Apple position
        assert standard_portfolio.has_position(apple_stock)
        assert not standard_portfolio.has_position(microsoft_stock)
        first_cash = 100000.0 - (150.0 * 10 + 9.99)
        assert standard_portfolio.cash == pytest.approx(first_cash)

        # Open Microsoft position
        standard_portfolio.open_position(microsoft_transaction)

        # Check both positions
        assert standard_portfolio.has_position(apple_stock)
        assert standard_portfolio.has_position(microsoft_stock)

        second_cash = first_cash - (250.0 * 5 + 9.99)
        assert standard_portfolio.cash == pytest.approx(second_cash)

        # Create prices dictionary for portfolio valuation
        current_prices = {apple_stock: 155.0, microsoft_stock: 255.0}

        # Portfolio value should equal cash + positions value
        expected_value = second_cash + (10 * 155.0) + (5 * 255.0)
        assert standard_portfolio.portfolio_value(current_prices) == pytest.approx(
            expected_value
        )

    def test_open_short_position_when_allowed(self, short_portfolio, apple_stock):
        """Test opening a short position when short selling is allowed."""
        # Create a short transaction
        short_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-10,  # Negative quantity for short
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        # Open a short position
        position = short_portfolio.open_position(short_transaction)

        # Verify short position was opened correctly
        assert short_portfolio.has_position(apple_stock)
        assert position.open_transaction == short_transaction
        assert not position.is_closed
        assert position.open_transaction.quantity < 0  # Confirm it's a short

        # Check cash was updated correctly (increases for shorts): 100000 + (150 * 10) - 9.99 = 101490.01
        expected_cash = 100000.0 + (150.0 * 10) - 9.99
        assert short_portfolio.cash == pytest.approx(expected_cash)

    def test_open_short_position_when_not_allowed(
        self, standard_portfolio, apple_stock
    ):
        """Test opening a short position when short selling is not allowed."""
        # Create a short transaction
        short_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-10,  # Negative quantity for short
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        # Attempt to open a short position should fail
        with pytest.raises(ValueError):
            standard_portfolio.open_position(short_transaction)

        # Verify no position was opened and cash didn't change
        assert not standard_portfolio.has_position(apple_stock)
        assert standard_portfolio.cash == 100000.0

    def test_open_position_with_insufficient_cash(
        self, standard_portfolio, apple_stock
    ):
        """Test opening a position with insufficient cash and no margin allowed."""
        # Create a transaction that costs more than available cash
        large_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=1000,  # Large quantity requiring more cash than available
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        # Attempt to open position should fail
        with pytest.raises(ValueError):
            standard_portfolio.open_position(large_transaction)

        # Verify no position was opened and cash didn't change
        assert not standard_portfolio.has_position(apple_stock)
        assert standard_portfolio.cash == 100000.0

    def test_open_position_with_margin(self, margin_portfolio, apple_stock):
        """Test opening a position with insufficient cash but margin trading allowed."""
        # Create a transaction that costs more than available cash
        large_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=1000,  # Large quantity requiring more cash than available
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        # Open position with margin
        position = margin_portfolio.open_position(large_transaction)

        # Verify position was opened
        assert margin_portfolio.has_position(apple_stock)
        assert position.open_transaction == large_transaction
        assert not position.is_closed

        # Check cash was updated (should be negative due to margin)
        expected_cash = 100000.0 - (150.0 * 1000 + 9.99)
        assert margin_portfolio.cash == pytest.approx(expected_cash)
        assert margin_portfolio.cash < 0  # Cash should be negative

    def test_open_both_long_and_short_positions(self, full_portfolio, apple_stock):
        """Test opening both long and short positions for the same item and closing them in random order."""
        # Create a long transaction
        long_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        # Create a short transaction
        short_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-5,  # Negative quantity for short
            price=160.0,
            date=date(2023, 1, 15),
            transaction_cost=9.99,
        )

        # Open long position
        long_position = full_portfolio.open_position(long_transaction)

        # Check long position
        assert full_portfolio.has_position(apple_stock)
        first_cash = 100000.0 - (150.0 * 10 + 9.99)
        assert full_portfolio.cash == pytest.approx(first_cash)

        # Open short position
        short_position = full_portfolio.open_position(short_transaction)

        # Check both positions exist
        assert full_portfolio.has_position(apple_stock)
        assert not long_position.is_closed
        assert not short_position.is_closed

        # Check cash after short (increases): first_cash + (160 * 5) - 9.99
        second_cash = first_cash + (160.0 * 5) - 9.99
        assert full_portfolio.cash == pytest.approx(second_cash)

        # Validate positions are different
        assert long_position != short_position
        assert long_position.open_transaction.quantity > 0  # Long is positive
        assert short_position.open_transaction.quantity < 0  # Short is negative

        # Create prices dictionary for portfolio valuation
        current_prices = {apple_stock: 155.0}

        # Portfolio value: cash + (long position value) - (short position obligation)
        expected_value = second_cash + (10 * 155.0) - (5 * 155.0)
        assert full_portfolio.portfolio_value(current_prices) == pytest.approx(
            expected_value
        )

        # Now close the positions in random order (short first, then long)

        # Create close transaction for short position (buying back shares)
        short_close_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=5,  # Positive to close short
            price=145.0,  # Lower than open short price (profitable)
            date=date(2023, 2, 1),
            transaction_cost=9.99,
        )

        # Close the short position
        closed_short = full_portfolio.close_position(
            short_position, short_close_transaction
        )

        # Check short position is closed
        assert closed_short.is_closed

        # Calculate expected cash after closing short:
        # When closing short at 145, we pay 145 * 5 + 9.99 = 735.99
        # But we already received 160 * 5 = 800 when opening, so we profit 800 - 735.99 = 64.01
        third_cash = second_cash - (145.0 * 5 + 9.99)
        assert full_portfolio.cash == pytest.approx(third_cash)

        # Portfolio value after closing short should include only the long position
        expected_value_after_short_close = third_cash + (10 * 155.0)
        assert full_portfolio.portfolio_value(current_prices) == pytest.approx(
            expected_value_after_short_close
        )

        # Create close transaction for long position
        long_close_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-10,  # Negative to close long
            price=175.0,  # Higher than open price (profitable)
            date=date(2023, 2, 15),
            transaction_cost=9.99,
        )

        # Close the long position
        closed_long = full_portfolio.close_position(
            long_position, long_close_transaction
        )

        # Check long position is closed
        assert closed_long.is_closed

        # Calculate expected cash after closing long:
        # When closing long, we receive 175 * 10 - 9.99 = 1740.01
        final_cash = third_cash + (175.0 * 10) - 9.99
        assert full_portfolio.cash == pytest.approx(final_cash)

        # Portfolio should have no positions now
        assert not full_portfolio.has_position(apple_stock)

        # Portfolio value should equal final cash
        assert full_portfolio.portfolio_value(current_prices) == pytest.approx(
            final_cash
        )

        # Check realized profit/loss
        # Short profit: (160 - 145) * 5 - 2 * 9.99 = 55 - 19.98 = 35.02
        # Long profit: (175 - 150) * 10 - 2 * 9.99 = 250 - 19.98 = 230.02
        # Total profit: 35.02 + 230.02 = 265.04
        expected_total_profit = ((160 - 145) * 5) + ((175 - 150) * 10) - 4 * 9.99
        assert full_portfolio.realized_profit_loss == pytest.approx(
            expected_total_profit
        )

    def test_open_position_with_non_allowed_item(self, standard_portfolio):
        """Test opening a position with a tradeable item not in the allowed list."""
        # Create a non-allowed tradeable item
        non_allowed_item = TradeableItem(id="AMZN", asset_class=AssetClass.EQUITY)

        # Create a transaction with non-allowed item
        transaction = Transaction(
            tradeable_item=non_allowed_item,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        # Attempt to open position should fail
        with pytest.raises(ValueError):
            standard_portfolio.open_position(transaction)

        # Verify no position was opened and cash didn't change
        assert not standard_portfolio.has_position(non_allowed_item)
        assert standard_portfolio.cash == 100000.0


@pytest.mark.unit
class TestPortfolioCanTrade:
    """Unit tests specifically for the can_trade method of the Portfolio class."""

    @pytest.fixture
    def apple_stock(self):
        """Return an Apple stock tradeable item."""
        return TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def microsoft_stock(self):
        """Return a Microsoft stock tradeable item."""
        return TradeableItem(id="MSFT", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def bitcoin(self):
        """Return a Bitcoin tradeable item."""
        return TradeableItem(id="BTC", asset_class=AssetClass.CRYPTOCURRENCY)

    @pytest.fixture
    def tradeable_items(self, apple_stock, microsoft_stock, bitcoin):
        """Return a list of tradeable items for testing."""
        return [apple_stock, microsoft_stock, bitcoin]

    @pytest.fixture
    def standard_portfolio(self, tradeable_items):
        """Return a standard portfolio for testing (no margin, no short)."""
        return Portfolio(
            initial_cash=10000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
        )

    @pytest.fixture
    def margin_portfolio(self, tradeable_items):
        """Return a portfolio with margin trading allowed."""
        return Portfolio(
            initial_cash=10000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
            allow_margin=True,
            allow_short=False,
        )

    @pytest.fixture
    def short_portfolio(self, tradeable_items):
        """Return a portfolio with short selling allowed."""
        return Portfolio(
            initial_cash=10000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
            allow_margin=False,
            allow_short=True,
        )

    @pytest.fixture
    def full_portfolio(self, tradeable_items):
        """Return a portfolio with both margin trading and short selling allowed."""
        return Portfolio(
            initial_cash=10000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
            allow_margin=True,
            allow_short=True,
        )

    @pytest.fixture
    def portfolio_with_open_position(self, tradeable_items, apple_stock):
        """Return a portfolio with an open position in Apple stock."""
        portfolio = Portfolio(
            initial_cash=10000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
        )

        # Open a position in Apple stock
        transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )
        portfolio.open_position(transaction)

        return portfolio

    @pytest.fixture
    def portfolio_with_short_position(self, tradeable_items, apple_stock):
        """Return a portfolio with a short position in Apple stock."""
        portfolio = Portfolio(
            initial_cash=10000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
            allow_short=True,
        )

        # Open a short position in Apple stock
        transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-5,
            price=160.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )
        portfolio.open_position(transaction)

        return portfolio

    def test_can_trade_allowed_item(self, standard_portfolio, apple_stock):
        """Test can_trade with an allowed tradeable item."""
        transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        assert standard_portfolio.can_trade(transaction) is True

    def test_cannot_trade_non_allowed_item(self, standard_portfolio):
        """Test can_trade with a non-allowed tradeable item."""
        non_allowed_item = TradeableItem(id="AMZN", asset_class=AssetClass.EQUITY)

        transaction = Transaction(
            tradeable_item=non_allowed_item,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        assert standard_portfolio.can_trade(transaction) is False

    def test_can_trade_close_position(self, portfolio_with_open_position, apple_stock):
        """Test can_trade with a transaction that closes an existing position."""
        # Create a transaction that would close the existing position
        close_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-10,  # Opposite of the open position quantity
            price=160.0,
            date=date(2023, 1, 15),
            transaction_cost=9.99,
        )

        # Should be tradeable regardless of other constraints
        assert portfolio_with_open_position.can_trade(close_transaction) is True

    def test_can_trade_close_short_position(
        self, portfolio_with_short_position, apple_stock
    ):
        """Test can_trade with a transaction that closes an existing short position."""
        # Create a transaction that would close the existing short position
        close_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=5,  # Opposite of the open short position quantity
            price=140.0,
            date=date(2023, 1, 15),
            transaction_cost=9.99,
        )

        # Should be tradeable regardless of other constraints
        assert portfolio_with_short_position.can_trade(close_transaction) is True

    def test_can_trade_short_when_allowed(self, short_portfolio, apple_stock):
        """Test can_trade with a short sale when short selling is allowed."""
        short_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-10,  # Negative for short
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        assert short_portfolio.can_trade(short_transaction) is True

    def test_cannot_trade_short_when_not_allowed(self, standard_portfolio, apple_stock):
        """Test can_trade with a short sale when short selling is not allowed."""
        short_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-10,  # Negative for short
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        assert standard_portfolio.can_trade(short_transaction) is False

    def test_can_trade_with_sufficient_cash(self, standard_portfolio, apple_stock):
        """Test can_trade with a purchase that is within available cash."""
        # Transaction cost is less than portfolio cash
        transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=10,
            price=150.0,  # Total cost: 150 * 10 + 9.99 = 1509.99
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        assert standard_portfolio.can_trade(transaction) is True

    def test_cannot_trade_with_insufficient_cash_no_margin(
        self, standard_portfolio, apple_stock
    ):
        """Test can_trade with a purchase that exceeds available cash when margin is not allowed."""
        # Transaction cost exceeds portfolio cash
        transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=100,
            price=150.0,  # Total cost: 150 * 100 + 9.99 = 15009.99
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        assert standard_portfolio.can_trade(transaction) is False

    def test_can_trade_with_insufficient_cash_but_margin_allowed(
        self, margin_portfolio, apple_stock
    ):
        """Test can_trade with a purchase that exceeds available cash when margin is allowed."""
        # Transaction cost exceeds portfolio cash
        transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=100,
            price=150.0,  # Total cost: 150 * 100 + 9.99 = 15009.99
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        assert margin_portfolio.can_trade(transaction) is True

    def test_can_trade_boundary_cases(
        self, standard_portfolio, margin_portfolio, apple_stock
    ):
        """Test can_trade with boundary cases for cash availability."""
        # Transaction cost exactly equals portfolio cash
        exact_cash_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=66,
            price=151.36,  # Total cost: 151.36 * 66 + 9.99 ≈ 9999.75
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        # Transaction cost slightly exceeds portfolio cash
        slightly_over_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=67,
            price=151.36,  # Total cost: 151.36 * 67 + 9.99 ≈ 10151.11
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        # Standard portfolio (no margin) should allow exact cash transaction but not over
        assert standard_portfolio.can_trade(exact_cash_transaction) is True
        assert standard_portfolio.can_trade(slightly_over_transaction) is False

        # Margin portfolio should allow both
        assert margin_portfolio.can_trade(exact_cash_transaction) is True
        assert margin_portfolio.can_trade(slightly_over_transaction) is True

    def test_can_trade_combinations(
        self, full_portfolio, standard_portfolio, apple_stock
    ):
        """Test can_trade with combinations of conditions."""
        # Case 1: Non-allowed item but otherwise valid - should be False for any portfolio
        non_allowed_item = TradeableItem(id="AMZN", asset_class=AssetClass.EQUITY)

        transaction1 = Transaction(
            tradeable_item=non_allowed_item,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        assert full_portfolio.can_trade(transaction1) is False

        # Case 2: Short sale with insufficient cash but short and margin allowed - should be True
        transaction2 = Transaction(
            tradeable_item=apple_stock,
            quantity=-100,  # Large short position
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        assert full_portfolio.can_trade(transaction2) is True

        # Case 3: Extremely large position (exceeds even margin capability)
        # This is implementation-dependent but generally margin has limits
        transaction3 = Transaction(
            tradeable_item=apple_stock,
            quantity=1000000,  # Extremely large position
            price=150.0,  # Total cost: 150 * 1000000 = 150,000,000
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )

        # The implementation allows unlimited margin, so this should be true for margin portfolio
        assert full_portfolio.can_trade(transaction3) is True
        assert standard_portfolio.can_trade(transaction3) is False


@pytest.mark.unit
class TestPortfolioClosePositionErrors:
    """Unit tests for error cases in the close_position method of the Portfolio class."""

    @pytest.fixture
    def apple_stock(self):
        """Return an Apple stock tradeable item."""
        return TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def microsoft_stock(self):
        """Return a Microsoft stock tradeable item."""
        return TradeableItem(id="MSFT", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def tradeable_items(self, apple_stock, microsoft_stock):
        """Return a list of tradeable items for testing."""
        return [
            apple_stock,
            microsoft_stock,
            TradeableItem(id="BTC", asset_class=AssetClass.CRYPTOCURRENCY),
        ]

    @pytest.fixture
    def portfolio_with_position(self, tradeable_items, apple_stock):
        """Return a portfolio with an open position in Apple stock."""
        portfolio = Portfolio(
            initial_cash=10000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
        )

        # Open a position in Apple stock
        transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )
        position = portfolio.open_position(transaction)

        return portfolio, position

    def test_close_position_with_wrong_tradeable_item(
        self, portfolio_with_position, microsoft_stock
    ):
        """Test that closing a position with a different tradeable item raises an error."""
        portfolio, position = portfolio_with_position

        # Create a close transaction with a different tradeable item
        close_transaction = Transaction(
            tradeable_item=microsoft_stock,  # Different from the position's Apple stock
            quantity=-10,
            price=200.0,
            date=date(2023, 1, 15),
            transaction_cost=9.99,
        )

        # Attempt to close the position with the wrong tradeable item
        with pytest.raises(
            ValueError, match="Close transaction must match open transaction."
        ):
            portfolio.close_position(position, close_transaction)

    def test_close_position_with_earlier_date(
        self, portfolio_with_position, apple_stock
    ):
        """Test that closing a position with a date earlier than the open date raises an error."""
        portfolio, position = portfolio_with_position

        # The position was opened on 2023-01-10
        # Create a close transaction with an earlier date
        close_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-10,
            price=160.0,
            date=date(2023, 1, 5),  # Earlier than open date
            transaction_cost=9.99,
        )

        # Attempt to close the position with an earlier date
        with pytest.raises(
            ValueError,
            match="Close transaction date must be after open transaction date.",
        ):
            portfolio.close_position(position, close_transaction)

    def test_close_position_with_wrong_quantity(
        self, portfolio_with_position, apple_stock
    ):
        """Test that closing a position with a quantity that doesn't match the open position raises an error."""
        portfolio, position = portfolio_with_position

        # Create a close transaction with a different quantity
        close_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-5,  # Different from the position's quantity of 10
            price=160.0,
            date=date(2023, 1, 15),
            transaction_cost=9.99,
        )

        # Attempt to close the position with the wrong quantity
        with pytest.raises(
            ValueError,
            match="Close transaction quantity must be the -ve open transaction quantity.",
        ):
            portfolio.close_position(position, close_transaction)

    def test_close_already_closed_position(self, portfolio_with_position, apple_stock):
        """Test that closing an already closed position raises an error."""
        portfolio, position = portfolio_with_position

        # Create a close transaction
        close_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-10,
            price=160.0,
            date=date(2023, 1, 15),
            transaction_cost=9.99,
        )

        # Close the position
        closed_position = portfolio.close_position(position, close_transaction)

        # Attempt to close the position again
        with pytest.raises(ValueError, match="Position is already closed."):
            portfolio.close_position(closed_position, close_transaction)

    def test_close_non_existent_position(self, tradeable_items, apple_stock):
        """Test that closing a position that is not in the portfolio raises an error."""
        portfolio = Portfolio(
            initial_cash=10000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
        )

        # First create and add a different position to initialize the dictionary for apple_stock
        initial_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=5,  # Different quantity than our test position
            price=140.0,
            date=date(2023, 1, 5),
            transaction_cost=9.99,
        )
        portfolio.open_position(initial_transaction)

        # Create a position that is not added to the portfolio
        open_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )
        position = PortfolioPosition(open_transaction)

        # Create a close transaction
        close_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=-10,
            price=160.0,
            date=date(2023, 1, 15),
            transaction_cost=9.99,
        )

        # Attempt to close a position that's not in the portfolio
        with pytest.raises(ValueError, match="Position not found in open positions."):
            portfolio.close_position(position, close_transaction)


@pytest.mark.unit
class TestPortfolioValueEdgeCases:
    """Unit tests for edge cases in the portfolio_value method of the Portfolio class."""

    @pytest.fixture
    def apple_stock(self):
        """Return an Apple stock tradeable item."""
        return TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def microsoft_stock(self):
        """Return a Microsoft stock tradeable item."""
        return TradeableItem(id="MSFT", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def bitcoin(self):
        """Return a Bitcoin tradeable item."""
        return TradeableItem(id="BTC", asset_class=AssetClass.CRYPTOCURRENCY)

    @pytest.fixture
    def tradeable_items(self, apple_stock, microsoft_stock, bitcoin):
        """Return a list of tradeable items for testing."""
        return [apple_stock, microsoft_stock, bitcoin]

    @pytest.fixture
    def portfolio_with_positions(
        self, tradeable_items, apple_stock, microsoft_stock, bitcoin
    ):
        """Return a portfolio with multiple open positions."""
        portfolio = Portfolio(
            initial_cash=10000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
            allow_short=True,
        )

        # Open a long position in Apple
        apple_transaction = Transaction(
            tradeable_item=apple_stock,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )
        portfolio.open_position(apple_transaction)

        # Open a short position in Microsoft
        msft_transaction = Transaction(
            tradeable_item=microsoft_stock,
            quantity=-5,
            price=250.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )
        portfolio.open_position(msft_transaction)

        # Open a long position in Bitcoin
        btc_transaction = Transaction(
            tradeable_item=bitcoin,
            quantity=0.1,  # Reduced from 0.5 to make it affordable
            price=30000.0,
            date=date(2023, 1, 10),
            transaction_cost=9.99,
        )
        portfolio.open_position(btc_transaction)

        return portfolio

    def test_portfolio_value_missing_price(
        self, portfolio_with_positions, apple_stock, microsoft_stock
    ):
        """Test portfolio valuation when a required price is missing from the prices dictionary."""
        # Create a prices dictionary missing the Bitcoin price
        incomplete_prices = {
            apple_stock: 160.0,
            microsoft_stock: 260.0,
            # Bitcoin price is missing
        }

        # Attempt to calculate portfolio value should raise ValueError
        with pytest.raises(ValueError, match="Price not found for tradeable item."):
            portfolio_with_positions.portfolio_value(incomplete_prices)

    def test_portfolio_value_mixed_profitability(
        self, portfolio_with_positions, apple_stock, microsoft_stock, bitcoin
    ):
        """Test portfolio value with mixed profitable and unprofitable positions."""
        # Create prices that make some positions profitable and others unprofitable
        mixed_prices = {
            apple_stock: 180.0,  # Up from 150 (profitable)
            microsoft_stock: 200.0,  # Down from 250 (profitable for short)
            bitcoin: 25000.0,  # Down from 30000 (unprofitable)
        }

        # Calculate expected portfolio value:
        # Cash: 10000 - (150*10 + 9.99) + (250*5 - 9.99) - (30000*0.1 + 9.99) = 10000 - 1509.99 + 1240.01 - 3009.99 = 6720.03
        # Apple position: 10 * 180 = 1800
        # Microsoft position: -5 * 200 = -1000
        # Bitcoin position: 0.1 * 25000 = 2500
        # Total: 6720.03 + 1800 - 1000 + 2500 = 10020.03

        expected_value = (
            # Cash remaining
            10000.0
            - (150.0 * 10 + 9.99)
            + (250.0 * 5 - 9.99)
            - (30000.0 * 0.1 + 9.99)
            # Current positions value
            + (10 * 180.0)
            + (-5 * 200.0)
            + (0.1 * 25000.0)
        )

        # Calculate actual portfolio value
        actual_value = portfolio_with_positions.portfolio_value(mixed_prices)

        # Verify the calculation
        assert actual_value == pytest.approx(expected_value)

    def test_portfolio_value_extreme_price_movements(
        self, portfolio_with_positions, apple_stock, microsoft_stock, bitcoin
    ):
        """Test portfolio value with extreme price movements (very high and very low prices)."""
        # Create extreme prices
        extreme_prices = {
            apple_stock: 1500.0,  # 10x increase
            microsoft_stock: 1.0,  # 99.6% decrease
            bitcoin: 300000.0,  # 10x increase
        }

        # Calculate expected portfolio value:
        # Cash: Same as before = 6720.03
        # Apple position: 10 * 1500 = 15000
        # Microsoft position: -5 * 1 = -5
        # Bitcoin position: 0.1 * 300000 = 30000
        # Total: 6720.03 + 15000 - 5 + 30000 = 51715.03

        expected_value = (
            # Cash remaining
            10000.0
            - (150.0 * 10 + 9.99)
            + (250.0 * 5 - 9.99)
            - (30000.0 * 0.1 + 9.99)
            # Current positions value
            + (10 * 1500.0)
            + (-5 * 1.0)
            + (0.1 * 300000.0)
        )

        # Calculate actual portfolio value
        actual_value = portfolio_with_positions.portfolio_value(extreme_prices)

        # Verify the calculation
        assert actual_value == pytest.approx(expected_value)

        # Verify that the portfolio value is extremely high due to price movements
        assert actual_value > 50000  # Significantly higher than initial value
