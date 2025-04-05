import pytest
from quantforge.qtypes.tradeableitem import TradeableItem
from quantforge.qtypes.assetclass import AssetClass


class TestTradeableItem:
    """Tests for the TradeableItem class."""

    def test_initialization(self):
        """Test that a TradeableItem can be properly initialized."""
        item = TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)
        assert item.id == "AAPL"
        assert item.asset_class == AssetClass.EQUITY

    def test_string_representation(self):
        """Test the string representation of a TradeableItem."""
        item = TradeableItem(id="BTCUSD", asset_class=AssetClass.CRYPTOCURRENCY)
        expected_str = "TradeableItem: BTCUSD, Asset Class: cryptocurrency"
        expected_repr = "TradeableItem(id=BTCUSD, asset_class=cryptocurrency)"

        assert str(item) == expected_str
        assert repr(item) == expected_repr

    def test_immutability(self):
        """Test that TradeableItem is immutable."""
        item = TradeableItem(id="MSFT", asset_class=AssetClass.EQUITY)

        with pytest.raises(AttributeError):
            item.id = "GOOG"

        with pytest.raises(AttributeError):
            item.asset_class = AssetClass.BOND

    def test_equality(self):
        """Test equality comparison between TradeableItem instances."""
        item1 = TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)
        item2 = TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)
        item3 = TradeableItem(id="MSFT", asset_class=AssetClass.EQUITY)
        item4 = TradeableItem(id="AAPL", asset_class=AssetClass.BOND)

        assert item1 == item2
        assert item1 != item3
        assert item1 != item4

    def test_with_different_asset_classes(self):
        """Test TradeableItem with different asset classes."""
        for asset_class in AssetClass:
            item = TradeableItem(id=f"TEST_{asset_class.name}", asset_class=asset_class)
            assert item.asset_class == asset_class
            assert asset_class.name in repr(item)
