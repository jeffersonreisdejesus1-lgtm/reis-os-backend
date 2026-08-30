from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.action_proposals.domain.enums import (
    ActionExecutionStatus,
    ActionProposalStatus,
)
from app.shared.database.base import Base
from app.shared.database.types import TimestampMixin, UUIDPrimaryKeyMixin


class ActionProposalModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "action_proposals"

    action_type: Mapped[str] = mapped_column(String(100))
    target: Mapped[str] = mapped_column(String(500))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    requested_by: Mapped[str] = mapped_column(String(200))
    status: Mapped[ActionProposalStatus] = mapped_column(
        Enum(
            ActionProposalStatus,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=ActionProposalStatus.PENDING,
        nullable=False,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    execution_status: Mapped[ActionExecutionStatus | None] = mapped_column(
        Enum(
            ActionExecutionStatus,
            native_enum=False,
            length=30,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=True,
    )
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
