from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.base import Base
from app.shared.database.types import TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)

    memberships = relationship(
        "MembershipModel", back_populates="organization", cascade="all, delete-orphan"
    )
