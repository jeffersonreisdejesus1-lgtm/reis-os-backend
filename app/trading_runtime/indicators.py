from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt

from .strategy import Candle

CALCULATION_VERSION = "trading-native-indicators-v1"


@dataclass(frozen=True)
class IndicatorSnapshot:
    timeframe: str
    observed_at: datetime
    source_snapshot_ref: str
    calculation_version: str
    sma_fast: float
    sma_slow: float
    ema_fast: float
    ema_slow: float
    rsi: float
    macd: float
    macd_signal: float
    atr: float
    bollinger_mid: float
    bollinger_upper: float
    bollinger_lower: float
    realized_volatility: float
    support: float
    resistance: float


def _sma(values: list[float], period: int) -> float:
    if len(values) < period:
        raise ValueError("insufficient samples")
    return sum(values[-period:]) / period


def _ema_series(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        raise ValueError("insufficient samples")
    alpha = 2.0 / (period + 1.0)
    seed = sum(values[:period]) / period
    result = [seed]
    for value in values[period:]:
        result.append(alpha * value + (1.0 - alpha) * result[-1])
    return result


def _rsi(values: list[float], period: int = 14) -> float:
    if len(values) <= period:
        raise ValueError("insufficient samples")
    deltas = [b - a for a, b in zip(values, values[1:])]
    recent = deltas[-period:]
    gains = sum(max(delta, 0.0) for delta in recent) / period
    losses = sum(max(-delta, 0.0) for delta in recent) / period
    if losses == 0:
        return 100.0 if gains > 0 else 50.0
    rs = gains / losses
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(candles: list[Candle], period: int = 14) -> float:
    if len(candles) <= period:
        raise ValueError("insufficient samples")
    trs: list[float] = []
    for previous, current in zip(candles, candles[1:]):
        trs.append(max(current.high - current.low, abs(current.high - previous.close), abs(current.low - previous.close)))
    return sum(trs[-period:]) / period


def _stddev(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def calculate_indicators(
    candles: list[Candle],
    *,
    timeframe: str,
    source_snapshot_ref: str,
    observed_at: datetime | None = None,
) -> IndicatorSnapshot:
    if len(candles) < 35:
        raise ValueError("at least 35 closed candles are required")
    closes = [c.close for c in candles]
    ema12 = _ema_series(closes, 12)
    ema26 = _ema_series(closes, 26)
    aligned = min(len(ema12), len(ema26))
    macd_series = [a - b for a, b in zip(ema12[-aligned:], ema26[-aligned:])]
    macd = macd_series[-1]
    macd_signal = _ema_series(macd_series, 9)[-1] if len(macd_series) >= 9 else macd
    bb_window = closes[-20:]
    bb_mid = sum(bb_window) / len(bb_window)
    bb_sigma = _stddev(bb_window)
    returns = [(b / a) - 1.0 for a, b in zip(closes[-21:-1], closes[-20:]) if a > 0]
    recent = candles[-20:]
    return IndicatorSnapshot(
        timeframe=timeframe,
        observed_at=observed_at or datetime.now(timezone.utc),
        source_snapshot_ref=source_snapshot_ref,
        calculation_version=CALCULATION_VERSION,
        sma_fast=_sma(closes, 5),
        sma_slow=_sma(closes, 20),
        ema_fast=ema12[-1],
        ema_slow=ema26[-1],
        rsi=_rsi(closes),
        macd=macd,
        macd_signal=macd_signal,
        atr=_atr(candles),
        bollinger_mid=bb_mid,
        bollinger_upper=bb_mid + 2.0 * bb_sigma,
        bollinger_lower=bb_mid - 2.0 * bb_sigma,
        realized_volatility=_stddev(returns),
        support=min(c.low for c in recent),
        resistance=max(c.high for c in recent),
    )
