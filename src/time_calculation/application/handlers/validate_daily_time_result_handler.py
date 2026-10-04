"""Validate a daily time result."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import DailyTimeResult
from ...domain.repositories import IDailyTimeResultRepository
from ...domain.value_objects import DailyTimeResultId
from ..commands import ValidateDailyTimeResultCommand
from ..dtos import DailyTimeResultDTO


class ValidateDailyTimeResultHandler(CommandHandler[ValidateDailyTimeResultCommand, DailyTimeResultDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        daily_time_result_repository: IDailyTimeResultRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._results = daily_time_result_repository

    async def _execute(
        self, request: ValidateDailyTimeResultCommand
    ) -> tuple[DailyTimeResultDTO, Sequence[AggregateRoot]]:
        result = await self._results.get_by_id(DailyTimeResultId(request.daily_time_result_id))
        result.validate()
        return DailyTimeResultDTO.from_aggregate(result), [result]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, DailyTimeResult):
            await self._results.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
