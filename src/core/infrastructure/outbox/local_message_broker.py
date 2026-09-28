from collections.abc import Mapping

from cqrs.dispatcher.event import EventDispatcher
from cqrs.events.event import IEvent
from cqrs.message_brokers.protocol import Message, MessageBroker


class LocalMessageBroker(MessageBroker):
    """``MessageBroker`` that delivers inside the same process.

    Rehydrates the notification event from the message payload (via the
    event-name registry) and hands it to the cqrs ``EventDispatcher``, which
    resolves and runs the consumer handlers. This is the zero-infrastructure
    default — a deployment with a real broker swaps this class for a
    cqrs-backed broker (kafka / amqp) plus a consuming worker, and nothing
    upstream of the broker changes.

    ``event_registry`` maps ``event_name`` → notification event type; it is
    the consume-side mirror of the write-side mappers in
    ``TransactionalOutbox``.
    """

    def __init__(
        self,
        *,
        dispatcher: EventDispatcher,
        event_registry: Mapping[str, type[IEvent]],
    ) -> None:
        self._dispatcher = dispatcher
        self._event_registry = event_registry

    async def send_message(self, message: Message) -> None:
        event_type = self._event_registry.get(message.message_name)
        if event_type is None:
            raise TypeError(
                f"No notification event registered for {message.message_name!r}; "
                f"add it to the consumer-side event registry"
            )
        event = event_type.from_dict(**message.payload)
        await self._dispatcher.dispatch(event)
