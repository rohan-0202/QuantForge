import pytest
import pandas as pd
from datetime import date, datetime
import pytz

from quantforge.backtesting.trading_dates import extract_trading_dates
from quantforge.strategies.data_requirement import DataRequirement
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.assetclass import AssetClass


@pytest.fixture
def tradeable_item1():
    """Create a tradeable item for testing."""
    return TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY)


@pytest.fixture
def tradeable_item2():
    """Create another tradeable item for testing."""
    return TradeableItem(id="MSFT", asset_class=AssetClass.EQUITY)


@pytest.fixture
def ticker_data_with_dates():
    """Create a DataFrame with ticker data and DatetimeIndex."""
    dates = [
        datetime(2023, 1, 1, tzinfo=pytz.UTC),
        datetime(2023, 1, 2, tzinfo=pytz.UTC),
        datetime(2023, 1, 3, tzinfo=pytz.UTC),
    ]
    df = pd.DataFrame(
        {
            "open": [100, 101, 102],
            "high": [105, 106, 107],
            "low": [95, 96, 97],
            "close": [102, 103, 104],
            "volume": [1000, 2000, 3000],
        },
        index=pd.DatetimeIndex(dates),
    )
    return df


@pytest.fixture
def ticker_data_no_datetime_index():
    """Create a DataFrame with ticker data but without DatetimeIndex."""
    df = pd.DataFrame(
        {
            "timestamp": [
                datetime(2023, 1, 1, tzinfo=pytz.UTC),
                datetime(2023, 1, 2, tzinfo=pytz.UTC),
                datetime(2023, 1, 3, tzinfo=pytz.UTC),
            ],
            "open": [100, 101, 102],
            "high": [105, 106, 107],
            "low": [95, 96, 97],
            "close": [102, 103, 104],
            "volume": [1000, 2000, 3000],
        }
    )
    return df


@pytest.mark.unit
class TestExtractTradingDates:
    """Tests for the extract_trading_dates function."""

    def test_empty_input_data(self):
        """Test with empty input data."""
        input_data = {}
        result = extract_trading_dates(input_data)
        assert result == []

    def test_no_ticker_data(self, tradeable_item1):
        """Test with input data that doesn't contain TICKER requirement."""
        # Create input data with non-TICKER requirement
        input_data = {
            tradeable_item1: {
                DataRequirement.OPTIONS: pd.DataFrame({"data": [1, 2, 3]})
            }
        }
        result = extract_trading_dates(input_data)
        assert result == []

    def test_single_item_ticker_data(self, tradeable_item1, ticker_data_with_dates):
        """Test with a single tradeable item with TICKER data."""
        input_data = {tradeable_item1: {DataRequirement.TICKER: ticker_data_with_dates}}
        result = extract_trading_dates(input_data)
        expected_dates = [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)]
        assert result == expected_dates

    def test_multiple_items_same_dates(
        self, tradeable_item1, tradeable_item2, ticker_data_with_dates
    ):
        """Test with multiple tradeable items with same dates."""
        input_data = {
            tradeable_item1: {DataRequirement.TICKER: ticker_data_with_dates},
            tradeable_item2: {DataRequirement.TICKER: ticker_data_with_dates},
        }
        result = extract_trading_dates(input_data)
        expected_dates = [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)]
        assert result == expected_dates

    def test_multiple_items_different_dates(
        self, tradeable_item1, tradeable_item2, ticker_data_with_dates
    ):
        """Test with multiple tradeable items with different dates."""
        # Create a second dataframe with different dates
        dates2 = [
            datetime(2023, 1, 2, tzinfo=pytz.UTC),
            datetime(2023, 1, 3, tzinfo=pytz.UTC),
            datetime(2023, 1, 4, tzinfo=pytz.UTC),
        ]
        df2 = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [102, 103, 104],
                "volume": [1000, 2000, 3000],
            },
            index=pd.DatetimeIndex(dates2),
        )

        input_data = {
            tradeable_item1: {DataRequirement.TICKER: ticker_data_with_dates},
            tradeable_item2: {DataRequirement.TICKER: df2},
        }
        result = extract_trading_dates(input_data)
        expected_dates = [
            date(2023, 1, 1),
            date(2023, 1, 2),
            date(2023, 1, 3),
            date(2023, 1, 4),
        ]
        assert result == expected_dates

    def test_mixed_data_requirements(self, tradeable_item1, ticker_data_with_dates):
        """Test with mixed data requirements (TICKER and others)."""
        input_data = {
            tradeable_item1: {
                DataRequirement.TICKER: ticker_data_with_dates,
                DataRequirement.OPTIONS: pd.DataFrame({"data": [1, 2, 3]}),
            }
        }
        result = extract_trading_dates(input_data)
        expected_dates = [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)]
        assert result == expected_dates

    def test_non_datetime_index(self, tradeable_item1, ticker_data_no_datetime_index):
        """Test with ticker data that doesn't have DatetimeIndex."""
        input_data = {
            tradeable_item1: {DataRequirement.TICKER: ticker_data_no_datetime_index}
        }
        result = extract_trading_dates(input_data)
        # Should return empty list since we only extract from DatetimeIndex
        assert result == []

    def test_mixed_index_types(
        self,
        tradeable_item1,
        tradeable_item2,
        ticker_data_with_dates,
        ticker_data_no_datetime_index,
    ):
        """Test with mixed index types across different tradeable items."""
        input_data = {
            tradeable_item1: {DataRequirement.TICKER: ticker_data_with_dates},
            tradeable_item2: {DataRequirement.TICKER: ticker_data_no_datetime_index},
        }
        result = extract_trading_dates(input_data)
        expected_dates = [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)]
        assert result == expected_dates
