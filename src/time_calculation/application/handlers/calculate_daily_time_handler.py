"""Calculate one employee's work date (``TimeCalculationService.calculerJournee``)."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot
from identity.domain import EmployeeId

from ...domain.entities import DailyTimeResult
from ...domain.repositories import IDailyTimeResultRepository
from ..commands import CalculateDailyTimeCommand
from ..dtos import DailyTimeResultDTO
from ..services import TimeCalculationService


class CalculateDailyTimeHandler(CommandHandler[CalculateDailyTimeCommand, DailyTimeResultDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        time_calculation_service: TimeCalculationService,
        daily_time_result_repository: IDailyTimeResultRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._time_calculation = time_calculation_service
        self._results = daily_time_result_repository

    async def _execute(
        self, request: CalculateDailyTimeCommand
    ) -> tuple[DailyTimeResultDTO, Sequence[AggregateRoot]]:
        result = await self._time_calculation.calculate_day(EmployeeId(request.employee_id), request.work_date)
        return DailyTimeResultDTO.from_aggregate(result), [result]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, DailyTimeResult):
            await self._results.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
