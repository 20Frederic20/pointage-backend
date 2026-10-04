"""Close a period (``PeriodService.cloturerPeriode``) once no blocking anomaly is open."""

from collections.abc import Sequence
from datetime import UTC, datetime, time, timedelta

from adjustements.domain.repositories import IAnomalyRepository
from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import Period
from ...domain.repositories import IPeriodRepository
from ...domain.value_objects import PeriodId
from ..commands import ClosePeriodCommand
from ..dtos import PeriodDTO


class ClosePeriodHandler(CommandHandler[ClosePeriodCommand, PeriodDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        period_repository: IPeriodRepository,
        anomaly_repository: IAnomalyRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._periods = period_repository
        self._anomalies = anomaly_repository

    async def _execute(self, request: ClosePeriodCommand) -> tuple[PeriodDTO, Sequence[AggregateRoot]]:
        period = await self._periods.get_by_id(PeriodId(request.period_id))
        # ``verifierAnomaliesBloquantes``: period dates are read as UTC days.
        has_open_blocking_anomalies = await self._anomalies.exists_open_blocking_between(
            datetime.combine(period.start_date, time.min, UTC),
            datetime.combine(period.end_date + timedelta(days=1), time.min, UTC),
        )
        period.close(has_open_blocking_anomalies=has_open_blocking_anomalies)
        return PeriodDTO.from_aggregate(period), [period]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Period):
            await self._periods.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
