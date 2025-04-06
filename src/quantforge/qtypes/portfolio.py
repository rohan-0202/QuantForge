from datetime import date
from logging import getLogger

from quantforge.qtypes.portfolio_position import PortfolioPosition
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.transaction import Transaction

logger = getLogger(__name__)


class Portfolio:
    """
    Class representing a portfolio of tradeable items.
    """

    def __init__(
        self,
        initial_cash: float,
        allowed_tradeable_items: list[TradeableItem],
        start_date: date,
        allow_margin: bool = False,
        allow_short: bool = False,
    ):
        # Initialize the portfolio with initial cash and allowed tradeable items.
        if initial_cash <= 0:
            raise ValueError("Initial cash cannot be negative.")
        self._cash = initial_cash
        self._start_date = start_date
        self._allow_margin = allow_margin
        self._allow_short = allow_short

        # Check if the allowed tradeable items are valid.
        if not allowed_tradeable_items:
            raise ValueError("Allowed tradeable items cannot be empty.")
        if not all(isinstance(item, TradeableItem) for item in allowed_tradeable_items):
            raise ValueError(
                "All allowed tradeable items must be instances of TradeableItem."
            )

        self._allowed_tradeable_items = allowed_tradeable_items
        self._closed_positions: list[PortfolioPosition] = []
        self._open_positions_by_tradeable_item: dict[
            TradeableItem, list[PortfolioPosition]
        ] = {}

        logger.info(
            f"Portfolio initialized with cash: {initial_cash}, start_date: {start_date}, "
            f"allow_margin: {allow_margin}, allow_short: {allow_short}"
        )

    def portfolio_value(self, prices: dict[TradeableItem, float]) -> float:
        """
        Calculate the total value of the portfolio, including cash and unrealized positions.
        """
        total_value = self._cash
        for positions in self._open_positions_by_tradeable_item.values():
            for position in positions:
                if position.open_transaction.tradeable_item not in prices:
                    raise ValueError("Price not found for tradeable item.")
                total_value += position.position_value(
                    prices[position.open_transaction.tradeable_item]
                )
        return total_value

    @property
    def allow_margin(self) -> bool:
        return self._allow_margin

    @property
    def allow_short(self) -> bool:
        return self._allow_short

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def allowed_tradeable_items(self) -> list[TradeableItem]:
        return self._allowed_tradeable_items

    def has_position(self, tradeable_item: TradeableItem) -> bool:
        """
        Check if the portfolio has an open position for the given tradeable item.
        """
        return (
            tradeable_item in self._open_positions_by_tradeable_item
            and len(self._open_positions_by_tradeable_item[tradeable_item]) > 0
        )

    @property
    def realized_profit_loss(self) -> float:
        """
        Calculate the realized profit or loss from all closed positions.
        """
        return sum(
            position.realized_profit_loss() for position in self._closed_positions
        )

    def can_trade(self, transaction: Transaction) -> bool:
        """
        Check if the transaction can be executed based on the allowed tradeable items.
        """

        if transaction.tradeable_item not in self.allowed_tradeable_items:
            return False

        # if this is a close of an existing position, then we can always trade.
        # to check we need to check if we have the exact oppostite position of this transaction
        # which means the quantity of the transaction should be negative of the quantity of the position
        # in the dictionary of open positions
        if transaction.tradeable_item in self._open_positions_by_tradeable_item:
            positions = self._open_positions_by_tradeable_item[
                transaction.tradeable_item
            ]
            for position in positions:
                if position.open_transaction.quantity == -transaction.quantity:
                    return True

        # if this is a short sale, then we need to check if we are allowed to short
        # if we are not allowed to short, then we cannot short
        if transaction.quantity < 0:
            return self._allow_short
        else:
            # if this is a purchase, then we need to check if we have enough cash
            if self._cash < (
                transaction.price * transaction.quantity + transaction.transaction_cost
            ):
                return self._allow_margin

        return True

    def get_open_positions_by_item(self, tradeable_item: TradeableItem) -> list[PortfolioPosition]:
        """
        Get the list of open positions for a specific tradeable item.
        """
        return self._open_positions_by_tradeable_item.get(tradeable_item, [])

    def close_position(
        self, position: PortfolioPosition, close_transaction: Transaction
    ) -> PortfolioPosition:
        """
        Close a position in the portfolio.
        """
        logger.info(
            f"Attempting to close position: {position} with transaction: {close_transaction}"
        )

        if position.is_closed:
            logger.error("Position is already closed.")
            raise ValueError("Position is already closed.")

        if close_transaction.tradeable_item != position.open_transaction.tradeable_item:
            logger.error("Close transaction must match open transaction.")
            raise ValueError("Close transaction must match open transaction.")

        if close_transaction.date <= position.open_transaction.date:
            logger.error("Close transaction date must be after open transaction date.")
            raise ValueError(
                "Close transaction date must be after open transaction date."
            )

        if close_transaction.quantity != -position.open_transaction.quantity:
            logger.error(
                "Close transaction quantity must be the -ve open transaction quantity."
            )
            raise ValueError(
                "Close transaction quantity must be the -ve open transaction quantity."
            )

        if (
            position
            not in self._open_positions_by_tradeable_item[
                position.open_transaction.tradeable_item
            ]
        ):
            logger.error("Position not found in open positions.")
            raise ValueError("Position not found in open positions.")

        # Remove the position from the open positions
        self._open_positions_by_tradeable_item[
            position.open_transaction.tradeable_item
        ].remove(position)

        # If the list becomes empty, remove the tradeable item from the dictionary
        if not self._open_positions_by_tradeable_item[
            position.open_transaction.tradeable_item
        ]:
            del self._open_positions_by_tradeable_item[
                position.open_transaction.tradeable_item
            ]

        # Create a transaction with this position
        t: Transaction = Transaction(
            tradeable_item=position.open_transaction.tradeable_item,
            quantity=-position.open_transaction.quantity,
            price=close_transaction.price,
            date=close_transaction.date,
            transaction_cost=close_transaction.transaction_cost,
        )

        # Add the position to the closed positions
        closed_position = position.close(t)
        self._closed_positions.append(closed_position)

        # Update the cash in the portfolio
        self._cash += closed_position.sale_proceeds

        logger.info(
            f"{closed_position}: Position closed successfully. Sale proceeds: {closed_position.sale_proceeds}, "
            f"Updated cash: {self._cash}"
        )

        return closed_position

    def open_position(self, transaction: Transaction) -> PortfolioPosition:
        """
        Open a position in the portfolio.
        """
        logger.info(f"Attempting to open position with transaction: {transaction}")

        if not self.can_trade(transaction):
            logger.error(f"Transaction {transaction} cannot be executed.")
            raise ValueError(f"Transaction {transaction} cannot be executed.")

        # Create a new position with this transaction
        position = PortfolioPosition(transaction)

        # Initialize the list for this tradeable item if it doesn't exist
        if transaction.tradeable_item not in self._open_positions_by_tradeable_item:
            self._open_positions_by_tradeable_item[transaction.tradeable_item] = []

        # Add the position to the open positions
        self._open_positions_by_tradeable_item[transaction.tradeable_item].append(
            position
        )

        # Update the cash in the portfolio
        cost_basis = (
            transaction.price * transaction.quantity + transaction.transaction_cost
        )
        self._cash -= cost_basis

        logger.info(
            f"{position} Position opened successfully. Transaction cost basis: {cost_basis}, "
            f"Updated cash: {self._cash}"
        )

        return position
