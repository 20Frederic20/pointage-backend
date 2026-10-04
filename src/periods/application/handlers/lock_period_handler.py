"""Lock an open period (``PeriodService.verrouillerPeriode``)."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import Period
from ...domain.repositories import IPeriodRepository
from ...domain.value_objects import PeriodId
from ..commands import LockPeriodCommand
from ..dtos import PeriodDTO


class LockPeriodHandler(CommandHandler[LockPeriodCommand, PeriodDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        period_repository: IPeriodRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._periods = period_repository

    async def _execute(self, request: LockPeriodCommand) -> tuple[PeriodDTO, Sequence[AggregateRoot]]:
        period = await self._periods.get_by_id(PeriodId(request.period_id))
        period.lock()
        return PeriodDTO.from_aggregate(period), [period]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Period):
            await self._periods.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
