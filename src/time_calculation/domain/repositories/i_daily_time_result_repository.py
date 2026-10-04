from abc import abstractmethod
from datetime import date

from core.domain.repositories import IRepository
from identity.domain import EmployeeId

from ..entities import DailyTimeResult
from ..value_objects import DailyTimeResultId


class IDailyTimeResultRepository(IRepository[DailyTimeResult, DailyTimeResultId]):

    @abstractmethod
    async def find_by_employee_and_date(self, employee_id: EmployeeId, work_date: date) -> DailyTimeResult | None:
        ...
