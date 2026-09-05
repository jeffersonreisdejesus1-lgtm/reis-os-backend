from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from jose import JWTError, jwt

from app.shared.config.settings import get_settings
from app.shared.errors.exceptions import AppError

ALGORITHM = "HS256"


@dataclass(frozen=True)
class SessionIdentity:
    user_id: UUID
    session_version: int


def create_access_token(user_id: UUID, *, session_version: int = 0) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sv": session_version,
        "exp": expires_at,
    }
    return cast(str, jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM))


def decode_session_identity(token: str) -> SessionIdentity:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        session_version = payload.get("sv", 0)
        if not isinstance(subject, str) or not isinstance(session_version, int):
            raise ValueError("invalid session identity")
        return SessionIdentity(
            user_id=UUID(subject),
            session_version=session_version,
        )
    except (JWTError, ValueError) as exc:
        raise AppError(
            "Invalid or expired access token.",
            code="invalid_token",
            status_code=401,
        ) from exc


def decode_access_token(token: str) -> UUID:
    """Backward-compatible subject decoder for non-session callers/tests."""
    return decode_session_identity(token).user_id
