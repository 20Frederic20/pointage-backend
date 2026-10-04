"""Open a new period."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import Period
from ...domain.errors import OverlappingPeriodError
from ...domain.repositories import IPeriodRepository
from ...domain.value_objects import PeriodId
from ..commands import OpenPeriodCommand
from ..dtos import PeriodDTO


class OpenPeriodHandler(CommandHandler[OpenPeriodCommand, PeriodDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        period_repository: IPeriodRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._periods = period_repository

    async def _execute(self, request: OpenPeriodCommand) -> tuple[PeriodDTO, Sequence[AggregateRoot]]:
        period = Period.open(PeriodId.generate(), start_date=request.start_date, end_date=request.end_date)
        if await self._periods.exists_overlapping(request.start_date, request.end_date):
            raise OverlappingPeriodError(
                f"A period already covers part of {request.start_date} - {request.end_date}",
                context=f"{request.start_date}/{request.end_date}",
            )
        return PeriodDTO.from_aggregate(period), [period]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Period):
            await self._periods.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
