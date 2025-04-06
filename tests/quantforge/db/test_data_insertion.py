import os
import sys
import sqlite3
import pytest
from datetime import datetime, date, timezone
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from quantforge.db.create_database import create_stock_database
from quantforge.db.data_insertion import (
    parse_db_datetime,
    get_earliest_data_date_from_history,
    save_ticker_info,
    save_historical_data,
    save_financial_metrics,
    save_options_data,
    save_recent_news,
    save_all_data_for_ticker,
    ensure_ticker_in_file,
)


@pytest.mark.unit
class TestParseDbDatetime:
    """Test the parse_db_datetime function."""

    def test_parse_none(self):
        """Test parsing None value."""
        assert parse_db_datetime(None) is None

    def test_parse_datetime_object(self):
        """Test parsing a datetime object."""
        dt = datetime.now()
        assert parse_db_datetime(dt) == dt

    def test_parse_with_microseconds(self):
        """Test parsing a string with microseconds."""
        dt_str = "2023-04-01 12:30:45.123456"
        expected = datetime(2023, 4, 1, 12, 30, 45, 123456)
        assert parse_db_datetime(dt_str) == expected

    def test_parse_without_microseconds(self):
        """Test parsing a string without microseconds."""
        dt_str = "2023-04-01 12:30:45"
        expected = datetime(2023, 4, 1, 12, 30, 45)
        assert parse_db_datetime(dt_str) == expected

    def test_parse_iso_format(self):
        """Test parsing an ISO format string."""
        dt_str = "2023-04-01T12:30:45Z"
        expected = datetime(2023, 4, 1, 12, 30, 45, tzinfo=timezone.utc)
        assert parse_db_datetime(dt_str) == expected

    def test_parse_date_only(self):
        """Test parsing a date-only string."""
        dt_str = "2023-04-01"
        expected = datetime(2023, 4, 1, 0, 0, 0)
        assert parse_db_datetime(dt_str) == expected


