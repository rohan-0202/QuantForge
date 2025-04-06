import pytest
import pandas as pd
from datetime import datetime, timedelta
from quantforge.db.db_util import get_historical_data, get_options_data


class TestGetHistoricalData:
    def test_get_historical_data_success(self):
        """Test that we can successfully retrieve historical data for a known ticker."""
        # Use a common stock ticker that should exist in the database
        ticker = "AAPL"
        df = get_historical_data(ticker)

        # Verify the structure of the returned DataFrame
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert isinstance(df.index, pd.DatetimeIndex)
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]

        # Check data types
        assert df["open"].dtype == float
        assert df["high"].dtype == float
        assert df["low"].dtype == float
        assert df["close"].dtype == float
        assert df["volume"].dtype == int or df["volume"].dtype == float

    def test_get_historical_data_days_parameter(self):
        """Test that the days parameter correctly limits the date range."""
        ticker = "MSFT"
        days = 30

        df = get_historical_data(ticker, days=days)

        # Check that the data range doesn't exceed our requested days
        # Add a small buffer for test execution time
        assert not df.empty
        latest_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        earliest_expected_date = latest_date - timedelta(days=days)
        earliest_actual_date = df.index.min().to_pydatetime().replace(tzinfo=None)

        # The earliest date in the data should not be before our calculated date
        # (allowing a day of margin for different timezones)
        assert earliest_actual_date >= earliest_expected_date - timedelta(days=1)

    def test_get_historical_data_invalid_ticker(self):
        """Test that requesting data for a non-existent ticker raises ValueError."""
        # Use a ticker that should not exist in any database
        invalid_ticker = "INVALID_TICKER_123456789"

        with pytest.raises(ValueError) as excinfo:
            get_historical_data(invalid_ticker)

        assert f"No historical data found for {invalid_ticker}" in str(excinfo.value)

    def test_get_historical_data_custom_db(self):
        """Test retrieving data from a custom database file."""
        # This test assumes stock_data.db exists and contains data
        ticker = "AAPL"
        df = get_historical_data(ticker, db_name="stock_data.db")

        assert isinstance(df, pd.DataFrame)
        assert not df.empty


class TestGetOptionsData:
    def test_get_options_data_success(self):
        """Test that we can successfully retrieve options data for a known ticker."""
        # Use a common stock ticker that should exist in the database
        ticker = "AAPL"
        df = get_options_data(ticker)

        # Verify the structure of the returned DataFrame
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert isinstance(df.index, pd.DatetimeIndex)

        # Check that all expected columns are present
        expected_columns = [
            "option_type",
            "strike",
            "last_price",
            "bid",
            "ask",
            "volume",
            "open_interest",
            "implied_volatility",
            "last_updated",
        ]
        assert all(column in df.columns for column in expected_columns)

        # Check basic data types
        assert df["option_type"].isin(["call", "put"]).all()
        assert df["strike"].dtype == float
        assert df["last_price"].dtype == float
        assert df["bid"].dtype == float
        assert df["ask"].dtype == float
        assert df["implied_volatility"].dtype == float

    def test_get_options_data_days_parameter(self):
        """Test that the days parameter correctly limits the date range."""
        ticker = "MSFT"
        days = 30

        df = get_options_data(ticker, days=days)

        # Check that the data range doesn't exceed our requested days
        assert not df.empty

        # The expiration dates should all be after (now - days)
        earliest_expected_date = (datetime.now() - timedelta(days=days)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Since expiration_date is the index, we can check directly
        earliest_actual_date = df.index.min().to_pydatetime().replace(tzinfo=None)

        # Allow a day of margin for timezone differences
        assert earliest_actual_date >= earliest_expected_date - timedelta(days=1)

    def test_get_options_data_invalid_ticker(self):
        """Test that requesting data for a non-existent ticker raises ValueError."""
        invalid_ticker = "INVALID_TICKER_123456789"

        with pytest.raises(ValueError) as excinfo:
            get_options_data(invalid_ticker)

        assert f"No options data found for {invalid_ticker}" in str(excinfo.value)

    def test_get_options_data_custom_db(self):
        """Test retrieving data from a custom database file."""
        ticker = "AAPL"
        df = get_options_data(ticker, db_name="stock_data.db")

        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_get_options_data_call_put_filtering(self):
        """Test that both call and put options are present in the results."""
        ticker = "AAPL"
        df = get_options_data(ticker)

        # Check that we have both call and put options
        assert "call" in df["option_type"].unique()
        assert "put" in df["option_type"].unique()

        # Verify we can filter by option type
        calls = df[df["option_type"] == "call"]
        puts = df[df["option_type"] == "put"]

        assert not calls.empty
        assert not puts.empty
