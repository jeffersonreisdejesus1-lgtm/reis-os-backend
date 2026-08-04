from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.dependencies import CurrentUser
from app.auth.api.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.shared.database.session import get_db_session
from app.shared.errors.exceptions import AppError
from app.shared.security.passwords import hash_password, verify_password
from app.shared.security.tokens import create_access_token
from app.users.infrastructure.models import UserModel

router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: DbSession) -> AuthResponse:
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
    return AuthResponse(
        access_token=create_access_token(user.id),
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, session: DbSession) -> AuthResponse:
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
    return AuthResponse(
        access_token=create_access_token(user.id),
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
