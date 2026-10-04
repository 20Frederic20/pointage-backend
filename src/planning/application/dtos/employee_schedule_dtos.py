from dataclasses import dataclass
from datetime import date, datetime

from core.application import DTO

from ...domain.entities import EmployeeSchedule


@dataclass(frozen=True)
class EmployeeScheduleDTO(DTO):
    id: str
    employee_id: str
    time_profile_version_id: str
    start_date: date
    end_date: date | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_aggregate(cls, employee_schedule: EmployeeSchedule) -> "EmployeeScheduleDTO":
        return cls(
            id=employee_schedule.id.value,
            employee_id=employee_schedule.employee_id.value,
            time_profile_version_id=employee_schedule.time_profile_version_id.value,
            start_date=employee_schedule.start_date,
            end_date=employee_schedule.end_date,
            created_at=employee_schedule.created_at,
            updated_at=employee_schedule.updated_at,
        )
