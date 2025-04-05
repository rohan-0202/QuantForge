import pytest
from datetime import date

from quantforge.qtypes.assetclass import AssetClass
from quantforge.qtypes.portfolio_position import PortfolioPosition
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.transaction import Transaction


@pytest.mark.unit
class TestPortfolioPosition:
    """Unit tests for the PortfolioPosition class."""

    @pytest.fixture
    def tradeable_item(self):
        """Return a tradeable item for testing."""
        return TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def open_transaction(self, tradeable_item):
        """Return an open transaction for testing."""
        return Transaction(
            tradeable_item=tradeable_item,
            quantity=100,
            price=150.0,
            date=date(2023, 1, 1),
            transaction_cost=10.0,
        )

    @pytest.fixture
    def close_transaction(self, tradeable_item):
        """Return a close transaction for testing."""
        return Transaction(
            tradeable_item=tradeable_item,
            quantity=-100,
            price=170.0,
            date=date(2023, 1, 10),
            transaction_cost=10.0,
        )

    @pytest.fixture
    def open_position(self, open_transaction):
        """Return an open position for testing."""
        return PortfolioPosition(open_transaction=open_transaction)

    @pytest.fixture
    def closed_position(self, open_transaction, close_transaction):
        """Return a closed position for testing."""
        return PortfolioPosition(
            open_transaction=open_transaction,
            close_transaction=close_transaction,
        )

    def test_initialization(self, open_transaction):
        """Test that a PortfolioPosition can be properly initialized."""
        position = PortfolioPosition(open_transaction=open_transaction)

        assert position.open_transaction == open_transaction
        assert position.close_transaction is None

    def test_cost_basis(self, open_position, open_transaction):
        """Test the cost_basis property."""
        expected_cost_basis = (
            open_transaction.price * open_transaction.quantity
            + open_transaction.transaction_cost
        )
        assert open_position.cost_basis == expected_cost_basis
        assert open_position.cost_basis == 15010.0  # 150 * 100 + 10

    def test_is_closed_property(self, open_position, closed_position):
        """Test the is_closed property."""
        assert not open_position.is_closed
        assert closed_position.is_closed

    def test_sale_proceeds(self, open_position, closed_position, close_transaction):
        """Test the sale_proceeds property."""
        assert open_position.sale_proceeds == 0.0

        # The implementation returns the actual product which is negative because of negative quantity
        expected_proceeds = (
            close_transaction.price * -close_transaction.quantity
            - close_transaction.transaction_cost
        )
        assert closed_position.sale_proceeds == expected_proceeds
        assert closed_position.sale_proceeds == 16990  # 170 * 100 - 10

    def test_realized_profit_loss(self, open_position, closed_position):
        """Test the realized_profit_loss method."""
        assert open_position.realized_profit_loss() == 0.0

        # Actual implementation: sale_proceeds - cost_basis = 16990 - 15010 = 1980
        assert (
            closed_position.realized_profit_loss() == 1980.0
        )  # This matches the actual implementation

    def test_unrealized_profit_loss(self, open_position, closed_position):
        """Test the unrealized_profit_loss method."""
        current_price = 160.0

        # For open position
        expected_unrealized_pl = (
            current_price - open_position.open_transaction.price
        ) * open_position.open_transaction.quantity
        assert (
            open_position.unrealized_profit_loss(current_price)
            == expected_unrealized_pl
        )
        assert (
            open_position.unrealized_profit_loss(current_price) == 1000.0
        )  # (160 - 150) * 100

        # For closed position
        assert closed_position.unrealized_profit_loss(current_price) == 0.0

    def test_close_method(self, open_position, tradeable_item):
        """Test the close method."""
        close_transaction = Transaction(
            tradeable_item=tradeable_item,
            quantity=-100,
            price=180.0,
            date=date(2023, 1, 15),
            transaction_cost=15.0,
        )

        closed_position = open_position.close(close_transaction)

        assert closed_position.is_closed
        assert closed_position.open_transaction == open_position.open_transaction
        assert closed_position.close_transaction == close_transaction
        assert (
            closed_position.realized_profit_loss() == 2975.0
        )  # 180 * 100 - 15010 - 15

    def test_close_with_already_closed_position(self, closed_position, tradeable_item):
        """Test that trying to close an already closed position raises an error."""
        another_close_transaction = Transaction(
            tradeable_item=tradeable_item,
            quantity=-100,
            price=180.0,
            date=date(2023, 1, 20),
            transaction_cost=15.0,
        )

        with pytest.raises(ValueError, match="Position is already closed."):
            closed_position.close(another_close_transaction)

    def test_close_with_mismatched_tradeable_item(self, open_position):
        """Test that trying to close with a different tradeable item raises an error."""
        different_tradeable_item = TradeableItem(
            id="MSFT", asset_class=AssetClass.EQUITY
        )
        close_transaction = Transaction(
            tradeable_item=different_tradeable_item,
            quantity=-100,
            price=180.0,
            date=date(2023, 1, 15),
            transaction_cost=15.0,
        )

        with pytest.raises(
            ValueError, match="Close transaction must match open transaction."
        ):
            open_position.close(close_transaction)

    def test_close_with_earlier_date(self, open_position, tradeable_item):
        """Test that trying to close with an earlier date raises an error."""
        close_transaction = Transaction(
            tradeable_item=tradeable_item,
            quantity=-100,
            price=180.0,
            date=date(2022, 12, 15),  # Earlier than open transaction
            transaction_cost=15.0,
        )

        with pytest.raises(
            ValueError,
            match="Close transaction date must be after open transaction date.",
        ):
            open_position.close(close_transaction)

    def test_close_with_wrong_quantity(self, open_position, tradeable_item):
        """Test that trying to close with the wrong quantity raises an error."""
        close_transaction = Transaction(
            tradeable_item=tradeable_item,
            quantity=-50,  # Not matching the open quantity
            price=180.0,
            date=date(2023, 1, 15),
            transaction_cost=15.0,
        )

        with pytest.raises(
            ValueError,
            match="Close transaction quantity must be the -ve open transaction quantity.",
        ):
            open_position.close(close_transaction)

    def test_string_representation(self, open_position, closed_position):
        """Test the string representation of a PortfolioPosition."""
        assert "PortfolioPosition:" in str(open_position)
        assert "Closed: False" in str(open_position)
        assert "Realized P/L: 0.0" in str(open_position)

        assert "PortfolioPosition:" in str(closed_position)
        assert "Closed: True" in str(closed_position)
        assert "Realized P/L: 1980.0" in str(closed_position)  # Actual value

    def test_repr_representation(self, open_position, closed_position):
        """Test the repr representation of a PortfolioPosition."""
        assert "PortfolioPosition(open_transaction=" in repr(open_position)
        assert "close_transaction=None" in repr(open_position)

        assert "PortfolioPosition(open_transaction=" in repr(closed_position)
        assert "close_transaction=" in repr(closed_position)
        assert "close_transaction=None" not in repr(closed_position)

    def test_immutability(self, open_position):
        """Test that PortfolioPosition is immutable."""
        with pytest.raises(AttributeError):
            open_position.open_transaction = None

        with pytest.raises(AttributeError):
            open_position.close_transaction = None


