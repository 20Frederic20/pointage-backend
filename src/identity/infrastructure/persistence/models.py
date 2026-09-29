"""ORM models of the users bounded context (D10: unprefixed table names)."""

from datetime import datetime

from geoalchemy2 import Geography
from shapely.geometry import Point
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from core.infrastructure.database import BaseModel

from ...domain.value_objects.role import Role


class DirectoryModel(BaseModel):
    __tablename__ = "directories"

    code: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Point] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False
    )


class UserModel(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, native_enum=False, length=16), nullable=False
    )
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
