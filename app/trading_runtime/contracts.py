from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class HoldReason(str, Enum):
    NO_EDGE = "NO_EDGE"
    DATA = "HOLD_DATA"
    COST = "HOLD_COST"
    MODEL = "HOLD_MODEL"
    RISK = "HOLD_RISK"
    DRAWDOWN = "HOLD_DRAWDOWN"
    ANOMALY = "HOLD_ANOMALY"
    PROVIDER = "HOLD_PROVIDER"
    SYSTEM_STOP = "SYSTEM_STOP"


@dataclass(frozen=True)
class MarketSnapshot:
    asset: str
    price: float
    market_data_timestamp: datetime
    received_at: datetime
    data_cutoff: datetime
    source: str = "BINANCE_PUBLIC"


@dataclass(frozen=True)
class Signal:
    signal_id: str
    run_id: str
    asset: str
    direction: Direction
    estimated_holding_minutes: int | None
    signal_expires_at: datetime
    entry_price: float | None
    target_price: float | None
    stop_price: float | None
    gross_expected_return_pct: float | None
    estimated_trading_cost_pct: float
    net_expected_return_pct: float | None
    position_size: float
    account_risk_pct: float
    confidence_score: float | None
    data_cutoff: datetime
    market_data_timestamp: datetime
    evidence_ref: str
    hold_reason: HoldReason | None = None
