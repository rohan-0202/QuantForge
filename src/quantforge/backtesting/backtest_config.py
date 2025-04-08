from dataclasses import dataclass
from typing import Optional
from datetime import date, datetime

from quantforge.qtypes.portfolio import Portfolio


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for backtesting."""

    initial_portfolio: Portfolio
    strategy_name: str
    end_date: Optional[date] = None

    def __post_init__(self):
        """
        Validates the backtest configuration after initialization.

        Ensures:
        - Start date is provided
        - Initial portfolio is provided
        - Strategy name is provided
        - End date is not before start date
        """
        assert self.initial_portfolio is not None, "Initial portfolio must be provided"
        assert self.strategy_name is not None, "Strategy name must be provided"

        if self.end_date is not None:
            assert (
                self.end_date >= self.initial_portfolio.start_date
            ), "End date must be greater than or equal to start date"

        # finally the portfolio must not have any closed positions
        assert (
            len(self.initial_portfolio.closed_positions) == 0
        ), "Portfolio must not have any closed positions"

    @classmethod
    def from_dict(cls, data: dict) -> "BacktestConfig":
        """
        Create a BacktestConfig instance from a dictionary.

        Args:
            data (dict): A dictionary containing the BacktestConfig's attributes.

        Returns:
            BacktestConfig: A new BacktestConfig instance.

        Raises:
            ValueError: If the dictionary is missing required fields or contains invalid values.
        """
        # Convert date strings to date objects if needed

        end_date = data.get("end_date")
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Use Portfolio's from_dict method
        initial_portfolio = Portfolio.from_dict(data["initial_portfolio"])

        return cls(
            initial_portfolio=initial_portfolio,
            strategy_name=data["strategy_name"],
            end_date=end_date,
        )
