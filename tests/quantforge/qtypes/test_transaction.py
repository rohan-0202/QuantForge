import pytest
from datetime import date
from dataclasses import asdict
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

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "zero_quantity",
                "kwargs": {"quantity": 0, "price": 150.0, "date": date(2023, 1, 1)},
                "error": ValueError,
                "match": "Transaction quantity cannot be zero",
            },
            {
                "name": "zero_price",
                "kwargs": {"quantity": 10, "price": 0, "date": date(2023, 1, 1)},
                "error": ValueError,
                "match": "Transaction price must be positive",
            },
            {
                "name": "negative_price",
                "kwargs": {"quantity": 10, "price": -50.0, "date": date(2023, 1, 1)},
                "error": ValueError,
                "match": "Transaction price must be positive",
            },
            {
                "name": "invalid_date",
                "kwargs": {"quantity": 10, "price": 150.0, "date": "2023-01-01"},
                "error": ValueError,
                "match": "Transaction date must be a date object",
            },
            {
                "name": "invalid_tradeable_item",
                "kwargs": {
                    "tradeable_item": "AAPL",
                    "quantity": 10,
                    "price": 150.0,
                    "date": date(2023, 1, 1),
                },
                "error": ValueError,
                "match": "Transaction tradeable item must be an instance of TradeableItem",
            },
            {
                "name": "invalid_transaction_cost_type",
                "kwargs": {
                    "quantity": 10,
                    "price": 150.0,
                    "date": date(2023, 1, 1),
                    "transaction_cost": "9.99",
                },
                "error": ValueError,
                "match": "Transaction cost must be a number",
            },
            {
                "name": "negative_transaction_cost",
                "kwargs": {
                    "quantity": 10,
                    "price": 150.0,
                    "date": date(2023, 1, 1),
                    "transaction_cost": -5.0,
                },
                "error": ValueError,
                "match": "Transaction cost cannot be negative",
            },
        ],
    )
    def test_validation(self, tradeable_item, test_case):
        """Test various validation scenarios for Transaction."""
        kwargs = test_case["kwargs"].copy()

        # Add tradeable_item if not explicitly provided in the test case
        if "tradeable_item" not in kwargs:
            kwargs["tradeable_item"] = tradeable_item

        with pytest.raises(test_case["error"], match=test_case["match"]):
            Transaction(**kwargs)

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

    def test_from_dict(self, tradeable_item):
        """Test the from_dict class method of Transaction."""
        data = {
            "tradeable_item": tradeable_item,
            "quantity": 100,
            "price": 150.0,
            "date": date(2023, 1, 1),
            "transaction_cost": 9.99,
        }

        transaction = Transaction.from_dict(data)

        assert transaction.tradeable_item == tradeable_item
        assert transaction.quantity == 100
        assert transaction.price == 150.0
        assert transaction.date == date(2023, 1, 1)
        assert transaction.transaction_cost == 9.99

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "with_tradeable_item_dict",
                "data": {
                    "tradeable_item": {"id": "AAPL", "asset_class": "EQUITY"},
                    "quantity": 100,
                    "price": 150.0,
                    "date": date(2023, 1, 1),
                    "transaction_cost": 9.99,
                },
                "assertions": lambda t: [
                    (t.tradeable_item.id, "AAPL"),
                    (t.tradeable_item.asset_class, AssetClass.EQUITY),
                    (t.quantity, 100),
                    (t.price, 150.0),
                    (t.date, date(2023, 1, 1)),
                    (t.transaction_cost, 9.99),
                ],
            },
            {
                "name": "with_string_date",
                "data": {
                    "tradeable_item": {"id": "AAPL", "asset_class": "EQUITY"},
                    "quantity": 100,
                    "price": 150.0,
                    "date": "2023-01-01",
                    "transaction_cost": 9.99,
                },
                "assertions": lambda t: [
                    (t.tradeable_item.id, "AAPL"),
                    (t.tradeable_item.asset_class, AssetClass.EQUITY),
                    (t.quantity, 100),
                    (t.price, 150.0),
                    (t.date, date(2023, 1, 1)),
                    (t.transaction_cost, 9.99),
                ],
            },
            {
                "name": "without_transaction_cost",
                "data": {
                    "tradeable_item": {"id": "AAPL", "asset_class": "EQUITY"},
                    "quantity": 100,
                    "price": 150.0,
                    "date": "2023-01-01",
                },
                "assertions": lambda t: [
                    (t.tradeable_item.id, "AAPL"),
                    (t.tradeable_item.asset_class, AssetClass.EQUITY),
                    (t.quantity, 100),
                    (t.price, 150.0),
                    (t.date, date(2023, 1, 1)),
                    (t.transaction_cost, 0.0),
                ],
            },
        ],
    )
    def test_from_dict_variations(self, test_case):
        """Test from_dict with various input formats."""
        transaction = Transaction.from_dict(test_case["data"])

        for actual, expected in test_case["assertions"](transaction):
            assert actual == expected

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "missing_required_field",
                "data": {
                    "tradeable_item": {"id": "AAPL", "asset_class": "EQUITY"},
                    "quantity": 100,
                    "price": 150.0,
                    # Missing date
                },
                "error": ValueError,
                "match": "Dictionary must contain 'date' field",
            },
            {
                "name": "invalid_date_format",
                "data": {
                    "tradeable_item": {"id": "AAPL", "asset_class": "EQUITY"},
                    "quantity": 100,
                    "price": 150.0,
                    "date": "01-01-2023",  # Wrong format
                    "transaction_cost": 9.99,
                },
                "error": ValueError,
                "match": "Invalid date format",
            },
        ],
    )
    def test_from_dict_errors(self, test_case):
        """Test from_dict with invalid inputs."""
        with pytest.raises(test_case["error"], match=test_case["match"]):
            Transaction.from_dict(test_case["data"])

    def test_serialization_deserialization(self, valid_transaction):
        """Test that a transaction can be serialized to a dictionary and then deserialized back to a transaction."""
        # Convert transaction to dictionary
        transaction_dict = asdict(valid_transaction)

        # Convert dictionary back to transaction
        reconstructed_transaction = Transaction.from_dict(transaction_dict)

        # Verify that the reconstructed transaction is equal to the original
        assert reconstructed_transaction == valid_transaction

        # Verify individual fields
        assert (
            reconstructed_transaction.tradeable_item == valid_transaction.tradeable_item
        )
        assert reconstructed_transaction.quantity == valid_transaction.quantity
        assert reconstructed_transaction.price == valid_transaction.price
        assert reconstructed_transaction.date == valid_transaction.date
        assert (
            reconstructed_transaction.transaction_cost
            == valid_transaction.transaction_cost
        )
