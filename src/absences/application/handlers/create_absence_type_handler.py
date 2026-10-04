"""Create an absence type."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import AbsenceType
from ...domain.repositories import IAbsenceTypeRepository
from ...domain.value_objects import AbsenceTypeId
from ..commands import CreateAbsenceTypeCommand
from ..dtos import AbsenceTypeDTO


class CreateAbsenceTypeHandler(
    CommandHandler[CreateAbsenceTypeCommand, AbsenceTypeDTO]
):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        absence_type_repository: IAbsenceTypeRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._absence_types = absence_type_repository

    async def _execute(
        self, request: CreateAbsenceTypeCommand
    ) -> tuple[AbsenceTypeDTO, Sequence[AggregateRoot]]:
        absence_type = AbsenceType.create(
            AbsenceTypeId.generate(),
            name=request.name,
            paid=request.paid,
            counts_as_work_time=request.counts_as_work_time,
            deducts_balance=request.deducts_balance,
        )
        return AbsenceTypeDTO.from_aggregate(absence_type), [absence_type]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, AbsenceType):
            await self._absence_types.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
