import pytest
from datetime import date
from dataclasses import asdict

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

    def test_from_dict_open_position(self, open_position):
        """Test creating a PortfolioPosition from a dictionary with only an open transaction."""
        # Convert to dictionary
        position_dict = asdict(open_position)

        # Convert back to PortfolioPosition
        reconstructed_position = PortfolioPosition.from_dict(position_dict)

        # Verify the reconstructed position matches the original
        assert reconstructed_position.open_transaction == open_position.open_transaction
        assert reconstructed_position.close_transaction is None
        assert reconstructed_position.is_closed == open_position.is_closed
        assert reconstructed_position.cost_basis == open_position.cost_basis

    def test_from_dict_closed_position(self, closed_position):
        """Test creating a PortfolioPosition from a dictionary with both open and close transactions."""
        # Convert to dictionary
        position_dict = asdict(closed_position)

        # Convert back to PortfolioPosition
        reconstructed_position = PortfolioPosition.from_dict(position_dict)

        # Verify the reconstructed position matches the original
        assert (
            reconstructed_position.open_transaction == closed_position.open_transaction
        )
        assert (
            reconstructed_position.close_transaction
            == closed_position.close_transaction
        )
        assert reconstructed_position.is_closed == closed_position.is_closed
        assert reconstructed_position.cost_basis == closed_position.cost_basis
        assert reconstructed_position.sale_proceeds == closed_position.sale_proceeds
        assert (
            reconstructed_position.realized_profit_loss()
            == closed_position.realized_profit_loss()
        )

    def test_from_dict_missing_required_field(self):
        """Test that from_dict raises an error when a required field is missing."""
        with pytest.raises(
            ValueError, match="Dictionary must contain 'open_transaction' field"
        ):
            PortfolioPosition.from_dict({})

    def test_from_dict_with_transaction_dicts(self, tradeable_item):
        """Test creating a PortfolioPosition from a dictionary with transaction dictionaries."""
        # Create a dictionary with transaction dictionaries
        position_dict = {
            "open_transaction": {
                "tradeable_item": {
                    "id": tradeable_item.id,
                    "asset_class": tradeable_item.asset_class,
                },
                "quantity": 100,
                "price": 150.0,
                "date": date(2023, 1, 1),
                "transaction_cost": 10.0,
            },
            "close_transaction": {
                "tradeable_item": {
                    "id": tradeable_item.id,
                    "asset_class": tradeable_item.asset_class,
                },
                "quantity": -100,
                "price": 170.0,
                "date": date(2023, 1, 10),
                "transaction_cost": 10.0,
            },
        }

        # Convert to PortfolioPosition
        position = PortfolioPosition.from_dict(position_dict)

        # Verify the position was created correctly
        assert position.open_transaction.quantity == 100
        assert position.open_transaction.price == 150.0
        assert position.open_transaction.date == date(2023, 1, 1)
        assert position.open_transaction.transaction_cost == 10.0
        assert position.open_transaction.tradeable_item.id == tradeable_item.id

        assert position.close_transaction.quantity == -100
        assert position.close_transaction.price == 170.0
        assert position.close_transaction.date == date(2023, 1, 10)
        assert position.close_transaction.transaction_cost == 10.0
        assert position.close_transaction.tradeable_item.id == tradeable_item.id

        assert position.is_closed
        assert position.realized_profit_loss() == 1980.0  # 16990 - 15010
