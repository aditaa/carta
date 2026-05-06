import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.domains.buildings.models import OwnedBuilding


class DenizenRole(enum.StrEnum):
    read_only = "read_only"
    member = "member"
    manager = "manager"
    admin = "admin"


class Denizen(Base):
    __tablename__ = "denizens"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[DenizenRole] = mapped_column(
        Enum(DenizenRole),
        default=DenizenRole.read_only,
    )
    religion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    primary_house_id: Mapped[int | None] = mapped_column(ForeignKey("houses.id"), nullable=True)
    primary_kingdom_id: Mapped[int | None] = mapped_column(
        ForeignKey("kingdoms.id"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    memberships: Mapped[list["HouseMembership"]] = relationship(
        back_populates="denizen",
        cascade="all, delete-orphan",
    )
    owned_buildings: Mapped[list["OwnedBuilding"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    kingdom_memberships: Mapped[list["KingdomMembership"]] = relationship(
        back_populates="denizen",
        cascade="all, delete-orphan",
        foreign_keys="KingdomMembership.denizen_id",
    )
    holdings: Mapped[list["DenizenHolding"]] = relationship(
        back_populates="denizen",
        cascade="all, delete-orphan",
    )
    house_held_holdings: Mapped[list["HouseDenizenHolding"]] = relationship(
        back_populates="denizen",
        cascade="all, delete-orphan",
    )


class House(Base):
    __tablename__ = "houses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    kingdom_id: Mapped[int | None] = mapped_column(ForeignKey("kingdoms.id"), nullable=True)
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
    kingdom: Mapped["Kingdom | None"] = relationship(back_populates="houses")
    holdings: Mapped[list["HouseHolding"]] = relationship(
        back_populates="house",
        cascade="all, delete-orphan",
    )
    denizen_holdings: Mapped[list["HouseDenizenHolding"]] = relationship(
        back_populates="house",
        cascade="all, delete-orphan",
    )


class Kingdom(Base):
    __tablename__ = "kingdoms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    houses: Mapped[list["House"]] = relationship(back_populates="kingdom")
    memberships: Mapped[list["KingdomMembership"]] = relationship(
        back_populates="kingdom",
        cascade="all, delete-orphan",
    )
    holdings: Mapped[list["KingdomHolding"]] = relationship(
        back_populates="kingdom",
        cascade="all, delete-orphan",
    )


class HouseMembership(Base):
    __tablename__ = "house_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    denizen_id: Mapped[int] = mapped_column(ForeignKey("denizens.id"), index=True)
    house_id: Mapped[int] = mapped_column(ForeignKey("houses.id"), index=True)
    role: Mapped[DenizenRole] = mapped_column(Enum(DenizenRole), default=DenizenRole.read_only)
    can_view_house: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    denizen: Mapped[Denizen] = relationship(back_populates="memberships")
    house: Mapped[House] = relationship(back_populates="memberships")


class KingdomMembership(Base):
    __tablename__ = "kingdom_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    denizen_id: Mapped[int] = mapped_column(ForeignKey("denizens.id"), index=True)
    kingdom_id: Mapped[int] = mapped_column(ForeignKey("kingdoms.id"), index=True)
    role: Mapped[DenizenRole] = mapped_column(Enum(DenizenRole), default=DenizenRole.read_only)
    can_view_kingdom: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    denizen: Mapped[Denizen] = relationship(back_populates="kingdom_memberships")
    kingdom: Mapped[Kingdom] = relationship(back_populates="memberships")


class DenizenHolding(Base):
    __tablename__ = "denizen_holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    denizen_id: Mapped[int] = mapped_column(ForeignKey("denizens.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(40), index=True)
    item_key: Mapped[str] = mapped_column(String(120), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    denizen: Mapped[Denizen] = relationship(back_populates="holdings")


class HouseHolding(Base):
    __tablename__ = "house_holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    house_id: Mapped[int] = mapped_column(ForeignKey("houses.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(40), index=True)
    item_key: Mapped[str] = mapped_column(String(120), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    house: Mapped[House] = relationship(back_populates="holdings")


class HouseDenizenHolding(Base):
    __tablename__ = "house_denizen_holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    house_id: Mapped[int] = mapped_column(ForeignKey("houses.id"), index=True)
    denizen_id: Mapped[int] = mapped_column(ForeignKey("denizens.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(40), index=True)
    item_key: Mapped[str] = mapped_column(String(120), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    house: Mapped[House] = relationship(back_populates="denizen_holdings")
    denizen: Mapped[Denizen] = relationship(back_populates="house_held_holdings")


class KingdomHolding(Base):
    __tablename__ = "kingdom_holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    kingdom_id: Mapped[int] = mapped_column(ForeignKey("kingdoms.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(40), index=True)
    item_key: Mapped[str] = mapped_column(String(120), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    kingdom: Mapped[Kingdom] = relationship(back_populates="holdings")
