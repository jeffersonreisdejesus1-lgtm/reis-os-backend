from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .contracts import MarketSnapshot
from .radar import TradingRadar
from .runtime import TradingRuntime

app = FastAPI(title="REIS OS Trading Mission Runtime V1")
runtime = TradingRuntime()
radar = TradingRadar(runtime=runtime)


class EvaluateRequest(BaseModel):
    asset: str
    price: float = Field(gt=0)
    market_data_timestamp: datetime
    data_cutoff: datetime
    capital: float = Field(gt=0)
    technical_stop_price: float | None = None
    target_price: float | None = None
    estimated_holding_minutes: int = Field(default=120, ge=60, le=480)
    confidence_score: float | None = Field(default=None, ge=0, le=100)


def _signal_payload(signal: object) -> dict[str, object]:
    return {
        "signal_id": signal.signal_id,
        "run_id": signal.run_id,
        "asset": signal.asset,
        "direction": signal.direction.value,
        "estimated_holding_minutes": signal.estimated_holding_minutes,
        "signal_expires_at": signal.signal_expires_at.isoformat(),
        "entry_price": signal.entry_price,
        "target_price": signal.target_price,
        "stop_price": signal.stop_price,
        "gross_expected_return_pct": signal.gross_expected_return_pct,
        "estimated_trading_cost_pct": signal.estimated_trading_cost_pct,
        "net_expected_return_pct": signal.net_expected_return_pct,
        "position_size": signal.position_size,
        "account_risk_pct": signal.account_risk_pct,
        "confidence_score": signal.confidence_score,
        "hold_reason": signal.hold_reason.value if signal.hold_reason else None,
        "evidence_ref": signal.evidence_ref,
    }


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "runtime": "META-ARQ-REIS-OS-TRADING-MISSION-RUNTIME-V1-ECONOMIC-002",
        "real_money_autonomous_execution": False,
        "paper_trading_required": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/evaluate")
def evaluate(req: EvaluateRequest) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    snapshot = MarketSnapshot(
        asset=req.asset,
        price=req.price,
        market_data_timestamp=req.market_data_timestamp,
        received_at=now,
        data_cutoff=req.data_cutoff,
    )
    signal = runtime.evaluate(
        snapshot,
        capital=req.capital,
        technical_stop_price=req.technical_stop_price,
        target_price=req.target_price,
        estimated_holding_minutes=req.estimated_holding_minutes,
        confidence_score=req.confidence_score,
    )
    return _signal_payload(signal)


@app.get("/radar/{asset}")
def scan_radar(asset: str, capital: float = 1000.0) -> dict[str, object]:
    try:
        signal = radar.scan(asset.upper(), capital)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="market data unavailable") from exc
    return _signal_payload(signal)


@app.get("/evidence")
def evidence() -> list[dict[str, object]]:
    return radar.ledger.events()
