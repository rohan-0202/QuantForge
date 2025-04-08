import pytest
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.transaction import Transaction
from quantforge.qtypes.tradeable_item import TradeableItem, AssetClass
from datetime import date
from dataclasses import asdict


@pytest.mark.unit
class TestPortfolioSerialization:
    """Tests for serialization and deserialization of Portfolio."""

    @pytest.fixture
    def tradeable_items(self):
        """Return a list of tradeable items for testing."""
        return [
            TradeableItem(id="AAPL", asset_class=AssetClass.EQUITY),
            TradeableItem(id="MSFT", asset_class=AssetClass.EQUITY),
        ]

    @pytest.fixture
    def start_date(self):
        """Return a date for testing."""
        return date(2023, 1, 1)

    @pytest.fixture
    def empty_portfolio(self, tradeable_items, start_date):
        """Return an empty portfolio for testing."""
        return Portfolio(
            initial_cash=50000.0,
            allowed_tradeable_items=tradeable_items,
            start_date=start_date,
            allow_margin=True,
            allow_short=True,
        )

    @pytest.fixture
    def portfolio_with_positions(self, empty_portfolio, tradeable_items):
        """Return a portfolio with positions for testing."""
        # Create transactions
        buy_transaction = Transaction(
            tradeable_item=tradeable_items[0],
            quantity=100,
            price=150.0,
            date=date(2023, 1, 2),
            transaction_cost=10.0,
        )

        # Open a position
        empty_portfolio.open_position(buy_transaction)

        # Create a second position and close it
        buy_transaction2 = Transaction(
            tradeable_item=tradeable_items[1],
            quantity=50,
            price=200.0,
            date=date(2023, 1, 3),
            transaction_cost=10.0,
        )
        position = empty_portfolio.open_position(buy_transaction2)

        sell_transaction = Transaction(
            tradeable_item=tradeable_items[1],
            quantity=-50,
            price=220.0,
            date=date(2023, 1, 10),
            transaction_cost=10.0,
        )

        empty_portfolio.close_position(position, sell_transaction)

        return empty_portfolio

    def create_portfolio_dict(self, portfolio):
        """Create a dictionary representation of a portfolio."""
        if len(portfolio._open_positions_by_tradeable_item) > 0:
            open_positions = [
                {
                    "tradeable_item": asdict(item),
                    "positions": [asdict(position) for position in positions],
                }
                for item, positions in portfolio._open_positions_by_tradeable_item.items()
            ]
        else:
            open_positions = {}

        return {
            "_cash": portfolio.cash,
            "_start_date": portfolio.start_date,
            "_allow_margin": portfolio.allow_margin,
            "_allow_short": portfolio.allow_short,
            "_allowed_tradeable_items": [
                asdict(item) for item in portfolio.allowed_tradeable_items
            ],
            "_closed_positions": [
                asdict(position) for position in portfolio._closed_positions
            ],
            "_open_positions_by_tradeable_item": open_positions,
        }

    def verify_portfolios_equal(self, original, reconstructed):
        """Verify that two portfolios have the same properties."""
        # Check basic properties
        assert reconstructed.cash == original.cash
        assert reconstructed.start_date == original.start_date
        assert reconstructed.allow_margin == original.allow_margin
        assert reconstructed.allow_short == original.allow_short

        # Check allowed tradeable items
        assert len(reconstructed.allowed_tradeable_items) == len(
            original.allowed_tradeable_items
        )
        for i, item in enumerate(original.allowed_tradeable_items):
            assert reconstructed.allowed_tradeable_items[i].id == item.id
            assert (
                reconstructed.allowed_tradeable_items[i].asset_class == item.asset_class
            )

        # Check closed positions
        assert len(reconstructed._closed_positions) == len(original._closed_positions)

        # Check open positions
        assert len(reconstructed._open_positions_by_tradeable_item) == len(
            original._open_positions_by_tradeable_item
        )

        # Check positions for each tradeable item
        for tradeable_item in original.allowed_tradeable_items:
            if original.has_position(tradeable_item):
                assert reconstructed.has_position(tradeable_item)

                original_positions = original.get_open_positions_by_item(tradeable_item)
                reconstructed_positions = reconstructed.get_open_positions_by_item(
                    tradeable_item
                )

                assert len(reconstructed_positions) == len(original_positions)

    @pytest.mark.parametrize(
        "portfolio_fixture_name", ["empty_portfolio", "portfolio_with_positions"]
    )
    def test_portfolio_serialization_deserialization(
        self, portfolio_fixture_name, request
    ):
        """Test serialization and deserialization of portfolios."""
        # Get the portfolio fixture
        portfolio = request.getfixturevalue(portfolio_fixture_name)

        # Convert to dictionary
        portfolio_dict = self.create_portfolio_dict(portfolio)

        # Convert back to Portfolio
        reconstructed_portfolio = Portfolio.from_dict(portfolio_dict)

        # Verify properties match
        self.verify_portfolios_equal(portfolio, reconstructed_portfolio)

    @pytest.mark.parametrize(
        "invalid_key, invalid_value, error_message",
        [
            (
                "_closed_positions",
                ["not_a_position"],
                "Expected dict or PortfolioPosition",
            ),
            (
                "_open_positions_by_tradeable_item",
                [{"tradeable_item": "not_a_tradeable_item", "positions": []}],
                "Expected dict or TradeableItem",
            ),
            (
                "_open_positions_by_tradeable_item",
                [
                    {
                        "tradeable_item": asdict(
                            TradeableItem(id="TEST", asset_class=AssetClass.EQUITY)
                        ),
                        "positions": ["not_a_position"],
                    }
                ],
                "Expected dict or PortfolioPosition",
            ),
        ],
    )
    def test_invalid_types_raise_error(
        self,
        empty_portfolio,
        tradeable_items,
        invalid_key,
        invalid_value,
        error_message,
    ):
        """Test that invalid types in different parts of the portfolio dictionary raise a ValueError."""
        portfolio_dict = {
            "_cash": empty_portfolio.cash,
            "_start_date": empty_portfolio.start_date,
            "_allow_margin": empty_portfolio.allow_margin,
            "_allow_short": empty_portfolio.allow_short,
            "_allowed_tradeable_items": [
                asdict(item) for item in empty_portfolio.allowed_tradeable_items
            ],
            "_closed_positions": [],
            "_open_positions_by_tradeable_item": [],
        }

        # Replace the appropriate key with the invalid value
        portfolio_dict[invalid_key] = invalid_value

        # Attempting to deserialize should raise a ValueError
        with pytest.raises(ValueError) as excinfo:
            Portfolio.from_dict(portfolio_dict)

        # Verify the error message
        assert error_message in str(excinfo.value)
