import pytest
from unittest.mock import MagicMock, patch

from quantforge.strategies.strategy_factory import StrategyFactory
from quantforge.strategies.abstract_strategy import AbstractStrategy
from quantforge.strategies.simple_ticker_strategy import SimpleTickerDataStrategy
from quantforge.qtypes.portfolio import Portfolio


# Define a dummy strategy for testing the factory's discovery mechanism
class DummyTestStrategy(AbstractStrategy):
    """A dummy strategy class used just for testing the factory."""

    def __init__(self, portfolio: Portfolio, test_param: str = "default"):
        super().__init__(name="DummyTestStrategy", portfolio=portfolio)
        self.test_param = test_param

    def generate_signals(self, input_data):
        return {}

    def get_data_requirements(self):
        return []

    def allocate_capital(self, buy_signals, next_day_data):
        return {}


class TestStrategyFactory:
    @pytest.fixture
    def portfolio(self):
        """Create a mock portfolio for testing."""
        return MagicMock(spec=Portfolio)

    @pytest.fixture
    def mock_strategy_modules(self):
        """Mock the strategy modules to control what's available for testing."""
        # Create a mock module for our dummy strategy
        mock_module = MagicMock()
        mock_module.DummyTestStrategy = DummyTestStrategy

        # Create a mock module for SimpleTickerDataStrategy
        simple_ticker_module = MagicMock()
        simple_ticker_module.SimpleTickerDataStrategy = SimpleTickerDataStrategy

        # Create a mock module for AbstractStrategy
        abstract_module = MagicMock()
        abstract_module.AbstractStrategy = AbstractStrategy

        # Create a mock for os.listdir to return our test files
        with patch("os.listdir") as mock_listdir:
            mock_listdir.return_value = [
                "simple_ticker_strategy.py",
                "test_dummy_strategy.py",
                "abstract_strategy.py",
                "__init__.py",
            ]

            # Create a mock for importlib.import_module
            with patch("importlib.import_module") as mock_import:
                # Set up the mock to return our mock modules
                def mock_import_side_effect(module_path):
                    if module_path == "quantforge.strategies.simple_ticker_strategy":
                        return simple_ticker_module
                    elif module_path == "quantforge.strategies.test_dummy_strategy":
                        return mock_module
                    elif module_path == "quantforge.strategies.abstract_strategy":
                        return abstract_module
                    else:
                        raise ImportError(f"Module {module_path} not found")

                mock_import.side_effect = mock_import_side_effect

                yield

    def test_get_available_strategies(self, mock_strategy_modules):
        """Test that the factory can discover available strategies."""
        strategies = StrategyFactory.get_available_strategies()

        # The list should contain our two known strategies
        assert "SimpleTickerDataStrategy" in strategies
        assert "DummyTestStrategy" in strategies

    def test_create_existing_strategy(self, portfolio, mock_strategy_modules):
        """Test that the factory can create an existing strategy."""
        strategy = StrategyFactory.create_strategy(
            "SimpleTickerDataStrategy", portfolio
        )

        # Verify that the created instance is of the correct type
        assert isinstance(strategy, SimpleTickerDataStrategy)
        assert strategy.portfolio == portfolio

    def test_create_test_strategy(self, portfolio, mock_strategy_modules):
        """Test that the factory can create our test strategy."""
        # Test with default parameters
        strategy = StrategyFactory.create_strategy("DummyTestStrategy", portfolio)
        assert isinstance(strategy, DummyTestStrategy)
        assert strategy.portfolio == portfolio
        assert strategy.test_param == "default"

        # Test with custom parameters
        strategy = StrategyFactory.create_strategy(
            "DummyTestStrategy", portfolio, test_param="custom"
        )
        assert strategy.test_param == "custom"

    def test_strategy_not_found(self, portfolio, mock_strategy_modules):
        """Test that the factory raises an error for non-existent strategies."""
        with pytest.raises(ValueError) as excinfo:
            StrategyFactory.create_strategy("NonExistentStrategy", portfolio)

        # Check that the error message includes the available strategies
        assert "NonExistentStrategy" in str(excinfo.value)
        assert "Available strategies:" in str(excinfo.value)
        assert "SimpleTickerDataStrategy" in str(excinfo.value)
        assert "DummyTestStrategy" in str(excinfo.value)

    def test_get_all_strategy_classes(self, mock_strategy_modules):
        """Test the internal method to get all strategy classes."""
        strategy_classes = StrategyFactory._get_all_strategy_classes()

        # Convert to a list of class names for easier assertion
        class_names = [cls.__name__ for cls in strategy_classes]

        assert "SimpleTickerDataStrategy" in class_names
        assert "DummyTestStrategy" in class_names
        assert (
            "AbstractStrategy" not in class_names
        )  # Should not include the abstract base class
