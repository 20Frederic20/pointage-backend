"""Create an employee and their first assignment to a directory."""

from collections.abc import Sequence
from datetime import UTC, datetime

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot
from identity.domain import DirectoryId, EmployeeAssignmentId, EmployeeId, Role, UserId
from identity.domain.errors.errors import EmployeeWithThisNumberAlreadyExistsError

from ...domain.entities import Employee, EmployeeAssignment
from ...domain.repositories import (
    IDirectoryRepository,
    IEmployeeAssignmentRepository,
    IEmployeeRepository,
    ISiteRepository,
    IUserRepository,
)
from ..commands import CreateEmployeeCommand
from ..dtos import EmployeeDTO
from ..services import AssignmentSiteService


class CreateEmployeeHandler(
    CommandHandler[CreateEmployeeCommand, EmployeeDTO]
):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        user_repository: IUserRepository,
        employee_repository: IEmployeeRepository,
        employee_assignment_repository: IEmployeeAssignmentRepository,
        directory_repository: IDirectoryRepository,
        site_repository: ISiteRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._users = user_repository
        self._employees = employee_repository
        self._assignments = employee_assignment_repository
        self._directories = directory_repository
        self._assignment_sites = AssignmentSiteService(site_repository=site_repository)

    async def _execute(
        self, request: CreateEmployeeCommand
    ) -> tuple[EmployeeDTO, Sequence[AggregateRoot]]:
        if await self._employees.exists_by_employee_number(request.employee_number):
            raise EmployeeWithThisNumberAlreadyExistsError(
                f"An employee with number {request.employee_number!r} already exists",
                context=request.employee_number,
            )
        # The account must exist (NotFoundError otherwise): the event store has
        # no foreign keys, so nothing else would refuse an unknown user.
        user = await self._users.get_by_id(UserId(request.user_id))
        directory = await self._directories.get_by_id(DirectoryId(request.directory_id))
        site = await self._assignment_sites.resolve(directory, request.site_id)

        employee = Employee.create(
            employee_id=EmployeeId.generate(),
            employee_number=request.employee_number,
            user_id=user.id,
            phone=request.phone,
            role=Role(request.role),
            is_active=request.is_active if request.is_active else False,
        )
        assignment = EmployeeAssignment.assign(
            EmployeeAssignmentId.generate(),
            employee_id=employee.id,
            directory_id=directory.id,
            site_id=site.id,
            start_date=request.assignment_start_date or datetime.now(UTC).date(),
        )
        return EmployeeDTO.from_aggregate(employee), [employee, assignment]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Employee):
            await self._employees.save(aggregate)
        elif isinstance(aggregate, EmployeeAssignment):
            await self._assignments.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
