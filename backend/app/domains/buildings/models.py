from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.domains.auth.models import House, User


class OwnedBuilding(Base):
    __tablename__ = "owned_buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    house_id: Mapped[int | None] = mapped_column(ForeignKey("houses.id"), index=True)
    building_definition_id: Mapped[str] = mapped_column(String(120), index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped["User"] = relationship(back_populates="owned_buildings")
    house: Mapped["House | None"] = relationship(back_populates="owned_buildings")
