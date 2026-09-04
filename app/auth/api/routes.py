from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.dependencies import CurrentUser
from app.auth.api.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.shared.config.settings import get_settings
from app.shared.database.session import get_db_session
from app.shared.errors.exceptions import AppError
from app.shared.security.passwords import hash_password, verify_password
from app.shared.security.tokens import create_access_token
from app.users.infrastructure.models import UserModel

router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


async def _authenticate(payload: LoginRequest, session: AsyncSession) -> UserModel:
    user = await session.scalar(
        select(UserModel).where(UserModel.email == str(payload.email).lower())
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError(
            "Invalid email or password.",
            code="invalid_credentials",
            status_code=401,
        )
    if not user.is_active:
        raise AppError("User is inactive.", code="user_inactive", status_code=403)
    return user


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    payload: RegisterRequest,
    session: DbSession,
    response: Response,
) -> AuthResponse:
    settings = get_settings()
    if not settings.public_signup_enabled:
        raise AppError(
            "Public registration is disabled.",
            code="public_registration_disabled",
            status_code=404,
        )

    user = UserModel(
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            "Email is already registered.",
            code="email_already_registered",
            status_code=409,
        ) from exc
    await session.refresh(user)
    token = create_access_token(user.id, session_version=user.session_version)
    _set_session_cookie(response, token)
    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    session: DbSession,
    response: Response,
) -> AuthResponse:
    """Platform-compatible bearer login; not used by the COMMAND browser shell."""
    user = await _authenticate(payload, session)
    token = create_access_token(user.id, session_version=user.session_version)
    _set_session_cookie(response, token)
    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/session/login", response_model=UserResponse)
async def session_login(
    payload: LoginRequest,
    session: DbSession,
    response: Response,
) -> UserResponse:
    """Private product login: session credential remains in an HttpOnly cookie."""
    user = await _authenticate(payload, session)
    token = create_access_token(user.id, session_version=user.session_version)
    _set_session_cookie(response, token)
    return UserResponse.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: CurrentUser,
    session: DbSession,
    response: Response,
) -> None:
    current_user.session_version += 1
    await session.commit()
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
