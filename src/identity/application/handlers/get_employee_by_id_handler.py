"""Load one employee by id."""

from core.application import QueryHandler
from core.domain.errors import InvalidEntityIdError, NotFoundError

from ...domain import EmployeeId
from ...domain.repositories import IEmployeeRepository
from ..dtos import EmployeeDTO
from ..queries import GetEmployeeByIdQuery


class GetEmployeeByIdHandler(QueryHandler[GetEmployeeByIdQuery, EmployeeDTO | None]):
    """A malformed id cannot name an employee: it is a miss, not a 4xx of its own."""

    def __init__(self, *, employee_repository: IEmployeeRepository) -> None:
        super().__init__()
        self._employees = employee_repository

    async def handle(self, request: GetEmployeeByIdQuery) -> EmployeeDTO | None:
        try:
            employee = await self._employees.get_by_id(EmployeeId(request.employee_id))
        except (InvalidEntityIdError, NotFoundError):
            return None
        return EmployeeDTO.from_aggregate(employee)
