from abc import abstractmethod
from datetime import datetime

from adjustements.domain import Anomaly, AnomalyId
from core.domain.repositories import IRepository
from identity.domain import EmployeeId


class IAnomalyRepository(IRepository[Anomaly, AnomalyId]):

    @abstractmethod
    async def exists_open_blocking_between(self, start: datetime, end: datetime) -> bool:
        """Whether a BLOCKING anomaly still OPEN or IN_PROGRESS was detected in ``[start, end)``."""
        ...

    @abstractmethod
    async def find_open_by_employee_between(
        self, employee_id: EmployeeId, start: datetime, end: datetime
    ) -> list[Anomaly]:
        """OPEN or IN_PROGRESS anomalies of an employee detected in ``[start, end)``."""
        ...
