from __future__ import annotations

from dataclasses import dataclass

from .contracts import Direction


@dataclass(frozen=True)
class Candle:
    open: float
    high: float
    low: float
    close: float
    close_time_ms: int


@dataclass(frozen=True)
class Opportunity:
    direction: Direction
    entry: float
    stop: float | None
    target: float | None
    estimated_holding_minutes: int
    confidence_score: float


def _sma(values: list[float], n: int) -> float:
    return sum(values[-n:]) / n


def _atr(candles: list[Candle], n: int = 14) -> float:
    recent = candles[-n:]
    return sum(c.high - c.low for c in recent) / len(recent)


def derive_opportunity(candles: list[Candle]) -> Opportunity:
    if len(candles) < 20:
        return Opportunity(Direction.HOLD, candles[-1].close if candles else 0.0, None, None, 120, 0.0)
    closes = [c.close for c in candles]
    fast = _sma(closes, 5)
    slow = _sma(closes, 20)
    atr = _atr(candles)
    entry = closes[-1]
    if entry <= 0 or atr <= 0:
        return Opportunity(Direction.HOLD, entry, None, None, 120, 0.0)
    spread = abs(fast - slow) / entry * 100
    confidence = min(100.0, round(50.0 + spread * 25.0, 2))
    stop_distance = min(entry * 0.05, atr * 1.5)
    if fast > slow:
        return Opportunity(Direction.BUY, entry, entry - stop_distance, entry + stop_distance * 2, 120, confidence)
    if fast < slow:
        return Opportunity(Direction.SELL, entry, entry + stop_distance, entry - stop_distance * 2, 120, confidence)
    return Opportunity(Direction.HOLD, entry, None, None, 120, confidence)
