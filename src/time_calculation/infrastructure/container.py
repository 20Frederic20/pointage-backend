"""The time calculation context's composition root — request-scope wiring."""

from dataclasses import dataclass, field
from datetime import date, datetime

from cqrs.requests.map import RequestMap
from sqlalchemy.ext.asyncio import AsyncSession

from absences.infrastructure.persistence.event_sourced_absence_repository import EventSourcedAbsenceRepository
from adjustements.infrastructure.persistence.event_sourced_anomaly_repository import EventSourcedAnomalyRepository
from core.application import ApplicationMediator, HandlerContainer, IUnitOfWork
from core.domain.events import BaseEvent, IEventBus
from core.infrastructure.database import SQLAlchemyUnitOfWork
from core.infrastructure.event_store import EventStore
from core.infrastructure.events import EventBusEmitter
from core.infrastructure.outbox import TransactionalOutbox
from identity.domain import EmployeeId
from periods.infrastructure.persistence.event_sourced_period_repository import EventSourcedPeriodRepository
from planning.infrastructure.persistence.event_sourced_employee_schedule_repository import (
    EventSourcedEmployeeScheduleRepository,
)
from planning.infrastructure.persistence.event_sourced_time_profile_repository import (
    EventSourcedTimeProfileRepository,
)
from punch.infrastructure.persistence.event_sourced_time_entry_repository import EventSourcedTimeEntryRepository

from ..application import (
    CalculateDailyTimeCommand,
    CreateCalculationRuleVersionCommand,
    GetDailyTimeResultByIdQuery,
    RecalculatePeriodCommand,
    ValidateDailyTimeResultCommand,
)
from ..application.handlers import (
    CalculateDailyTimeHandler,
    CreateCalculationRuleVersionHandler,
    GetDailyTimeResultByIdHandler,
    RecalculatePeriodHandler,
    ValidateDailyTimeResultHandler,
)
from ..application.notifications import TIME_CALCULATION_EVENT_MAPPERS
from ..application.services import TimeCalculationService
from .persistence.daily_time_result_repository import DailyTimeResultRepository
from .persistence.event_sourced_calculation_rule_version_repository import (
    EventSourcedCalculationRuleVersionRepository,
)
from .persistence.event_sourced_daily_time_result_repository import EventSourcedDailyTimeResultRepository


@dataclass
class TimeCalculationContainer:
    """Request-scope wiring for the time calculation bounded context.

    Commands (and the calculation service they use) load and save aggregates
    through the event store (write database); queries read the read models.
    """

    daily_time_result_repository: EventSourcedDailyTimeResultRepository
    calculation_rule_version_repository: EventSourcedCalculationRuleVersionRepository
    period_repository: EventSourcedPeriodRepository
    employee_schedule_repository: EventSourcedEmployeeScheduleRepository
    time_profile_repository: EventSourcedTimeProfileRepository
    time_entry_repository: EventSourcedTimeEntryRepository
    absence_repository: EventSourcedAbsenceRepository
    anomaly_repository: EventSourcedAnomalyRepository
    daily_time_result_read_repository: DailyTimeResultRepository
    unit_of_work: IUnitOfWork
    event_bus: IEventBus[BaseEvent]
    event_outbox: TransactionalOutbox | None = None
    _mediator: ApplicationMediator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        request_map = RequestMap()
        request_map.bind(CreateCalculationRuleVersionCommand, CreateCalculationRuleVersionHandler)
        request_map.bind(CalculateDailyTimeCommand, CalculateDailyTimeHandler)
        request_map.bind(RecalculatePeriodCommand, RecalculatePeriodHandler)
        request_map.bind(ValidateDailyTimeResultCommand, ValidateDailyTimeResultHandler)
        request_map.bind(GetDailyTimeResultByIdQuery, GetDailyTimeResultByIdHandler)

        self._mediator = ApplicationMediator(
            request_map=request_map,
            container=HandlerContainer(self._resolve_handler),
            event_emitter=EventBusEmitter(self.event_bus),
        )

    def _time_calculation_service(self) -> TimeCalculationService:
        return TimeCalculationService(
            daily_time_result_repository=self.daily_time_result_repository,
            calculation_rule_version_repository=self.calculation_rule_version_repository,
            period_repository=self.period_repository,
            employee_schedule_repository=self.employee_schedule_repository,
            time_profile_repository=self.time_profile_repository,
            time_entry_repository=self.time_entry_repository,
            absence_repository=self.absence_repository,
            anomaly_repository=self.anomaly_repository,
        )

    def _resolve_handler(self, handler_type: type):
        """Build a handler bound to this request scope."""
        if handler_type is CreateCalculationRuleVersionHandler:
            return CreateCalculationRuleVersionHandler(
                unit_of_work=self.unit_of_work,
                calculation_rule_version_repository=self.calculation_rule_version_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type in (CalculateDailyTimeHandler, RecalculatePeriodHandler):
            return handler_type(
                unit_of_work=self.unit_of_work,
                time_calculation_service=self._time_calculation_service(),
                daily_time_result_repository=self.daily_time_result_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is ValidateDailyTimeResultHandler:
            return ValidateDailyTimeResultHandler(
                unit_of_work=self.unit_of_work,
                daily_time_result_repository=self.daily_time_result_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is GetDailyTimeResultByIdHandler:
            return GetDailyTimeResultByIdHandler(daily_time_result_repository=self.daily_time_result_read_repository)
        raise TypeError(
            f"No time-calculation-scope wiring for handler {handler_type.__name__}"
        )

    async def work_date_of(self, employee_id: str, instant: datetime) -> date:
        """The employee's work date of ``instant``, in their time-profile timezone."""
        return await self._time_calculation_service().work_date_of(EmployeeId(employee_id), instant)

    async def send(self, request):
        """Dispatch a time calculation command/query and return its result."""
        return await self._mediator.send(request)


def build_time_calculation_container(
    *,
    write_session: AsyncSession,
    read_session: AsyncSession,
    event_bus: IEventBus[BaseEvent],
    event_outbox: TransactionalOutbox | None = None,
) -> TimeCalculationContainer:
    """Build a request-scoped time calculation container."""
    event_store = EventStore(write_session)
    return TimeCalculationContainer(
        daily_time_result_repository=EventSourcedDailyTimeResultRepository(event_store),
        calculation_rule_version_repository=EventSourcedCalculationRuleVersionRepository(event_store),
        period_repository=EventSourcedPeriodRepository(event_store),
        employee_schedule_repository=EventSourcedEmployeeScheduleRepository(event_store),
        time_profile_repository=EventSourcedTimeProfileRepository(event_store),
        time_entry_repository=EventSourcedTimeEntryRepository(event_store),
        absence_repository=EventSourcedAbsenceRepository(event_store),
        anomaly_repository=EventSourcedAnomalyRepository(event_store),
        daily_time_result_read_repository=DailyTimeResultRepository(read_session),
        unit_of_work=SQLAlchemyUnitOfWork(write_session),
        event_bus=event_bus,
        event_outbox=event_outbox
        or TransactionalOutbox(session=write_session, mappers=TIME_CALCULATION_EVENT_MAPPERS),
    )
