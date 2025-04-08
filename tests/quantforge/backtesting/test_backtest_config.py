import pytest
from datetime import date, timedelta
from dataclasses import asdict

from quantforge.backtesting.backtest_config import BacktestConfig
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem, AssetClass
from quantforge.qtypes.transaction import Transaction


@pytest.mark.unit
class TestBacktestConfig:
    """Tests for BacktestConfig class."""

    @pytest.fixture
    def tradeable_items(self):
        """Return a list of tradeable items for testing."""
        return [
            TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY),
            TradeableItem(id="MSFT", asset_class=AssetClass.EQUITY),
        ]

    @pytest.fixture
    def portfolio(self, tradeable_items):
        """Return a portfolio for testing."""
        return Portfolio(
            initial_cash=50000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=date(2023, 1, 1),
            allow_margin=False,
            allow_short=False,
        )

    @pytest.fixture
    def backtest_config(self, portfolio):
        """Return a backtest config for testing."""
        return BacktestConfig(
            initial_portfolio=portfolio,
            strategy_name="test_strategy",
            end_date=date(2023, 12, 31),
        )

    def test_from_dict_with_date_objects(self, portfolio):
        """Test creating a BacktestConfig from a dict with date objects."""
        config_dict = {
            "end_date": date(2023, 12, 31),
            "initial_portfolio": {
                "_cash": portfolio.cash,
                "_start_date": portfolio.start_date,
                "_allow_margin": portfolio.allow_margin,
                "_allow_short": portfolio.allow_short,
                "_allowed_tradeable_items": [
                    asdict(item) for item in portfolio.allowed_tradeable_items
                ],
                "_closed_positions": [],
                "_open_positions_by_tradeable_item": [],
            },
            "strategy_name": "test_strategy",
        }

        config = BacktestConfig.from_dict(config_dict)

        assert config.initial_portfolio.start_date == date(2023, 1, 1)
        assert config.end_date == date(2023, 12, 31)
        assert config.strategy_name == "test_strategy"
        assert config.initial_portfolio.cash == portfolio.cash
        assert len(config.initial_portfolio.allowed_tradeable_items) == len(
            portfolio.allowed_tradeable_items
        )

    def test_from_dict_with_date_strings(self, portfolio):
        """Test creating a BacktestConfig from a dict with date strings."""
        config_dict = {
            "end_date": "2023-12-31",
            "initial_portfolio": {
                "_cash": portfolio.cash,
                "_start_date": portfolio.start_date,
                "_allow_margin": portfolio.allow_margin,
                "_allow_short": portfolio.allow_short,
                "_allowed_tradeable_items": [
                    asdict(item) for item in portfolio.allowed_tradeable_items
                ],
                "_closed_positions": [],
                "_open_positions_by_tradeable_item": [],
            },
            "strategy_name": "test_strategy",
        }

        config = BacktestConfig.from_dict(config_dict)

        assert config.initial_portfolio.start_date == date(2023, 1, 1)
        assert config.end_date == date(2023, 12, 31)
        assert config.strategy_name == "test_strategy"
        assert config.initial_portfolio.cash == portfolio.cash

    def test_from_dict_without_end_date(self, portfolio):
        """Test creating a BacktestConfig from a dict without an end date."""
        config_dict = {
            "initial_portfolio": {
                "_cash": portfolio.cash,
                "_start_date": portfolio.start_date,
                "_allow_margin": portfolio.allow_margin,
                "_allow_short": portfolio.allow_short,
                "_allowed_tradeable_items": [
                    asdict(item) for item in portfolio.allowed_tradeable_items
                ],
                "_closed_positions": [],
                "_open_positions_by_tradeable_item": [],
            },
            "strategy_name": "test_strategy",
        }

        config = BacktestConfig.from_dict(config_dict)

        assert config.initial_portfolio.start_date == date(2023, 1, 1)
        assert config.end_date is None
        assert config.strategy_name == "test_strategy"
        assert config.initial_portfolio.cash == portfolio.cash

    def test_post_init_validation_success(self, portfolio):
        """Test that __post_init__ validation passes with valid data."""
        config = BacktestConfig(
            initial_portfolio=portfolio,
            strategy_name="test_strategy",
            end_date=date(2023, 12, 31),
        )

        # If we get here, __post_init__ didn't raise an assertion error
        assert config.initial_portfolio == portfolio
        assert config.strategy_name == "test_strategy"
        assert config.end_date == date(2023, 12, 31)

    def test_post_init_end_date_before_start_date(self, portfolio):
        """Test that __post_init__ fails when end_date is before portfolio start_date."""
        # Set end_date to one day before portfolio start_date
        bad_end_date = portfolio.start_date - timedelta(days=1)

        with pytest.raises(AssertionError) as excinfo:
            BacktestConfig(
                initial_portfolio=portfolio,
                strategy_name="test_strategy",
                end_date=bad_end_date,
            )

        assert "End date must be greater than or equal to start date" in str(
            excinfo.value
        )

    def test_post_init_portfolio_with_closed_positions(
        self, portfolio, tradeable_items
    ):
        """Test that __post_init__ fails when portfolio has closed positions."""
        # Create a transaction
        buy_transaction = Transaction(
            tradeable_item=tradeable_items[0],
            quantity=100,
            price=150.0,
            date=date(2023, 1, 2),
            transaction_cost=10.0,
        )

        # Open a position
        position = portfolio.open_position(buy_transaction)

        # Close the position
        sell_transaction = Transaction(
            tradeable_item=tradeable_items[0],
            quantity=-100,
            price=160.0,
            date=date(2023, 1, 3),
            transaction_cost=10.0,
        )

        portfolio.close_position(position, sell_transaction)

        # Now the portfolio has a closed position, should fail validation
        with pytest.raises(AssertionError) as excinfo:
            BacktestConfig(
                initial_portfolio=portfolio,
                strategy_name="test_strategy",
                end_date=date(2023, 12, 31),
            )

        assert "Portfolio must not have any closed positions" in str(excinfo.value)
