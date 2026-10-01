from datetime import datetime

from core.domain.repositories import IRepository
from identity.domain import EmployeeId
from punch.domain import TimeEntryId
from punch.domain.entities import TimeEntry
from punch.domain.value_objects import EntryType


class TimeEntryRepository(IRepository[TimeEntry, TimeEntryId]):

    async def exists_by_employee_id_and_occured_at(self, employee_id: EmployeeId, occured_at: datetime) -> bool:
        ...

    async def exists_by_employee_id_and_entry_type(self, employee_id: EmployeeId, entry_type: EntryType) -> bool:
        ...