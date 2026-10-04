from datetime import date, datetime, timedelta

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Interval, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.infrastructure.database import BaseModel


class CalculationRuleVersionModel(BaseModel):
    __tablename__ = "calculation_rule_versions"

    rule_version: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    min_break_duration: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    break_threshold: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    max_daily_work_duration: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    max_amplitude: Mapped[timedelta] = mapped_column(Interval, nullable=False)


class DailyTimeResultModel(BaseModel):
    __tablename__ = "daily_time_results"
    __table_args__ = (UniqueConstraint("employee_id", "work_date"),)

    employee_id: Mapped[str] = mapped_column(String(32), ForeignKey("employees.id"), nullable=False)
    period_id: Mapped[str] = mapped_column(String(32), ForeignKey("periods.id"), nullable=False, index=True)
    calculation_rule_version_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("calculation_rule_versions.id"), nullable=False
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_duration: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    worked_duration: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    break_duration: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    absence_duration: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    late_duration: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
