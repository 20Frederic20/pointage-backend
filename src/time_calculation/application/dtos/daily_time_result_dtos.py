from dataclasses import dataclass
from datetime import date, datetime, timedelta

from core.application import DTO

from ...domain.entities import DailyTimeResult


@dataclass(frozen=True)
class DailyTimeResultDTO(DTO):
    id: str
    employee_id: str
    period_id: str
    calculation_rule_version_id: str
    work_date: date
    planned_duration: timedelta
    worked_duration: timedelta
    break_duration: timedelta
    absence_duration: timedelta
    late_duration: timedelta
    status: str
    calculated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_aggregate(cls, daily_time_result: DailyTimeResult) -> "DailyTimeResultDTO":
        return cls(
            id=daily_time_result.id.value,
            employee_id=daily_time_result.employee_id.value,
            period_id=daily_time_result.period_id.value,
            calculation_rule_version_id=daily_time_result.calculation_rule_version_id.value,
            work_date=daily_time_result.work_date,
            planned_duration=daily_time_result.planned_duration,
            worked_duration=daily_time_result.worked_duration,
            break_duration=daily_time_result.break_duration,
            absence_duration=daily_time_result.absence_duration,
            late_duration=daily_time_result.late_duration,
            status=daily_time_result.status.value,
            calculated_at=daily_time_result.calculated_at,
            created_at=daily_time_result.created_at,
            updated_at=daily_time_result.updated_at,
        )


@dataclass(frozen=True)
class PeriodRecalculationDTO(DTO):
    period_id: str
    recalculated_count: int
    skipped_validated_count: int
