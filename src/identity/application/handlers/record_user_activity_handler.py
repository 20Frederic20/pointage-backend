"""Presence stamping — called by auth on login/refresh (D5)."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import User
from ...domain.repositories import IUserRepository
from ...domain.value_objects.ids import UserId
from ..commands import RecordUserActivityCommand


class RecordUserActivityHandler(
    CommandHandler[RecordUserActivityCommand, None]
):
    """Fire-and-forget telemetry: returns nothing, records no events."""

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        user_repository: IUserRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._users = user_repository

    async def _execute(
        self, request: RecordUserActivityCommand
    ) -> tuple[None, Sequence[AggregateRoot]]:
        user = await self._users.get_by_id(UserId(request.user_id))
        user.record_activity()
        return None, [user]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, User):
            await self._users.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")