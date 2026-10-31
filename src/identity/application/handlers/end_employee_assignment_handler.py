"""Set the last day of an employee assignment (``terminer``)."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import EmployeeAssignment
from ...domain.errors import OverlappingEmployeeAssignmentError
from ...domain.repositories import IEmployeeAssignmentRepository
from ...domain.value_objects.ids import EmployeeAssignmentId
from ..commands import EndEmployeeAssignmentCommand
from ..dtos import EmployeeAssignmentDTO
from ..services import ensure_responsible


class EndEmployeeAssignmentHandler(CommandHandler[EndEmployeeAssignmentCommand, EmployeeAssignmentDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        employee_assignment_repository: IEmployeeAssignmentRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._assignments = employee_assignment_repository

    async def _execute(
        self, request: EndEmployeeAssignmentCommand
    ) -> tuple[EmployeeAssignmentDTO, Sequence[AggregateRoot]]:
        ensure_responsible(request.actor_role)
        assignment = await self._assignments.get_by_id(EmployeeAssignmentId(request.employee_assignment_id))
        if await self._assignments.exists_overlapping(
            assignment.employee_id, assignment.start_date, request.end_date, excluding=assignment.id
        ):
            raise OverlappingEmployeeAssignmentError(
                f"Employee {assignment.employee_id.value} already has an assignment in this date range",
                context=assignment.employee_id.value,
            )
        assignment.end(request.end_date)
        return EmployeeAssignmentDTO.from_aggregate(assignment), [assignment]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, EmployeeAssignment):
            await self._assignments.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
