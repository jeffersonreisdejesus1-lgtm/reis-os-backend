from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.trading_runtime.contracts import Direction, HoldReason, MarketSnapshot
from app.trading_runtime.economics import BudgetPolicy, EconomicGovernor
from app.trading_runtime.risk import RiskPolicy
from app.trading_runtime.runtime import TradingRuntime
from app.trading_runtime.strategy import Candle, derive_opportunity


def snapshot(age_seconds: int = 0) -> MarketSnapshot:
    now = datetime.now(timezone.utc)
    return MarketSnapshot(
        asset="BTC/USDT",
        price=100.0,
        market_data_timestamp=now - timedelta(seconds=age_seconds),
        received_at=now,
        data_cutoff=now,
    )


def candles(prices: list[float]) -> list[Candle]:
    return [Candle(p - 0.5, p + 1.0, p - 1.0, p, i) for i, p in enumerate(prices)]


def test_buy_signal_contains_net_return_time_and_risk() -> None:
    signal = TradingRuntime().evaluate(
        snapshot(),
        capital=1000,
        technical_stop_price=98,
        target_price=104,
        estimated_holding_minutes=120,
        confidence_score=70,
    )
    assert signal.direction is Direction.BUY
    assert signal.net_expected_return_pct == 3.8
    assert signal.estimated_holding_minutes == 120
    assert signal.account_risk_pct == 1.0
    assert signal.position_size == 500.0


def test_sell_signal_is_supported() -> None:
    signal = TradingRuntime().evaluate(
        snapshot(), capital=1000, technical_stop_price=102, target_price=96
    )
    assert signal.direction is Direction.SELL
    assert signal.net_expected_return_pct == 3.8


def test_stale_market_data_holds_closed() -> None:
    signal = TradingRuntime(max_data_age_seconds=60).evaluate(
        snapshot(61), capital=1000, technical_stop_price=98, target_price=104
    )
    assert signal.direction is Direction.HOLD
    assert signal.hold_reason is HoldReason.DATA


def test_stop_distance_above_absolute_ceiling_holds_risk() -> None:
    signal = TradingRuntime(risk_policy=RiskPolicy()).evaluate(
        snapshot(), capital=1000, technical_stop_price=70, target_price=104
    )
    assert signal.direction is Direction.HOLD
    assert signal.hold_reason is HoldReason.RISK


def test_no_market_edge_returns_hold() -> None:
    signal = TradingRuntime().evaluate(
        snapshot(), capital=1000, technical_stop_price=None, target_price=None
    )
    assert signal.direction is Direction.HOLD
    assert signal.hold_reason is HoldReason.NO_EDGE


def test_economic_governor_reserves_reconciles_and_counts_strong_calls() -> None:
    governor = EconomicGovernor(
        BudgetPolicy(
            daily=Decimal("1"),
            monthly=Decimal("10"),
            run=Decimal("0.50"),
            signal=Decimal("0.20"),
            cycle_call_limit=2,
            strong_model_limit=1,
        )
    )
    reservation = governor.reserve(Decimal("0.10"), strong=True)
    assert reservation is not None
    assert governor.reconcile(reservation.reservation_id, Decimal("0.08"), strong=True)
    assert governor.strong_calls_today == 1
    assert governor.spent_run == Decimal("0.08")
    assert governor.reserve(Decimal("0.10"), strong=True) is None


def test_uptrend_generates_bounded_buy_opportunity() -> None:
    opportunity = derive_opportunity(candles([100 + i for i in range(25)]))
    assert opportunity.direction is Direction.BUY
    assert opportunity.stop is not None and opportunity.stop < opportunity.entry
    assert opportunity.target is not None and opportunity.target > opportunity.entry


def test_downtrend_generates_bounded_sell_opportunity() -> None:
    opportunity = derive_opportunity(candles([150 - i for i in range(25)]))
    assert opportunity.direction is Direction.SELL
    assert opportunity.stop is not None and opportunity.stop > opportunity.entry
    assert opportunity.target is not None and opportunity.target < opportunity.entry


def test_insufficient_history_holds() -> None:
    opportunity = derive_opportunity(candles([100, 101, 102]))
    assert opportunity.direction is Direction.HOLD
