import pytest
from quantforge.strategies.data_requirement import DataRequirement


@pytest.mark.unit
class TestDataRequirement:
    """Test cases for the DataRequirement enumeration."""

    def test_enum_members_exist(self):
        """Verify that the enum has the expected members."""
        assert hasattr(DataRequirement, "TICKER")
        assert hasattr(DataRequirement, "NEWS")
        assert hasattr(DataRequirement, "OPTIONS")
        assert hasattr(DataRequirement, "FUNDAMENTALS")

    def test_enum_uniqueness(self):
        """Verify that all enum values are unique."""
        values = [
            DataRequirement.TICKER,
            DataRequirement.NEWS,
            DataRequirement.OPTIONS,
            DataRequirement.FUNDAMENTALS,
        ]
        assert len(values) == len(set(values))

    def test_enum_auto_values(self):
        """Verify that auto() assigns unique integer values (basic check)."""
        assert isinstance(DataRequirement.TICKER.value, int)
        assert isinstance(DataRequirement.NEWS.value, int)
        assert DataRequirement.TICKER.value != DataRequirement.NEWS.value 