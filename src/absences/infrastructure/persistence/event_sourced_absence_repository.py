"""Event-store adapter for the Absence aggregate (write side)."""

from datetime import datetime

from sqlalchemy import select

from core.domain.errors import NotFoundError
from core.domain.events import encode_datetime
from core.infrastructure.event_store import EventModel, EventStore
from identity.domain import EmployeeId

from ...domain.entities import Absence
from ...domain.events import (
    AbsenceApproved,
    AbsenceDeclared,
    AbsenceImported,
    AbsenceRejected,
)
from ...domain.repositories import IAbsenceRepository
from ...domain.value_objects import AbsenceId, AbsenceStatus

ABSENCE_STREAM = "absences.absence"

ABSENCE_EVENT_TYPES = {
    "absences.absence.declared": AbsenceDeclared,
    "absences.absence.approved": AbsenceApproved,
    "absences.absence.rejected": AbsenceRejected,
    "absences.absence.imported": AbsenceImported,
}


class EventSourcedAbsenceRepository(IAbsenceRepository):
    """An absence is the replay of its stream; lookups query the payloads."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, absence_id: AbsenceId) -> Absence:
        events = await self._store.load(absence_id.value, ABSENCE_EVENT_TYPES)
        if not events:
            raise NotFoundError(f"Absence {absence_id.value} not found", context=absence_id.value)
        return Absence.rehydrate(absence_id, events)

    async def exists(self, absence_id: AbsenceId) -> bool:
        return await self._store.exists(absence_id.value, ABSENCE_STREAM)

    async def find_approved_by_employee_between(
        self, employee_id: EmployeeId, start: datetime, end: datetime
    ) -> list[Absence]:
        # Employee and period are set by the first event and never change;
        # the status is checked on the replayed state.
        start_at = EventModel.payload["start_at"].astext
        end_at = EventModel.payload["end_at"].astext
        stream_ids = list(
            (
                await self._store.session.scalars(
                    select(EventModel.stream_id)
                    .where(
                        EventModel.stream_type == ABSENCE_STREAM,
                        EventModel.stream_version == 1,
                        EventModel.payload.contains({"employee_id": employee_id.value}),
                        start_at < encode_datetime(end),
                        end_at > encode_datetime(start),
                    )
                    .order_by(EventModel.global_position)
                )
            ).all()
        )
        streams = await self._store.load_streams(stream_ids, ABSENCE_EVENT_TYPES)
        absences = [Absence.rehydrate(AbsenceId(stream_id), events) for stream_id, events in streams.items()]
        return [absence for absence in absences if absence.status == AbsenceStatus.APPROVED]

    async def save(self, absence: Absence) -> None:
        events = absence.domain_events
        await self._store.append(
            stream_type=ABSENCE_STREAM,
            stream_id=absence.id.value,
            expected_version=absence.version,
            events=events,
        )
        absence._advance_version(len(events))

    async def delete(self, absence_id: AbsenceId) -> None:
        raise NotImplementedError("Event-sourced absences are never deleted")
