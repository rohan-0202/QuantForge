from dataclasses import dataclass, replace

from quantforge.qtypes.transaction import Transaction


@dataclass(frozen=True)
class PortfolioPosition:
    """
    Class representing a position in a portfolio.
    """

    open_transaction: Transaction
    close_transaction: Transaction = None

    @property
    def cost_basis(self) -> float:
        return (
            self.open_transaction.price * self.open_transaction.quantity
            + self.open_transaction.transaction_cost
        )

    @property
    def is_closed(self) -> bool:
        return self.close_transaction is not None

    @property
    def sale_proceeds(self) -> float:
        """
        Calculate the cash proceeds from the sale of the position.
        """
        if not self.is_closed:
            return 0.0
        return (
            self.close_transaction.price * -self.close_transaction.quantity
            - self.close_transaction.transaction_cost
        )

    def realized_profit_loss(self) -> float:
        """
        Calculate the realized profit or loss from the position.
        """
        if not self.is_closed:
            return 0.0
        return self.sale_proceeds - self.cost_basis

    def unrealized_profit_loss(self, price: float) -> float:
        """
        Calculate the unrealized profit or loss from the position.
        """
        if self.is_closed:
            return 0.0
        return (price - self.open_transaction.price) * self.open_transaction.quantity

    def close(self, close_transaction: Transaction) -> "PortfolioPosition":
        """
        Close the position with a close transaction and return a new frozen instance.
        """
        if self.is_closed:
            raise ValueError("Position is already closed.")
        if close_transaction.tradeable_item != self.open_transaction.tradeable_item:
            raise ValueError("Close transaction must match open transaction.")
        if close_transaction.date < self.open_transaction.date:
            raise ValueError(
                "Close transaction date must be after open transaction date."
            )
        if close_transaction.quantity != -self.open_transaction.quantity:
            raise ValueError(
                "Close transaction quantity must be the -ve open transaction quantity."
            )
        return replace(self, close_transaction=close_transaction)

    def __str__(self) -> str:
        return f"PortfolioPosition: {self.open_transaction}, Closed: {self.is_closed}, Realized P/L: {self.realized_profit_loss()}, Unrealized P/L: {self.unrealized_profit_loss(0.0)}"

    def __repr__(self) -> str:
        return f"PortfolioPosition(open_transaction={self.open_transaction}, close_transaction={self.close_transaction})"
