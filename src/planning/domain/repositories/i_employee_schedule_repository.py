from abc import abstractmethod
from datetime import date

from core.domain.repositories import IRepository
from identity.domain import EmployeeId

from ..entities import EmployeeSchedule
from ..value_objects import EmployeeScheduleId


class IEmployeeScheduleRepository(IRepository[EmployeeSchedule, EmployeeScheduleId]):

    @abstractmethod
    async def exists_overlapping(
        self,
        employee_id: EmployeeId,
        start_date: date,
        end_date: date | None,
        *,
        excluding: EmployeeScheduleId | None = None,
    ) -> bool:
        ...

    @abstractmethod
    async def find_applicable(self, employee_id: EmployeeId, day: date) -> EmployeeSchedule | None:
        ...

    @abstractmethod
    async def find_employee_ids_between(self, start_date: date, end_date: date) -> list[EmployeeId]:
        """Employees with a schedule overlapping ``[start_date, end_date]``."""
        ...
