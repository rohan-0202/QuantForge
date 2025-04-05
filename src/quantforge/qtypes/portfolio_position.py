from dataclasses import dataclass, replace

from quantforge.qtypes.transaction import Transaction


@dataclass(frozen=True)
class PortfolioPosition:
    """
    Class representing a position in a portfolio.
    A position tracks an open transaction (buy) and optionally a close transaction (sell).
    """

    open_transaction: Transaction  # Buy transaction that opens the position
    close_transaction: Transaction = (
        None  # Optional sell transaction that closes the position
    )

    @property
    def cost_basis(self) -> float:
        """
        Calculate the total cost basis of the position.
        Formula: (open_price * quantity) + transaction_cost
        This represents the total capital invested to open the position, including fees.
        """
        return (
            self.open_transaction.price * self.open_transaction.quantity
            + self.open_transaction.transaction_cost
        )

    @property
    def is_closed(self) -> bool:
        """
        Check if the position has been closed by a sell transaction.
        """
        return self.close_transaction is not None

    @property
    def sale_proceeds(self) -> float:
        """
        Calculate the cash proceeds from the sale of the position.
        Formula: (close_price * -quantity) - transaction_cost

        Notes:
        - Returns 0 if position is not closed
        - Quantity is negated because close_transaction quantity is negative (sell)
        - Transaction costs reduce the proceeds
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
        Formula: sale_proceeds - cost_basis

        This represents the actual profit/loss after the position is closed:
        - Positive value means profit
        - Negative value means loss
        - Returns 0 if position is not closed
        """
        if not self.is_closed:
            return 0.0
        return self.sale_proceeds - self.cost_basis

    def unrealized_profit_loss(self, price: float) -> float:
        """
        Calculate the unrealized profit or loss from the position at a given current price.
        Formula: (current_price - open_price) * quantity

        Notes:
        - Returns 0 if position is closed (since P/L is then realized)
        - This is the mark-to-market value that reflects current value but hasn't been realized
        - Does not include transaction costs which will be applied when actually closed
        """
        if self.is_closed:
            return 0.0
        return (price - self.open_transaction.price) * self.open_transaction.quantity

    def position_value(self, price: float) -> float:
        """
        Calculate the current market value of the position at a given price.
        Formula: current_price * quantity

        Notes:
        - Returns 0 if position is closed
        - This represents the total current market value of the position
        """
        if self.is_closed:
            return 0.0
        return price * self.open_transaction.quantity

    def close(self, close_transaction: Transaction) -> "PortfolioPosition":
        """
        Close the position with a close transaction and return a new frozen instance.

        Enforces several validation rules:
        1. Position must not already be closed
        2. Close transaction must be for the same tradeable item
        3. Close date must be after open date
        4. Close quantity must exactly offset the open quantity (negative of open)

        Returns a new immutable position object with the close_transaction set.
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
        """
        String representation showing key information about the position.
        Includes open transaction details, closed status, and P/L calculations.
        """
        return f"PortfolioPosition: {self.open_transaction}, Closed: {self.is_closed}, Realized P/L: {self.realized_profit_loss()}, Unrealized P/L: {self.unrealized_profit_loss(0.0)}"

    def __repr__(self) -> str:
        """
        Detailed representation showing the internal state of the position object.
        """
        return f"PortfolioPosition(open_transaction={self.open_transaction}, close_transaction={self.close_transaction})"
