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

from collections.abc import Callable

from cqrs.dispatcher.event import EventDispatcher
from cqrs.events.map import EventMap

from core.application import HandlerContainer
from core.infrastructure.outbox import LocalMessageBroker, OutboxRelay
from core.infrastructure.outbox.outbox_relay import SessionFactory

# Notification event → consumer class. Empty until a context publishes
# events worth delivering — nothing reaches the broker until a producing
# context wires its mappers into a TransactionalOutbox.
_EVENT_MAP: dict[type, type] = {}

# Consumer class → zero-arg factory (keeps the resolver dumb).
_CONSUMER_FACTORIES: dict[type, Callable[[], object]] = {}

# Outbox event_name → notification class, for broker-side rehydration.
_EVENT_REGISTRY: dict[str, type] = {}


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
