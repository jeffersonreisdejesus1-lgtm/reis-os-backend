from datetime import datetime, timedelta, timezone

import pytest

from app.trading_runtime.contracts import Direction, HoldReason, MarketSnapshot
from app.trading_runtime.indicators import CALCULATION_VERSION, calculate_indicators
from app.trading_runtime.market_evidence import (
    DisagreementState,
    EvidencePolicy,
    FreshnessState,
    MarketObservation,
    assess_market_evidence,
    resolve_instrument,
)
from app.trading_runtime.runtime import TradingRuntime
from app.trading_runtime.strategy import Candle


def _candles(count: int = 60) -> list[Candle]:
    base = 100.0
    result = []
    for index in range(count):
        close = base + index * 0.25
        result.append(
            Candle(
                open=close - 0.10,
                high=close + 0.50,
                low=close - 0.50,
                close=close,
                close_time_ms=1_700_000_000_000 + index * 900_000,
            )
        )
    return result


def _observation(provider: str, value: float, observed_at: datetime, *, mismatch: bool = False) -> MarketObservation:
    return MarketObservation(
        provider=provider,
        canonical_symbol="BTCUSDT",
        venue="BINANCE_SPOT" if provider == "BINANCE" else "AGGREGATED_REFERENCE",
        quote_currency="USDT" if provider == "BINANCE" else "USD",
        timeframe="15m" if provider == "BINANCE" else "SPOT_REFERENCE",
        raw_value=value,
        normalized_value=value,
        observed_at=observed_at,
        freshness=FreshnessState.UNKNOWN,
        quality="TEST",
        source_ref=f"test:{provider}",
        disagreement=DisagreementState.SEMANTIC_MISMATCH if mismatch else DisagreementState.NONE,
    )


def test_native_indicator_engine_is_deterministic_and_provenanced():
    observed_at = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)
    first = calculate_indicators(_candles(), timeframe="15m", source_snapshot_ref="binance:BTCUSDT:1", observed_at=observed_at)
    second = calculate_indicators(_candles(), timeframe="15m", source_snapshot_ref="binance:BTCUSDT:1", observed_at=observed_at)
    assert first == second
    assert first.calculation_version == CALCULATION_VERSION
    assert first.source_snapshot_ref == "binance:BTCUSDT:1"
    assert 0.0 <= first.rsi <= 100.0
    assert first.bollinger_lower < first.bollinger_mid < first.bollinger_upper
    assert first.support < first.resistance


def test_indicator_engine_requires_sufficient_closed_candles():
    with pytest.raises(ValueError, match="at least 35"):
        calculate_indicators(_candles(20), timeframe="15m", source_snapshot_ref="x")


def test_missing_required_provider_fails_closed_to_hold_data():
    now = datetime.now(timezone.utc)
    policy = EvidencePolicy(required_providers=("BINANCE", "COINGECKO"))
    assessment = assess_market_evidence([_observation("BINANCE", 100.0, now)], policy=policy, now=now)
    assert assessment.hold is True
    assert assessment.hold_reason == "HOLD_DATA:MISSING_REQUIRED_PROVIDER:COINGECKO"


def test_stale_required_provider_fails_closed():
    now = datetime.now(timezone.utc)
    stale = now - timedelta(minutes=10)
    assessment = assess_market_evidence([_observation("BINANCE", 100.0, stale)], now=now)
    assert assessment.hold is True
    assert assessment.hold_reason == "HOLD_DATA:STALE_REQUIRED_PROVIDER:BINANCE"


def test_material_same_semantics_disagreement_fails_closed():
    now = datetime.now(timezone.utc)
    policy = EvidencePolicy(material_price_disagreement_pct=1.0)
    assessment = assess_market_evidence(
        [_observation("BINANCE", 100.0, now), _observation("TEST_REFERENCE", 103.0, now)],
        policy=policy,
        now=now,
    )
    assert assessment.hold is True
    assert "MATERIAL_PROVIDER_DISAGREEMENT" in assessment.hold_reason


def test_usd_reference_semantic_mismatch_is_preserved_not_averaged():
    now = datetime.now(timezone.utc)
    assessment = assess_market_evidence(
        [_observation("BINANCE", 100.0, now), _observation("COINGECKO", 103.0, now, mismatch=True)],
        now=now,
    )
    assert assessment.hold is False
    assert assessment.observations[1].disagreement is DisagreementState.SEMANTIC_MISMATCH


def test_instrument_mapping_is_explicit_and_fail_closed():
    btc = resolve_instrument("BTC/USDT")
    assert btc.binance_symbol == "BTCUSDT"
    assert btc.coingecko_id == "bitcoin"
    with pytest.raises(ValueError, match="unmapped instrument"):
        resolve_instrument("UNKNOWNUSDT")


def test_runtime_accepts_explicit_data_hold_without_creating_trade():
    now = datetime.now(timezone.utc)
    snapshot = MarketSnapshot(
        asset="BTCUSDT",
        price=100.0,
        market_data_timestamp=now,
        received_at=now,
        data_cutoff=now,
    )
    signal = TradingRuntime().evaluate(
        snapshot,
        capital=1000.0,
        technical_stop_price=95.0,
        target_price=110.0,
        forced_hold_reason=HoldReason.DATA,
    )
    assert signal.direction is Direction.HOLD
    assert signal.hold_reason is HoldReason.DATA
    assert signal.position_size == 0
    assert signal.entry_price is None
