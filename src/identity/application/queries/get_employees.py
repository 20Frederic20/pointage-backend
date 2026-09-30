from dataclasses import dataclass

from core.application import Query

from ...domain.value_objects import Role
from ..dtos import EmployeesPageDTO


@dataclass(frozen=True)
class GetEmployeesQuery(Query):

    employee_number: str | None = None
    role: Role | None = None
    is_active: bool | None = None
    limit: int = 50
    offset: int = 0

    Result = EmployeesPageDTO