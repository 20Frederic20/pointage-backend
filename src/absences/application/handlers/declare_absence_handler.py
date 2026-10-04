"""Declare an absence (``AbsenceService.declarerAbsence``)."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot
from core.domain.errors import NotFoundError
from identity.domain import EmployeeId
from identity.domain.repositories import IEmployeeRepository

from ...domain.entities import Absence
from ...domain.repositories import IAbsenceRepository, IAbsenceTypeRepository
from ...domain.value_objects import AbsenceId, AbsenceTypeId
from ..commands import DeclareAbsenceCommand
from ..dtos import AbsenceDTO


class DeclareAbsenceHandler(CommandHandler[DeclareAbsenceCommand, AbsenceDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        absence_repository: IAbsenceRepository,
        absence_type_repository: IAbsenceTypeRepository,
        employee_repository: IEmployeeRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._absences = absence_repository
        self._absence_types = absence_type_repository
        self._employees = employee_repository

    async def _execute(
        self, request: DeclareAbsenceCommand
    ) -> tuple[AbsenceDTO, Sequence[AggregateRoot]]:
        employee_id = EmployeeId(request.employee_id)
        if not await self._employees.exists(employee_id):
            raise NotFoundError(
                f"Employee {employee_id.value} not found", context=employee_id.value
            )
        absence_type = await self._absence_types.get_by_id(
            AbsenceTypeId(request.absence_type_id)
        )

        absence = Absence.declare(
            AbsenceId.generate(),
            employee_id=employee_id,
            absence_type=absence_type,
            start_at=request.start_at,
            end_at=request.end_at,
            reason=request.reason,
            justification_reference=request.justification_reference,
        )
        return AbsenceDTO.from_aggregate(absence), [absence]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Absence):
            await self._absences.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
