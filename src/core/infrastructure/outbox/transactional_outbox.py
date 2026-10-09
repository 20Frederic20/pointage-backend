from collections.abc import Callable, Mapping

from cqrs.events.event import INotificationEvent
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.application.outbox import IEventOutbox
from core.domain.events import BaseEvent

from .models import OutboxModel


class TransactionalOutbox(IEventOutbox):
    """``IEventOutbox`` over the request-scoped SQLAlchemy session.

    The row insert shares the handler's session — and therefore the handler's
    transaction — so the aggregate write and its events commit atomically.
    That is the transactional outbox guarantee: the two cannot diverge.

    Domain events become *integration events* (cqrs
    ``INotificationEvent``) via the ``mappers`` registry each bounded context
    wires in its composition root — the domain event itself never leaves the
    process, and not every domain event has to become an integration event:
    a context maps such an event to ``None`` explicitly (an unmapped event is
    still an error, so a new event is never silently dropped).
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        mappers: Mapping[type[BaseEvent], Callable[[BaseEvent], INotificationEvent] | None],
    ) -> None:
        self._session = session
        self._mappers = mappers

    def add(self, event: BaseEvent) -> None:
        if type(event) not in self._mappers:
            raise TypeError(
                f"No notification-event mapping registered for {type(event).__name__}; "
                f"add one to the context's outbox mappers to publish it "
                f"(or map it to None to keep it inside the context)"
            )
        mapper = self._mappers[type(event)]
        if mapper is None:
            return  # explicitly internal: stored in the event store, never published
        notification = mapper(event)
        self._session.add(
            OutboxModel(
                event_id=event.event_id,
                event_name=notification.event_name,
                topic=notification.topic,
                payload=notification.to_dict(),
            )
        )
