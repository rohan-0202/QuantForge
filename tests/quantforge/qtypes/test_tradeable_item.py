import pytest
from dataclasses import asdict
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.assetclass import AssetClass


@pytest.mark.unit
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

    @pytest.mark.parametrize("asset_class", list(AssetClass))
    def test_with_different_asset_classes(self, asset_class):
        """Test TradeableItem with different asset classes."""
        item = TradeableItem(id=f"TEST_{asset_class.name}", asset_class=asset_class)
        assert item.asset_class == asset_class
        assert asset_class.name in repr(item)

    def test_to_dict(self):
        """Test converting TradeableItem to dictionary using asdict."""
        item = TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)
        result = asdict(item)

        assert isinstance(result, dict)
        assert result["id"] == "AAPL"
        assert result["asset_class"] == AssetClass.EQUITY

    def test_to_dict_with_different_asset_classes(self):
        """Test converting TradeableItem to dictionary with different asset classes."""
        # Test with a few different asset classes
        for asset_class in [
            AssetClass.EQUITY,
            AssetClass.BOND,
            AssetClass.CRYPTOCURRENCY,
        ]:
            item = TradeableItem(id=f"TEST_{asset_class.name}", asset_class=asset_class)
            result = asdict(item)

            assert result["id"] == f"TEST_{asset_class.name}"
            assert result["asset_class"] == asset_class

    def test_round_trip_conversion(self):
        """Test round-trip conversion from TradeableItem to dict and back."""
        original_item = TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)
        item_dict = asdict(original_item)
        reconstructed_item = TradeableItem.from_dict(item_dict)

        assert original_item == reconstructed_item
        assert original_item.id == reconstructed_item.id
        assert original_item.asset_class == reconstructed_item.asset_class

    def test_round_trip_conversion_with_different_asset_classes(self):
        """Test round-trip conversion with different asset classes."""
        # Test with a few different asset classes
        for asset_class in [
            AssetClass.EQUITY,
            AssetClass.BOND,
            AssetClass.CRYPTOCURRENCY,
        ]:
            original = TradeableItem(
                id=f"TEST_{asset_class.name}", asset_class=asset_class
            )
            item_dict = asdict(original)
            reconstructed = TradeableItem.from_dict(item_dict)

            assert original == reconstructed
            assert original.id == reconstructed.id
            assert original.asset_class == reconstructed.asset_class

    def test_from_dict(self):
        """Test the from_dict class method of TradeableItem."""
        data = {"id": "AAPL", "asset_class": AssetClass.EQUITY}
        item = TradeableItem.from_dict(data)

        assert item.id == "AAPL"
        assert item.asset_class == AssetClass.EQUITY

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "with_string_asset_class",
                "data": {"id": "AAPL", "asset_class": "EQUITY"},
                "expected_id": "AAPL",
                "expected_asset_class": AssetClass.EQUITY,
            },
            {
                "name": "with_lowercase_string_asset_class",
                "data": {"id": "AAPL", "asset_class": "equity"},
                "expected_id": "AAPL",
                "expected_asset_class": AssetClass.EQUITY,
            },
        ],
    )
    def test_from_dict_with_string_asset_class(self, test_case):
        """Test from_dict with string asset class."""
        item = TradeableItem.from_dict(test_case["data"])

        assert item.id == test_case["expected_id"]
        assert item.asset_class == test_case["expected_asset_class"]

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "missing_id",
                "data": {"asset_class": AssetClass.EQUITY},
                "error": ValueError,
                "match": "Dictionary must contain 'id' field",
            },
            {
                "name": "missing_asset_class",
                "data": {"id": "AAPL"},
                "error": ValueError,
                "match": "Dictionary must contain 'asset_class' field",
            },
            {
                "name": "invalid_asset_class",
                "data": {"id": "AAPL", "asset_class": "INVALID"},
                "error": ValueError,
                "match": "Invalid asset class",
            },
        ],
    )
    def test_from_dict_errors(self, test_case):
        """Test from_dict with invalid inputs."""
        with pytest.raises(test_case["error"], match=test_case["match"]):
            TradeableItem.from_dict(test_case["data"])
