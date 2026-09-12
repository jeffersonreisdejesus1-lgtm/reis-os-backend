from asyncio import to_thread
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.routes import router as auth_router
from app.cognitive_validation.operational_qualification_runtime import (
    app as coi15_operational_app,
    run_qualification as run_coi15_operational_qualification,
)
from app.cognitive_validation.phase_d2_adversarial_semantic_v2 import (
    read_phase_d2_evidence,
    run_phase_d2_semantic_qualification,
)
from app.command.api.instance_routes import router as command_instance_router
from app.command.api.routes import router as command_router
from app.execution_bindings import router as execution_bindings_router
from app.governance_refactor.api import router as governance_refactor_router
from app.governance_refactor.schema import migrate_governance_candidate_store
from app.organizations.api.routes import router as organizations_router
from app.projects.api.routes import router as projects_router
from app.shared.config.settings import get_settings
from app.shared.database.session import engine, get_db_session
from app.shared.errors.handlers import register_exception_handlers
from app.shared.logging.setup import configure_logging
from app.tasks.api.routes import router as tasks_router
from app.workspaces.api.routes import router as workspaces_router

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # COI15 Phase D and D2 execute inside the deployed web-runtime process.
    # Startup fails closed if either operational qualification cannot produce
    # its externally observable evidence. Neither routine changes assurance
    # disposition or executes Founder promotion.
    await to_thread(run_coi15_operational_qualification)
    await to_thread(run_phase_d2_semantic_qualification)
    migrate_governance_candidate_store(settings.governance_candidate_store_path)
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(workspaces_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(command_router)
app.include_router(command_instance_router)
app.include_router(governance_refactor_router)
app.include_router(execution_bindings_router)
app.mount("/coi15-operational", coi15_operational_app)


@app.get("/coi15/phase-d2-evidence", tags=["system"])
async def coi15_phase_d2_evidence() -> dict[str, Any]:
    return read_phase_d2_evidence()


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
async def ready(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    await session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
