"""List an employee's assignments, most recent first."""

from dataclasses import dataclass

from core.application import Query

from ..dtos import EmployeeAssignmentDTO


@dataclass(frozen=True)
class GetEmployeeAssignmentsQuery(Query):

    employee_id: str

    Result = tuple[EmployeeAssignmentDTO, ...]
