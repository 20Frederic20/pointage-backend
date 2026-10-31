from dataclasses import dataclass
from datetime import date, datetime

from core.application import DTO

from ...domain.entities import EmployeeAssignment


@dataclass(frozen=True)
class EmployeeAssignmentDTO(DTO):
    id: str
    employee_id: str
    directory_id: str
    site_id: str
    start_date: date
    end_date: date | None = None
    site_name: str | None = None
    directory_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_aggregate(
        cls,
        employee_assignment: EmployeeAssignment,
        *,
        site_name: str | None = None,
        directory_name: str | None = None,
    ) -> "EmployeeAssignmentDTO":
        return cls(
            id=employee_assignment.id.value,
            employee_id=employee_assignment.employee_id.value,
            directory_id=employee_assignment.directory_id.value,
            site_id=employee_assignment.site_id.value,
            start_date=employee_assignment.start_date,
            end_date=employee_assignment.end_date,
            site_name=site_name,
            directory_name=directory_name,
            created_at=employee_assignment.created_at,
            updated_at=employee_assignment.updated_at,
        )
