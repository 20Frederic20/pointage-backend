"""Outbox worker — the consumer-side composition root.

Wires the delivery pipeline with the same manual-DI idiom the request scope
uses: event types are bound to consumer classes in a cqrs ``EventMap``,
consumers are resolved through the shared ``HandlerContainer`` resolver, and
the cqrs ``EventDispatcher`` runs them. The broker default delivers
in-process; a deployment with real infrastructure swaps
``LocalMessageBroker`` for a broker-backed adapter here — everything
upstream (handlers, outbox, relay) is untouched.

Add a consuming context by binding its notification events + consumers below
(see ``users.application.notifications`` / ``users.application.consumers``
for the first real binding).
"""

from cqrs.dispatcher.event import EventDispatcher
from cqrs.events.map import EventMap

from absences.application.consumers import ABSENCES_CONSUMERS
from absences.application.notifications import ABSENCES_EVENT_REGISTRY
from adjustements.application.consumers import ADJUSTMENTS_CONSUMERS
from adjustements.application.notifications import ADJUSTMENTS_EVENT_REGISTRY
from core.application import HandlerContainer
from core.infrastructure.outbox import LocalMessageBroker, OutboxRelay
from core.infrastructure.outbox.outbox_relay import SessionFactory
from identity.application.consumers import USERS_CONSUMERS
from identity.application.notifications import USERS_EVENT_REGISTRY
from punch.application.consumers import PUNCHES_CONSUMERS
from punch.application.notifications import PUNCHES_EVENT_REGISTRY

_EVENT_MAP = {
    **USERS_CONSUMERS,
    **PUNCHES_CONSUMERS,
    **ADJUSTMENTS_CONSUMERS,
    **ABSENCES_CONSUMERS,
}

_CONSUMER_FACTORIES = {
    consumer_type: consumer_type
    for consumer_type in _EVENT_MAP.values()
}

_EVENT_REGISTRY = {
    **USERS_EVENT_REGISTRY,
    **PUNCHES_EVENT_REGISTRY,
    **ADJUSTMENTS_EVENT_REGISTRY,
    **ABSENCES_EVENT_REGISTRY,
}


def build_outbox_worker(
    *,
    session_factory: SessionFactory,
    poll_interval: float = 1.0,
) -> OutboxRelay:
    """Compose the relay: EventMap + HandlerContainer → dispatcher → broker."""
    event_map = EventMap()
    for notification_type, consumer_type in _EVENT_MAP.items():
        event_map.bind(notification_type, consumer_type)

    container = HandlerContainer(lambda type_: _CONSUMER_FACTORIES[type_]())

    broker = LocalMessageBroker(
        dispatcher=EventDispatcher(event_map, container),
        event_registry=dict(_EVENT_REGISTRY),
    )
    return OutboxRelay(
        session_factory=session_factory,
        broker=broker,
        poll_interval=poll_interval,
    )
