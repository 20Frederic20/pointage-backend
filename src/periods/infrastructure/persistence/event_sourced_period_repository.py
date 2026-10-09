"""Event-store adapter for the Period aggregate (write side)."""

from datetime import date

from sqlalchemy import select

from core.domain.errors import NotFoundError
from core.domain.events import encode_date
from core.infrastructure.event_store import EventModel, EventStore

from ...domain.entities import Period
from ...domain.events import PeriodClosed, PeriodImported, PeriodLocked, PeriodOpened
from ...domain.repositories import IPeriodRepository
from ...domain.value_objects import PeriodId

PERIOD_STREAM = "periods.period"

PERIOD_EVENT_TYPES = {
    "periods.period.opened": PeriodOpened,
    "periods.period.locked": PeriodLocked,
    "periods.period.closed": PeriodClosed,
    "periods.period.imported": PeriodImported,
}


class EventSourcedPeriodRepository(IPeriodRepository):
    """A period is the replay of its stream; date lookups query the first event's payload."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, period_id: PeriodId) -> Period:
        events = await self._store.load(period_id.value, PERIOD_EVENT_TYPES)
        if not events:
            raise NotFoundError(f"Period {period_id.value} not found", context=period_id.value)
        return Period.rehydrate(period_id, events)

    async def exists(self, period_id: PeriodId) -> bool:
        return await self._store.exists(period_id.value, PERIOD_STREAM)

    async def exists_overlapping(self, start_date: date, end_date: date) -> bool:
        stream_id = await self._store.session.scalar(self._overlapping(start_date, end_date).limit(1))
        return stream_id is not None

    async def find_containing(self, day: date) -> Period | None:
        stream_id = await self._store.session.scalar(self._overlapping(day, day).limit(1))
        return await self.get_by_id(PeriodId(stream_id)) if stream_id is not None else None

    def _overlapping(self, start_date: date, end_date: date):
        # Only the first event (opened / imported) carries the dates, which never change;
        # ISO dates compare correctly as text.
        return select(EventModel.stream_id).where(
            EventModel.stream_type == PERIOD_STREAM,
            EventModel.stream_version == 1,
            EventModel.payload["start_date"].astext <= encode_date(end_date),
            EventModel.payload["end_date"].astext >= encode_date(start_date),
        )

    async def save(self, period: Period) -> None:
        events = period.domain_events
        await self._store.append(
            stream_type=PERIOD_STREAM,
            stream_id=period.id.value,
            expected_version=period.version,
            events=events,
        )
        period._advance_version(len(events))

    async def delete(self, period_id: PeriodId) -> None:
        raise NotImplementedError("Event-sourced periods are never deleted")
