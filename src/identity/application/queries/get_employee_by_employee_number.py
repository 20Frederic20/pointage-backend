from dataclasses import dataclass

from core.application import Query

from ..dtos import EmployeeDTO


@dataclass(frozen=True)
class GetEmployeeByEmployeeNumberQuery(Query):
    employee_number: str

    Result = EmployeeDTO | None
