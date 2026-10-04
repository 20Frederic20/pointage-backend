"""The planning context's composition root — request-scope wiring."""

from dataclasses import dataclass, field

from cqrs.requests.map import RequestMap
from sqlalchemy.ext.asyncio import AsyncSession

from core.application import ApplicationMediator, HandlerContainer, IUnitOfWork
from core.domain.events import BaseEvent, IEventBus
from core.infrastructure.database import SQLAlchemyUnitOfWork
from core.infrastructure.events import EventBusEmitter
from core.infrastructure.outbox import TransactionalOutbox
from identity.infrastructure.persistence.employee_repository import EmployeeRepository

from ..application import (
    AddTimeProfileVersionCommand,
    AssignEmployeeScheduleCommand,
    CreateTimeProfileCommand,
    EndEmployeeScheduleCommand,
    GetTimeProfileByIdQuery,
)
from ..application.handlers import (
    AddTimeProfileVersionHandler,
    AssignEmployeeScheduleHandler,
    CreateTimeProfileHandler,
    EndEmployeeScheduleHandler,
    GetTimeProfileByIdHandler,
)
from ..application.notifications import PLANNING_EVENT_MAPPERS
from .persistence.employee_schedule_repository import EmployeeScheduleRepository
from .persistence.time_profile_repository import TimeProfileRepository


@dataclass
class PlanningContainer:
    """Request-scope wiring for the planning bounded context."""

    time_profile_repository: TimeProfileRepository
    employee_schedule_repository: EmployeeScheduleRepository
    employee_repository: EmployeeRepository
    unit_of_work: IUnitOfWork
    event_bus: IEventBus[BaseEvent]
    event_outbox: TransactionalOutbox | None = None
    _mediator: ApplicationMediator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        request_map = RequestMap()
        request_map.bind(CreateTimeProfileCommand, CreateTimeProfileHandler)
        request_map.bind(AddTimeProfileVersionCommand, AddTimeProfileVersionHandler)
        request_map.bind(AssignEmployeeScheduleCommand, AssignEmployeeScheduleHandler)
        request_map.bind(EndEmployeeScheduleCommand, EndEmployeeScheduleHandler)
        request_map.bind(GetTimeProfileByIdQuery, GetTimeProfileByIdHandler)

        self._mediator = ApplicationMediator(
            request_map=request_map,
            container=HandlerContainer(self._resolve_handler),
            event_emitter=EventBusEmitter(self.event_bus),
        )

    def _resolve_handler(self, handler_type: type):
        """Build a handler bound to this request scope."""
        if handler_type in (CreateTimeProfileHandler, AddTimeProfileVersionHandler):
            return handler_type(
                unit_of_work=self.unit_of_work,
                time_profile_repository=self.time_profile_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is AssignEmployeeScheduleHandler:
            return AssignEmployeeScheduleHandler(
                unit_of_work=self.unit_of_work,
                employee_schedule_repository=self.employee_schedule_repository,
                time_profile_repository=self.time_profile_repository,
                employee_repository=self.employee_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is EndEmployeeScheduleHandler:
            return EndEmployeeScheduleHandler(
                unit_of_work=self.unit_of_work,
                employee_schedule_repository=self.employee_schedule_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is GetTimeProfileByIdHandler:
            return GetTimeProfileByIdHandler(time_profile_repository=self.time_profile_repository)
        raise TypeError(
            f"No planning-scope wiring for handler {handler_type.__name__}"
        )

    async def send(self, request):
        """Dispatch a planning command/query and return its result."""
        return await self._mediator.send(request)


def build_planning_container(
    *,
    session: AsyncSession,
    event_bus: IEventBus[BaseEvent],
    event_outbox: TransactionalOutbox | None = None,
) -> PlanningContainer:
    """Build a request-scoped planning container."""
    return PlanningContainer(
        time_profile_repository=TimeProfileRepository(session),
        employee_schedule_repository=EmployeeScheduleRepository(session),
        employee_repository=EmployeeRepository(session),
        unit_of_work=SQLAlchemyUnitOfWork(session),
        event_bus=event_bus,
        event_outbox=event_outbox
        or TransactionalOutbox(session=session, mappers=PLANNING_EVENT_MAPPERS),
    )
