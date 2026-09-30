from dataclasses import dataclass

from core.application import Query

from ..dtos import EmployeeDTO


@dataclass(frozen=True)
class GetEmployeeByIdQuery(Query):
    employee_id: str

    Result = EmployeeDTO | None
