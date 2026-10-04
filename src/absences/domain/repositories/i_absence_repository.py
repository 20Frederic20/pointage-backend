from abc import abstractmethod
from datetime import datetime

from core.domain.repositories import IRepository
from identity.domain import EmployeeId

from ..entities import Absence
from ..value_objects import AbsenceId


class IAbsenceRepository(IRepository[Absence, AbsenceId]):

    @abstractmethod
    async def find_approved_by_employee_between(
        self, employee_id: EmployeeId, start: datetime, end: datetime
    ) -> list[Absence]:
        """Approved absences of an employee overlapping ``[start, end)``."""
        ...
