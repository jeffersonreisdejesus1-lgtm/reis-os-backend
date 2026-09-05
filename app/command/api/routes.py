from fastapi import APIRouter

from app.command.api.dependencies import CommandReadAccess
from app.command.api.schemas import OCSListResponse, OCSProfileResponse
from app.command.application import get_ocs_profile, list_ocs_profiles
from app.shared.errors.exceptions import AppError

router = APIRouter(prefix="/v1/command", tags=["command"])


@router.get("/ocs", response_model=OCSListResponse)
async def list_ocs(command_read_access: CommandReadAccess) -> OCSListResponse:
    return list_ocs_profiles()


@router.get("/ocs/{ocs_slug}", response_model=OCSProfileResponse)
async def get_ocs(
    ocs_slug: str,
    command_read_access: CommandReadAccess,
) -> OCSProfileResponse:
    profile = get_ocs_profile(ocs_slug)
    if profile is None:
        raise AppError(
            "OCS profile not found.",
            code="ocs_profile_not_found",
            status_code=404,
        )
    return profile
