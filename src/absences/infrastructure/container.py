"""The absences context's composition root — request-scope wiring."""

from dataclasses import dataclass, field

from cqrs.requests.map import RequestMap
from sqlalchemy.ext.asyncio import AsyncSession

from adjustements.infrastructure.persistence.anomaly_repository import AnomalyRepository
from core.application import ApplicationMediator, HandlerContainer, IUnitOfWork
from core.domain.events import BaseEvent, IEventBus
from core.infrastructure.database import SQLAlchemyUnitOfWork
from core.infrastructure.events import EventBusEmitter
from core.infrastructure.outbox import TransactionalOutbox
from identity.infrastructure.persistence.employee_repository import EmployeeRepository
from punch.infrastructure.persistence.time_entry_repository import TimeEntryRepository

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
from .persistence.absence_type_repository import AbsenceTypeRepository


@dataclass
class AbsencesContainer:
    """Request-scope wiring for the absences bounded context."""

    absence_repository: AbsenceRepository
    absence_type_repository: AbsenceTypeRepository
    employee_repository: EmployeeRepository
    anomaly_repository: AnomalyRepository
    time_entry_repository: TimeEntryRepository
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
            return GetAbsenceByIdHandler(absence_repository=self.absence_repository)
        raise TypeError(
            f"No absences-scope wiring for handler {handler_type.__name__}"
        )

    async def send(self, request):
        """Dispatch an absences command/query and return its result."""
        return await self._mediator.send(request)


def build_absences_container(
    *,
    session: AsyncSession,
    event_bus: IEventBus[BaseEvent],
    event_outbox: TransactionalOutbox | None = None,
) -> AbsencesContainer:
    """Build a request-scoped absences container."""
    return AbsencesContainer(
        absence_repository=AbsenceRepository(session),
        absence_type_repository=AbsenceTypeRepository(session),
        employee_repository=EmployeeRepository(session),
        anomaly_repository=AnomalyRepository(session),
        time_entry_repository=TimeEntryRepository(session),
        unit_of_work=SQLAlchemyUnitOfWork(session),
        event_bus=event_bus,
        event_outbox=event_outbox
        or TransactionalOutbox(session=session, mappers=ABSENCES_EVENT_MAPPERS),
    )
