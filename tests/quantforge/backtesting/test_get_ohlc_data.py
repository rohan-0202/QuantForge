import pytest
import pandas as pd
from datetime import date, datetime, timedelta
from unittest.mock import patch

from quantforge.backtesting.get_ohlc_data import extract_ohlc_data
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.ohlc import OHLCData
from quantforge.strategies.data_requirement import DataRequirement
from quantforge.qtypes.assetclass import AssetClass
from quantforge.db.df_columns import TIMESTAMP, OPEN, HIGH, LOW, CLOSE, VOLUME


class TestGetOHLCData:
    @pytest.fixture
    def sample_date(self):
        return date(2023, 5, 1)

    @pytest.fixture
    def next_date(self, sample_date):
        return sample_date + timedelta(days=1)

    @pytest.fixture
    def tradeable_item1(self):
        return TradeableItem("AAPL", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def tradeable_item2(self):
        return TradeableItem("MSFT", asset_class=AssetClass.EQUITY)

    @pytest.fixture
    def portfolio(self, tradeable_item1, tradeable_item2):
        allowed_items = [tradeable_item1, tradeable_item2]
        return Portfolio(
            initial_cash=10000.0,
            allowed_tradeable_items=allowed_items,
            start_date=date(2023, 5, 1),
        )

    @pytest.fixture
    def valid_ticker_data(self, sample_date, next_date):
        """Create mock ticker data for two dates"""
        df = pd.DataFrame(
            {
                TIMESTAMP: [
                    datetime.combine(sample_date, datetime.min.time()),
                    datetime.combine(next_date, datetime.min.time()),
                ],
                OPEN: [150.0, 152.0],
                HIGH: [155.0, 157.0],
                LOW: [148.0, 151.0],
                CLOSE: [153.0, 156.0],
                VOLUME: [1000000, 1100000],
            }
        )
        # Set timestamp as index to match db_util.py behavior
        df.set_index(TIMESTAMP, inplace=True)
        return df

    @pytest.fixture
    def strategy_input_data(self, tradeable_item1, tradeable_item2, valid_ticker_data):
        """Create valid strategy input data for two tradeable items"""
        strategy_data = {}

        # Add data for tradeable_item1
        item1_data = {}
        item1_data[DataRequirement.TICKER] = valid_ticker_data.copy()
        strategy_data[tradeable_item1] = item1_data

        # Add data for tradeable_item2
        item2_data = {}
        item2_data[DataRequirement.TICKER] = valid_ticker_data.copy()
        # Modify values to be different
        item2_data[DataRequirement.TICKER][OPEN] = (
            item2_data[DataRequirement.TICKER][OPEN] * 2
        )
        item2_data[DataRequirement.TICKER][HIGH] = (
            item2_data[DataRequirement.TICKER][HIGH] * 2
        )
        item2_data[DataRequirement.TICKER][LOW] = (
            item2_data[DataRequirement.TICKER][LOW] * 2
        )
        item2_data[DataRequirement.TICKER][CLOSE] = (
            item2_data[DataRequirement.TICKER][CLOSE] * 2
        )
        strategy_data[tradeable_item2] = item2_data

        return strategy_data

    def test_extract_ohlc_data_with_valid_data(
        self,
        sample_date,
        tradeable_item1,
        tradeable_item2,
        portfolio,
        strategy_input_data,
    ):
        """Test with valid data for all tradeable items"""
        result = extract_ohlc_data(strategy_input_data, portfolio, sample_date)

        # Check that we got data for both tradeable items
        assert len(result) == 2
        assert tradeable_item1 in result
        assert tradeable_item2 in result

        # Check AAPL data
        aapl_data = result[tradeable_item1]
        assert isinstance(aapl_data, OHLCData)
        assert aapl_data.date == sample_date
        assert aapl_data.open == 150.0
        assert aapl_data.high == 155.0
        assert aapl_data.low == 148.0
        assert aapl_data.close == 153.0
        assert aapl_data.volume == 1000000

        # Check MSFT data (values should be 2x AAPL values)
        msft_data = result[tradeable_item2]
        assert isinstance(msft_data, OHLCData)
        assert msft_data.date == sample_date
        assert msft_data.open == 300.0  # 2 * 150.0
        assert msft_data.high == 310.0  # 2 * 155.0
        assert msft_data.low == 296.0  # 2 * 148.0
        assert msft_data.close == 306.0  # 2 * 153.0
        assert msft_data.volume == 1000000

    def test_extract_ohlc_data_with_missing_date(self, portfolio, strategy_input_data):
        """Test with a date that doesn't exist in the data"""
        missing_date = date(2022, 1, 1)

        with patch("quantforge.backtesting.get_ohlc_data.logger") as mock_logger:
            result = extract_ohlc_data(strategy_input_data, portfolio, missing_date)

            # Verify warnings were logged
            assert mock_logger.warning.call_count == 2

            # Verify empty result
            assert result == {}

    def test_extract_ohlc_data_with_partial_data(
        self,
        sample_date,
        tradeable_item1,
        tradeable_item2,
        portfolio,
        strategy_input_data,
    ):
        """Test with data missing for one tradeable item"""
        # Remove data for tradeable_item2
        del strategy_input_data[tradeable_item2]

        with patch("quantforge.backtesting.get_ohlc_data.logger") as mock_logger:
            result = extract_ohlc_data(strategy_input_data, portfolio, sample_date)

            # Check that we only got data for tradeable_item1
            assert len(result) == 1
            assert tradeable_item1 in result
            assert tradeable_item2 not in result

            # Verify warning was logged for the missing item
            mock_logger.warning.assert_called_once()

    def test_extract_ohlc_data_with_invalid_columns(
        self, sample_date, tradeable_item1, portfolio
    ):
        """Test with missing required columns in the data"""
        # Create data with missing columns
        invalid_data = {}
        item_data = {}

        # Create dataframe with missing columns
        df = pd.DataFrame(
            {
                TIMESTAMP: [datetime.combine(sample_date, datetime.min.time())],
                OPEN: [150.0],
                # Missing HIGH, LOW
                CLOSE: [153.0],
                VOLUME: [1000000],
            }
        )
        # Set timestamp as index to match db_util.py behavior
        df.set_index(TIMESTAMP, inplace=True)

        item_data[DataRequirement.TICKER] = df
        invalid_data[tradeable_item1] = item_data

        # This should raise a KeyError when trying to access missing columns
        with pytest.raises(KeyError):
            extract_ohlc_data(invalid_data, portfolio, sample_date)

    def test_next_day_data_extraction(
        self, sample_date, next_date, tradeable_item1, portfolio, strategy_input_data
    ):
        """Test extraction for the next day's data"""
        result = extract_ohlc_data(strategy_input_data, portfolio, next_date)

        # Check that we got data for the next day
        assert tradeable_item1 in result
        next_day_data = result[tradeable_item1]

        assert next_day_data.date == next_date
        assert next_day_data.open == 152.0  # Next day's price
        assert next_day_data.close == 156.0  # Next day's close
