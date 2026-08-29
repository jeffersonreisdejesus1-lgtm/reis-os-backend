import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.routes import router as auth_router
from app.command.api.routes import router as command_router
from app.command.application.refresh import refresh_supervisor
from app.command.application.seed import ensure_initial_observation_seed
from app.organizations.api.routes import router as organizations_router
from app.projects.api.routes import router as projects_router
from app.shared.config.settings import get_settings
from app.shared.database.session import SessionLocal, engine, get_db_session
from app.shared.errors.handlers import register_exception_handlers
from app.shared.logging.setup import configure_logging
from app.tasks.api.routes import router as tasks_router
from app.workspaces.api.routes import router as workspaces_router

settings = get_settings()
configure_logging(settings.log_level)
COMMAND_UI = Path(__file__).resolve().parent / "command" / "frontend" / "index.html"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    refresh_task: asyncio.Task[None] | None = None
    if settings.command_refresh_enabled:
        async with SessionLocal() as session:
            await ensure_initial_observation_seed(session, settings=settings)
        refresh_task = asyncio.create_task(refresh_supervisor())
    try:
        yield
    finally:
        if refresh_task is not None:
            refresh_task.cancel()
            with suppress(asyncio.CancelledError):
                await refresh_task
        await engine.dispose()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(workspaces_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(command_router)


@app.get("/", include_in_schema=False)
@app.get("/command-ui", include_in_schema=False)
async def command_ui() -> FileResponse:
    return FileResponse(COMMAND_UI)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
async def ready(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    await session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
