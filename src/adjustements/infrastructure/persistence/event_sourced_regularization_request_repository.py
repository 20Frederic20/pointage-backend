"""Event-store adapter for the RegularizationRequest aggregate (write side)."""

from core.domain.errors import NotFoundError
from core.infrastructure.event_store import EventStore

from ...domain.entities import RegularizationRequest
from ...domain.events import RegularizationRequestCreated, RegularizationRequestImported
from ...domain.repositories import IRegularizationRequestRepository
from ...domain.value_objects import RegularizationRequestId

REGULARIZATION_REQUEST_STREAM = "adjustements.regularization_request"

REGULARIZATION_REQUEST_EVENT_TYPES = {
    "adjustments.regularization_request.created": RegularizationRequestCreated,
    "adjustments.regularization_request.imported": RegularizationRequestImported,
}


class EventSourcedRegularizationRequestRepository(IRegularizationRequestRepository):
    """A regularization request is the replay of its stream."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, aggregate_id: RegularizationRequestId) -> RegularizationRequest:
        events = await self._store.load(aggregate_id.value, REGULARIZATION_REQUEST_EVENT_TYPES)
        if not events:
            raise NotFoundError(f"Regularization request {aggregate_id} not found", context=aggregate_id.value)
        return RegularizationRequest.rehydrate(aggregate_id, events)

    async def exists(self, aggregate_id: RegularizationRequestId) -> bool:
        return await self._store.exists(aggregate_id.value, REGULARIZATION_REQUEST_STREAM)

    async def save(self, aggregate: RegularizationRequest) -> None:
        events = aggregate.domain_events
        await self._store.append(
            stream_type=REGULARIZATION_REQUEST_STREAM,
            stream_id=aggregate.id.value,
            expected_version=aggregate.version,
            events=events,
        )
        aggregate._advance_version(len(events))

    async def delete(self, aggregate_id: RegularizationRequestId) -> None:
        raise NotImplementedError("Event-sourced regularization requests are never deleted")
