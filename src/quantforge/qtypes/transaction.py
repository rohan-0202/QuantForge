from dataclasses import dataclass, field
from datetime import date

from quantforge.qtypes.tradeable_item import TradeableItem


@dataclass(frozen=True)
class Transaction:
    """
    Class representing a transaction in a portfolio.
    """

    tradeable_item: TradeableItem
    quantity: float
    price: float
    date: date
    transaction_cost: float = field(default=0.0)

    def __post_init__(self):
        """
        Perform validations after initialization.
        """
        if self.quantity == 0:
            raise ValueError("Transaction quantity cannot be zero.")
        if self.price <= 0:
            raise ValueError("Transaction price must be positive.")
        if not isinstance(self.date, date):
            raise ValueError("Transaction date must be a date object.")
        if not isinstance(self.tradeable_item, TradeableItem):
            raise ValueError(
                "Transaction tradeable item must be an instance of TradeableItem."
            )
        if not isinstance(self.transaction_cost, (int, float)):
            raise ValueError("Transaction cost must be a number.")
        if self.transaction_cost < 0:
            raise ValueError("Transaction cost cannot be negative.")

    def __str__(self) -> str:
        return f"Transaction: {self.tradeable_item}, Quantity: {self.quantity}, Price: {self.price}, Date: {self.date}"

    def __repr__(self) -> str:
        return (
            f"Transaction(tradeable_item={self.tradeable_item}, quantity={self.quantity}, "
            f"price={self.price}, date={self.date}, transaction_cost={self.transaction_cost})"
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        """
        Create a Transaction instance from a dictionary.

        Args:
        data (dict): A dictionary containing the Transaction's attributes.

        Returns:
        Transaction: A new Transaction instance.

        Raises:
        ValueError: If the dictionary is missing required fields or contains invalid values.
        """
        # Check for required fields
        required_fields = ["tradeable_item", "quantity", "price", "date"]
        for required_field in required_fields:
            if required_field not in data:
                raise ValueError(f"Dictionary must contain '{required_field}' field")

        # Handle tradeable_item if it's a dictionary
        tradeable_item = data["tradeable_item"]
        if isinstance(tradeable_item, dict):
            tradeable_item = TradeableItem.from_dict(tradeable_item)

        # Handle date if it's a string
        transaction_date = data["date"]
        if isinstance(transaction_date, str):
            try:
                # Assuming format YYYY-MM-DD
                year, month, day = map(int, transaction_date.split("-"))
                transaction_date = date(year, month, day)
            except (ValueError, AttributeError) as err:
                raise ValueError(
                    f"Invalid date format: {transaction_date}. Expected YYYY-MM-DD"
                ) from err

        # Create the transaction
        return cls(
            tradeable_item=tradeable_item,
            quantity=data["quantity"],
            price=data["price"],
            date=transaction_date,
            transaction_cost=data.get("transaction_cost", 0.0),
        )
