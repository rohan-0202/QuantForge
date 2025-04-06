import pytest
import dataclasses
from datetime import date
from quantforge.qtypes.ohlc import OHLCData


@pytest.mark.unit
class TestOHLCData:
    def test_valid_ohlc_creation(self):
        """Test that a valid OHLCData object can be created."""
        today = date.today()
        ohlc = OHLCData(
            open=100.0, high=105.0, low=98.0, close=103.5, date=today, volume=10000
        )

        assert ohlc.open == 100.0
        assert ohlc.high == 105.0
        assert ohlc.low == 98.0
        assert ohlc.close == 103.5
        assert ohlc.date == today
        assert ohlc.volume == 10000

    def test_ohlc_creation_without_volume(self):
        """Test that an OHLCData object can be created without volume."""
        today = date.today()
        ohlc = OHLCData(open=100.0, high=105.0, low=98.0, close=103.5, date=today)

        assert ohlc.open == 100.0
        assert ohlc.high == 105.0
        assert ohlc.low == 98.0
        assert ohlc.close == 103.5
        assert ohlc.date == today
        assert ohlc.volume is None

    def test_ohlc_immutability(self):
        """Test that OHLCData is immutable (frozen)."""
        today = date.today()
        ohlc = OHLCData(open=100.0, high=105.0, low=98.0, close=103.5, date=today)

        with pytest.raises(dataclasses.FrozenInstanceError):
            ohlc.open = 101.0

    def test_validation_date_not_none(self):
        """Test that OHLCData requires date to be provided."""
        with pytest.raises(AssertionError, match="Date must be provided"):
            OHLCData(open=100.0, high=105.0, low=98.0, close=103.5, date=None)

    def test_validation_open_non_negative(self):
        """Test that OHLCData requires open price to be non-negative."""
        with pytest.raises(AssertionError, match="Open price must be non-negative"):
            OHLCData(open=-1.0, high=105.0, low=98.0, close=103.5, date=date.today())

    def test_zero_price_is_valid(self):
        """Test that zero is a valid price for open."""
        today = date.today()
        ohlc = OHLCData(open=0.0, high=105.0, low=98.0, close=103.5, date=today)
        assert ohlc.open == 0.0

    def test_equality(self):
        """Test equality between OHLCData objects."""
        today = date.today()
        ohlc1 = OHLCData(open=100.0, high=105.0, low=98.0, close=103.5, date=today)
        ohlc2 = OHLCData(open=100.0, high=105.0, low=98.0, close=103.5, date=today)
        ohlc3 = OHLCData(open=101.0, high=105.0, low=98.0, close=103.5, date=today)

        assert ohlc1 == ohlc2
        assert ohlc1 != ohlc3
