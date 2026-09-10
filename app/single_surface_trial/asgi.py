from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine

from .store import TrialStore


def create_trial_app() -> FastAPI:
    database_url = os.getenv("TRIAL_DATABASE_URL")
    if not database_url:
        raise RuntimeError("TRIAL_DATABASE_URL_REQUIRED_FAIL_CLOSED")
    engine = create_engine(database_url)
    store = TrialStore(engine)
    app = FastAPI(
        title="REIS OS Single Surface Controlled Trial",
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/trial/health")
    def health() -> dict[str, str]:
        return {
            "status": "builder_surface_ready",
            "trial_execution": "not_authorized",
            "production": "not_authorized",
        }

    @app.get("/trial/missions/{mission_id}")
    def mission_projection(mission_id: str) -> dict[str, object]:
        try:
            return store.projection(mission_id)
        except Exception as exc:
            raise HTTPException(status_code=404, detail="mission_not_found") from exc

    return app


app = create_trial_app()
