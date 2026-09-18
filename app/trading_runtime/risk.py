from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskPolicy:
    max_capital_at_risk_per_trade_pct: float = 1.0
    max_daily_realized_loss_pct: float = 3.0
    max_daily_total_risk_pct: float = 4.0
    max_concurrent_exposure_pct: float = 25.0
    max_correlated_exposure_pct: float = 15.0
    max_drawdown_pct: float = 10.0
    absolute_max_stop_distance_pct: float = 25.0

    def position_size(self, capital: float, entry: float, stop: float) -> tuple[float, float]:
        if capital <= 0 or entry <= 0 or stop <= 0:
            raise ValueError("capital, entry, and stop must be positive")
        stop_distance_pct = abs(entry - stop) / entry * 100
        if stop_distance_pct <= 0 or stop_distance_pct > self.absolute_max_stop_distance_pct:
            raise ValueError("stop distance outside policy")
        risk_amount = capital * (self.max_capital_at_risk_per_trade_pct / 100)
        units = risk_amount / abs(entry - stop)
        position_value = units * entry
        return position_value, self.max_capital_at_risk_per_trade_pct
