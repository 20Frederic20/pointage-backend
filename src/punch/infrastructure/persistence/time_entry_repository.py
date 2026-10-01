"""SQLAlchemy adapter for the TimeEntry aggregate."""

from datetime import UTC, datetime

from sqlalchemy import delete, insert, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError
from identity.domain import EmployeeId
from identity.domain.value_objects.location import Location
from punch.domain import EntryType

from ...domain.entities import TimeEntry
from ...domain.repositories import ITimeEntryRepository
from ...domain.value_objects.ids import TimeEntryId
from .models import TimeEntryModel


class TimeEntryRepository(ITimeEntryRepository):
    """Same versioned save protocol as :class:`UserRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, time_entry_id: TimeEntryId) -> TimeEntry:
        row = await self._session.get(TimeEntryModel, time_entry_id.value)
        if row is None:
            raise NotFoundError(
                f"TimeEntry {time_entry_id} not found",
                context=time_entry_id.value,
            )
        return self._to_aggregate(row)

    async def exists(self, time_entry_id: TimeEntryId) -> bool:
        row = await self._session.scalar(
            select(TimeEntryModel.id).where(TimeEntryModel.id == time_entry_id.value)
        )
        return row is not None

    async def exists_any(self) -> bool:
        row = await self._session.scalar(select(TimeEntryModel.id).limit(1))
        return row is not None

    async def exists_by_employee_id_and_entry_type(self, employee_id: EmployeeId, entry_type: EntryType) -> bool:
        row = await self._session.scalar(
            select(TimeEntryModel.id).where(
                TimeEntryModel.employee_id == employee_id.value,
                TimeEntryModel.entry_type == entry_type
            ).limit(1)
        )
        return row is not None

    async def exists_by_employee_id_and_occured_at(self, employee_id: EmployeeId, occured_at: datetime) -> bool:
        row = await self._session.scalar(
            select(TimeEntryModel.id).where(
                or_(
                    TimeEntryModel.employee_id == employee_id.value,
                    TimeEntryModel.occured_at == occured_at
                )
            ).limit(1)
        )
        return row is not None

    async def save(self, time_entry: TimeEntry) -> None:
        if time_entry.version == 0:
            await self._insert(time_entry)
        time_entry._advance_version()

    async def delete(self, time_entry_id: TimeEntryId) -> None:
        await self._session.execute(
            delete(TimeEntryModel).where(TimeEntryModel.id == time_entry_id.value)
        )

    async def _insert(self, time_entry: TimeEntry) -> None:
        try:
            await self._session.execute(
                insert(TimeEntryModel).values(
                    id=time_entry.id.value,
                    employee_id=time_entry.employee_id.value,
                    entry_type=time_entry.entry_type,
                    occured_at=time_entry.occured_at,
                    location=time_entry.location.to_wkt(),
                    location_confidence=time_entry.location_confidence,
                    source=time_entry.source,
                    idempotency_key=time_entry.idempotency_key,
                    wifi_identifier=time_entry.wifi_identifier or None,
                    created_at=time_entry.created_at or datetime.now(UTC),
                    updated_at=time_entry.updated_at or datetime.now(UTC),
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"TimeEntry {time_entry.id} already exists",
                context=time_entry.id.value,
            ) from exc

    def _to_aggregate(self, row) -> TimeEntry:

        location = Location(row.location)
        return TimeEntry(
            TimeEntryId(row.id),
            employee_id=EmployeeId(row.employee_id),
            occured_at=row.occured_at,
            entry_type=row.entry_type,
            location=location,
            location_confidence=row.location_confidence,
            source=row.source,
            idempotency_key=row.idempotency_key,
            wifi_identifier=row.wifi_identifier or None,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version,
        )
