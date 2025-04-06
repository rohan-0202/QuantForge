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
        next_day_data: dict[str, OHLCData],
    ) -> None:
        """Executes sell signals using the next day's open price."""
        for tradeable_item, signal in sell_signals.items():
            positions_to_close = self.portfolio._open_positions_by_tradeable_item.get(tradeable_item, [])
            if positions_to_close:
                # Specific check for missing data
                if tradeable_item.id not in next_day_data:
                    print(f"Warning: Missing next day price data for {tradeable_item.id}, cannot execute sell.")
                    continue
                
                # Removed the broad try...except block here
                next_day_price_info = next_day_data[tradeable_item.id]
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
        next_day_data: dict[str, OHLCData],
    ) -> None:
        """Executes buy signals based on allocated quantities using the next day's open price."""
        for tradeable_item, quantity in allocated_quantities.items():
            if quantity <= 0:
                continue

            # Specific check for missing data
            if tradeable_item.id not in next_day_data:
                print(f"Warning: Missing next day price data for {tradeable_item.id}, cannot execute buy.")
                continue
            
            # Removed the broad try...except block here
            next_day_price_info = next_day_data[tradeable_item.id]
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
        next_day_data: dict[str, OHLCData],
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
             if item.id in next_day_data:
                 # Use dictionary key access
                 price = next_day_data[item.id]['open']
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

    def execute(
        self, input_data: StrategyInputData, next_day_data: dict[str, OHLCData]
    ) -> None:
        """Overrides base execute to pass next_day_data to relevant methods."""
        # --- Data Validation ---
        required_data_valid = True
        # Check data requirements only for items we might trade (in portfolio's allowed list)
        for tradeable_item in self.portfolio.allowed_tradeable_items:
            # It's okay if input_data doesn't contain *every* allowed item,
            # but if it *is* present, it must have the required data types.
            if tradeable_item in input_data:
                for data_requirement in self.get_data_requirements():
                    if data_requirement not in input_data[tradeable_item]:
                        required_data_valid = False
                        # Decide if you want to stop execution or just skip this item
                        # For now, let's log error and prevent execution

        if not required_data_valid:
             print(f"Strategy {self.name} execution halted due to missing required data.") # Basic print
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
        if buy_signals:
            allocated_quantities = self.allocate_capital(buy_signals, next_day_data)
        else:
            allocated_quantities = {} # No buys, so no allocation needed


        # --- Execute Buys ---
        if allocated_quantities:
            self.execute_buy_signals(allocated_quantities, next_day_data)


        print(f"Strategy {self.name} execution complete. Final Cash: {self.portfolio.cash:.2f}") # Basic print
