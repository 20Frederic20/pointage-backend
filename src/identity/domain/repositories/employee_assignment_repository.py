"""Persistence port for the EmployeeAssignment aggregate."""

from abc import abstractmethod
from datetime import date

from core.domain.repositories import IRepository

from ..entities import EmployeeAssignment
from ..value_objects.ids import EmployeeAssignmentId, EmployeeId


class IEmployeeAssignmentRepository(IRepository[EmployeeAssignment, EmployeeAssignmentId]):

    @abstractmethod
    async def exists_overlapping(
        self,
        employee_id: EmployeeId,
        start_date: date,
        end_date: date | None,
        *,
        excluding: EmployeeAssignmentId | None = None,
    ) -> bool:
        ...

    @abstractmethod
    async def find_active(self, employee_id: EmployeeId, day: date) -> EmployeeAssignment | None:
        """The employee's assignment covering ``day`` (at most one)."""
        ...

    @abstractmethod
    async def find_by_employee(self, employee_id: EmployeeId) -> list[EmployeeAssignment]:
        """Every assignment of an employee, most recent first."""
        ...
