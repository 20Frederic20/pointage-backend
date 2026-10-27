"""Event-store adapter for the TimeEntry aggregate (write side)."""

from datetime import datetime

from sqlalchemy import select

from core.domain.errors import NotFoundError
from core.domain.events import encode_datetime
from core.infrastructure.event_store import EventModel, EventStore
from identity.domain import EmployeeId
from punch.domain import EntryType, TimeEntryValidationStatus

from ...domain.entities import TimeEntry
from ...domain.events import TimeEntryCreated, TimeEntryImported, TimeEntryRejected, TimeEntryValidated
from ...domain.repositories import ITimeEntryRepository
from ...domain.value_objects.ids import TimeEntryId

TIME_ENTRY_STREAM = "punch.time_entry"

IDEMPOTENCY_KEY_SCOPE = "punch.idempotency_key"

TIME_ENTRY_EVENT_TYPES = {
    "punchs.time_entry.created": TimeEntryCreated,
    "punchs.time_entry.imported": TimeEntryImported,
    "punchs.time_entry.validated": TimeEntryValidated,
    "punchs.time_entry.rejected": TimeEntryRejected,
}


class EventSourcedTimeEntryRepository(ITimeEntryRepository):
    """A time entry is the replay of its stream; lookups query the payloads."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, time_entry_id: TimeEntryId) -> TimeEntry:
        events = await self._store.load(time_entry_id.value, TIME_ENTRY_EVENT_TYPES)
        if not events:
            raise NotFoundError(f"TimeEntry {time_entry_id} not found", context=time_entry_id.value)
        return TimeEntry.rehydrate(time_entry_id, events)

    async def exists(self, time_entry_id: TimeEntryId) -> bool:
        return await self._store.exists(time_entry_id.value, TIME_ENTRY_STREAM)

    async def exists_by_employee_id_and_entry_type(self, employee_id: EmployeeId, entry_type: EntryType) -> bool:
        ids = await self._store.find_stream_ids(
            TIME_ENTRY_STREAM, {"employee_id": employee_id.value, "entry_type": entry_type.value}
        )
        return bool(ids)

    async def exists_by_employee_id_and_occured_at(self, employee_id: EmployeeId, occured_at: datetime) -> bool:
        ids = await self._store.find_stream_ids(
            TIME_ENTRY_STREAM, {"employee_id": employee_id.value, "occured_at": encode_datetime(occured_at)}
        )
        return bool(ids)

    async def find_last_by_employee_id(self, employee_id: EmployeeId) -> TimeEntry | None:
        """The newest entry that was not rejected (a rejected punch never happened)."""
        stream_ids = (
            await self._store.session.scalars(
                self._employee_entries(employee_id).order_by(EventModel.payload["occured_at"].astext.desc())
            )
        ).all()
        for stream_id in stream_ids:
            entry = await self.get_by_id(TimeEntryId(stream_id))
            if entry.validation_status != TimeEntryValidationStatus.REJECTED:
                return entry
        return None

    async def reserve_idempotency_key(self, idempotency_key: str, time_entry_id: TimeEntryId) -> None:
        await self._store.reserve(IDEMPOTENCY_KEY_SCOPE, idempotency_key, time_entry_id.value)

    async def find_by_employee_between(
        self, employee_id: EmployeeId, start: datetime, end: datetime
    ) -> list[TimeEntry]:
        occured_at = EventModel.payload["occured_at"].astext
        stream_ids = list(
            (
                await self._store.session.scalars(
                    self._employee_entries(employee_id)
                    .where(occured_at >= encode_datetime(start), occured_at < encode_datetime(end))
                    .order_by(occured_at)
                )
            ).all()
        )
        streams = await self._store.load_streams(stream_ids, TIME_ENTRY_EVENT_TYPES)
        return [TimeEntry.rehydrate(TimeEntryId(stream_id), events) for stream_id, events in streams.items()]

    def _employee_entries(self, employee_id: EmployeeId):
        # Only the first event carries the punch (a time entry never changes).
        return select(EventModel.stream_id).where(
            EventModel.stream_type == TIME_ENTRY_STREAM,
            EventModel.stream_version == 1,
            EventModel.payload.contains({"employee_id": employee_id.value}),
        )

    async def save(self, time_entry: TimeEntry) -> None:
        events = time_entry.domain_events
        await self._store.append(
            stream_type=TIME_ENTRY_STREAM,
            stream_id=time_entry.id.value,
            expected_version=time_entry.version,
            events=events,
        )
        time_entry._advance_version(len(events))

    async def delete(self, time_entry_id: TimeEntryId) -> None:
        raise NotImplementedError("Event-sourced time entries are never deleted")
