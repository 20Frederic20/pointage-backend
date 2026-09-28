from collections import defaultdict
from collections.abc import Callable

from core.domain.events import BaseEvent
from core.domain.events.event_bus_schema import IEventBus


class InProcessEventBus(IEventBus[BaseEvent]):
    """Synchronous in-process event bus.

    Subscribers are keyed by event TYPE. Delivery is direct and blocking —
    appropriate for the template slice; a production bus would fan out via
    Redis / Celery / a transactional outbox.
    """

    def __init__(self) -> None:
        self._subscribers: dict[type[BaseEvent], list[Callable[[BaseEvent], None]]] = (
            defaultdict(list)
        )

    def publish(self, event: BaseEvent) -> None:
        for callback in self._subscribers[type(event)]:
            callback(event)

    def subscribe(
        self, event_type: type[BaseEvent], callback: Callable[[BaseEvent], None]
    ) -> None:
        self._subscribers[event_type].append(callback)

    def unsubscribe(
        self, event_type: type[BaseEvent], callback: Callable[[BaseEvent], None]
    ) -> None:
        try:
            self._subscribers[event_type].remove(callback)
        except ValueError:
            pass
