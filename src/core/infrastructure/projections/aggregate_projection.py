from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.entity import AggregateRoot
from core.domain.repositories import IRepository
from core.infrastructure.event_store import EventModel, EventTypes, to_event


class AggregateProjection:
    """Keeps one read-model table in step with one kind of stream.

    The read model is the state-table repository of the aggregate (the one
    query handlers read). For each stored event the projection loads the
    row's aggregate, applies the event exactly as the write side did, and
    saves it back: the row's ``version_id`` always equals the stream version
    it reflects, so an event already applied is skipped.

    Configured per aggregate in each context's ``infrastructure/projections.py``
    (like the outbox mappers), never subclassed.
    """

    def __init__(
        self,
        *,
        stream_type: str,
        aggregate_type: type[AggregateRoot],
        id_type: Callable[[str], object],
        repository_type: Callable[[AsyncSession], IRepository],
        event_types: EventTypes,
    ) -> None:
        self.stream_type = stream_type
        self._aggregate_type = aggregate_type
        self._id_type = id_type
        self._repository_type = repository_type
        self._event_types = event_types

    async def project(self, session: AsyncSession, row: EventModel) -> None:
        event = to_event(row, self._event_types)
        aggregate_id = self._id_type(row.stream_id)
        repository = self._repository_type(session)
        if row.stream_version == 1:
            if await repository.exists(aggregate_id):
                return
            aggregate = self._aggregate_type.rehydrate(aggregate_id, [])
        else:
            aggregate = await repository.get_by_id(aggregate_id)
            if aggregate.version >= row.stream_version:
                return
        aggregate.apply(event)
        await repository.save(aggregate)
