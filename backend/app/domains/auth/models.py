import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.domains.buildings.models import OwnedBuilding


class HouseRole(enum.StrEnum):
    member = "member"
    manager = "manager"
    admin = "admin"
    read_only = "read_only"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    memberships: Mapped[list["HouseMembership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    owned_buildings: Mapped[list["OwnedBuilding"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )


class House(Base):
    __tablename__ = "houses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    memberships: Mapped[list["HouseMembership"]] = relationship(
        back_populates="house",
        cascade="all, delete-orphan",
    )
    owned_buildings: Mapped[list["OwnedBuilding"]] = relationship(
        back_populates="house",
        cascade="all, delete-orphan",
    )


class HouseMembership(Base):
    __tablename__ = "house_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    house_id: Mapped[int] = mapped_column(ForeignKey("houses.id"), index=True)
    role: Mapped[HouseRole] = mapped_column(Enum(HouseRole), default=HouseRole.member)
    can_view_house: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="memberships")
    house: Mapped[House] = relationship(back_populates="memberships")
