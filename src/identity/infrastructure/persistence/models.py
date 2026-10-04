"""ORM models of the users bounded context (D10: unprefixed table names)."""

from datetime import date, datetime

from geoalchemy2 import Geography
from shapely.geometry import Point
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from core.infrastructure.database import BaseModel

from ...domain.value_objects.role import Role


class SiteModel(BaseModel):
    __tablename__ = "sites"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DirectoryModel(BaseModel):
    __tablename__ = "directories"

    code: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Point] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False
    )
    site_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("sites.id"), nullable=False, index=True
    )
    parent_directory_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("directories.id"), nullable=True, index=True
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


class EmployeeModel(BaseModel):
    __tablename__ = "employees"

    role: Mapped[Role] = mapped_column(
        SAEnum(Role, native_enum=False, length=16), nullable=False
    )
    employee_number: Mapped[str] = mapped_column(String(32))
    phone: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id"), nullable=False, index=True
    )


class EmployeeAssignmentModel(BaseModel):
    __tablename__ = "employee_assignments"

    employee_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("employees.id"), nullable=False, index=True
    )
    directory_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("directories.id"), nullable=False, index=True
    )
    site_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("sites.id"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

