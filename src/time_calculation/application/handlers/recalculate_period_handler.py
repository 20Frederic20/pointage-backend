"""Recalculate a period (``TimeCalculationService.recalculerPeriode``)."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot
from periods.domain import PeriodId

from ...domain.entities import DailyTimeResult
from ...domain.repositories import IDailyTimeResultRepository
from ..commands import RecalculatePeriodCommand
from ..dtos import PeriodRecalculationDTO
from ..services import TimeCalculationService


class RecalculatePeriodHandler(CommandHandler[RecalculatePeriodCommand, PeriodRecalculationDTO]):
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
        self, request: RecalculatePeriodCommand
    ) -> tuple[PeriodRecalculationDTO, Sequence[AggregateRoot]]:
        results, skipped_validated = await self._time_calculation.recalculate_period(PeriodId(request.period_id))
        summary = PeriodRecalculationDTO(
            period_id=request.period_id,
            recalculated_count=len(results),
            skipped_validated_count=skipped_validated,
        )
        return summary, results

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, DailyTimeResult):
            await self._results.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
