from dataclasses import field, dataclass

from cqrs.requests.map import RequestMap
from sqlalchemy.ext.asyncio import AsyncSession
from core.infrastructure.database import SQLAlchemyUnitOfWork

from core.application import ApplicationMediator, HandlerContainer, IUnitOfWork
from core.domain.events import BaseEvent, IEventBus
from core.infrastructure.events import EventBusEmitter
from core.infrastructure.outbox import TransactionalOutbox
from identity.infrastructure.persistence.directory_repository import DirectoryRepository
from identity.infrastructure.persistence.employee_assignment_repository import EmployeeAssignmentRepository
from identity.infrastructure.persistence.employee_repository import EmployeeRepository
from punch.application.commands import CreateTimeEntryCommand
from punch.application.handlers.create_time_entry_handler import CreateTimeEntryHandler
from punch.application.notifications import PUNCHES_EVENT_MAPPERS
from punch.infrastructure.persistence.time_entry_repository import TimeEntryRepository


@dataclass
class PunchesContainer:
    """Request-scope wiring for the punch bounded context."""

    time_entry_repository: TimeEntryRepository
    employee_repository: EmployeeRepository
    directory_repository: DirectoryRepository
    employee_assignment_repository: EmployeeAssignmentRepository
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
                employee_repository=self.employee_repository,
                directory_repository=self.directory_repository,
                employee_assignment_repository=self.employee_assignment_repository,
                event_outbox=self.event_outbox,
            )
        raise TypeError(
            f"No punch-scope wiring for handler {handler_type.__name__}"
        )

    async def send(self, request):
        """Dispatch a users command/query and return its result."""
        return await self._mediator.send(request)


def build_punches_container(
    *,
    session: AsyncSession,
    event_bus: IEventBus[BaseEvent],
    event_outbox: TransactionalOutbox | None = None,
) -> PunchesContainer:
    """Build a request-scoped punch container."""
    return PunchesContainer(
        employee_repository=EmployeeRepository(session),
        directory_repository=DirectoryRepository(session),
        employee_assignment_repository=EmployeeAssignmentRepository(session),
        time_entry_repository=TimeEntryRepository(session),
        unit_of_work=SQLAlchemyUnitOfWork(session),
        event_bus=event_bus,
        event_outbox=event_outbox or TransactionalOutbox(session=session, mappers=PUNCHES_EVENT_MAPPERS),
    )