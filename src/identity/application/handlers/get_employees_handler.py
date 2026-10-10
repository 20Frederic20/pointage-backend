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
from ..dtos import EmployeeDTO, EmployeesPageDTO
from ..queries import GetEmployeesQuery


class GetEmployeesHandler(QueryHandler[GetEmployeesQuery, EmployeesPageDTO]):
    """Combines the directory leaf spec with any optional filters and lets
    the repository translate the tree — no in-Python filtering."""

    def __init__(self, *, employee_repository: IEmployeeRepository) -> None:
        super().__init__()
        self._employees = employee_repository

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
            items=tuple(EmployeeDTO.from_aggregate(u) for u in employees),
            total=total,
        )
