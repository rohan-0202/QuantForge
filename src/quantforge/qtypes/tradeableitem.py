from dataclasses import dataclass

from quantforge.qtypes.assetclass import AssetClass


@dataclass(frozen=True)
class TradeableItem:
    """
    Abstract base class representing a tradeable item in a portfolio.

    This class serves as a blueprint for all tradeable items, such as equities, bonds, or other asset types.
    It enforces the implementation of common properties and methods that all tradeable items must have.
    """

    id: str
    asset_class: AssetClass

    def __str__(self) -> str:
        """
        Return a human-readable string representation of the tradeable item.

        Returns:
        str: A string describing the tradeable item, including its ID and asset class.
        """
        return f"TradeableItem: {self.id}, Asset Class: {self.asset_class}"

    def __repr__(self) -> str:
        """
        Return a detailed string representation of the tradeable item for debugging.

        Returns:
        str: A string representation of the tradeable item, including its ID and asset class.
        """
        return f"TradeableItem(id={self.id}, asset_class={self.asset_class})"
