from enum import Enum, auto


class AssetClass(Enum):
    """
    Enum representing different asset classes that can be traded and held in a portfolio.
    """

    EQUITY = auto()
    BOND = auto()
    COMMODITY = auto()
    CURRENCY = auto()
    DERIVATIVE = auto()
    CRYPTOCURRENCY = auto()

    def __str__(self):
        return self.name.lower()

    def __repr__(self):
        return f"AssetClass.{self.name}"
