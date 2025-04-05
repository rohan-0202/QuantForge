import os
import sys
import sqlite3
import pytest
from unittest.mock import patch

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import the function from the db module
from src.quantforge.db.create_database import create_stock_database


@pytest.mark.unit
class TestCreateDatabase:
    """Test the create_database.py functionality."""
    
    @pytest.fixture
    def test_db(self):
        """Fixture for the test database file."""
        db_name = "test_stock_data.db"
        # Remove the test database if it exists
        if os.path.exists(db_name):
            os.remove(db_name)
        yield db_name
        # Clean up the test database after the test
        if os.path.exists(db_name):
            os.remove(db_name)
    
    def test_database_creation(self, test_db):
        """Test if the database is created successfully."""
        # Create the database
        create_stock_database(test_db)
        
        # Check if the database file exists
        assert os.path.exists(test_db), "Database file was not created"
        
        # Connect to the database
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # Check if all required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        
        expected_tables = [
            'ticker_info',
            'historical_prices',
            'financial_metrics',
            'options_data',
            'recent_news'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table '{table}' is missing from the database"
        
        conn.close()
    
    def test_table_schemas(self, test_db):
        """Test if the tables have the correct schema."""
        # Create the database
        create_stock_database(test_db)
        
        # Connect to the database
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # Define expected columns for each table
        expected_schemas = {
            'ticker_info': [
                'ticker', 'company_name', 'sector', 'industry', 
                'market_cap', 'currency', 'last_updated'
            ],
            'historical_prices': [
                'ticker', 'timestamp', 'open', 'high', 
                'low', 'close', 'volume', 'dividends'
            ],
            'financial_metrics': [
                'ticker', 'timestamp', 'is_quarterly', 'revenue',
                'earnings', 'eps', 'pe_ratio', 'debt_to_equity', 
                'operating_margin', 'roe'
            ],
            'options_data': [
                'id', 'ticker', 'expiration_date', 'option_type',
                'strike', 'last_price', 'bid', 'ask', 'volume',
                'open_interest', 'implied_volatility', 'last_updated'
            ],
            'recent_news': [
                'id', 'ticker', 'title', 'publish_date'
            ]
        }
        
        # Check each table's schema
        for table, expected_columns in expected_schemas.items():
            cursor.execute(f"PRAGMA table_info({table});")
            actual_columns = [info[1] for info in cursor.fetchall()]  # Column names are at index 1
            
            for column in expected_columns:
                assert column in actual_columns, f"Column '{column}' is missing from table '{table}'"
        
        conn.close()
    
    def test_success_message(self, test_db):
        """Test if success message is printed."""
        with patch('src.quantforge.db.create_database.print') as mock_print:
            create_stock_database(test_db)
            
            # Check if the success message was printed
            mock_print.assert_called_with(f"Database '{test_db}' created successfully with essential trading tables.") 