from abc import ABC, abstractmethod
from typing import TypeAlias

import pandas as pd

from quantforge.strategies.data_requirement import DataRequirement
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.strategies.trading_signal import TradingSignal, TradingSignalType
from quantforge.qtypes.ohlc import OHLCData

TradeableItemData: TypeAlias = dict[DataRequirement, pd.DataFrame]
StrategyInputData: TypeAlias = dict[TradeableItem, TradeableItemData]


class AbstractStrategy(ABC):
    def __init__(self, name: str, portfolio: Portfolio):
        self._name = name
        self._portfolio = portfolio

    @property
    def name(self) -> str:
        return self._name

    @property
    def portfolio(self) -> Portfolio:
        return self._portfolio

    @abstractmethod
    def generate_signals(
        self, input_data: StrategyInputData
    ) -> dict[TradeableItem, TradingSignal]:
        pass

    @abstractmethod
    def get_data_requirements(self) -> list[DataRequirement]:
        pass

    @abstractmethod
    def execute_sell_signals(
        self, trading_signals: dict[TradeableItem, TradingSignal]
    ) -> None:
        pass

    @abstractmethod
    def execute_buy_signals(
        self, trading_signals: dict[TradeableItem, TradingSignal]
    ) -> None:
        pass

    @abstractmethod
    def allocate_capital(
        self,
        input_data: StrategyInputData,
        buy_signals: dict[TradeableItem, TradingSignal],
    ) -> dict[TradeableItem, int]:
        pass

    def execute(
        self, input_data: StrategyInputData, next_day_data: dict[str, OHLCData]
    ) -> None:
        # first ensure that we have all the data required to execute the strategy in the input_data
        # for each tradeable item in the portfolio, check that we have all the data requireed to execute the strategy
        for tradeable_item in self.portfolio.tradeable_items:
            if tradeable_item not in input_data:
                raise ValueError(f"Missing data for {tradeable_item}")
            for data_requirement in self.get_data_requirements():
                if data_requirement not in input_data[tradeable_item]:
                    raise ValueError(
                        f"Missing data for {data_requirement} for {tradeable_item}"
                    )

        # now we can execute the strategy, generate the trading signals
        trading_signals = self.generate_signals(input_data)

        self.execute_sell_signals(trading_signals)
        self.execute_buy_signals(trading_signals)


class SimpleTickerDataStrategy(AbstractStrategy):
    def __init__(self, portfolio: Portfolio):
        super().__init__(name="SimpleTickerDataStrategy", portfolio=portfolio)

    @abstractmethod
    def generate_signals(
        self, input_data: StrategyInputData
    ) -> dict[TradeableItem, TradingSignal]:
        pass

    def get_data_requirements(self) -> list[DataRequirement]:
        return [DataRequirement.TICKER]

    def execute_sell_signals(
        self, trading_signals: dict[TradeableItem, TradingSignal]
    ) -> None:
        # TODO: Implement the logic to execute the sell signals
        for tradeable_item, signal in trading_signals.items():
            if signal.signal_type == TradingSignalType.SELL:
                # TODO: Sell all positions for the tradeable item if they exist
                print(f"Selling all positions for {tradeable_item}")
                pass

    def execute_buy_signals(
        self, trading_signals: dict[TradeableItem, TradingSignal]
    ) -> None:
        # TODO: Implement the logic to execute the buy signals
        pass

    def allocate_capital(
        self,
        input_data: StrategyInputData,
        buy_signals: dict[TradeableItem, TradingSignal],
    ) -> dict[TradeableItem, int]:
        # TODO: Implement the logic to allocate the capital to the buy signals
        pass
