from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from app.shared.config.settings import get_settings
from app.shared.errors.exceptions import AppError

ALGORITHM = "HS256"


def create_access_token(user_id: UUID) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if not isinstance(subject, str):
            raise ValueError("missing subject")
        return UUID(subject)
    except (JWTError, ValueError) as exc:
        raise AppError(
            "Invalid or expired access token.",
            code="invalid_token",
            status_code=401,
        ) from exc
