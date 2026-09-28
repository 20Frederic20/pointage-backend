from typing import Any

from cqrs.container.protocol import Container
from cqrs.events.event_emitter import EventEmitter
from cqrs.mediator import RequestMediator
from cqrs.requests.map import RequestMap
from cqrs.requests.request import IRequest


class ApplicationMediator:
    """CQRS facade over python-cqrs' ``RequestMediator``.

    Bundles the static request→handler map, the per-request ``Container``, and
    the event emitter so callers just ``await mediator.send(request)``. One
    instance is built per request scope by the bounded context's composition
    root (see ``inbox.InboxContainer``).
    """

    def __init__(
        self,
        *,
        request_map: RequestMap,
        container: Container,
        event_emitter: EventEmitter | None = None,
    ) -> None:
        self._mediator = RequestMediator(
            request_map=request_map,
            container=container,
            event_emitter=event_emitter,
        )

    async def send(self, request: IRequest) -> Any:
        """Dispatch a command/query to its handler and return its response."""
        return await self._mediator.send(request)
