"""Set the last day of an employee assignment (``terminer``)."""

from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot
from core.domain.errors import ConflictError

from ...domain.entities import EmployeeAssignment
from ...domain.errors import AssignmentInPastError, OverlappingEmployeeAssignmentError
from ...domain.repositories import IEmployeeAssignmentRepository
from ...domain.value_objects.ids import EmployeeAssignmentId
from ..commands import EndEmployeeAssignmentCommand
from ..dtos import EmployeeAssignmentDTO
from ..services import ensure_can_manage, ensure_responsible


class EndEmployeeAssignmentHandler(CommandHandler[EndEmployeeAssignmentCommand, EmployeeAssignmentDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        employee_assignment_repository: IEmployeeAssignmentRepository,
        employee_repository=None,
        event_outbox: IEventOutbox | None = None,
        clock: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._assignments = employee_assignment_repository
        self._employees = employee_repository
        self._today = clock

    async def _execute(
        self, request: EndEmployeeAssignmentCommand
    ) -> tuple[EmployeeAssignmentDTO, Sequence[AggregateRoot]]:
        actor_role = ensure_responsible(request.actor_role)
        assignment = await self._assignments.get_by_id(EmployeeAssignmentId(request.employee_assignment_id))
        if assignment.is_cancelled:
            raise ConflictError(f"Assignment {assignment.id.value} was cancelled", context=assignment.id.value)
        if self._employees is not None:
            ensure_can_manage(actor_role, (await self._employees.get_by_id(assignment.employee_id)).role)
        if request.end_date < self._today():
            # Punches already checked against this site keep their coverage.
            raise AssignmentInPastError(f"Assignment cannot end in the past ({request.end_date})", context=assignment.id.value)
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
