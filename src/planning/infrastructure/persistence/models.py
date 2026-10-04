from datetime import date, time, timedelta

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Interval, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from core.infrastructure.database import BaseModel


class TimeProfileModel(BaseModel):
    __tablename__ = "time_profiles"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TimeProfileVersionModel(BaseModel):
    __tablename__ = "time_profile_versions"

    time_profile_id: Mapped[str] = mapped_column(String(32), ForeignKey("time_profiles.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class TimeProfileDayModel(BaseModel):
    __tablename__ = "time_profile_days"

    time_profile_version_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("time_profile_versions.id"), nullable=False, index=True
    )
    day_of_week: Mapped[str] = mapped_column(String(16), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_duration: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    break_threshold: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    tolerance: Mapped[timedelta] = mapped_column(Interval, nullable=False)


class EmployeeScheduleModel(BaseModel):
    __tablename__ = "employee_schedules"

    employee_id: Mapped[str] = mapped_column(String(32), ForeignKey("employees.id"), nullable=False, index=True)
    time_profile_version_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("time_profile_versions.id"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
