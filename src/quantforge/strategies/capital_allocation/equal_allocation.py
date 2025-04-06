from quantforge.qtypes.tradeable_item import TradeableItem
from quantforge.strategies.trading_signal import TradingSignal
from quantforge.qtypes.ohlc import OHLCData
from quantforge.qtypes.portfolio import Portfolio


def equal_allocation(
    portfolio: Portfolio,
    buy_signals: dict[TradeableItem, TradingSignal],
    next_day_data: dict[TradeableItem, OHLCData],
) -> dict[TradeableItem, int]:
    """
    Allocates capital equally among buy signals based on available cash and next day's prices.
    """
    allocated_quantities: dict[TradeableItem, int] = {}
    buy_items = list(buy_signals.keys())

    if not buy_items:
        return {}

    available_cash = portfolio.cash
    if available_cash <= 0:
        return {}

    prices = {}
    valid_buy_items = []
    for item in buy_items:
        # Check using TradeableItem key
        if item in next_day_data:
            # Access using TradeableItem key
            price = next_day_data[item]["open"]
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