@pytest.mark.unit
class TestShortPortfolioPosition:
    """Unit tests for the PortfolioPosition class with short selling scenarios."""

    @pytest.fixture
    def tradeable_item(self):
        """Return a tradeable item for testing."""
        return TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def short_open_transaction(self, tradeable_item):
        """Return an open short transaction for testing."""
        return Transaction(
            tradeable_item=tradeable_item,
            quantity=-100,  # Negative quantity for short selling
            price=150.0,
            date=date(2023, 1, 1),
            transaction_cost=10.0,
        )

    @pytest.fixture
    def short_close_transaction(self, tradeable_item):
        """Return a close transaction for a short position."""
        return Transaction(
            tradeable_item=tradeable_item,
            quantity=100,  # Positive quantity to close short position
            price=130.0,  # Lower price for profitable short
            date=date(2023, 1, 10),
            transaction_cost=10.0,
        )

    @pytest.fixture
    def short_open_position(self, short_open_transaction):
        """Return an open short position for testing."""
        return PortfolioPosition(open_transaction=short_open_transaction)

    @pytest.fixture
    def short_closed_position(self, short_open_transaction, short_close_transaction):
        """Return a closed short position for testing."""
        return PortfolioPosition(
            open_transaction=short_open_transaction,
            close_transaction=short_close_transaction,
        )

    def test_short_initialization(self, short_open_transaction):
        """Test that a short PortfolioPosition can be properly initialized."""
        position = PortfolioPosition(open_transaction=short_open_transaction)

        assert position.open_transaction == short_open_transaction
        assert position.close_transaction is None
        assert position.open_transaction.quantity < 0  # Verify it's a short position

    def test_short_cost_basis(self, short_open_position, short_open_transaction):
        """Test the cost_basis property for a short position."""
        # For shorts, cost basis is negative (money received minus transaction cost)
        expected_cost_basis = (
            short_open_transaction.price * short_open_transaction.quantity
            + short_open_transaction.transaction_cost
        )
        assert short_open_position.cost_basis == expected_cost_basis
        assert short_open_position.cost_basis == -14990.0  # 150 * (-100) + 10

    def test_short_is_closed_property(self, short_open_position, short_closed_position):
        """Test the is_closed property for short positions."""
        assert not short_open_position.is_closed
        assert short_closed_position.is_closed

    def test_short_sale_proceeds(
        self, short_open_position, short_closed_position, short_close_transaction
    ):
        """Test the sale_proceeds property for a short position."""
        assert short_open_position.sale_proceeds == 0.0

        # For shorts, the implementation calculates sale proceeds as:
        # close_transaction.price * -close_transaction.quantity - close_transaction.transaction_cost
        expected_proceeds = (
            short_close_transaction.price * -short_close_transaction.quantity
            - short_close_transaction.transaction_cost
        )
        assert short_closed_position.sale_proceeds == expected_proceeds
        assert (
            short_closed_position.sale_proceeds == -13010.0
        )  # 130 * (-100) - 10 = -13010

    def test_short_realized_profit_loss(
        self, short_open_position, short_closed_position
    ):
        """Test the realized_profit_loss method for a short position."""
        assert short_open_position.realized_profit_loss() == 0.0

        # For short positions: sale_proceeds - cost_basis = -13010 - (-14990) = 1980
        assert short_closed_position.realized_profit_loss() == 1980.0

    def test_short_unrealized_profit_loss(
        self, short_open_position, short_closed_position
    ):
        """Test the unrealized_profit_loss method for a short position."""
        current_price = 140.0  # Lower than open price - profitable short

        # For open short position: unrealized P/L is positive when price goes down
        expected_unrealized_pl = (
            current_price - short_open_position.open_transaction.price
        ) * short_open_position.open_transaction.quantity
        assert (
            short_open_position.unrealized_profit_loss(current_price)
            == expected_unrealized_pl
        )
        assert (
            short_open_position.unrealized_profit_loss(current_price) == 1000.0
        )  # (140 - 150) * (-100)

        # Higher price - unprofitable short
        current_price = 160.0
        expected_unrealized_pl = (
            current_price - short_open_position.open_transaction.price
        ) * short_open_position.open_transaction.quantity
        assert (
            short_open_position.unrealized_profit_loss(current_price)
            == expected_unrealized_pl
        )
        assert (
            short_open_position.unrealized_profit_loss(current_price) == -1000.0
        )  # (160 - 150) * (-100)

        # For closed position
        assert short_closed_position.unrealized_profit_loss(current_price) == 0.0

    def test_short_close_method(self, short_open_position, tradeable_item):
        """Test the close method for a short position."""
        close_transaction = Transaction(
            tradeable_item=tradeable_item,
            quantity=100,  # Positive quantity to close short
            price=120.0,  # Lower price for more profit
            date=date(2023, 1, 15),
            transaction_cost=15.0,
        )

        closed_position = short_open_position.close(close_transaction)

        assert closed_position.is_closed
        assert closed_position.open_transaction == short_open_position.open_transaction
        assert closed_position.close_transaction == close_transaction
        # Expected: sale_proceeds - cost_basis = (-12015) - (-14990) = 2975
        assert closed_position.realized_profit_loss() == 2975.0

    def test_short_close_with_already_closed_position(
        self, short_closed_position, tradeable_item
    ):
        """Test that trying to close an already closed short position raises an error."""
        another_close_transaction = Transaction(
            tradeable_item=tradeable_item,
            quantity=100,
            price=110.0,
            date=date(2023, 1, 20),
            transaction_cost=15.0,
        )

        with pytest.raises(ValueError, match="Position is already closed."):
            short_closed_position.close(another_close_transaction)

    def test_short_close_with_wrong_quantity(self, short_open_position, tradeable_item):
        """Test that trying to close a short with the wrong quantity raises an error."""
        close_transaction = Transaction(
            tradeable_item=tradeable_item,
            quantity=50,  # Not matching the open quantity magnitude
            price=120.0,
            date=date(2023, 1, 15),
            transaction_cost=15.0,
        )

        with pytest.raises(
            ValueError,
            match="Close transaction quantity must be the -ve open transaction quantity.",
        ):
            short_open_position.close(close_transaction)

    def test_short_string_representation(
        self, short_open_position, short_closed_position
    ):
        """Test the string representation of a short PortfolioPosition."""
        assert "PortfolioPosition:" in str(short_open_position)
        assert "Closed: False" in str(short_open_position)
        assert "Realized P/L: 0.0" in str(short_open_position)

        assert "PortfolioPosition:" in str(short_closed_position)
        assert "Closed: True" in str(short_closed_position)
        assert "Realized P/L: 1980.0" in str(short_closed_position)
