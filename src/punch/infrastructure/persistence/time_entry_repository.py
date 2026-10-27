"""SQLAlchemy adapter for the TimeEntry aggregate."""

from datetime import UTC, datetime

from sqlalchemy import delete, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError
from identity.domain import EmployeeId, UserId
from identity.domain.value_objects.location import Location
from punch.domain import EntryType, TimeEntryValidationStatus

from ...domain.entities import TimeEntry
from ...domain.repositories import ITimeEntryRepository
from ...domain.value_objects.ids import TimeEntryId
from .models import TimeEntryModel


def _to_aggregate(row) -> TimeEntry:

    location = Location.from_wkt(row.location) if row.location is not None else None
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
        assisted_by_user_id=UserId(row.assisted_by_user_id) if row.assisted_by_user_id else None,
        photo_key=row.photo_key,
        validation_status=TimeEntryValidationStatus(row.validation_status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        version=row.version_id,
    )


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
        return _to_aggregate(row)

    async def reserve_idempotency_key(self, idempotency_key: str, time_entry_id: TimeEntryId) -> None:
        """The state table has no reservation table: refuse a key another entry holds."""
        holder = await self._session.scalar(
            select(TimeEntryModel.id).where(
                TimeEntryModel.idempotency_key == idempotency_key, TimeEntryModel.id != time_entry_id.value
            )
        )
        if holder is not None:
            raise ConflictError(f"Idempotency key already used by {holder}", context=idempotency_key)

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

    async def find_last_by_employee_id(self, employee_id: EmployeeId) -> TimeEntry | None:
        row = await self._session.scalar(
            select(TimeEntryModel)
            .where(
                TimeEntryModel.employee_id == employee_id.value,
                TimeEntryModel.validation_status != TimeEntryValidationStatus.REJECTED,
            )
            .order_by(TimeEntryModel.occured_at.desc())
            .limit(1)
        )
        return _to_aggregate(row) if row is not None else None

    async def find_by_employee_between(
        self, employee_id: EmployeeId, start: datetime, end: datetime
    ) -> list[TimeEntry]:
        rows = await self._session.scalars(
            select(TimeEntryModel)
            .where(
                TimeEntryModel.employee_id == employee_id.value,
                TimeEntryModel.occured_at >= start,
                TimeEntryModel.occured_at < end,
            )
            .order_by(TimeEntryModel.occured_at)
        )
        return [_to_aggregate(row) for row in rows.all()]

    async def save(self, time_entry: TimeEntry) -> None:
        if time_entry.version == 0:
            await self._insert(time_entry)
        else:
            await self._update(time_entry)
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
                    location=time_entry.location.to_wkt() if time_entry.location else None,
                    location_confidence=time_entry.location_confidence,
                    source=time_entry.source,
                    idempotency_key=time_entry.idempotency_key,
                    wifi_identifier=time_entry.wifi_identifier or None,
                    assisted_by_user_id=time_entry.assisted_by_user_id.value if time_entry.assisted_by_user_id else None,
                    photo_key=time_entry.photo_key,
                    validation_status=time_entry.validation_status,
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

    async def _update(self, time_entry: TimeEntry) -> None:
        """Only the validation status changes after a punch; optimistic on the version."""
        result = await self._session.execute(
            update(TimeEntryModel.__table__)
            .where(TimeEntryModel.id == time_entry.id.value)
            .where(TimeEntryModel.version_id == time_entry.version)
            .values(
                validation_status=time_entry.validation_status,
                updated_at=time_entry.updated_at,
                version_id=time_entry.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"TimeEntry {time_entry.id} was modified concurrently (stale version {time_entry.version})",
                context=time_entry.id.value,
            )
