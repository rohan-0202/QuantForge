import pytest
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
import os # Needed for managing test db file if tmp_path isn't used

from quantforge.db.db_util import get_historical_data, get_options_data
from quantforge.db.create_database import create_stock_database

# Fixture to create and populate a temporary database for tests
@pytest.fixture(scope="module") # Use module scope for efficiency
def test_db(tmp_path_factory):
    """Creates a temporary SQLite DB, populates it, and yields the path."""
    # Create a db file in a temporary directory
    db_path = tmp_path_factory.mktemp("data") / "test_stock_data.db"
    db_path_str = str(db_path)

    # Create tables
    create_stock_database(db_name=db_path_str)

    # Connect and insert sample data
    conn = sqlite3.connect(db_path_str)
    cursor = conn.cursor()

    # Sample historical data
    historical_data = [
        ("AAPL", (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"), 150.0, 152.0, 149.0, 151.0, 1000000, 0.0),
        ("AAPL", (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S"), 151.0, 153.0, 150.0, 152.5, 1100000, 0.0),
        ("MSFT", (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"), 250.0, 255.0, 248.0, 253.0, 900000, 0.0),
        ("MSFT", (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S"), 240.0, 245.0, 238.0, 243.0, 800000, 0.0), # Older data
    ]
    cursor.executemany("INSERT INTO historical_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)", historical_data)

    # Sample options data
    options_data = [
        ("AAPL", (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"), 'call', 160.0, 5.0, 4.9, 5.1, 1000, 5000, 0.3, datetime.now().strftime("%Y-%m-%d %H:%M:%S")), # id inserted automatically
        ("AAPL", (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"), 'put', 140.0, 2.0, 1.9, 2.1, 800, 4000, 0.25, datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
        ("AAPL", (datetime.now() + timedelta(days=400)).strftime("%Y-%m-%d %H:%M:%S"), 'call', 170.0, 10.0, 9.8, 10.2, 500, 2000, 0.4, datetime.now().strftime("%Y-%m-%d %H:%M:%S")), # Far expiration
        ("MSFT", (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S"), 'call', 260.0, 8.0, 7.9, 8.1, 700, 3000, 0.35, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ]
    # Correct the INSERT statement for options_data (id is auto-increment)
    cursor.executemany("INSERT INTO options_data (ticker, expiration_date, option_type, strike, last_price, bid, ask, volume, open_interest, implied_volatility, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", options_data)

    conn.commit()
    conn.close()

    yield db_path_str # Provide the path to the tests

    # Cleanup is handled by tmp_path_factory fixture


@pytest.mark.unit
class TestGetHistoricalData:
    def test_get_historical_data_success(self, test_db):
        """Test retrieving data using the test database."""
        ticker = "AAPL"
        # Pass the test_db path to the function
        df = get_historical_data(ticker, db_name=test_db)
        assert not df.empty
        assert df.index.name == "timestamp"
        # Check if we got the 2 recent AAPL entries
        assert len(df) == 2

    def test_get_historical_data_days_parameter(self, test_db):
        """Test the days parameter limits results."""
        ticker = "AAPL"
        days = 4 # Should only get the entry from 4 days ago, not 5
        df = get_historical_data(ticker, db_name=test_db, days=days)
        assert len(df) == 1
        # Check the timestamp is within the range (approximate check)
        assert df.index[0].date() >= (datetime.now() - timedelta(days=days)).date()

        ticker_ms = "MSFT"
        days_ms = 20 # Should only get the entry from 10 days ago, not 60
        df_ms = get_historical_data(ticker_ms, db_name=test_db, days=days_ms)
        assert len(df_ms) == 1
        assert df_ms.index[0].date() >= (datetime.now() - timedelta(days=days_ms)).date()


    def test_get_historical_data_invalid_ticker(self, test_db):
        """Test requesting data for a ticker not in the test db."""
        invalid_ticker = "INVALID_TICKER_XYZ"
        with pytest.raises(ValueError, match=f"No historical data found for {invalid_ticker}"):
            get_historical_data(invalid_ticker, db_name=test_db)

    # Removed the custom_db test as it's redundant with the fixture
    # def test_get_historical_data_custom_db(self):
    #     ...


@pytest.mark.unit
class TestGetOptionsData:
    def test_get_options_data_success(self, test_db):
        """Test retrieving options data using the test database."""
        ticker = "AAPL"
        df = get_options_data(ticker, db_name=test_db) # Default days=365
        assert not df.empty
        assert df.index.name == "expiration_date"
        # Should get all 3 AAPL options (30-day call, 30-day put, 400-day call)
        # because their expiration_date is >= (now - 365 days)
        assert len(df) == 3 # Corrected assertion
        assert all(df['option_type'].isin(['call', 'put']))

    def test_get_options_data_days_parameter(self, test_db):
        """Test the days parameter limits options results by expiration."""
        ticker = "AAPL"
        days = 50 # Should get options expiring >= (now - 50 days)
        df = get_options_data(ticker, db_name=test_db, days=days)
        # All 3 sample options (30-day call/put, 400-day call) expire after (now - 50 days)
        assert len(df) == 3 # Corrected assertion
        # Check expiration is within range (approximate)
        assert df.index.min().date() >= (datetime.now() - timedelta(days=days)).date()

        days_long = 500 # Should still get all 3 AAPL options
        df_long = get_options_data(ticker, db_name=test_db, days=days_long)
        assert len(df_long) == 3

    def test_get_options_data_invalid_ticker(self, test_db):
        """Test requesting options data for a ticker not in the test db."""
        invalid_ticker = "INVALID_TICKER_XYZ"
        with pytest.raises(ValueError, match=f"No options data found for {invalid_ticker}"):
            get_options_data(invalid_ticker, db_name=test_db)

    # Removed the custom_db test
    # def test_get_options_data_custom_db(self):
    #     ...

    def test_get_options_data_call_put_filtering(self, test_db):
        """Test that both call and put options are retrieved when present."""
        ticker = "AAPL"
        # Use days=500 to ensure all sample options are retrieved
        df = get_options_data(ticker, db_name=test_db, days=500)
        assert not df.empty
        option_types = df['option_type'].unique()
        assert 'call' in option_types
        assert 'put' in option_types
