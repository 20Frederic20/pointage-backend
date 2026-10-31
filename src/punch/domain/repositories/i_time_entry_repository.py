from abc import abstractmethod
from datetime import datetime

from core.domain.repositories import IRepository
from identity.domain import EmployeeId
from punch.domain import TimeEntryId
from punch.domain.entities import TimeEntry
from punch.domain.value_objects import EntryType


class ITimeEntryRepository(IRepository[TimeEntry, TimeEntryId]):

    async def exists_by_employee_id_and_occured_at(self, employee_id: EmployeeId, occured_at: datetime) -> bool:
        ...

    async def exists_by_employee_id_and_entry_type(self, employee_id: EmployeeId, entry_type: EntryType) -> bool:
        ...

    async def find_last_by_employee_id(self, employee_id: EmployeeId) -> TimeEntry | None:
        ...

    @abstractmethod
    async def reserve_idempotency_key(self, idempotency_key: str, time_entry_id: TimeEntryId) -> None:
        """Take ``idempotency_key`` for ``time_entry_id`` in the command's transaction;
        ``ConflictError`` if another time entry holds it."""

    @abstractmethod
    async def find_by_employee_between(
        self, employee_id: EmployeeId, start: datetime, end: datetime
    ) -> list[TimeEntry]:
        """Entries of an employee with ``start <= occured_at < end``, oldest first."""
        ...
