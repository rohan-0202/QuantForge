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

    @classmethod
    def from_dict(cls, data: dict) -> "TradeableItem":
        """
        Create a TradeableItem instance from a dictionary.

        Args:
        data (dict): A dictionary containing the TradeableItem's attributes.

        Returns:
        TradeableItem: A new TradeableItem instance.

        Raises:
        ValueError: If the dictionary is missing required fields or contains invalid values.
        """
        if "id" not in data:
            raise ValueError("Dictionary must contain 'id' field")
        if "asset_class" not in data:
            raise ValueError("Dictionary must contain 'asset_class' field")

        # Handle the case where asset_class is a string instead of an AssetClass enum
        asset_class = data["asset_class"]
        if isinstance(asset_class, str):
            try:
                asset_class = AssetClass[asset_class.upper()]
            except KeyError as err:
                raise ValueError(f"Invalid asset class: {asset_class}") from err

        return cls(id=data["id"], asset_class=asset_class)
