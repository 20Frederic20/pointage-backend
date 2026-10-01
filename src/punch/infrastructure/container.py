from dataclasses import field

from cqrs.requests.map import RequestMap

from core.application import ApplicationMediator, HandlerContainer, IUnitOfWork
from core.domain.events import BaseEvent, IEventBus
from core.infrastructure.events import EventBusEmitter
from core.infrastructure.outbox import TransactionalOutbox
from punch.application.commands import CreateTimeEntryCommand
from punch.application.handlers.create_time_entry_handler import CreateTimeEntryHandler
from punch.infrastructure.persistence.time_entry_repository import TimeEntryRepository


class PunchContainer:
    """Request-scope wiring for the punch bounded context."""

    time_entry_repository: TimeEntryRepository
    unit_of_work: IUnitOfWork
    event_bus: IEventBus[BaseEvent]
    event_outbox: TransactionalOutbox | None = None
    _mediator: ApplicationMediator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        request_map = RequestMap()
        request_map.bind(CreateTimeEntryCommand, CreateTimeEntryHandler)

        self._mediator = ApplicationMediator(
            request_map=request_map,
            container=HandlerContainer(self._resolve_handler),
            event_emitter=EventBusEmitter(self.event_bus),
        )

    def _resolve_handler(self, handler_type: type):
        """Build a handler bound to this request scope."""
        if handler_type is CreateTimeEntryHandler:
            return CreateTimeEntryHandler(
                unit_of_work=self.unit_of_work,
                time_entry_repository=self.time_entry_repository,
                event_outbox=self.event_outbox,
            )
        raise TypeError(
            f"No punch-scope wiring for handler {handler_type.__name__}"
        )
