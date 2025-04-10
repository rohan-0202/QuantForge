from quantforge.strategies.abstract_strategy import AbstractStrategy, StrategyInputData
from quantforge.qtypes.portfolio import Portfolio
from quantforge.strategies.trading_signal import TradingSignal, TradingSignalType
from quantforge.strategies.data_requirement import DataRequirement
from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.qtypes.ohlc import OHLCData
from quantforge.strategies.capital_allocation.equal_allocation import equal_allocation


class SimpleTickerDataStrategy(AbstractStrategy):
    """
    A simple strategy that generates signals based on the last close price of a ticker data.

    This strategy is not really meant to be used in practice, but rather to test the framework.
    """

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
            if "close" not in ticker_data.columns:
                continue

            first_close = ticker_data["close"].iloc[0]
            last_close = ticker_data["close"].iloc[-1]

            if last_close > first_close:
                signals[item] = TradingSignal(
                    TradingSignalType.BUY, signal_strength=1.0
                )
            elif last_close < first_close:
                signals[item] = TradingSignal(
                    TradingSignalType.SELL, signal_strength=-1.0
                )
            # else: No HOLD signal for simplicity in this basic strategy
            # signals[item] = TradingSignal(TradingSignalType.HOLD, signal_strength=0.0)

        return signals

    def get_data_requirements(self) -> tuple[list[DataRequirement], int]:
        return [DataRequirement.TICKER], 1

    def allocate_capital(
        self,
        buy_signals: dict[TradeableItem, TradingSignal],
        next_day_data: dict[TradeableItem, OHLCData],
    ) -> dict[TradeableItem, int]:
        """Allocates capital equally among buy signals based on available cash and next day's prices."""
        return equal_allocation(self.portfolio, buy_signals, next_day_data)
