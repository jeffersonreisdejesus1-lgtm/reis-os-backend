from fastapi import APIRouter

from app.auth.api.dependencies import CurrentUser
from app.command.api.schemas import OCSListResponse, OCSProfileResponse
from app.command.application import get_ocs_profile, list_ocs_profiles
from app.shared.errors.exceptions import AppError
from app.shared.security.organization import CurrentOrganizationId

router = APIRouter(prefix="/v1/command", tags=["command"])


@router.get("/ocs", response_model=OCSListResponse)
async def list_ocs(
    current_user: CurrentUser,
    organization_id: CurrentOrganizationId,
) -> OCSListResponse:
    return list_ocs_profiles()


@router.get("/ocs/{ocs_id}", response_model=OCSProfileResponse)
async def get_ocs(
    ocs_id: str,
    current_user: CurrentUser,
    organization_id: CurrentOrganizationId,
) -> OCSProfileResponse:
    profile = get_ocs_profile(ocs_id)
    if profile is None:
        raise AppError(
            "OCS profile not found.",
            code="ocs_profile_not_found",
            status_code=404,
        )
    return profile