@pytest.mark.unit
class TestDataInsertion:
    """Test the data insertion functions."""

    @pytest.fixture
    def test_db(self):
        """Fixture for the test database file."""
        db_name = "test_stock_data.db"
        # Create the test database
        create_stock_database(db_name)
        yield db_name
        # Clean up after tests
        if os.path.exists(db_name):
            os.remove(db_name)

    def test_get_earliest_data_date_from_history(self):
        """Test getting the earliest data date from history."""
        with patch("quantforge.db.data_insertion.yf.Ticker") as mock_ticker:
            # Create a mock Ticker instance
            mock_ticker_instance = MagicMock()
            mock_ticker.return_value = mock_ticker_instance

            # Create mock history DataFrame with index of dates
            dates = pd.date_range(start="2010-01-01", end="2023-01-01")
            mock_history = pd.DataFrame(index=dates, data={"Close": [100] * len(dates)})
            mock_ticker_instance.history.return_value = mock_history

            # Call the function
            result = get_earliest_data_date_from_history("AAPL")

            # Verify the result
            assert result == date(2010, 1, 1)
            mock_ticker_instance.history.assert_called_once_with(
                period="max", auto_adjust=False, actions=False
            )

    def test_save_ticker_info(self, test_db):
        """Test saving ticker info to the database."""
        with patch("quantforge.db.data_insertion.yf.Ticker") as mock_ticker:
            # Create a mock Ticker instance
            mock_ticker_instance = MagicMock()
            mock_ticker.return_value = mock_ticker_instance

            # Set up mock info
            mock_ticker_instance.info = {
                "shortName": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "marketCap": 2500000000000,
                "currency": "USD",
            }

            # Call the function
            save_ticker_info("AAPL", test_db)

            # Verify the data was saved correctly
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT company_name, sector, industry, market_cap, currency FROM ticker_info WHERE ticker = 'AAPL'"
            )
            result = cursor.fetchone()
            conn.close()

            assert result[0] == "Apple Inc."
            assert result[1] == "Technology"
            assert result[2] == "Consumer Electronics"
            assert result[3] == 2500000000000
            assert result[4] == "USD"

    def test_save_historical_data_new_ticker(self, test_db):
        """Test saving historical data for a new ticker."""
        with patch("quantforge.db.data_insertion.yf.Ticker") as mock_ticker:
            with patch(
                "quantforge.db.data_insertion.get_earliest_data_date_from_history"
            ) as mock_get_earliest:
                # Set up mock earliest date
                mock_get_earliest.return_value = date(2010, 1, 1)

                # Create a mock Ticker instance
                mock_ticker_instance = MagicMock()
                mock_ticker.return_value = mock_ticker_instance

                # Create mock historical data
                date_index = pd.date_range(
                    start="2010-01-01", end="2023-01-01", freq="D"
                )
                mock_data = pd.DataFrame(
                    {
                        "Open": np.random.random(len(date_index)) * 100,
                        "High": np.random.random(len(date_index)) * 100,
                        "Low": np.random.random(len(date_index)) * 100,
                        "Close": np.random.random(len(date_index)) * 100,
                        "Volume": np.random.randint(1000, 1000000, len(date_index)),
                        "Dividends": np.random.random(len(date_index)) * 1,
                    },
                    index=date_index,
                )
                mock_ticker_instance.history.return_value = mock_data

                # Call the function
                save_historical_data("AAPL", period="max", db_name=test_db)

                # Verify data was saved correctly
                conn = sqlite3.connect(test_db)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM historical_prices WHERE ticker = 'AAPL'"
                )
                count = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT MIN(timestamp), MAX(timestamp) FROM historical_prices WHERE ticker = 'AAPL'"
                )
                min_date, max_date = cursor.fetchone()
                conn.close()

                # Check number of records matches our mock data
                assert count == len(date_index)

                # Check date range matches our mock data
                min_dt = parse_db_datetime(min_date)
                max_dt = parse_db_datetime(max_date)
                assert min_dt.date() == date(2010, 1, 1)
                assert max_dt.date() == date(2023, 1, 1)

    def test_save_financial_metrics(self, test_db):
        """Test saving financial metrics."""
        with patch("quantforge.db.data_insertion.yf.Ticker") as mock_ticker:
            # Create a mock Ticker instance
            mock_ticker_instance = MagicMock()
            mock_ticker.return_value = mock_ticker_instance

            # Create mock financial data
            dates = pd.DatetimeIndex(["2020-12-31", "2021-12-31", "2022-12-31"])
            mock_income = pd.DataFrame(
                [
                    [100000, 120000, 140000],  # Total Revenue
                    [20000, 25000, 30000],  # Net Income
                    [30000, 35000, 40000],  # Operating Income
                ],
                index=["Total Revenue", "Net Income", "Operating Income"],
                columns=dates,
            )

            mock_balance = pd.DataFrame(
                [
                    [50000, 60000, 70000],  # Total Stockholder Equity
                    [30000, 25000, 20000],  # Total Debt
                ],
                index=["Total Stockholder Equity", "Total Debt"],
                columns=dates,
            )

            # Create mock quarterly data with same structure
            q_dates = pd.DatetimeIndex(
                ["2022-03-31", "2022-06-30", "2022-09-30", "2022-12-31"]
            )
            mock_q_income = pd.DataFrame(
                [
                    [35000, 36000, 37000, 38000],  # Total Revenue
                    [7000, 7500, 8000, 8500],  # Net Income
                    [10000, 10500, 11000, 11500],  # Operating Income
                ],
                index=["Total Revenue", "Net Income", "Operating Income"],
                columns=q_dates,
            )

            mock_q_balance = pd.DataFrame(
                [
                    [52000, 54000, 56000, 58000],  # Total Stockholder Equity
                    [28000, 26000, 24000, 22000],  # Total Debt
                ],
                index=["Total Stockholder Equity", "Total Debt"],
                columns=q_dates,
            )

            # Assign mock data to ticker
            mock_ticker_instance.income_stmt = mock_income
            mock_ticker_instance.balance_sheet = mock_balance
            mock_ticker_instance.quarterly_income_stmt = mock_q_income
            mock_ticker_instance.quarterly_balance_sheet = mock_q_balance
            mock_ticker_instance.info = {
                "sharesOutstanding": 1000000,
                "currentPrice": 150,
            }

            # Call the function
            save_financial_metrics("AAPL", test_db)

            # Verify annual data was saved correctly
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM financial_metrics WHERE ticker = 'AAPL' AND is_quarterly = 0"
            )
            annual_count = cursor.fetchone()[0]

            # Verify quarterly data was saved correctly
            cursor.execute(
                "SELECT COUNT(*) FROM financial_metrics WHERE ticker = 'AAPL' AND is_quarterly = 1"
            )
            quarterly_count = cursor.fetchone()[0]
            conn.close()

            # We should have 3 annual records and 4 quarterly records
            assert annual_count == 3
            assert quarterly_count == 4

    def test_save_options_data(self, test_db):
        """Test saving options data."""
        with patch("quantforge.db.data_insertion.yf.Ticker") as mock_ticker:
            # Create a mock Ticker instance
            mock_ticker_instance = MagicMock()
            mock_ticker.return_value = mock_ticker_instance

            # Set up mock options data
            mock_ticker_instance.options = ["2023-06-16", "2023-09-15", "2023-12-15"]

            # Mock option chain creation function to make it return consistent values
            def get_mock_option_chain(date):
                # Create option chain with calls and puts
                mock_calls = pd.DataFrame(
                    {
                        "strike": [140, 150, 160],
                        "lastPrice": [10, 5, 2],
                        "bid": [9.5, 4.8, 1.9],
                        "ask": [10.5, 5.2, 2.1],
                        "volume": [100, 200, 300],
                        "openInterest": [1000, 2000, 3000],
                        "impliedVolatility": [0.2, 0.15, 0.1],
                    }
                )

                mock_puts = pd.DataFrame(
                    {
                        "strike": [140, 150, 160],
                        "lastPrice": [2, 5, 10],
                        "bid": [1.9, 4.8, 9.5],
                        "ask": [2.1, 5.2, 10.5],
                        "volume": [100, 200, 300],
                        "openInterest": [1000, 2000, 3000],
                        "impliedVolatility": [0.2, 0.15, 0.1],
                    }
                )

                # Create a mock OptionChain object
                mock_chain = type(
                    "OptionChain", (), {"calls": mock_calls, "puts": mock_puts}
                )
                return mock_chain

            # Set the option_chain function to use our mock
            mock_ticker_instance.option_chain.side_effect = get_mock_option_chain

            # Call the function
            save_options_data("AAPL", test_db)

            # Verify options data was saved correctly
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()

            # Check number of call and put options
            cursor.execute(
                "SELECT COUNT(*) FROM options_data WHERE ticker = 'AAPL' AND option_type = 'call'"
            )
            call_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM options_data WHERE ticker = 'AAPL' AND option_type = 'put'"
            )
            put_count = cursor.fetchone()[0]

            conn.close()

            # We should have 9 call options and 9 put options (3 strike prices for each of 3 expiration dates)
            assert call_count == 9
            assert put_count == 9

    def test_save_recent_news(self, test_db):
        """Test saving recent news."""
        with patch("quantforge.db.data_insertion.yf.Ticker") as mock_ticker:
            # Create a mock Ticker instance
            mock_ticker_instance = MagicMock()
            mock_ticker.return_value = mock_ticker_instance

            # Set up mock news data
            current_time = datetime.now().timestamp()
            mock_news = [
                {
                    "title": "Apple Announces New iPhone",
                    "providerPublishTime": current_time - 86400,  # 1 day ago
                },
                {
                    "title": "Apple Reports Strong Earnings",
                    "providerPublishTime": current_time - 172800,  # 2 days ago
                },
                {
                    "title": "Apple Launches New Service",
                    "providerPublishTime": current_time - 259200,  # 3 days ago
                },
            ]
            mock_ticker_instance.news = mock_news

            # Call the function
            save_recent_news("AAPL", test_db)

            # Verify news data was saved correctly
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM recent_news WHERE ticker = 'AAPL'")
            count = cursor.fetchone()[0]
            conn.close()

            assert count == 3

    def test_save_all_data_for_ticker(self, test_db):
        """Test saving all data for a ticker."""
        with (
            patch("quantforge.db.data_insertion.save_ticker_info") as mock_save_ticker,
            patch(
                "quantforge.db.data_insertion.save_historical_data"
            ) as mock_save_hist,
            patch(
                "quantforge.db.data_insertion.save_financial_metrics"
            ) as mock_save_fin,
            patch("quantforge.db.data_insertion.save_options_data") as mock_save_opts,
            patch("quantforge.db.data_insertion.save_recent_news") as mock_save_news,
        ):
            # Set all mocks to return None (success)
            mock_save_ticker.return_value = None
            mock_save_hist.return_value = None
            mock_save_fin.return_value = None
            mock_save_opts.return_value = None
            mock_save_news.return_value = None

            # Call the function
            result = save_all_data_for_ticker("AAPL", test_db)

            # Verify all functions were called with correct arguments
            mock_save_ticker.assert_called_once_with("AAPL", test_db)
            mock_save_hist.assert_called_once_with(
                "AAPL", period="max", db_name=test_db
            )
            mock_save_fin.assert_called_once_with("AAPL", test_db)
            mock_save_opts.assert_called_once_with("AAPL", test_db)
            mock_save_news.assert_called_once_with("AAPL", test_db)

            # Verify the function returned True
            assert result is True

    @pytest.fixture
    def temp_tickers_file(self):
        """Fixture for temporary tickers file."""
        temp_file = "temp_tickers.txt"
        with open(temp_file, "w") as f:
            f.write("AAPL\nMSFT\nGOOGL\n")
        yield temp_file
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)

    def test_ensure_ticker_in_file(self, temp_tickers_file):
        """Test ensuring a ticker is in a file."""
        # Test with an existing ticker
        tickers = ensure_ticker_in_file("AAPL", temp_tickers_file)
        assert "AAPL" in tickers

        # Test with a new ticker
        tickers = ensure_ticker_in_file("NVDA", temp_tickers_file)
        assert "NVDA" in tickers

        # Verify the file was updated
        with open(temp_tickers_file, "r") as f:
            lines = f.readlines()
            assert "NVDA\n" in lines
