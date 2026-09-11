from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import Direction, Signal
from .strategy import Candle


class PaperResult(str, Enum):
    TARGET = "TARGET"
    STOP = "STOP"
    TIMEOUT = "TIMEOUT"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_ENTERED = "NOT_ENTERED"


@dataclass(frozen=True)
class PaperOutcome:
    result: PaperResult
    exit_price: float | None
    candles_observed: int


def simulate(signal: Signal, future_candles: list[Candle]) -> PaperOutcome:
    if signal.direction is Direction.HOLD or signal.entry_price is None:
        return PaperOutcome(PaperResult.NOT_ENTERED, None, 0)
    if signal.target_price is None or signal.stop_price is None:
        return PaperOutcome(PaperResult.NOT_ENTERED, None, 0)
    entered = False
    for index, candle in enumerate(future_candles, start=1):
        if not entered:
            entered = candle.low <= signal.entry_price <= candle.high
            if not entered:
                continue
        if signal.direction is Direction.BUY:
            hit_target = candle.high >= signal.target_price
            hit_stop = candle.low <= signal.stop_price
        else:
            hit_target = candle.low <= signal.target_price
            hit_stop = candle.high >= signal.stop_price
        if hit_target and hit_stop:
            return PaperOutcome(PaperResult.AMBIGUOUS, None, index)
        if hit_stop:
            return PaperOutcome(PaperResult.STOP, signal.stop_price, index)
        if hit_target:
            return PaperOutcome(PaperResult.TARGET, signal.target_price, index)
    if not entered:
        return PaperOutcome(PaperResult.NOT_ENTERED, None, len(future_candles))
    return PaperOutcome(PaperResult.TIMEOUT, future_candles[-1].close if future_candles else None, len(future_candles))
