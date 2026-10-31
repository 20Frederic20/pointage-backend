"""Assign an employee to one site of a directory — a transfer when one is running."""

from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import EmployeeAssignment
from ...domain.errors import (
    AssignmentInPastError,
    DirectoryOutsideCompanyError,
    EmployeeInactiveError,
    FutureAssignmentExistsError,
)
from ...domain.repositories import (
    IDirectoryRepository,
    IEmployeeAssignmentRepository,
    IEmployeeRepository,
    ISiteRepository,
)
from ...domain.value_objects.ids import DirectoryId, EmployeeAssignmentId, EmployeeId
from ..commands import AssignEmployeeCommand
from ..dtos import EmployeeAssignmentDTO
from ..services import AssignmentSiteService, CompanyService, ensure_can_manage, ensure_responsible


def _today_utc() -> date:
    return datetime.now(UTC).date()


class AssignEmployeeHandler(CommandHandler[AssignEmployeeCommand, EmployeeAssignmentDTO]):
    """From ``start_date`` S the employee works at the new site:

    * the assignment covering S that started before S ends on S - 1;
    * the one starting on S itself is cancelled (same-day correction);
    * one starting after S is a scheduled transfer: refused, never rewritten silently.
    """

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        employee_assignment_repository: IEmployeeAssignmentRepository,
        employee_repository: IEmployeeRepository,
        directory_repository: IDirectoryRepository,
        site_repository: ISiteRepository,
        event_outbox: IEventOutbox | None = None,
        clock: Callable[[], date] = _today_utc,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._assignments = employee_assignment_repository
        self._employees = employee_repository
        self._directories = directory_repository
        self._assignment_sites = AssignmentSiteService(site_repository=site_repository)
        self._companies = CompanyService(directory_repository)
        self._today = clock

    async def _execute(
        self, request: AssignEmployeeCommand
    ) -> tuple[EmployeeAssignmentDTO, Sequence[AggregateRoot]]:
        actor_role = ensure_responsible(request.actor_role)
        employee_id = EmployeeId(request.employee_id)
        employee = await self._employees.get_by_id(employee_id)
        ensure_can_manage(actor_role, employee.role)
        if not employee.is_active:
            raise EmployeeInactiveError(f"Employee {employee_id.value} is inactive", context=employee_id.value)
        start = request.start_date
        if start < self._today():
            raise AssignmentInPastError(f"Assignment starts in the past ({start})", context=employee_id.value)

        directory = await self._directories.get_by_id(DirectoryId(request.directory_id))
        # Records created before the company was stored are checked once backfilled.
        if employee.company_directory_id is not None and not await self._companies.is_within(
            employee.company_directory_id, directory.id
        ):
            raise DirectoryOutsideCompanyError(
                f"Directory {directory.code!r} is not part of the employee's company", context=directory.id.value
            )
        site = await self._assignment_sites.resolve(directory, request.site_id)

        changed: list[EmployeeAssignment] = []
        for current in await self._assignments.find_by_employee(employee_id):
            if current.start_date > start:
                raise FutureAssignmentExistsError(
                    f"Employee {employee_id.value} already has an assignment from {current.start_date}",
                    context=current.id.value,
                )
            if current.start_date == start:
                current.cancel()
                changed.append(current)
            elif current.is_active_on(start):
                current.end(start - timedelta(days=1))
                changed.append(current)

        assignment = EmployeeAssignment.assign(
            EmployeeAssignmentId.generate(),
            employee_id=employee_id,
            directory_id=directory.id,
            site_id=site.id,
            start_date=start,
            end_date=request.end_date,
        )
        return EmployeeAssignmentDTO.from_aggregate(assignment), [*changed, assignment]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, EmployeeAssignment):
            await self._assignments.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
