"""Event-store adapter for the AbsenceType aggregate (write side)."""

from core.domain.errors import NotFoundError
from core.infrastructure.event_store import EventStore

from ...domain.entities import AbsenceType
from ...domain.events import AbsenceTypeCreated, AbsenceTypeImported
from ...domain.repositories import IAbsenceTypeRepository
from ...domain.value_objects import AbsenceTypeId

ABSENCE_TYPE_STREAM = "absences.absence_type"

ABSENCE_TYPE_EVENT_TYPES = {
    "absences.absence_type.created": AbsenceTypeCreated,
    "absences.absence_type.imported": AbsenceTypeImported,
}

ABSENCE_TYPE_NAME_SCOPE = "absences.absence_type.name"


class EventSourcedAbsenceTypeRepository(IAbsenceTypeRepository):
    """An absence type is the replay of its stream; its name is a unique key."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, absence_type_id: AbsenceTypeId) -> AbsenceType:
        events = await self._store.load(absence_type_id.value, ABSENCE_TYPE_EVENT_TYPES)
        if not events:
            raise NotFoundError(
                f"Absence type {absence_type_id.value} not found", context=absence_type_id.value
            )
        return AbsenceType.rehydrate(absence_type_id, events)

    async def exists(self, absence_type_id: AbsenceTypeId) -> bool:
        return await self._store.exists(absence_type_id.value, ABSENCE_TYPE_STREAM)

    async def save(self, absence_type: AbsenceType) -> None:
        events = absence_type.domain_events
        stream_id = absence_type.id.value
        # The name is only set at creation (no rename event): reserve it, never release.
        for event in events:
            if isinstance(event, AbsenceTypeCreated | AbsenceTypeImported):
                await self._store.reserve(ABSENCE_TYPE_NAME_SCOPE, event.name, stream_id)
        await self._store.append(
            stream_type=ABSENCE_TYPE_STREAM,
            stream_id=stream_id,
            expected_version=absence_type.version,
            events=events,
        )
        absence_type._advance_version(len(events))

    async def delete(self, absence_type_id: AbsenceTypeId) -> None:
        raise NotImplementedError("Event-sourced absence types are never deleted")
