from abc import ABC, abstractmethod
from typing import TypeAlias

import pandas as pd

from quantforge.strategies.data_requirement import DataRequirement
from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.strategies.trading_signal import TradingSignal, TradingSignalType
from quantforge.qtypes.ohlc import OHLCData
from quantforge.qtypes.transaction import Transaction

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

    def execute_sell_signals(
        self,
        sell_signals: dict[TradeableItem, TradingSignal],
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> None:
        """Executes sell signals using the next day's open price."""
        for tradeable_item, _ in sell_signals.items():
            positions_to_close = self.portfolio.get_open_positions_by_item(
                tradeable_item
            )
            if not positions_to_close:
                continue

            # Check for missing data using the TradeableItem key
            if tradeable_item not in next_day_data:
                print(
                    f"Warning: Missing next day price data for {tradeable_item}, cannot execute sell."
                )
                continue

            # Access using TradeableItem key
            next_day_price_info = next_day_data[tradeable_item]
            sell_price = next_day_price_info.open
            sell_date = next_day_price_info.date

            for position in list(positions_to_close):
                close_transaction = Transaction(
                    tradeable_item=tradeable_item,
                    quantity=-position.open_transaction.quantity,
                    price=sell_price,
                    date=sell_date,
                    transaction_cost=0.0,
                )
                # Let errors from close_position propagate
                self.portfolio.close_position(position, close_transaction)

    def execute_buy_signals(
        self,
        allocated_quantities: dict[TradeableItem, int],
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> None:
        """Executes buy signals based on allocated quantities using the next day's open price."""
        for tradeable_item, quantity in allocated_quantities.items():
            if quantity <= 0:
                continue

            # Specific check for missing data using TradeableItem key
            if tradeable_item not in next_day_data:
                print(
                    f"Warning: Missing next day price data for {tradeable_item}, cannot execute buy."
                )
                continue

            # Access using TradeableItem key
            next_day_price_info = next_day_data[tradeable_item]
            buy_price = next_day_price_info.open
            buy_date = next_day_price_info.date

            transaction = Transaction(
                tradeable_item=tradeable_item,
                quantity=quantity,
                price=buy_price,
                date=buy_date,
                transaction_cost=0.0,
            )

            # Let errors from open_position propagate
            if self.portfolio.can_trade(transaction):
                self.portfolio.open_position(transaction)

    @abstractmethod
    def allocate_capital(
        self,
        buy_signals: dict[TradeableItem, TradingSignal],
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> dict[TradeableItem, int]:
        pass

    def execute(
        self,
        input_data: StrategyInputData,
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> None:
        """Executes the strategy: validates data, generates signals, allocates capital, and executes trades."""
        # --- Data Validation ---
        required_data_valid = True
        # Check data requirements only for items relevant to the strategy (in input_data)
        # or potentially all allowed items if the strategy needs broader context (decision: check input_data keys)
        items_to_check = list(input_data.keys())
        # Alternatively: items_to_check = self.portfolio.allowed_tradeable_items

        for tradeable_item in items_to_check:
            if tradeable_item not in input_data:
                # This case might be handled depending on strategy logic - skipping check if not in input
                continue
            for data_requirement in self.get_data_requirements():
                if (
                    data_requirement not in input_data[tradeable_item]
                    or input_data[tradeable_item][data_requirement] is None
                    or input_data[tradeable_item][data_requirement].empty
                ):
                    required_data_valid = False
                    # Optionally break or collect all errors
                    break  # Stop checking this item if data is missing
            if not required_data_valid:
                break  # Stop checking other items if one failed validation

        if not required_data_valid:
            print(
                f"Strategy {self.name} execution halted due to missing required data."
            )
            return  # Stop execution if data is missing

        # --- Signal Generation ---
        trading_signals = self.generate_signals(input_data)
        if not trading_signals:
            return

        # --- Signal Separation ---
        sell_signals = {
            item: sig
            for item, sig in trading_signals.items()
            if sig.signal_type == TradingSignalType.SELL
        }
        buy_signals = {
            item: sig
            for item, sig in trading_signals.items()
            if sig.signal_type == TradingSignalType.BUY
        }

        # --- Execute Sells ---
        if sell_signals:
            self.execute_sell_signals(sell_signals, next_day_data)

        # --- Allocate Capital for Buys ---
        allocated_quantities = {}
        if buy_signals:
            allocated_quantities = self.allocate_capital(buy_signals, next_day_data)

        # --- Execute Buys ---
        if allocated_quantities:
            self.execute_buy_signals(allocated_quantities, next_day_data)

        print(
            f"Strategy {self.name} execution complete. Final Cash: {self.portfolio.cash:.2f}"
        )
