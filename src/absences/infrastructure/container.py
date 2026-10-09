"""The absences context's composition root — request-scope wiring."""

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
from identity.infrastructure.persistence.event_sourced_employee_repository import EventSourcedEmployeeRepository
from punch.infrastructure.persistence.event_sourced_time_entry_repository import EventSourcedTimeEntryRepository

from ..application import (
    ApproveAbsenceCommand,
    CreateAbsenceTypeCommand,
    DeclareAbsenceCommand,
    GetAbsenceByIdQuery,
    NeutralizeAnomalyCommand,
    RejectAbsenceCommand,
)
from ..application.handlers import (
    ApproveAbsenceHandler,
    CreateAbsenceTypeHandler,
    DeclareAbsenceHandler,
    GetAbsenceByIdHandler,
    NeutralizeAnomalyHandler,
    RejectAbsenceHandler,
)
from ..application.notifications import ABSENCES_EVENT_MAPPERS
from .persistence.absence_repository import AbsenceRepository
from .persistence.event_sourced_absence_repository import EventSourcedAbsenceRepository
from .persistence.event_sourced_absence_type_repository import EventSourcedAbsenceTypeRepository


@dataclass
class AbsencesContainer:
    """Request-scope wiring for the absences bounded context.

    Commands load and save aggregates through the event store (write
    database); queries read the read models (read database).
    """

    absence_repository: EventSourcedAbsenceRepository
    absence_type_repository: EventSourcedAbsenceTypeRepository
    employee_repository: EventSourcedEmployeeRepository
    anomaly_repository: EventSourcedAnomalyRepository
    time_entry_repository: EventSourcedTimeEntryRepository
    absence_read_repository: AbsenceRepository
    unit_of_work: IUnitOfWork
    event_bus: IEventBus[BaseEvent]
    event_outbox: TransactionalOutbox | None = None
    _mediator: ApplicationMediator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        request_map = RequestMap()
        request_map.bind(CreateAbsenceTypeCommand, CreateAbsenceTypeHandler)
        request_map.bind(DeclareAbsenceCommand, DeclareAbsenceHandler)
        request_map.bind(ApproveAbsenceCommand, ApproveAbsenceHandler)
        request_map.bind(RejectAbsenceCommand, RejectAbsenceHandler)
        request_map.bind(NeutralizeAnomalyCommand, NeutralizeAnomalyHandler)
        request_map.bind(GetAbsenceByIdQuery, GetAbsenceByIdHandler)

        self._mediator = ApplicationMediator(
            request_map=request_map,
            container=HandlerContainer(self._resolve_handler),
            event_emitter=EventBusEmitter(self.event_bus),
        )

    def _resolve_handler(self, handler_type: type):
        """Build a handler bound to this request scope."""
        if handler_type is CreateAbsenceTypeHandler:
            return CreateAbsenceTypeHandler(
                unit_of_work=self.unit_of_work,
                absence_type_repository=self.absence_type_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is DeclareAbsenceHandler:
            return DeclareAbsenceHandler(
                unit_of_work=self.unit_of_work,
                absence_repository=self.absence_repository,
                absence_type_repository=self.absence_type_repository,
                employee_repository=self.employee_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type in (ApproveAbsenceHandler, RejectAbsenceHandler):
            return handler_type(
                unit_of_work=self.unit_of_work,
                absence_repository=self.absence_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is NeutralizeAnomalyHandler:
            return NeutralizeAnomalyHandler(
                unit_of_work=self.unit_of_work,
                absence_repository=self.absence_repository,
                anomaly_repository=self.anomaly_repository,
                time_entry_repository=self.time_entry_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is GetAbsenceByIdHandler:
            return GetAbsenceByIdHandler(absence_repository=self.absence_read_repository)
        raise TypeError(
            f"No absences-scope wiring for handler {handler_type.__name__}"
        )

    async def send(self, request):
        """Dispatch an absences command/query and return its result."""
        return await self._mediator.send(request)


def build_absences_container(
    *,
    write_session: AsyncSession,
    read_session: AsyncSession,
    event_bus: IEventBus[BaseEvent],
    event_outbox: TransactionalOutbox | None = None,
) -> AbsencesContainer:
    """Build a request-scoped absences container."""
    event_store = EventStore(write_session)
    return AbsencesContainer(
        absence_repository=EventSourcedAbsenceRepository(event_store),
        absence_type_repository=EventSourcedAbsenceTypeRepository(event_store),
        employee_repository=EventSourcedEmployeeRepository(event_store),
        anomaly_repository=EventSourcedAnomalyRepository(event_store),
        time_entry_repository=EventSourcedTimeEntryRepository(event_store),
        absence_read_repository=AbsenceRepository(read_session),
        unit_of_work=SQLAlchemyUnitOfWork(write_session),
        event_bus=event_bus,
        event_outbox=event_outbox
        or TransactionalOutbox(session=write_session, mappers=ABSENCES_EVENT_MAPPERS),
    )
