from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .contracts import Direction, HoldReason, MarketSnapshot, Signal
from .risk import RiskPolicy


@dataclass
class TradingRuntime:
    risk_policy: RiskPolicy = RiskPolicy()
    max_data_age_seconds: int = 120
    assumed_trading_cost_pct: float = 0.20

    def evaluate(
        self,
        snapshot: MarketSnapshot,
        *,
        capital: float,
        technical_stop_price: float | None,
        target_price: float | None,
        estimated_holding_minutes: int = 120,
        confidence_score: float | None = None,
        forced_hold_reason: HoldReason | None = None,
    ) -> Signal:
        now = datetime.now(timezone.utc)
        age = (now - snapshot.market_data_timestamp).total_seconds()
        run_id = str(uuid4())
        signal_id = str(uuid4())
        expires_at = now + timedelta(minutes=max(30, estimated_holding_minutes // 2))

        if forced_hold_reason is not None:
            return self._hold(snapshot, run_id, signal_id, expires_at, forced_hold_reason)

        if age < 0 or age > self.max_data_age_seconds:
            return self._hold(snapshot, run_id, signal_id, expires_at, HoldReason.DATA)

        if technical_stop_price is None or target_price is None:
            return self._hold(snapshot, run_id, signal_id, expires_at, HoldReason.NO_EDGE)

        entry = snapshot.price
        if entry <= 0:
            return self._hold(snapshot, run_id, signal_id, expires_at, HoldReason.DATA)

        if target_price > entry and technical_stop_price < entry:
            direction = Direction.BUY
            gross = (target_price - entry) / entry * 100
        elif target_price < entry and technical_stop_price > entry:
            direction = Direction.SELL
            gross = (entry - target_price) / entry * 100
        else:
            return self._hold(snapshot, run_id, signal_id, expires_at, HoldReason.NO_EDGE)

        try:
            position_size, account_risk_pct = self.risk_policy.position_size(
                capital, entry, technical_stop_price
            )
        except ValueError:
            return self._hold(snapshot, run_id, signal_id, expires_at, HoldReason.RISK)

        net = gross - self.assumed_trading_cost_pct
        if net <= 0:
            return self._hold(snapshot, run_id, signal_id, expires_at, HoldReason.NO_EDGE)

        return Signal(
            signal_id=signal_id,
            run_id=run_id,
            asset=snapshot.asset,
            direction=direction,
            estimated_holding_minutes=estimated_holding_minutes,
            signal_expires_at=expires_at,
            entry_price=entry,
            target_price=target_price,
            stop_price=technical_stop_price,
            gross_expected_return_pct=round(gross, 4),
            estimated_trading_cost_pct=self.assumed_trading_cost_pct,
            net_expected_return_pct=round(net, 4),
            position_size=round(position_size, 8),
            account_risk_pct=account_risk_pct,
            confidence_score=confidence_score,
            data_cutoff=snapshot.data_cutoff,
            market_data_timestamp=snapshot.market_data_timestamp,
            evidence_ref=f"signal:{signal_id}",
        )

    def _hold(
        self,
        snapshot: MarketSnapshot,
        run_id: str,
        signal_id: str,
        expires_at: datetime,
        reason: HoldReason,
    ) -> Signal:
        return Signal(
            signal_id=signal_id,
            run_id=run_id,
            asset=snapshot.asset,
            direction=Direction.HOLD,
            estimated_holding_minutes=None,
            signal_expires_at=expires_at,
            entry_price=None,
            target_price=None,
            stop_price=None,
            gross_expected_return_pct=None,
            estimated_trading_cost_pct=self.assumed_trading_cost_pct,
            net_expected_return_pct=None,
            position_size=0,
            account_risk_pct=0,
            confidence_score=None,
            data_cutoff=snapshot.data_cutoff,
            market_data_timestamp=snapshot.market_data_timestamp,
            evidence_ref=f"signal:{signal_id}",
            hold_reason=reason,
        )
