from dataclasses import dataclass

from core.application import Query
from punch.application.dtos import EmployeeLookupDTO


@dataclass(frozen=True)
class LookupEmployeeQuery(Query):
    """Confirm an employee number before an assisted punch (names only)."""

    actor_user_id: str
    employee_number: str

    Result = EmployeeLookupDTO
