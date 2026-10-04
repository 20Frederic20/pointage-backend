"""Reject an absence (``AbsenceService.refuserAbsence``)."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import Absence
from ...domain.repositories import IAbsenceRepository
from ...domain.value_objects import AbsenceId
from ..commands import RejectAbsenceCommand
from ..dtos import AbsenceDTO


class RejectAbsenceHandler(CommandHandler[RejectAbsenceCommand, AbsenceDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        absence_repository: IAbsenceRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._absences = absence_repository

    async def _execute(
        self, request: RejectAbsenceCommand
    ) -> tuple[AbsenceDTO, Sequence[AggregateRoot]]:
        absence = await self._absences.get_by_id(AbsenceId(request.absence_id))
        absence.reject()
        return AbsenceDTO.from_aggregate(absence), [absence]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Absence):
            await self._absences.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
