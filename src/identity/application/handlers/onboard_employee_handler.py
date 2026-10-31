"""Onboard a person in a company: their account (unless the email already has
one), the employee record and the first assignment, saved together — a failed
check leaves nothing behind."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot
from identity.domain import DirectoryId, EmployeeAssignmentId, EmployeeId, Role, UserId

from ...domain.entities import Employee, EmployeeAssignment, User
from ...domain.errors import AlreadyActiveInCompanyError, EmployeeWithThisNumberAlreadyExistsError
from ...domain.repositories import (
    IDirectoryRepository,
    IEmployeeAssignmentRepository,
    IEmployeeRepository,
    ISiteRepository,
    IUserRepository,
)
from ..commands import OnboardEmployeeCommand
from ..dtos import EmployeeDTO
from ..ports import PasswordHasher
from ..services import AssignmentSiteService, CompanyService, ensure_can_grant, ensure_responsible


class OnboardEmployeeHandler(
    CommandHandler[OnboardEmployeeCommand, EmployeeDTO]
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
        password_hasher: PasswordHasher,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._users = user_repository
        self._employees = employee_repository
        self._assignments = employee_assignment_repository
        self._directories = directory_repository
        self._assignment_sites = AssignmentSiteService(site_repository=site_repository)
        self._companies = CompanyService(directory_repository)
        self._password_hasher = password_hasher

    async def _execute(
        self, request: OnboardEmployeeCommand
    ) -> tuple[EmployeeDTO, Sequence[AggregateRoot]]:
        # Every check runs before anything is built: the template saves the
        # aggregates together, or none of them.
        role = Role(request.role) if request.role else Role.EMPLOYEE
        ensure_can_grant(ensure_responsible(request.actor_role), role)
        if await self._employees.exists_by_employee_number(request.employee_number):
            raise EmployeeWithThisNumberAlreadyExistsError(
                f"An employee with number {request.employee_number!r} already exists",
                context=request.employee_number,
            )
        directory = await self._directories.get_by_id(DirectoryId(request.directory_id))
        company_id = await self._companies.root_of(directory.id)
        site = await self._assignment_sites.resolve(directory, request.site_id)
        is_active = request.is_active if request.is_active is not None else True

        existing = await self._users.find_by_email(request.email)
        if existing is not None and is_active:
            for record in await self._employees.find_all_by_user_id(existing.id):
                if record.is_active and record.company_directory_id == company_id:
                    raise AlreadyActiveInCompanyError(
                        "This person already has an active record in this company", context=record.id.value
                    )
        user = existing or User.register_owner(
            UserId.generate(),
            email=request.email,
            password_hash=(
                self._password_hasher.hash(request.password)
                if request.password
                else None
            ),
            role=role,
            first_name=request.first_name,
            last_name=request.last_name,
        )
        employee = Employee.create(
            employee_id=EmployeeId.generate(),
            employee_number=request.employee_number,
            user_id=user.id,
            phone=request.phone,
            role=role,
            is_active=is_active,
            company_directory_id=company_id,
        )
        assignment = EmployeeAssignment.assign(
            EmployeeAssignmentId.generate(),
            employee_id=employee.id,
            directory_id=directory.id,
            site_id=site.id,
            start_date=request.assignment_start_date or datetime.now(UTC).date(),
        )
        dto = replace(EmployeeDTO.from_aggregate(employee), account_reused=existing is not None)
        aggregates = [employee, assignment] if existing is not None else [user, employee, assignment]
        return dto, aggregates

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, User):
            await self._users.save(aggregate)
        elif isinstance(aggregate, Employee):
            await self._employees.save(aggregate)
        elif isinstance(aggregate, EmployeeAssignment):
            await self._assignments.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
