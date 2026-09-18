from app.trading_runtime.contracts import Direction
from app.trading_runtime.strategy import Candle, derive_opportunity


def candles(prices: list[float]) -> list[Candle]:
    result: list[Candle] = []
    for index, price in enumerate(prices):
        result.append(Candle(price - 0.5, price + 1.0, price - 1.0, price, index))
    return result


def test_uptrend_generates_bounded_buy_opportunity() -> None:
    opportunity = derive_opportunity(candles([100 + i for i in range(25)]))
    assert opportunity.direction is Direction.BUY
    assert opportunity.stop is not None and opportunity.stop < opportunity.entry
    assert opportunity.target is not None and opportunity.target > opportunity.entry
    assert opportunity.estimated_holding_minutes >= 60


def test_downtrend_generates_bounded_sell_opportunity() -> None:
    opportunity = derive_opportunity(candles([150 - i for i in range(25)]))
    assert opportunity.direction is Direction.SELL
    assert opportunity.stop is not None and opportunity.stop > opportunity.entry
    assert opportunity.target is not None and opportunity.target < opportunity.entry


def test_insufficient_history_holds() -> None:
    opportunity = derive_opportunity(candles([100, 101, 102]))
    assert opportunity.direction is Direction.HOLD
