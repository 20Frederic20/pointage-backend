"""Create a calculation rule version; the previous one ends the day before."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import CalculationRuleVersion
from ...domain.repositories import ICalculationRuleVersionRepository
from ...domain.value_objects import CalculationRuleVersionId
from ..commands import CreateCalculationRuleVersionCommand
from ..dtos import CalculationRuleVersionDTO


class CreateCalculationRuleVersionHandler(
    CommandHandler[CreateCalculationRuleVersionCommand, CalculationRuleVersionDTO]
):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        calculation_rule_version_repository: ICalculationRuleVersionRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._rule_versions = calculation_rule_version_repository

    async def _execute(
        self, request: CreateCalculationRuleVersionCommand
    ) -> tuple[CalculationRuleVersionDTO, Sequence[AggregateRoot]]:
        previous = await self._rule_versions.find_latest()
        rule_version = CalculationRuleVersion.create(
            CalculationRuleVersionId.generate(),
            previous=previous,
            effective_from=request.effective_from,
            min_break_duration=request.min_break_duration,
            break_threshold=request.break_threshold,
            max_daily_work_duration=request.max_daily_work_duration,
            max_amplitude=request.max_amplitude,
        )
        changed = [previous, rule_version] if previous is not None else [rule_version]
        return CalculationRuleVersionDTO.from_aggregate(rule_version), changed

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, CalculationRuleVersion):
            await self._rule_versions.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
