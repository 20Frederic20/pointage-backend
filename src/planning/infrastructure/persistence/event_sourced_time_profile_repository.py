"""Event-store adapter for the TimeProfile aggregate (write side).

Versions and days live inside the profile's stream: ``UNIQUE (time_profile_id,
version)`` and ``UNIQUE (time_profile_version_id, day_of_week)`` are invariants
of the aggregate itself, so no unique keys are reserved.
"""

from sqlalchemy import or_, select

from core.domain.errors import NotFoundError
from core.infrastructure.event_store import EventModel, EventStore

from ...domain.entities import TimeProfile
from ...domain.events import TimeProfileCreated, TimeProfileImported, TimeProfileVersionAdded
from ...domain.repositories import ITimeProfileRepository
from ...domain.value_objects import TimeProfileId, TimeProfileVersionId

TIME_PROFILE_STREAM = "planning.time_profile"

TIME_PROFILE_EVENT_TYPES = {
    "planning.time_profile.created": TimeProfileCreated,
    "planning.time_profile.version_added": TimeProfileVersionAdded,
    "planning.time_profile.imported": TimeProfileImported,
}


class EventSourcedTimeProfileRepository(ITimeProfileRepository):
    """A time profile is the replay of its stream; version ids are found in the payloads."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, time_profile_id: TimeProfileId) -> TimeProfile:
        events = await self._store.load(time_profile_id.value, TIME_PROFILE_EVENT_TYPES)
        if not events:
            raise NotFoundError(
                f"Time profile {time_profile_id.value} not found", context=time_profile_id.value
            )
        return TimeProfile.rehydrate(time_profile_id, events)

    async def exists(self, time_profile_id: TimeProfileId) -> bool:
        return await self._store.exists(time_profile_id.value, TIME_PROFILE_STREAM)

    async def find_by_version_id(self, time_profile_version_id: TimeProfileVersionId) -> TimeProfile | None:
        value = time_profile_version_id.value
        stream_id = await self._store.session.scalar(
            select(EventModel.stream_id)
            .where(
                EventModel.stream_type == TIME_PROFILE_STREAM,
                or_(
                    EventModel.payload.contains({"time_profile_version_id": value}),
                    EventModel.payload.contains({"versions": [{"id": value}]}),
                ),
            )
            .limit(1)
        )
        return await self.get_by_id(TimeProfileId(stream_id)) if stream_id is not None else None

    async def save(self, time_profile: TimeProfile) -> None:
        events = time_profile.domain_events
        await self._store.append(
            stream_type=TIME_PROFILE_STREAM,
            stream_id=time_profile.id.value,
            expected_version=time_profile.version,
            events=events,
        )
        time_profile._advance_version(len(events))

    async def delete(self, time_profile_id: TimeProfileId) -> None:
        raise NotImplementedError("Event-sourced time profiles are never deleted")
