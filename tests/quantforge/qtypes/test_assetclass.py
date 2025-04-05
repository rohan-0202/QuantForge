from quantforge.qtypes.assetclass import AssetClass


def test_assetclass_enum_values():
    """Test that AssetClass enum has the expected values."""
    assert len(AssetClass) == 6
    assert AssetClass.EQUITY is not None
    assert AssetClass.BOND is not None
    assert AssetClass.COMMODITY is not None
    assert AssetClass.CURRENCY is not None
    assert AssetClass.DERIVATIVE is not None
    assert AssetClass.CRYPTOCURRENCY is not None


def test_assetclass_str_representation():
    """Test the string representation of AssetClass enum."""
    assert str(AssetClass.EQUITY) == "equity"
    assert str(AssetClass.BOND) == "bond"
    assert str(AssetClass.COMMODITY) == "commodity"
    assert str(AssetClass.CURRENCY) == "currency"
    assert str(AssetClass.DERIVATIVE) == "derivative"
    assert str(AssetClass.CRYPTOCURRENCY) == "cryptocurrency"


def test_assetclass_repr_representation():
    """Test the repr representation of AssetClass enum."""
    assert repr(AssetClass.EQUITY) == "AssetClass.EQUITY"
    assert repr(AssetClass.BOND) == "AssetClass.BOND"
    assert repr(AssetClass.COMMODITY) == "AssetClass.COMMODITY"
    assert repr(AssetClass.CURRENCY) == "AssetClass.CURRENCY"
    assert repr(AssetClass.DERIVATIVE) == "AssetClass.DERIVATIVE"
    assert repr(AssetClass.CRYPTOCURRENCY) == "AssetClass.CRYPTOCURRENCY"


def test_assetclass_uniqueness():
    """Test that all AssetClass enum values are unique."""
    asset_classes = list(AssetClass)
    assert len(asset_classes) == len(set(asset_classes))


def test_assetclass_comparison():
    """Test that AssetClass enum values can be compared correctly."""
    assert AssetClass.EQUITY == AssetClass.EQUITY
    assert AssetClass.EQUITY != AssetClass.BOND
    assert AssetClass.EQUITY is AssetClass.EQUITY
