import pytest
from datetime import date
from quantforge.qtypes.transaction import Transaction
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.assetclass import AssetClass


@pytest.mark.unit
class TestTransaction:
    """Tests for the Transaction class."""

    @pytest.fixture
    def tradeable_item(self):
        """Return a tradeable item for testing."""
        return TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def valid_transaction(self, tradeable_item):
        """Return a valid transaction for testing."""
        return Transaction(
            tradeable_item=tradeable_item,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 1),
            transaction_cost=7.99,
        )

    def test_initialization(self, tradeable_item):
        """Test that a Transaction can be properly initialized."""
        transaction = Transaction(
            tradeable_item=tradeable_item,
            quantity=100,
            price=142.50,
            date=date(2023, 1, 1),
            transaction_cost=9.99,
        )

        assert transaction.tradeable_item == tradeable_item
        assert transaction.quantity == 100
        assert transaction.price == 142.50
        assert transaction.date == date(2023, 1, 1)
        assert transaction.transaction_cost == 9.99

    def test_default_transaction_cost(self, tradeable_item):
        """Test that transaction_cost defaults to 0.0 when not provided."""
        transaction = Transaction(
            tradeable_item=tradeable_item,
            quantity=50,
            price=200.0,
            date=date(2023, 1, 1),
        )

        assert transaction.transaction_cost == 0.0

    def test_string_representation(self, valid_transaction):
        """Test the string representation of a Transaction."""
        expected_str = "Transaction: TradeableItem: AAPL, Asset Class: equity, Quantity: 10, Price: 150.0, Date: 2023-01-01"

        assert str(valid_transaction) == expected_str
        assert "Transaction(tradeable_item=" in repr(valid_transaction)
        assert "quantity=10" in repr(valid_transaction)
        assert "price=150.0" in repr(valid_transaction)
        assert "date=2023-01-01" in repr(valid_transaction)
        assert "transaction_cost=7.99" in repr(valid_transaction)

    def test_immutability(self, valid_transaction):
        """Test that Transaction is immutable."""
        with pytest.raises(AttributeError):
            valid_transaction.quantity = 20

        with pytest.raises(AttributeError):
            valid_transaction.price = 160.0

        with pytest.raises(AttributeError):
            valid_transaction.date = date(2023, 1, 2)

        with pytest.raises(AttributeError):
            valid_transaction.transaction_cost = 8.99

    def test_validation_zero_quantity(self, tradeable_item):
        """Test that a zero quantity raises a ValueError."""
        with pytest.raises(ValueError, match="Transaction quantity cannot be zero"):
            Transaction(
                tradeable_item=tradeable_item,
                quantity=0,
                price=150.0,
                date=date(2023, 1, 1),
            )

    def test_validation_negative_price(self, tradeable_item):
        """Test that a negative or zero price raises a ValueError."""
        with pytest.raises(ValueError, match="Transaction price must be positive"):
            Transaction(
                tradeable_item=tradeable_item,
                quantity=10,
                price=0,
                date=date(2023, 1, 1),
            )

        with pytest.raises(ValueError, match="Transaction price must be positive"):
            Transaction(
                tradeable_item=tradeable_item,
                quantity=10,
                price=-50.0,
                date=date(2023, 1, 1),
            )

    def test_validation_invalid_date(self, tradeable_item):
        """Test that an invalid date type raises a ValueError."""
        with pytest.raises(ValueError, match="Transaction date must be a date object"):
            Transaction(
                tradeable_item=tradeable_item,
                quantity=10,
                price=150.0,
                date="2023-01-01",
            )

    def test_validation_invalid_tradeable_item(self):
        """Test that an invalid tradeable item raises a ValueError."""
        with pytest.raises(
            ValueError,
            match="Transaction tradeable item must be an instance of TradeableItem",
        ):
            Transaction(
                tradeable_item="AAPL", quantity=10, price=150.0, date=date(2023, 1, 1)
            )

    def test_validation_invalid_transaction_cost(self, tradeable_item):
        """Test that an invalid transaction cost raises a ValueError."""
        with pytest.raises(ValueError, match="Transaction cost must be a number"):
            Transaction(
                tradeable_item=tradeable_item,
                quantity=10,
                price=150.0,
                date=date(2023, 1, 1),
                transaction_cost="9.99",
            )

        with pytest.raises(ValueError, match="Transaction cost cannot be negative"):
            Transaction(
                tradeable_item=tradeable_item,
                quantity=10,
                price=150.0,
                date=date(2023, 1, 1),
                transaction_cost=-5.0,
            )

    def test_equality(self, tradeable_item):
        """Test equality comparison between Transaction instances."""
        transaction1 = Transaction(
            tradeable_item=tradeable_item,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 1),
            transaction_cost=7.99,
        )

        transaction2 = Transaction(
            tradeable_item=tradeable_item,
            quantity=10,
            price=150.0,
            date=date(2023, 1, 1),
            transaction_cost=7.99,
        )

        transaction3 = Transaction(
            tradeable_item=tradeable_item,
            quantity=20,
            price=150.0,
            date=date(2023, 1, 1),
            transaction_cost=7.99,
        )

        assert transaction1 == transaction2
        assert transaction1 != transaction3
