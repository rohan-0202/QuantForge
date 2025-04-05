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
