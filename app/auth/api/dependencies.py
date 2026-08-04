from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.session import get_db_session
from app.shared.errors.exceptions import AppError
from app.shared.security.tokens import decode_access_token
from app.users.infrastructure.models import UserModel

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserModel:
    if credentials is None:
        raise AppError("Authentication required.", code="unauthorized", status_code=401)
    user_id = decode_access_token(credentials.credentials)
    user = await session.scalar(
        select(UserModel).where(UserModel.id == user_id, UserModel.is_active.is_(True))
    )
    if user is None:
        raise AppError("User not found.", code="unauthorized", status_code=401)
    return user


CurrentUser = Annotated[UserModel, Depends(get_current_user)]
