"""Assign an employee to one site of a directory."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot
from core.domain.errors import NotFoundError

from ...domain.entities import EmployeeAssignment
from ...domain.errors import OverlappingEmployeeAssignmentError
from ...domain.repositories import (
    IDirectoryRepository,
    IEmployeeAssignmentRepository,
    IEmployeeRepository,
    ISiteRepository,
)
from ...domain.value_objects.ids import DirectoryId, EmployeeAssignmentId, EmployeeId
from ..commands import AssignEmployeeCommand
from ..services import AssignmentSiteService
from ..dtos import EmployeeAssignmentDTO


class AssignEmployeeHandler(CommandHandler[AssignEmployeeCommand, EmployeeAssignmentDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        employee_assignment_repository: IEmployeeAssignmentRepository,
        employee_repository: IEmployeeRepository,
        directory_repository: IDirectoryRepository,
        site_repository: ISiteRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._assignments = employee_assignment_repository
        self._employees = employee_repository
        self._directories = directory_repository
        self._assignment_sites = AssignmentSiteService(site_repository=site_repository)

    async def _execute(
        self, request: AssignEmployeeCommand
    ) -> tuple[EmployeeAssignmentDTO, Sequence[AggregateRoot]]:
        employee_id = EmployeeId(request.employee_id)
        if not await self._employees.exists(employee_id):
            raise NotFoundError(f"Employee {employee_id.value} not found", context=employee_id.value)
        directory = await self._directories.get_by_id(DirectoryId(request.directory_id))
        site = await self._assignment_sites.resolve(directory, request.site_id)
        if await self._assignments.exists_overlapping(employee_id, request.start_date, request.end_date):
            raise OverlappingEmployeeAssignmentError(
                f"Employee {employee_id.value} already has an assignment in this date range",
                context=employee_id.value,
            )

        assignment = EmployeeAssignment.assign(
            EmployeeAssignmentId.generate(),
            employee_id=employee_id,
            directory_id=directory.id,
            site_id=site.id,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        return EmployeeAssignmentDTO.from_aggregate(assignment), [assignment]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, EmployeeAssignment):
            await self._assignments.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
