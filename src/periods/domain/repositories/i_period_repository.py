from abc import abstractmethod
from datetime import date

from core.domain.repositories import IRepository

from ..entities import Period
from ..value_objects import PeriodId


class IPeriodRepository(IRepository[Period, PeriodId]):

    @abstractmethod
    async def exists_overlapping(self, start_date: date, end_date: date) -> bool:
        ...

    @abstractmethod
    async def find_containing(self, day: date) -> Period | None:
        ...
