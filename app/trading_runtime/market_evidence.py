from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class FreshnessState(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class DisagreementState(str, Enum):
    NONE = "NONE"
    MATERIAL = "MATERIAL"
    SEMANTIC_MISMATCH = "SEMANTIC_MISMATCH"


@dataclass(frozen=True)
class InstrumentMapping:
    canonical_symbol: str
    base_asset: str
    quote_asset: str
    binance_symbol: str
    coingecko_id: str | None
    coinmarketcap_symbol: str | None


@dataclass(frozen=True)
class MarketObservation:
    provider: str
    canonical_symbol: str
    venue: str
    quote_currency: str
    timeframe: str
    raw_value: float
    normalized_value: float
    observed_at: datetime
    freshness: FreshnessState
    quality: str
    source_ref: str
    derivation_version: str = "market-evidence-v1"
    disagreement: DisagreementState = DisagreementState.NONE


@dataclass(frozen=True)
class EvidencePolicy:
    max_age_seconds: int = 120
    material_price_disagreement_pct: float = 1.0
    required_providers: tuple[str, ...] = ("BINANCE",)
    confirmation_providers: tuple[str, ...] = ("COINGECKO", "COINMARKETCAP")
    version: str = "market-evidence-policy-v1"


@dataclass(frozen=True)
class EvidenceAssessment:
    observations: tuple[MarketObservation, ...]
    hold: bool
    hold_reason: str | None
    policy_version: str


DEFAULT_MAPPINGS: dict[str, InstrumentMapping] = {
    "BTCUSDT": InstrumentMapping("BTCUSDT", "BTC", "USDT", "BTCUSDT", "bitcoin", "BTC"),
    "ETHUSDT": InstrumentMapping("ETHUSDT", "ETH", "USDT", "ETHUSDT", "ethereum", "ETH"),
    "BNBUSDT": InstrumentMapping("BNBUSDT", "BNB", "USDT", "BNBUSDT", "binancecoin", "BNB"),
    "SOLUSDT": InstrumentMapping("SOLUSDT", "SOL", "USDT", "SOLUSDT", "solana", "SOL"),
}


def resolve_instrument(symbol: str) -> InstrumentMapping:
    canonical = symbol.replace("/", "").upper()
    mapping = DEFAULT_MAPPINGS.get(canonical)
    if mapping is None:
        raise ValueError(f"unmapped instrument: {symbol}")
    return mapping


def _freshness(observed_at: datetime, *, now: datetime, max_age_seconds: int) -> FreshnessState:
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    age = now - observed_at.astimezone(timezone.utc)
    if age < timedelta(seconds=-5):
        return FreshnessState.UNKNOWN
    return FreshnessState.FRESH if age <= timedelta(seconds=max_age_seconds) else FreshnessState.STALE


class CoinGeckoReferenceClient:
    base_url = "https://api.coingecko.com/api/v3"

    def price(self, mapping: InstrumentMapping, *, timeout_seconds: float = 5.0) -> MarketObservation:
        if not mapping.coingecko_id:
            raise ValueError("coingecko mapping unavailable")
        params = urlencode({"ids": mapping.coingecko_id, "vs_currencies": "usd", "include_last_updated_at": "true"})
        with urlopen(f"{self.base_url}/simple/price?{params}", timeout=timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
        item = payload[mapping.coingecko_id]
        observed_at = datetime.fromtimestamp(int(item["last_updated_at"]), tz=timezone.utc)
        value = float(item["usd"])
        return MarketObservation(
            provider="COINGECKO",
            canonical_symbol=mapping.canonical_symbol,
            venue="AGGREGATED_REFERENCE",
            quote_currency="USD",
            timeframe="SPOT_REFERENCE",
            raw_value=value,
            normalized_value=value,
            observed_at=observed_at,
            freshness=FreshnessState.UNKNOWN,
            quality="INDEPENDENT_REFERENCE",
            source_ref=f"coingecko:{mapping.coingecko_id}:{int(observed_at.timestamp())}",
            disagreement=DisagreementState.SEMANTIC_MISMATCH if mapping.quote_asset != "USD" else DisagreementState.NONE,
        )


class CoinMarketCapReferenceClient:
    base_url = "https://pro-api.coinmarketcap.com/v1"

    def price(self, mapping: InstrumentMapping, *, timeout_seconds: float = 5.0) -> MarketObservation:
        api_key = os.getenv("COINMARKETCAP_API_KEY")
        if not api_key:
            raise RuntimeError("coinmarketcap adapter configured but COINMARKETCAP_API_KEY is absent")
        if not mapping.coinmarketcap_symbol:
            raise ValueError("coinmarketcap mapping unavailable")
        params = urlencode({"symbol": mapping.coinmarketcap_symbol, "convert": "USD"})
        request = Request(
            f"{self.base_url}/cryptocurrency/quotes/latest?{params}",
            headers={"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"},
        )
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
        item = payload["data"][mapping.coinmarketcap_symbol]
        quote = item["quote"]["USD"]
        observed_at = datetime.fromisoformat(item["last_updated"].replace("Z", "+00:00"))
        value = float(quote["price"])
        return MarketObservation(
            provider="COINMARKETCAP",
            canonical_symbol=mapping.canonical_symbol,
            venue="AGGREGATED_REFERENCE",
            quote_currency="USD",
            timeframe="SPOT_REFERENCE",
            raw_value=value,
            normalized_value=value,
            observed_at=observed_at,
            freshness=FreshnessState.UNKNOWN,
            quality="MARKET_CONTEXT_REFERENCE",
            source_ref=f"coinmarketcap:{mapping.coinmarketcap_symbol}:{int(observed_at.timestamp())}",
            disagreement=DisagreementState.SEMANTIC_MISMATCH if mapping.quote_asset != "USD" else DisagreementState.NONE,
        )


def assess_market_evidence(
    observations: list[MarketObservation],
    *,
    policy: EvidencePolicy | None = None,
    now: datetime | None = None,
) -> EvidenceAssessment:
    policy = policy or EvidencePolicy()
    now = now or datetime.now(timezone.utc)
    refreshed: list[MarketObservation] = []
    for observation in observations:
        refreshed.append(
            MarketObservation(
                **{
                    **observation.__dict__,
                    "freshness": _freshness(observation.observed_at, now=now, max_age_seconds=policy.max_age_seconds),
                }
            )
        )
    by_provider = {item.provider: item for item in refreshed}
    for provider in policy.required_providers:
        item = by_provider.get(provider)
        if item is None:
            return EvidenceAssessment(tuple(refreshed), True, f"HOLD_DATA:MISSING_REQUIRED_PROVIDER:{provider}", policy.version)
        if item.freshness is not FreshnessState.FRESH:
            return EvidenceAssessment(tuple(refreshed), True, f"HOLD_DATA:STALE_REQUIRED_PROVIDER:{provider}", policy.version)

    primary = by_provider.get("BINANCE")
    if primary:
        for item in refreshed:
            if item.provider == "BINANCE" or item.disagreement is DisagreementState.SEMANTIC_MISMATCH:
                continue
            denominator = max(abs(primary.normalized_value), 1e-12)
            diff_pct = abs(item.normalized_value - primary.normalized_value) / denominator * 100.0
            if diff_pct > policy.material_price_disagreement_pct:
                return EvidenceAssessment(tuple(refreshed), True, f"HOLD_DATA:MATERIAL_PROVIDER_DISAGREEMENT:{item.provider}", policy.version)

    return EvidenceAssessment(tuple(refreshed), False, None, policy.version)
