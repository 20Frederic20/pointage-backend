"""Paged member listing, filtered at the storage by specification."""

from core.application import QueryHandler
from core.domain.specifications import Specification

from ...domain.entities import Employee
from ...domain.repositories import IEmployeeRepository
from ...domain.specifications import (
    EmployeeEmployeeNumberIs,
    EmployeeIsActiveIs,
    EmployeeRoleIs,
)
from ..dtos import EmployeesPageDTO
from ..services import EmployeeEnricher
from ..queries import GetEmployeesQuery


class GetEmployeesHandler(QueryHandler[GetEmployeesQuery, EmployeesPageDTO]):
    """Combines the directory leaf spec with any optional filters and lets
    the repository translate the tree — no in-Python filtering."""

    def __init__(self, *, employee_repository: IEmployeeRepository, enricher: EmployeeEnricher | None = None) -> None:
        super().__init__()
        self._employees = employee_repository
        self._enricher = enricher or EmployeeEnricher()

    async def handle(self, request: GetEmployeesQuery) -> EmployeesPageDTO:
        spec: Specification[Employee] | None = None
        for leaf in (
            EmployeeRoleIs(request.role) if request.role is not None else None,
            EmployeeIsActiveIs(request.is_active) if request.is_active is not None else None,
            EmployeeEmployeeNumberIs(request.employee_number) if request.employee_number else None,
        ):
            if leaf is not None:
                spec = leaf if spec is None else spec & leaf

        employees = await self._employees.find(
            spec, limit=request.limit, offset=request.offset
        )
        total = await self._employees.count(spec)
        return EmployeesPageDTO(
            items=tuple([await self._enricher.to_dto(employee) for employee in employees]),
            total=total,
        )
