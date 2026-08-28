from fastapi import APIRouter

from app.auth.api.dependencies import CurrentUser
from app.command.api.schemas import CommandModeResponse

router = APIRouter(prefix="/command", tags=["command"])


@router.get("/mode", response_model=CommandModeResponse)
async def get_command_mode(_: CurrentUser) -> CommandModeResponse:
    """Expose the currently enforced Command capability boundary."""
    return CommandModeResponse()
