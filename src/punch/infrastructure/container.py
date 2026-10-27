from dataclasses import dataclass, field

from cqrs.requests.map import RequestMap
from sqlalchemy.ext.asyncio import AsyncSession

from adjustements.application.notifications import ADJUSTMENTS_EVENT_MAPPERS
from adjustements.infrastructure.persistence.event_sourced_anomaly_repository import (
    EventSourcedAnomalyRepository,
)
from core.application import ApplicationMediator, HandlerContainer, IUnitOfWork
from core.domain.events import BaseEvent, IEventBus
from core.infrastructure.database import SQLAlchemyUnitOfWork
from core.infrastructure.event_store import EventStore
from core.infrastructure.events import EventBusEmitter
from core.infrastructure.outbox import TransactionalOutbox
from identity.infrastructure.persistence.event_sourced_employee_assignment_repository import (
    EventSourcedEmployeeAssignmentRepository,
)
from identity.infrastructure.persistence.event_sourced_employee_repository import (
    EventSourcedEmployeeRepository,
)
from identity.infrastructure.persistence.event_sourced_site_repository import (
    EventSourcedSiteRepository,
)
from identity.infrastructure.persistence.event_sourced_user_repository import (
    EventSourcedUserRepository,
)
from punch.application.commands import (
    CreateAssistedTimeEntryCommand,
    CreateManagerTimeEntryCommand,
    CreateTimeEntryCommand,
)
from punch.application.handlers.create_assisted_time_entry_handler import (
    CreateAssistedTimeEntryHandler,
)
from punch.application.handlers.create_manager_time_entry_handler import (
    CreateManagerTimeEntryHandler,
)
from punch.application.handlers.create_time_entry_handler import CreateTimeEntryHandler
from punch.application.handlers.lookup_employee_handler import LookupEmployeeHandler
from punch.application.notifications import PUNCHES_EVENT_MAPPERS
from punch.application.ports import IPhotoStorage
from punch.application.queries import LookupEmployeeQuery
from punch.infrastructure.persistence.event_sourced_time_entry_repository import (
    EventSourcedTimeEntryRepository,
)


@dataclass
class PunchesContainer:
    """Request-scope wiring for the punch bounded context.

    Commands load and save aggregates through the event store (write
    database); queries, when the context has some, read the read models.
    """

    time_entry_repository: EventSourcedTimeEntryRepository
    employee_repository: EventSourcedEmployeeRepository
    site_repository: EventSourcedSiteRepository
    employee_assignment_repository: EventSourcedEmployeeAssignmentRepository
    user_repository: EventSourcedUserRepository
    anomaly_repository: EventSourcedAnomalyRepository
    photo_storage: IPhotoStorage
    unit_of_work: IUnitOfWork
    event_bus: IEventBus[BaseEvent]
    event_outbox: TransactionalOutbox | None = None
    _mediator: ApplicationMediator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        request_map = RequestMap()
        request_map.bind(CreateTimeEntryCommand, CreateTimeEntryHandler)
        request_map.bind(CreateAssistedTimeEntryCommand, CreateAssistedTimeEntryHandler)
        request_map.bind(CreateManagerTimeEntryCommand, CreateManagerTimeEntryHandler)
        request_map.bind(LookupEmployeeQuery, LookupEmployeeHandler)

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
                site_repository=self.site_repository,
                employee_assignment_repository=self.employee_assignment_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is CreateAssistedTimeEntryHandler:
            return CreateAssistedTimeEntryHandler(
                unit_of_work=self.unit_of_work,
                time_entry_repository=self.time_entry_repository,
                employee_repository=self.employee_repository,
                site_repository=self.site_repository,
                employee_assignment_repository=self.employee_assignment_repository,
                anomaly_repository=self.anomaly_repository,
                photo_storage=self.photo_storage,
                event_outbox=self.event_outbox,
            )
        if handler_type is CreateManagerTimeEntryHandler:
            return CreateManagerTimeEntryHandler(
                unit_of_work=self.unit_of_work,
                time_entry_repository=self.time_entry_repository,
                employee_repository=self.employee_repository,
                employee_assignment_repository=self.employee_assignment_repository,
                site_repository=self.site_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is LookupEmployeeHandler:
            return LookupEmployeeHandler(
                employee_repository=self.employee_repository,
                user_repository=self.user_repository,
            )
        raise TypeError(
            f"No punch-scope wiring for handler {handler_type.__name__}"
        )

    async def send(self, request):
        """Dispatch a users command/query and return its result."""
        return await self._mediator.send(request)


def build_punches_container(
    *,
    write_session: AsyncSession,
    read_session: AsyncSession,
    event_bus: IEventBus[BaseEvent],
    photo_storage: IPhotoStorage,
    event_outbox: TransactionalOutbox | None = None,
) -> PunchesContainer:
    """Build a request-scoped punch container.

    ``read_session`` is unused for now: the context has no query handler yet.
    """
    event_store = EventStore(write_session)
    return PunchesContainer(
        employee_repository=EventSourcedEmployeeRepository(event_store),
        site_repository=EventSourcedSiteRepository(event_store),
        employee_assignment_repository=EventSourcedEmployeeAssignmentRepository(event_store),
        time_entry_repository=EventSourcedTimeEntryRepository(event_store),
        user_repository=EventSourcedUserRepository(event_store),
        anomaly_repository=EventSourcedAnomalyRepository(event_store),
        photo_storage=photo_storage,
        unit_of_work=SQLAlchemyUnitOfWork(write_session),
        event_bus=event_bus,
        event_outbox=event_outbox or TransactionalOutbox(session=write_session, mappers=PUNCHES_EVENT_MAPPERS | ADJUSTMENTS_EVENT_MAPPERS),
    )