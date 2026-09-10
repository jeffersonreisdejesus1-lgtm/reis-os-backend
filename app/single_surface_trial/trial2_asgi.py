from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text

from .trial2_integrity import IntegrityCheckedTrial2Store


def create_trial2_app() -> FastAPI:
    database_url = os.getenv("TRIAL_DATABASE_URL")
    if not database_url:
        raise RuntimeError("TRIAL_DATABASE_URL_REQUIRED_FAIL_CLOSED")

    engine = create_engine(database_url, pool_pre_ping=True)
    store = IntegrityCheckedTrial2Store(engine)

    app = FastAPI(
        title="REIS OS Trial 2 Persistent Infrastructure",
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/trial2/health")
    def health() -> dict[str, str]:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="persistent_database_unavailable") from exc
        return {
            "status": "persistent_infrastructure_ready",
            "trial_2_execution": "not_started_by_health_surface",
            "production": "not_authorized",
            "merge": "not_authorized",
        }

    @app.get("/trial2/missions/{mission_id}")
    def mission_recovery_projection(mission_id: str) -> dict[str, object]:
        try:
            snapshot = store.recover_snapshot(
                mission_id,
                authority_validator=lambda authority_ref, actor, role: bool(
                    authority_ref and actor and role
                ),
            )
        except Exception as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "mission_id": snapshot.mission_id,
            "current_primary_actor": snapshot.current_primary_actor,
            "current_instance": snapshot.current_instance,
            "current_gate": snapshot.current_gate,
            "current_handoff_ref": snapshot.current_handoff_ref,
            "last_valid_checkpoint": snapshot.last_valid_checkpoint,
            "authority_ref": snapshot.authority_ref,
            "role": snapshot.role,
            "fencing_epoch": snapshot.fencing_epoch,
            "autonomous_step_counter": snapshot.autonomous_step_counter,
            "autonomous_handoff_counter": snapshot.autonomous_handoff_counter,
            "repair_cycle_counter": snapshot.repair_cycle_counter,
        }

    return app


app = create_trial2_app()
