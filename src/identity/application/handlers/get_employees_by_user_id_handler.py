"""Every employee record of an account: what the login chooses from."""

from core.application import QueryHandler

from ...domain.repositories import IEmployeeRepository
from ...domain.specifications import EmployeeUserIs
from ..dtos import EmployeeDTO
from ..queries import GetEmployeesByUserIdQuery
from ..services import EmployeeEnricher

# An account works for a handful of companies at most.
_MAX_RECORDS = 50


class GetEmployeesByUserIdHandler(QueryHandler[GetEmployeesByUserIdQuery, tuple[EmployeeDTO, ...]]):
    def __init__(self, *, employee_repository: IEmployeeRepository, enricher: EmployeeEnricher | None = None) -> None:
        super().__init__()
        self._employees = employee_repository
        self._enricher = enricher or EmployeeEnricher()

    async def handle(self, request: GetEmployeesByUserIdQuery) -> tuple[EmployeeDTO, ...]:
        employees = await self._employees.find(EmployeeUserIs(request.user_id), limit=_MAX_RECORDS)
        return tuple([await self._enricher.to_dto(employee) for employee in employees])
