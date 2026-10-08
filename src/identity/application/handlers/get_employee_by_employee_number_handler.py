"""Login support: resolve an employee number to its employee record, if any."""

from core.application import QueryHandler

from ...domain.repositories import IEmployeeRepository
from ..dtos import EmployeeDTO
from ..queries import GetEmployeeByEmployeeNumberQuery


class GetEmployeeByEmployeeNumberHandler(
    QueryHandler[GetEmployeeByEmployeeNumberQuery, EmployeeDTO | None]
):
    """Returns ``None`` for unknown employee numbers."""

    def __init__(self, *, employee_repository: IEmployeeRepository) -> None:
        super().__init__()
        self._employees = employee_repository

    async def handle(self, request: GetEmployeeByEmployeeNumberQuery) -> EmployeeDTO | None:
        employee = await self._employees.find_by_employee_number(request.employee_number)
        if employee is None:
            return None
        return EmployeeDTO.from_aggregate(employee)
