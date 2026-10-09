"""Event-store adapter for the Anomaly aggregate (write side)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import aliased

from core.domain.errors import NotFoundError
from core.domain.events import encode_datetime
from core.infrastructure.event_store import EventModel, EventStore
from identity.domain import EmployeeId

from ...domain.entities import Anomaly
from ...domain.events import AnomalyCreated, AnomalyImported, AnomalyResolved
from ...domain.repositories import IAnomalyRepository
from ...domain.value_objects import AnomalyId, AnomalyStatus, Severity

ANOMALY_STREAM = "adjustements.anomaly"

ANOMALY_EVENT_TYPES = {
    "adjustments.anomaly.created": AnomalyCreated,
    "adjustments.anomaly.resolved": AnomalyResolved,
    "adjustments.anomaly.imported": AnomalyImported,
}

# Stream type of punch's time entries (see EventSourcedTimeEntryRepository).
_TIME_ENTRY_STREAM = "punch.time_entry"

_OPEN_STATUSES = (AnomalyStatus.OPEN, AnomalyStatus.IN_PROGRESS)


class EventSourcedAnomalyRepository(IAnomalyRepository):
    """An anomaly is the replay of its stream; lookups query the creation payloads."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, aggregate_id: AnomalyId) -> Anomaly:
        events = await self._store.load(aggregate_id.value, ANOMALY_EVENT_TYPES)
        if not events:
            raise NotFoundError(f"Anomaly {aggregate_id} not found", context=aggregate_id.value)
        return Anomaly.rehydrate(aggregate_id, events)

    async def exists(self, aggregate_id: AnomalyId) -> bool:
        return await self._store.exists(aggregate_id.value, ANOMALY_STREAM)

    async def exists_open_blocking_between(self, start: datetime, end: datetime) -> bool:
        statement = self._detected_between(start, end).where(
            EventModel.payload.contains({"severity": Severity.BLOCKING.value})
        )
        return any(anomaly.status in _OPEN_STATUSES for anomaly in await self._load(statement))

    async def find_open_by_employee_between(
        self, employee_id: EmployeeId, start: datetime, end: datetime
    ) -> list[Anomaly]:
        # The employee lives on the time entry: its first punch event carries it.
        time_entry = aliased(EventModel)
        employee_entries = select(time_entry.stream_id).where(
            time_entry.stream_type == _TIME_ENTRY_STREAM,
            time_entry.stream_version == 1,
            time_entry.payload.contains({"employee_id": employee_id.value}),
        )
        statement = self._detected_between(start, end).where(
            EventModel.payload["time_entry_id"].astext.in_(employee_entries)
        )
        return [anomaly for anomaly in await self._load(statement) if anomaly.status in _OPEN_STATUSES]

    def _detected_between(self, start: datetime, end: datetime):
        # Only the first event (created / imported) carries what never changes:
        # time entry, severity, detection time.
        detected_at = EventModel.payload["detected_at"].astext
        return (
            select(EventModel.stream_id)
            .where(
                EventModel.stream_type == ANOMALY_STREAM,
                EventModel.stream_version == 1,
                detected_at >= encode_datetime(start),
                detected_at < encode_datetime(end),
            )
            .order_by(detected_at, EventModel.stream_id)
        )

    async def _load(self, statement) -> list[Anomaly]:
        stream_ids = list((await self._store.session.scalars(statement)).all())
        streams = await self._store.load_streams(stream_ids, ANOMALY_EVENT_TYPES)
        return [Anomaly.rehydrate(AnomalyId(stream_id), events) for stream_id, events in streams.items()]

    async def save(self, aggregate: Anomaly) -> None:
        events = aggregate.domain_events
        await self._store.append(
            stream_type=ANOMALY_STREAM,
            stream_id=aggregate.id.value,
            expected_version=aggregate.version,
            events=events,
        )
        aggregate._advance_version(len(events))

    async def delete(self, aggregate_id: AnomalyId) -> None:
        raise NotImplementedError("Event-sourced anomalies are never deleted")
