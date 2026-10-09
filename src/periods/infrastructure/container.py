"""The periods context's composition root — request-scope wiring."""

from dataclasses import dataclass, field

from cqrs.requests.map import RequestMap
from sqlalchemy.ext.asyncio import AsyncSession

from adjustements.infrastructure.persistence.event_sourced_anomaly_repository import EventSourcedAnomalyRepository
from core.application import ApplicationMediator, HandlerContainer, IUnitOfWork
from core.domain.events import BaseEvent, IEventBus
from core.infrastructure.database import SQLAlchemyUnitOfWork
from core.infrastructure.event_store import EventStore
from core.infrastructure.events import EventBusEmitter
from core.infrastructure.outbox import TransactionalOutbox

from ..application import ClosePeriodCommand, GetPeriodByIdQuery, LockPeriodCommand, OpenPeriodCommand
from ..application.handlers import (
    ClosePeriodHandler,
    GetPeriodByIdHandler,
    LockPeriodHandler,
    OpenPeriodHandler,
)
from ..application.notifications import PERIODS_EVENT_MAPPERS
from .persistence.event_sourced_period_repository import EventSourcedPeriodRepository
from .persistence.period_repository import PeriodRepository


@dataclass
class PeriodsContainer:
    """Request-scope wiring for the periods bounded context.

    Commands load and save aggregates through the event store (write
    database); queries read the read models (read database).
    """

    period_repository: EventSourcedPeriodRepository
    period_read_repository: PeriodRepository
    anomaly_repository: EventSourcedAnomalyRepository
    unit_of_work: IUnitOfWork
    event_bus: IEventBus[BaseEvent]
    event_outbox: TransactionalOutbox | None = None
    _mediator: ApplicationMediator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        request_map = RequestMap()
        request_map.bind(OpenPeriodCommand, OpenPeriodHandler)
        request_map.bind(LockPeriodCommand, LockPeriodHandler)
        request_map.bind(ClosePeriodCommand, ClosePeriodHandler)
        request_map.bind(GetPeriodByIdQuery, GetPeriodByIdHandler)

        self._mediator = ApplicationMediator(
            request_map=request_map,
            container=HandlerContainer(self._resolve_handler),
            event_emitter=EventBusEmitter(self.event_bus),
        )

    def _resolve_handler(self, handler_type: type):
        """Build a handler bound to this request scope."""
        if handler_type is OpenPeriodHandler:
            return OpenPeriodHandler(
                unit_of_work=self.unit_of_work,
                period_repository=self.period_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is LockPeriodHandler:
            return LockPeriodHandler(
                unit_of_work=self.unit_of_work,
                period_repository=self.period_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is ClosePeriodHandler:
            return ClosePeriodHandler(
                unit_of_work=self.unit_of_work,
                period_repository=self.period_repository,
                anomaly_repository=self.anomaly_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is GetPeriodByIdHandler:
            return GetPeriodByIdHandler(period_repository=self.period_read_repository)
        raise TypeError(
            f"No periods-scope wiring for handler {handler_type.__name__}"
        )

    async def send(self, request):
        """Dispatch a periods command/query and return its result."""
        return await self._mediator.send(request)


def build_periods_container(
    *,
    write_session: AsyncSession,
    read_session: AsyncSession,
    event_bus: IEventBus[BaseEvent],
    event_outbox: TransactionalOutbox | None = None,
) -> PeriodsContainer:
    """Build a request-scoped periods container."""
    event_store = EventStore(write_session)
    return PeriodsContainer(
        period_repository=EventSourcedPeriodRepository(event_store),
        period_read_repository=PeriodRepository(read_session),
        anomaly_repository=EventSourcedAnomalyRepository(event_store),
        unit_of_work=SQLAlchemyUnitOfWork(write_session),
        event_bus=event_bus,
        event_outbox=event_outbox
        or TransactionalOutbox(session=write_session, mappers=PERIODS_EVENT_MAPPERS),
    )
