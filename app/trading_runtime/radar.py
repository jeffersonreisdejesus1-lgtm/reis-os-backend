from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from .contracts import HoldReason, MarketSnapshot, Signal
from .indicators import calculate_indicators
from .ledger import EvidenceLedger
from .market import BinancePublicClient
from .market_evidence import (
    CoinGeckoReferenceClient,
    CoinMarketCapReferenceClient,
    EvidencePolicy,
    MarketObservation,
    assess_market_evidence,
    resolve_instrument,
)
from .runtime import TradingRuntime
from .strategy import derive_opportunity


class TradingRadar:
    def __init__(
        self,
        *,
        market: BinancePublicClient | None = None,
        runtime: TradingRuntime | None = None,
        ledger: EvidenceLedger | None = None,
        evidence_policy: EvidencePolicy | None = None,
        coingecko: CoinGeckoReferenceClient | None = None,
        coinmarketcap: CoinMarketCapReferenceClient | None = None,
    ) -> None:
        self.market = market or BinancePublicClient()
        self.runtime = runtime or TradingRuntime()
        self.ledger = ledger or EvidenceLedger()
        self.evidence_policy = evidence_policy or EvidencePolicy()
        self.coingecko = coingecko or CoinGeckoReferenceClient()
        self.coinmarketcap = coinmarketcap or CoinMarketCapReferenceClient()

    def _collect_reference_observations(self, asset: str) -> tuple[list[MarketObservation], list[str]]:
        mapping = resolve_instrument(asset)
        observations: list[MarketObservation] = []
        failures: list[str] = []
        for provider, client in (("COINGECKO", self.coingecko), ("COINMARKETCAP", self.coinmarketcap)):
            if provider not in self.evidence_policy.confirmation_providers and provider not in self.evidence_policy.required_providers:
                continue
            try:
                observations.append(client.price(mapping))
            except Exception as exc:  # provider failures are evidence, never NO_OPPORTUNITY
                failures.append(f"{provider}:{type(exc).__name__}")
        return observations, failures

    def scan(self, asset: str, capital: float) -> Signal:
        mapping = resolve_instrument(asset)
        candles = self.market.klines(mapping.binance_symbol, interval="15m", limit=100)
        opportunity = derive_opportunity(candles)
        latest = candles[-1]
        now = datetime.now(timezone.utc)
        market_ts = datetime.fromtimestamp(latest.close_time_ms / 1000, tz=timezone.utc)
        source_ref = f"binance:{mapping.binance_symbol}:{latest.close_time_ms}"

        observations = [
            MarketObservation(
                provider="BINANCE",
                canonical_symbol=mapping.canonical_symbol,
                venue="BINANCE_SPOT",
                quote_currency=mapping.quote_asset,
                timeframe="15m",
                raw_value=opportunity.entry,
                normalized_value=opportunity.entry,
                observed_at=market_ts,
                freshness=self._unknown_freshness(),
                quality="PRIMARY_EXECUTABLE_MARKET_REFERENCE",
                source_ref=source_ref,
            )
        ]
        references, provider_failures = self._collect_reference_observations(mapping.canonical_symbol)
        observations.extend(references)
        assessment = assess_market_evidence(observations, policy=self.evidence_policy, now=now)
        indicators = calculate_indicators(
            candles,
            timeframe="15m",
            source_snapshot_ref=source_ref,
            observed_at=market_ts,
        )

        snapshot = MarketSnapshot(
            asset=mapping.canonical_symbol,
            price=opportunity.entry,
            market_data_timestamp=market_ts,
            received_at=now,
            data_cutoff=market_ts,
        )
        signal = self.runtime.evaluate(
            snapshot,
            capital=capital,
            technical_stop_price=opportunity.stop,
            target_price=opportunity.target,
            estimated_holding_minutes=opportunity.estimated_holding_minutes,
            confidence_score=opportunity.confidence_score,
            forced_hold_reason=HoldReason.DATA if assessment.hold else None,
        )
        self.ledger.append(
            run_id=signal.run_id,
            event_type="MARKET_EVIDENCE_ASSESSMENT",
            input_payload={
                "asset": mapping.canonical_symbol,
                "providers": [item.provider for item in assessment.observations],
                "provider_failures": provider_failures,
            },
            output_payload={"hold": assessment.hold, "hold_reason": assessment.hold_reason},
            config_payload={"policy_version": assessment.policy_version, "real_money": False},
            data_snapshot_ref=source_ref,
        )
        self.ledger.append(
            run_id=signal.run_id,
            event_type="NATIVE_TECHNICAL_INDICATORS",
            input_payload={"asset": mapping.canonical_symbol, "candles": len(candles)},
            output_payload=asdict(indicators),
            config_payload={"calculation_version": indicators.calculation_version},
            data_snapshot_ref=source_ref,
        )
        self.ledger.append(
            run_id=signal.run_id,
            event_type="RADAR_SIGNAL",
            input_payload={"asset": mapping.canonical_symbol, "candles": len(candles), "data_cutoff": market_ts.isoformat()},
            output_payload={"direction": signal.direction.value, "net": signal.net_expected_return_pct},
            config_payload={"interval": "15m", "limit": 100, "real_money": False},
            data_snapshot_ref=source_ref,
        )
        return signal

    @staticmethod
    def _unknown_freshness():
        from .market_evidence import FreshnessState

        return FreshnessState.UNKNOWN
