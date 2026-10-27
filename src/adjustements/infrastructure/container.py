"""The adjustements context's composition root — request-scope wiring."""

from dataclasses import dataclass, field

from cqrs.requests.map import RequestMap
from sqlalchemy.ext.asyncio import AsyncSession

from core.application import ApplicationMediator, HandlerContainer, IUnitOfWork
from core.domain.events import BaseEvent, IEventBus
from core.infrastructure.database import SQLAlchemyUnitOfWork
from core.infrastructure.event_store import EventStore
from core.infrastructure.events import EventBusEmitter
from core.infrastructure.outbox import TransactionalOutbox
from identity.infrastructure.persistence.event_sourced_employee_repository import (
    EventSourcedEmployeeRepository,
)
from punch.application.notifications import PUNCHES_EVENT_MAPPERS
from punch.application.ports import IPhotoStorage
from punch.infrastructure.persistence.event_sourced_time_entry_repository import (
    EventSourcedTimeEntryRepository,
)

from ..application.commands import DecideAnomalyCommand
from ..application.handlers import DecideAnomalyHandler, GetAnomaliesHandler, GetAnomalyByIdHandler
from ..application.notifications import ADJUSTMENTS_EVENT_MAPPERS
from ..application.ports import IAnomalyReadRepository
from ..application.queries import GetAnomaliesQuery, GetAnomalyByIdQuery
from .persistence.anomaly_read_repository import AnomalyReadRepository
from .persistence.event_sourced_anomaly_repository import EventSourcedAnomalyRepository


@dataclass
class AdjustementsContainer:
    """Request-scope wiring for the adjustements bounded context.

    Commands load and save aggregates through the event store (write
    database); queries read the read models.
    """

    anomaly_repository: EventSourcedAnomalyRepository
    time_entry_repository: EventSourcedTimeEntryRepository
    employee_repository: EventSourcedEmployeeRepository
    anomaly_read_repository: IAnomalyReadRepository
    photo_storage: IPhotoStorage
    unit_of_work: IUnitOfWork
    event_bus: IEventBus[BaseEvent]
    event_outbox: TransactionalOutbox | None = None
    _mediator: ApplicationMediator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        request_map = RequestMap()
        request_map.bind(DecideAnomalyCommand, DecideAnomalyHandler)
        request_map.bind(GetAnomaliesQuery, GetAnomaliesHandler)
        request_map.bind(GetAnomalyByIdQuery, GetAnomalyByIdHandler)

        self._mediator = ApplicationMediator(
            request_map=request_map,
            container=HandlerContainer(self._resolve_handler),
            event_emitter=EventBusEmitter(self.event_bus),
        )

    def _resolve_handler(self, handler_type: type):
        """Build a handler bound to this request scope."""
        if handler_type is DecideAnomalyHandler:
            return DecideAnomalyHandler(
                unit_of_work=self.unit_of_work,
                anomaly_repository=self.anomaly_repository,
                time_entry_repository=self.time_entry_repository,
                employee_repository=self.employee_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type in (GetAnomaliesHandler, GetAnomalyByIdHandler):
            return handler_type(anomaly_read_repository=self.anomaly_read_repository)
        raise TypeError(f"No adjustements-scope wiring for handler {handler_type.__name__}")

    async def send(self, request):
        """Dispatch an adjustements command/query and return its result."""
        return await self._mediator.send(request)


def build_adjustements_container(
    *,
    write_session: AsyncSession,
    read_session: AsyncSession,
    event_bus: IEventBus[BaseEvent],
    photo_storage: IPhotoStorage,
    event_outbox: TransactionalOutbox | None = None,
) -> AdjustementsContainer:
    """Build a request-scoped adjustements container."""
    event_store = EventStore(write_session)
    return AdjustementsContainer(
        anomaly_repository=EventSourcedAnomalyRepository(event_store),
        time_entry_repository=EventSourcedTimeEntryRepository(event_store),
        employee_repository=EventSourcedEmployeeRepository(event_store),
        anomaly_read_repository=AnomalyReadRepository(read_session),
        photo_storage=photo_storage,
        unit_of_work=SQLAlchemyUnitOfWork(write_session),
        event_bus=event_bus,
        event_outbox=event_outbox
        or TransactionalOutbox(session=write_session, mappers=ADJUSTMENTS_EVENT_MAPPERS | PUNCHES_EVENT_MAPPERS),
    )
