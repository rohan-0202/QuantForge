from abc import ABC, abstractmethod
from typing import TypeAlias
from datetime import date

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

    @abstractmethod
    def execute_sell_signals(
        self,
        sell_signals: dict[TradeableItem, TradingSignal],
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> None:
        pass

    @abstractmethod
    def execute_buy_signals(
        self,
        allocated_quantities: dict[TradeableItem, int],
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> None:
        pass

    @abstractmethod
    def allocate_capital(
        self,
        buy_signals: dict[TradeableItem, TradingSignal],
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> dict[TradeableItem, int]:
        pass

    def execute(
        self, input_data: StrategyInputData, next_day_data: dict[TradeableItem, OHLCData]
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
                if data_requirement not in input_data[tradeable_item] or input_data[tradeable_item][data_requirement] is None or input_data[tradeable_item][data_requirement].empty:
                    required_data_valid = False
                    # Optionally break or collect all errors
                    break # Stop checking this item if data is missing
            if not required_data_valid:
                break # Stop checking other items if one failed validation

        if not required_data_valid:
             print(f"Strategy {self.name} execution halted due to missing required data.")
             return # Stop execution if data is missing
        

        # --- Signal Generation ---
        trading_signals = self.generate_signals(input_data)
        if not trading_signals:
            return

        # --- Signal Separation ---
        sell_signals = {item: sig for item, sig in trading_signals.items() if sig.signal_type == TradingSignalType.SELL}
        buy_signals = {item: sig for item, sig in trading_signals.items() if sig.signal_type == TradingSignalType.BUY}

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


        print(f"Strategy {self.name} execution complete. Final Cash: {self.portfolio.cash:.2f}")


class SimpleTickerDataStrategy(AbstractStrategy):
    def __init__(self, portfolio: Portfolio):
        super().__init__(name="SimpleTickerDataStrategy", portfolio=portfolio)

    def generate_signals(
        self, input_data: StrategyInputData
    ) -> dict[TradeableItem, TradingSignal]:
        """
        Generates simple signals: BUY if last close > first close, SELL otherwise.
        """
        signals = {}
        for item, data in input_data.items():
            ticker_data = data.get(DataRequirement.TICKER)
            if ticker_data is None or ticker_data.empty:
                continue

            if len(ticker_data) < 2:
                 continue

            # Assuming the DataFrame has a 'close' column
            if 'close' not in ticker_data.columns:
                 continue

            first_close = ticker_data['close'].iloc[0]
            last_close = ticker_data['close'].iloc[-1]

            if last_close > first_close:
                signals[item] = TradingSignal(TradingSignalType.BUY, signal_strength=1.0)
            elif last_close < first_close:
                 signals[item] = TradingSignal(TradingSignalType.SELL, signal_strength=-1.0)
            # else: No HOLD signal for simplicity in this basic strategy
                 # signals[item] = TradingSignal(TradingSignalType.HOLD, signal_strength=0.0)

        return signals

    def get_data_requirements(self) -> list[DataRequirement]:
        return [DataRequirement.TICKER]

    def execute_sell_signals(
        self,
        sell_signals: dict[TradeableItem, TradingSignal],
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> None:
        """Executes sell signals using the next day's open price."""
        for tradeable_item, signal in sell_signals.items():
            positions_to_close = self.portfolio.get_open_positions_by_item(tradeable_item)
            if not positions_to_close:
                continue

            # Check for missing data using the TradeableItem key
            if tradeable_item not in next_day_data:
                print(f"Warning: Missing next day price data for {tradeable_item}, cannot execute sell.")
                continue

            # Access using TradeableItem key
            next_day_price_info = next_day_data[tradeable_item]
            sell_price = next_day_price_info['open']
            sell_date = next_day_price_info['date']

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
                print(f"Warning: Missing next day price data for {tradeable_item}, cannot execute buy.")
                continue
            
            # Access using TradeableItem key
            next_day_price_info = next_day_data[tradeable_item]
            buy_price = next_day_price_info['open']
            buy_date = next_day_price_info['date']

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

    def allocate_capital(
        self,
        buy_signals: dict[TradeableItem, TradingSignal],
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> dict[TradeableItem, int]:
        """Allocates capital equally among buy signals based on available cash and next day's prices."""
        allocated_quantities: dict[TradeableItem, int] = {}
        buy_items = list(buy_signals.keys())

        if not buy_items:
            return {}

        available_cash = self.portfolio.cash
        if available_cash <= 0:
             return {}

        prices = {}
        valid_buy_items = []
        for item in buy_items:
             # Check using TradeableItem key
             if item in next_day_data:
                 # Access using TradeableItem key
                 price = next_day_data[item]['open']
                 if price > 0:
                     prices[item] = price
                     valid_buy_items.append(item)

        if not valid_buy_items:
             return {}

        num_valid_items = len(valid_buy_items)
        if num_valid_items == 0:
            return {}
        cash_per_item = available_cash / num_valid_items

        total_cost_estimate = 0
        temp_allocations = {}

        for item in valid_buy_items:
            price = prices[item]
            quantity = int(cash_per_item // price)
            if quantity > 0:
                cost_for_item = quantity * price
                if total_cost_estimate + cost_for_item <= available_cash:
                    temp_allocations[item] = quantity
                    total_cost_estimate += cost_for_item

        allocated_quantities = temp_allocations

        return allocated_quantities
