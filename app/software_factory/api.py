from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .orchestrator import BuildCandidate, FounderGateBundle, SoftwareFactory

app = FastAPI(title="REIS OS Institutional Software Factory V1")
factory = SoftwareFactory()
_bundles: dict[str, FounderGateBundle] = {}


class CandidateRequest(BaseModel):
    software_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    source_sha: str = Field(min_length=7)
    files: dict[str, str]
    tests_total: int = Field(gt=0)
    tests_failed: int = Field(ge=0)
    changelog: list[str] = []
    rollback_ref: str = "main"


class PromotionRequest(BaseModel):
    bundle_id: str
    founder_approved: bool


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "runtime": "REIS-OS-INSTITUTIONAL-SOFTWARE-FACTORY-V1-001",
        "autonomous_pre_gate": True,
        "founder_final_gate_required": True,
        "paid_infra_authorized": False,
    }


@app.get("/capabilities")
def capabilities() -> dict[str, object]:
    return {
        "release_manager": True,
        "environment_manager": True,
        "security_pipeline": True,
        "artifact_registry": True,
        "observability": True,
        "incident_recovery": True,
        "autonomous_orchestrator": True,
        "production_without_founder": False,
    }


@app.post("/qualify")
def qualify(req: CandidateRequest) -> dict[str, object]:
    candidate = BuildCandidate(
        software_id=req.software_id,
        version=req.version,
        source_sha=req.source_sha,
        files=req.files,
        tests_total=req.tests_total,
        tests_failed=req.tests_failed,
        changelog=tuple(req.changelog),
        rollback_ref=req.rollback_ref,
    )
    bundle = factory.qualify(candidate)
    _bundles[bundle.bundle_id] = bundle
    return asdict(bundle)


@app.post("/promote")
def promote(req: PromotionRequest) -> dict[str, object]:
    bundle = _bundles.get(req.bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="bundle not found")
    if not req.founder_approved:
        raise HTTPException(status_code=403, detail="founder approval required")
    try:
        return factory.promote_after_founder(bundle, founder_approved=True)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/observability")
def observability() -> dict[str, object]:
    return factory.observability.snapshot()


@app.get("/incidents")
def incidents() -> list[dict[str, object]]:
    return factory.incidents.list()


@app.get("/artifacts")
def artifacts() -> list[dict[str, object]]:
    return factory.artifacts.records()
