import pandas as pd

from quantforge.qtypes.portfolio import Portfolio
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.ohlc import OHLCData
from quantforge.qtypes.transaction import Transaction
from quantforge.strategies.abstract_strategy import AbstractStrategy, StrategyInputData
from quantforge.strategies.data_requirement import DataRequirement
from quantforge.strategies.trading_signal import TradingSignal, TradingSignalType
from quantforge.strategies.utils import calculate_rsi


class RsiStrategy(AbstractStrategy):
    """A trading strategy based on the Relative Strength Index (RSI).

    Generates BUY signals when RSI crosses below an oversold threshold
    and SELL signals when RSI crosses above an overbought threshold.
    """

    def __init__(
        self,
        portfolio: Portfolio,
        rsi_window: int = 14,
        oversold_threshold: float = 30.0,
        overbought_threshold: float = 70.0,
    ):
        super().__init__(name="RsiStrategy", portfolio=portfolio)
        if not isinstance(rsi_window, int) or rsi_window <= 1:
            raise ValueError("RSI window must be an integer greater than 1.")
        if not (0 < oversold_threshold < 100):
            raise ValueError("Oversold threshold must be between 0 and 100.")
        if not (0 < overbought_threshold < 100):
            raise ValueError("Overbought threshold must be between 0 and 100.")
        if oversold_threshold >= overbought_threshold:
            raise ValueError("Oversold threshold must be less than overbought threshold.")
            
        self.rsi_window = rsi_window
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        print(f"RsiStrategy initialized with window={self.rsi_window}, oversold={self.oversold_threshold}, overbought={self.overbought_threshold}")

    def get_data_requirements(self) -> list[DataRequirement]:
        """Specifies that this strategy requires TICKER data."""
        return [DataRequirement.TICKER]

    def generate_signals(
        self, input_data: StrategyInputData
    ) -> dict[TradeableItem, TradingSignal]:
        """Generates BUY/SELL signals based on RSI thresholds."""
        signals = {}
        for item, data in input_data.items():
            ticker_data = data.get(DataRequirement.TICKER)
            if ticker_data is None or ticker_data.empty or 'close' not in ticker_data.columns:
                print(f"Warning: Missing or invalid ticker data for {item} in RsiStrategy.")
                continue

            close_prices = ticker_data['close']
            if len(close_prices) < self.rsi_window:
                # Not enough data to calculate RSI reliably
                continue

            # Calculate RSI
            rsi_values = calculate_rsi(close_prices, window=self.rsi_window)
            
            if rsi_values.empty:
                continue
                
            latest_rsi = rsi_values.iloc[-1]

            if pd.isna(latest_rsi):
                 continue # Skip if RSI couldn't be calculated for the latest point

            # Generate signals based on thresholds
            # Basic version: Signal if threshold is crossed. 
            # More advanced: Could check for *crossing* the threshold (e.g., was above, now below)
            if latest_rsi < self.oversold_threshold:
                signals[item] = TradingSignal(TradingSignalType.BUY, signal_strength=1.0)
            elif latest_rsi > self.overbought_threshold:
                # Only generate sell signal if we actually hold the position
                # This prevents trying to sell something we don't own based solely on RSI > 70
                if self.portfolio.has_position(item):
                     signals[item] = TradingSignal(TradingSignalType.SELL, signal_strength=-1.0)

        return signals

    def allocate_capital(
        self, 
        buy_signals: dict[TradeableItem, TradingSignal],
        next_day_data: dict[TradeableItem, OHLCData]
    ) -> dict[TradeableItem, int]:
        """Allocates capital equally among valid buy signals."""
        allocated_quantities: dict[TradeableItem, int] = {}
        buy_items = list(buy_signals.keys())

        if not buy_items:
            return {}

        available_cash = self.portfolio.cash
        if available_cash <= 0:
            return {}

        # Filter for items with valid price data for the next day
        prices = {}
        valid_buy_items = []
        for item in buy_items:
            if item in next_day_data:
                # Access using attribute
                price = next_day_data[item].open 
                if price > 0:
                    prices[item] = price
                    valid_buy_items.append(item)
                else:
                    print(f"Warning: Skipping allocation for {item} due to non-positive price.")
            else:
                 print(f"Warning: Skipping allocation for {item} due to missing next day price data.")


        if not valid_buy_items:
            return {}

        num_valid_items = len(valid_buy_items)
        cash_per_item = available_cash / num_valid_items

        # Calculate desired quantities, ensuring total cost doesn't exceed available cash
        total_cost_estimate = 0
        temp_allocations = {}
        for item in valid_buy_items:
            price = prices[item]
            quantity = int(cash_per_item // price) # Floor division for whole shares
            if quantity > 0:
                cost_for_item = quantity * price
                # Check if adding this item exceeds total cash (simple approach)
                if total_cost_estimate + cost_for_item <= available_cash:
                    temp_allocations[item] = quantity
                    total_cost_estimate += cost_for_item
                # else: Not enough cash left for this allocation in this simple model

        allocated_quantities = temp_allocations
        print(f"Allocated capital: {allocated_quantities}")
        return allocated_quantities

    def execute_buy_signals(
        self,
        allocated_quantities: dict[TradeableItem, int],
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> None:
        """Executes buy orders based on allocated quantities using the next day's open price."""
        for tradeable_item, quantity in allocated_quantities.items():
            if quantity <= 0:
                continue # Should not happen based on allocation logic, but good practice

            if tradeable_item not in next_day_data:
                print(f"Warning: Missing next day price data for {tradeable_item}, cannot execute buy.")
                continue
            
            # Access using attribute
            next_day_price_info = next_day_data[tradeable_item]
            # Access using attribute
            buy_price = next_day_price_info.open
            # Access using attribute
            buy_date = next_day_price_info.date

            if buy_price <= 0:
                print(f"Warning: Invalid buy price ({buy_price}) for {tradeable_item}, cannot execute buy.")
                continue

            transaction = Transaction(
                tradeable_item=tradeable_item,
                quantity=quantity,
                price=buy_price,
                date=buy_date,
                transaction_cost=0.0, # Assuming no transaction costs for simplicity
            )

            # Attempt to open the position
            try:
                if self.portfolio.can_trade(transaction):
                    self.portfolio.open_position(transaction)
                    print(f"Executed BUY: {quantity} of {tradeable_item} @ {buy_price}")
                else:
                    print(f"Could not execute BUY for {tradeable_item}: can_trade returned false (e.g., insufficient funds).")
            except ValueError as e:
                 print(f"Error executing BUY for {tradeable_item}: {e}")
            # Consider more specific error handling

    def execute_sell_signals(
        self,
        sell_signals: dict[TradeableItem, TradingSignal],
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> None:
        """Executes sell orders for signaled items using the next day's open price."""
        for tradeable_item, signal in sell_signals.items():
            # Check if we have open positions for this item
            positions_to_close = self.portfolio.get_open_positions_by_item(tradeable_item)
            if not positions_to_close:
                # This check might be redundant if generate_signals already checks has_position
                # print(f"Sell signal for {tradeable_item}, but no open position found.")
                continue 

            if tradeable_item not in next_day_data:
                print(f"Warning: Missing next day price data for {tradeable_item}, cannot execute sell.")
                continue

            # Access using attribute
            next_day_price_info = next_day_data[tradeable_item]
            # Access using attribute
            sell_price = next_day_price_info.open
            # Access using attribute
            sell_date = next_day_price_info.date

            if sell_price <= 0:
                 print(f"Warning: Invalid sell price ({sell_price}) for {tradeable_item}, cannot execute sell.")
                 continue

            # Close all open positions for this item
            for position in list(positions_to_close): # Iterate over a copy
                try:
                    close_transaction = Transaction(
                        tradeable_item=tradeable_item,
                        quantity=-position.open_transaction.quantity, # Sell the exact quantity bought
                        price=sell_price,
                        date=sell_date,
                        transaction_cost=0.0, # Assuming no transaction costs
                    )
                    self.portfolio.close_position(position, close_transaction)
                    print(f"Executed SELL: {-close_transaction.quantity} of {tradeable_item} @ {sell_price}")
                except ValueError as e:
                    print(f"Error executing SELL for position {position}: {e}")
                # Consider more specific error handling 