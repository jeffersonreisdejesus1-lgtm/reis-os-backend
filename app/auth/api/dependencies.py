from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.config.settings import get_settings
from app.shared.database.session import get_db_session
from app.shared.errors.exceptions import AppError
from app.shared.security.tokens import decode_session_identity
from app.users.infrastructure.models import UserModel

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserModel:
    settings = get_settings()
    token = credentials.credentials if credentials is not None else None
    if token is None:
        token = request.cookies.get(settings.session_cookie_name)
    if token is None:
        raise AppError("Authentication required.", code="unauthorized", status_code=401)

    identity = decode_session_identity(token)
    user = await session.scalar(
        select(UserModel).where(
            UserModel.id == identity.user_id,
            UserModel.is_active.is_(True),
        )
    )
    if user is None or user.session_version != identity.session_version:
        raise AppError(
            "Session expired or revoked.",
            code="session_revoked",
            status_code=401,
        )
    return user


CurrentUser = Annotated[UserModel, Depends(get_current_user)]
