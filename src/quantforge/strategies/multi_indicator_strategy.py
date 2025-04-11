import pandas as pd

from quantforge.strategies.abstract_strategy import AbstractStrategy, StrategyInputData
from quantforge.qtypes.portfolio import Portfolio
from quantforge.strategies.trading_signal import TradingSignal, TradingSignalType
from quantforge.strategies.data_requirement import DataRequirement
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.ohlc import OHLCData
from quantforge.strategies.capital_allocation.equal_allocation import equal_allocation

# Import signal calculation functions and parameters
from quantforge.signals.rsi.rsi import calculate_rsi
from quantforge.signals.rsi.rsi_params import RsiParams
from quantforge.signals.macd.macd import calculate_macd
from quantforge.signals.macd.macd_params import MacdParams
import ta 


class MultiIndicatorStrategy(AbstractStrategy):
    """
    A strategy that combines RSI, MACD, and OBV signals.

    - Buy Signal: RSI not overbought AND MACD bullish crossover AND OBV rising.
    - Sell Signal: RSI not oversold AND MACD bearish crossover
                   OR RSI is overbought.
    """

    def __init__(self, portfolio: Portfolio, **kwargs):
        super().__init__(name="MultiIndicatorStrategy", portfolio=portfolio, **kwargs)
        # Use default parameters if not provided in kwargs
        self._rsi_params = self.params.get("rsi_params", RsiParams.default())
        self._macd_params = self.params.get("macd_params", MacdParams.default())

        # Determine lookback period needed (Ensure enough for OBV comparison)
        self._lookback_days = max(
            self._rsi_params.rsi_period,
            self._macd_params.slow_period + self._macd_params.signal_period, # MACD needs more history
            3 # OBV needs at least 3 points for a comparison (current, previous) + calculation buffer
        ) + 5 # Add a small buffer

    def get_data_requirements(self) -> tuple[list[DataRequirement], int]:
        """Specifies that TICKER data is required for the lookback period."""
        return [DataRequirement.TICKER], self._lookback_days

    def generate_signals(
        self, input_data: StrategyInputData
    ) -> dict[TradeableItem, TradingSignal]:
        """Generates trading signals based on RSI, MACD, and OBV indicators."""
        signals = {}
        for item, data in input_data.items():
            ticker_data = data.get(DataRequirement.TICKER)

            # Ensure we have the required ticker data
            if ticker_data is None or ticker_data.empty:
                # print(f"Warning: Missing ticker data for {item} in MultiIndicatorStrategy.")
                continue

            # Ensure required columns are present
            if "close" not in ticker_data.columns or "volume" not in ticker_data.columns:
                # print(f"Warning: Missing 'close' or 'volume' for {item} in MultiIndicatorStrategy.")
                continue

            close_prices = ticker_data["close"]
            volume = ticker_data["volume"]

            # --- Calculate Indicators --- (Ensure enough data)
            if len(close_prices) < self._lookback_days:
                 # print(f"Warning: Insufficient data length for {item} in MultiIndicatorStrategy.")
                 continue # Skip if not enough data for lookback

            rsi_result = calculate_rsi(close_prices, self._rsi_params)
            macd_result = calculate_macd(close_prices, self._macd_params)

            # Calculate OBV Series directly
            obv_indicator = ta.volume.OnBalanceVolumeIndicator(
                close=close_prices, volume=volume, fillna=False
            )
            obv_series = obv_indicator.on_balance_volume()

            # --- Signal Logic ---
            # Ensure all indicators are valid before proceeding
            # Check OBV series validity as well
            if (not rsi_result.valid or not macd_result.valid or
                obv_series.empty or obv_series.isna().all() or len(obv_series) < 2 or
                pd.isna(obv_series.iloc[-1]) or pd.isna(obv_series.iloc[-2])):
                 # print(f"Warning: Invalid indicator result or insufficient OBV data for {item} in MultiIndicatorStrategy.")
                 continue

            # Default to HOLD
            signal_type = TradingSignalType.HOLD

            # --- OBV Trend Check ---
            # Simple check: Is the latest OBV higher than the previous one?
            is_obv_rising = obv_series.iloc[-1] > obv_series.iloc[-2]

            # --- Buy Conditions --- #
            is_macd_bullish = macd_result.histogram > 0
            is_rsi_not_overbought = not rsi_result.overbought

            # Add OBV confirmation to buy signal
            if is_macd_bullish and is_rsi_not_overbought and is_obv_rising:
                signal_type = TradingSignalType.BUY

            # --- Sell Conditions --- #
            is_macd_bearish = macd_result.histogram < 0
            is_rsi_not_oversold = not rsi_result.oversold

            if rsi_result.overbought:
                signal_type = TradingSignalType.SELL
            elif is_macd_bearish and is_rsi_not_oversold:
                 signal_type = TradingSignalType.SELL


            # Create signal if not HOLD
            if signal_type != TradingSignalType.HOLD:
                # Simple signal strength, could be refined
                strength = 1.0 if signal_type == TradingSignalType.BUY else -1.0
                signals[item] = TradingSignal(signal_type, signal_strength=strength)

        return signals

    def allocate_capital(
        self,
        buy_signals: dict[TradeableItem, TradingSignal],
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> dict[TradeableItem, int]:
        """Allocates capital equally among buy signals."""
        return equal_allocation(self.portfolio, buy_signals, next_day_data) 