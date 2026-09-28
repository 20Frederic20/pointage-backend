from abc import ABC, abstractmethod

from core.domain.events import BaseEvent


class IEventOutbox(ABC):
    """Port for queueing domain events for delivery to external consumers.

    Handlers add events **inside** their unit of work — implementations make
    the outbox write transactional with the aggregate's own write, so an event
    is durably queued only if its state change also committed. If the
    transaction rolls back, the queued event vanishes with it: nothing is ever
    announced to the outside world without its write being durable.

    Actual delivery is asynchronous and at-least-once (a relay worker drains
    the outbox into a message broker); consumers must therefore be idempotent
    — the payload carries ``event_id`` for deduplication.
    """

    @abstractmethod
    def add(self, event: BaseEvent) -> None:
        """Queue ``event`` for external delivery in the current transaction."""
        ...