from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .operations import MigrationPlan
from .orchestrator import BuildCandidate, FounderGateBundle, SoftwareFactory

app = FastAPI(title="REIS OS Institutional Software Factory V1")
factory = SoftwareFactory()
_bundles: dict[str, FounderGateBundle] = {}


class MigrationRequest(BaseModel):
    migration_id: str
    up: str
    down: str


class CandidateRequest(BaseModel):
    software_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    source_sha: str = Field(min_length=7)
    files: dict[str, str]
    tests_total: int = Field(gt=0)
    tests_failed: int = Field(ge=0)
    changelog: list[str] = Field(default_factory=list)
    rollback_ref: str = "main"
    performance_p95_ms: float = Field(default=0.0, ge=0)
    error_rate_pct: float = Field(default=0.0, ge=0)
    migration: MigrationRequest | None = None
    config: dict[str, str] = Field(default_factory=dict)
    feature_flags: dict[str, bool] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "runtime": "REIS-OS-INSTITUTIONAL-SOFTWARE-FACTORY-V1-001",
        "autonomous_pre_gate": True,
        "founder_final_gate_required": True,
        "public_production_promotion_endpoint": False,
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
        "config_and_secret_reference_policy": True,
        "feature_flags": True,
        "database_migration_gate": True,
        "performance_gate": True,
        "slo_policy": True,
        "sbom": True,
        "autonomous_orchestrator": True,
        "production_without_founder": False,
    }


@app.post("/qualify")
def qualify(req: CandidateRequest) -> dict[str, object]:
    migration = None
    if req.migration is not None:
        migration = MigrationPlan(req.migration.migration_id, req.migration.up, req.migration.down)
    candidate = BuildCandidate(
        software_id=req.software_id,
        version=req.version,
        source_sha=req.source_sha,
        files=req.files,
        tests_total=req.tests_total,
        tests_failed=req.tests_failed,
        changelog=tuple(req.changelog),
        rollback_ref=req.rollback_ref,
        performance_p95_ms=req.performance_p95_ms,
        error_rate_pct=req.error_rate_pct,
        migration=migration,
        config=tuple(sorted(req.config.items())),
        feature_flags=tuple(sorted(req.feature_flags.items())),
    )
    bundle = factory.qualify(candidate)
    _bundles[bundle.bundle_id] = bundle
    return asdict(bundle)


@app.get("/observability")
def observability() -> dict[str, object]:
    return factory.observability.snapshot()


@app.get("/incidents")
def incidents() -> list[dict[str, object]]:
    return factory.incidents.list()


@app.get("/artifacts")
def artifacts() -> list[dict[str, object]]:
    return factory.artifacts.records()


@app.get("/config")
def config() -> dict[str, str]:
    return factory.config.snapshot()
