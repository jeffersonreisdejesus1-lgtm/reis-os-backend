from uuid import UUID

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.memberships.domain.enums import MembershipRole, MembershipStatus
from app.shared.database.base import Base
from app.shared.database.types import TimestampMixin, UUIDPrimaryKeyMixin


class MembershipModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MembershipRole] = mapped_column(
        Enum(
            MembershipRole,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(
            MembershipStatus,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [item.value for item in enum],
        )
    )

    organization = relationship("OrganizationModel", back_populates="memberships")
    user = relationship("UserModel", back_populates="memberships")
