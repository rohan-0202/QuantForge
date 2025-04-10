import inspect
import os
import importlib
from typing import Type

from quantforge.strategies.abstract_strategy import AbstractStrategy
from quantforge.qtypes.portfolio import Portfolio


class StrategyFactory:
    """
    Factory class for creating strategy instances.
    Dynamically discovers all strategy classes that inherit from AbstractStrategy.
    """

    @staticmethod
    def create_strategy(
        strategy_name: str, portfolio: Portfolio, **kwargs
    ) -> AbstractStrategy:
        """
        Create a strategy instance by name.

        Args:
            strategy_name: Name of the strategy class
            portfolio: Portfolio instance to be used by the strategy
            **kwargs: Additional parameters to pass to the strategy constructor

        Returns:
            An instance of the requested strategy

        Raises:
            ValueError: If the strategy is not found or doesn't inherit from AbstractStrategy
        """
        # Get all classes that inherit from AbstractStrategy
        strategy_classes = StrategyFactory._get_all_strategy_classes()

        # Find the strategy class by name
        strategy_class = None
        for cls in strategy_classes:
            if cls.__name__ == strategy_name:
                strategy_class = cls
                break

        if not strategy_class:
            raise ValueError(
                f"Strategy '{strategy_name}' not found. Available strategies: {', '.join([cls.__name__ for cls in strategy_classes])}"
            )

        # Create an instance of the strategy
        return strategy_class(portfolio=portfolio, **kwargs)

    @staticmethod
    def _get_all_strategy_classes() -> list[Type[AbstractStrategy]]:
        """
        Discover all classes that inherit from AbstractStrategy.

        Returns:
            A list of strategy classes
        """
        strategy_classes = []

        # Get the directory of the strategies package
        strategies_dir = os.path.dirname(os.path.abspath(__file__))

        # Import all modules in the strategies package
        for filename in os.listdir(strategies_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]  # Remove .py extension

                # Skip the abstract_strategy module
                if module_name == "abstract_strategy":
                    continue

                # Import the module
                try:
                    module_path = f"quantforge.strategies.{module_name}"
                    module = importlib.import_module(module_path)

                    # Find all classes in the module that inherit from AbstractStrategy
                    for _, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, AbstractStrategy)
                            and obj != AbstractStrategy
                        ):
                            strategy_classes.append(obj)
                except Exception as e:
                    print(f"Error importing module {module_name}: {e}")
                    continue

        return strategy_classes

    @staticmethod
    def get_available_strategies() -> list[str]:
        """
        Get a list of all available strategy names.

        Returns:
            A list of strategy names
        """
        strategy_classes = StrategyFactory._get_all_strategy_classes()
        return [cls.__name__ for cls in strategy_classes]


if __name__ == "__main__":
    print(StrategyFactory.get_available_strategies())
