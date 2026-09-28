from collections.abc import Sequence
from typing import cast

from cqrs.events.event import IEvent
from cqrs.events.event_emitter import EventEmitter

from core.domain.events import BaseEvent
from core.domain.events.event_bus_schema import IEventBus


class EventBusEmitter(EventEmitter):
    """cqrs event emitter that publishes handler events to the shared IEventBus.

    The request mediator's event processor calls :meth:`emit` for every event a
    handler records (drained from aggregates after the unit of work commits).
    In-process delivery is synchronous and produces no follow-up events; a
    production emitter would fan out via Redis / a broker / an outbox instead.
    """

    def __init__(self, bus: IEventBus[BaseEvent]) -> None:
        self._bus = bus

    async def emit(self, event: IEvent) -> Sequence[IEvent]:
        self._bus.publish(cast(BaseEvent, event))
        return ()
