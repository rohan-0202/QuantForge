import sqlite3
from datetime import datetime, date

import pandas as pd


def fetch_historical_options_data(
    ticker_symbol: str,
    start_date: date,
    end_date: date = None,
    db_name: str = "stock_data.db",
) -> pd.DataFrame:
    """Fetch options data for a ticker from the database.
    CREATE TABLE IF NOT EXISTS options_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT,
        expiration_date TIMESTAMP,
        option_type TEXT,  -- 'call' or 'put'
        strike REAL,
        last_price REAL,
        bid REAL,
        ask REAL,
        volume INTEGER,
        open_interest INTEGER,
        implied_volatility REAL,
        last_updated TIMESTAMP,
        UNIQUE(ticker, expiration_date, option_type, strike)
    )

    """
    if end_date is None:
        end_date = datetime.now().date()

    conn = sqlite3.connect(db_name)

    # Query to get data from options table
    query = """
        SELECT expiration_date, option_type, strike, last_price, bid, ask, volume, open_interest, implied_volatility, last_updated
        FROM options_data
        WHERE ticker = ? AND last_updated >= ? AND last_updated <= ?
        ORDER BY expiration_date ASC
    """

    # First, get the data without parsing dates
    df = pd.read_sql_query(
        query,
        conn,
        params=(
            ticker_symbol,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        ),
    )

    conn.close()

    if df.empty:
        raise ValueError(f"No options data found for {ticker_symbol}")

    # Parse the timestamp column manually to avoid timezone issues
    df["expiration_date"] = pd.to_datetime(
        df["expiration_date"], errors="coerce", utc=True
    )

    # Set expiration_date as index
    df.set_index("expiration_date", inplace=True)

    return df


def fetch_historical_ticker_data(
    ticker_symbol: str,
    start_date: date,
    end_date: date = None,
    db_name: str = "stock_data.db",
) -> pd.DataFrame:
    """Helper function to fetch historical price data with date range parameters."""
    if end_date is None:
        end_date = datetime.now().date()

    conn = sqlite3.connect(db_name)

    # Query to get data
    query = """
    SELECT timestamp, open, high, low, close, volume
    FROM historical_prices
    WHERE ticker = ? AND timestamp >= ? AND timestamp <= ?
    ORDER BY timestamp ASC
    """

    # Get the data for the specified date range
    df = pd.read_sql_query(
        query,
        conn,
        params=(
            ticker_symbol,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        ),
    )

    conn.close()

    if df.empty:
        raise ValueError(
            f"No historical data found for {ticker_symbol} between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}"
        )

    # Parse the timestamp column manually to avoid timezone issues
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    # Set timestamp as index
    df.set_index("timestamp", inplace=True)

    return df
