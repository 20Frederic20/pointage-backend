from abc import ABC, abstractmethod
from collections.abc import Callable

from .base_event import BaseEvent


class IEventBus[EventT: BaseEvent](ABC):
    """Port for dispatching domain events out of the application layer.

    Concrete buses are infrastructure concerns (in-process bus, Redis pub/sub,
    Celery, transactional outbox). Subscribe by event TYPE, not by instance.
    """

    @abstractmethod
    def publish(self, event: EventT) -> None:
        """Dispatch a single event to all subscribers."""
        ...

    @abstractmethod
    def subscribe(
        self, event_type: type[EventT], callback: Callable[[EventT], None]
    ) -> None:
        """Register a callback for all events of ``event_type``."""
        ...

    @abstractmethod
    def unsubscribe(
        self, event_type: type[EventT], callback: Callable[[EventT], None]
    ) -> None:
        """Remove a previously registered callback."""
        ...
