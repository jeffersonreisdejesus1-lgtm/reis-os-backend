from __future__ import annotations

from datetime import datetime, timezone

from .contracts import MarketSnapshot, Signal
from .ledger import EvidenceLedger
from .market import BinancePublicClient
from .runtime import TradingRuntime
from .strategy import derive_opportunity


class TradingRadar:
    def __init__(
        self,
        *,
        market: BinancePublicClient | None = None,
        runtime: TradingRuntime | None = None,
        ledger: EvidenceLedger | None = None,
    ) -> None:
        self.market = market or BinancePublicClient()
        self.runtime = runtime or TradingRuntime()
        self.ledger = ledger or EvidenceLedger()

    def scan(self, asset: str, capital: float) -> Signal:
        candles = self.market.klines(asset, interval="15m", limit=100)
        opportunity = derive_opportunity(candles)
        latest = candles[-1]
        now = datetime.now(timezone.utc)
        market_ts = datetime.fromtimestamp(latest.close_time_ms / 1000, tz=timezone.utc)
        snapshot = MarketSnapshot(
            asset=asset,
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
        )
        self.ledger.append(
            run_id=signal.run_id,
            event_type="RADAR_SIGNAL",
            input_payload={"asset": asset, "candles": len(candles), "data_cutoff": market_ts.isoformat()},
            output_payload={"direction": signal.direction.value, "net": signal.net_expected_return_pct},
            config_payload={"interval": "15m", "limit": 100, "real_money": False},
            data_snapshot_ref=f"binance:{asset}:{latest.close_time_ms}",
        )
        return signal
