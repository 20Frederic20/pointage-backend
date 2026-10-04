"""The time calculation context's composition root — request-scope wiring."""

from dataclasses import dataclass, field

from cqrs.requests.map import RequestMap
from sqlalchemy.ext.asyncio import AsyncSession

from absences.infrastructure.persistence.absence_repository import AbsenceRepository
from adjustements.infrastructure.persistence.anomaly_repository import AnomalyRepository
from core.application import ApplicationMediator, HandlerContainer, IUnitOfWork
from core.domain.events import BaseEvent, IEventBus
from core.infrastructure.database import SQLAlchemyUnitOfWork
from core.infrastructure.events import EventBusEmitter
from core.infrastructure.outbox import TransactionalOutbox
from periods.infrastructure.persistence.period_repository import PeriodRepository
from planning.infrastructure.persistence.employee_schedule_repository import EmployeeScheduleRepository
from planning.infrastructure.persistence.time_profile_repository import TimeProfileRepository
from punch.infrastructure.persistence.time_entry_repository import TimeEntryRepository

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
from .persistence.calculation_rule_version_repository import CalculationRuleVersionRepository
from .persistence.daily_time_result_repository import DailyTimeResultRepository


@dataclass
class TimeCalculationContainer:
    """Request-scope wiring for the time calculation bounded context."""

    daily_time_result_repository: DailyTimeResultRepository
    calculation_rule_version_repository: CalculationRuleVersionRepository
    period_repository: PeriodRepository
    employee_schedule_repository: EmployeeScheduleRepository
    time_profile_repository: TimeProfileRepository
    time_entry_repository: TimeEntryRepository
    absence_repository: AbsenceRepository
    anomaly_repository: AnomalyRepository
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
            return GetDailyTimeResultByIdHandler(daily_time_result_repository=self.daily_time_result_repository)
        raise TypeError(
            f"No time-calculation-scope wiring for handler {handler_type.__name__}"
        )

    async def send(self, request):
        """Dispatch a time calculation command/query and return its result."""
        return await self._mediator.send(request)


def build_time_calculation_container(
    *,
    session: AsyncSession,
    event_bus: IEventBus[BaseEvent],
    event_outbox: TransactionalOutbox | None = None,
) -> TimeCalculationContainer:
    """Build a request-scoped time calculation container."""
    return TimeCalculationContainer(
        daily_time_result_repository=DailyTimeResultRepository(session),
        calculation_rule_version_repository=CalculationRuleVersionRepository(session),
        period_repository=PeriodRepository(session),
        employee_schedule_repository=EmployeeScheduleRepository(session),
        time_profile_repository=TimeProfileRepository(session),
        time_entry_repository=TimeEntryRepository(session),
        absence_repository=AbsenceRepository(session),
        anomaly_repository=AnomalyRepository(session),
        unit_of_work=SQLAlchemyUnitOfWork(session),
        event_bus=event_bus,
        event_outbox=event_outbox
        or TransactionalOutbox(session=session, mappers=TIME_CALCULATION_EVENT_MAPPERS),
    )
