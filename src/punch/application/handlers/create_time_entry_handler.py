from collections.abc import Sequence
from datetime import UTC, datetime

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.audit import audit
from core.domain.entity import AggregateRoot
from core.domain.errors import NotFoundError
from identity.domain import EmployeeId, UserId
from identity.domain.errors import EmployeeInactiveError
from identity.domain.entities import Employee, Site
from identity.domain.repositories import (
    IEmployeeAssignmentRepository,
    IEmployeeRepository,
    ISiteRepository,
)
from punch.application.commands import CreateTimeEntryCommand
from punch.application.dtos import TimeEntryDTO
from punch.application.services import punch_rules
from punch.domain import LocationConfidence, TimeEntryId
from punch.domain.entities import TimeEntry
from punch.domain.errors import EmployeeNotAssignedError, TooFarFromWorkplaceError
from punch.domain.repositories import ITimeEntryRepository


class CreateTimeEntryHandler(CommandHandler[CreateTimeEntryCommand, TimeEntryDTO]):
    """Handle the creation of a time entry."""

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        time_entry_repository: ITimeEntryRepository,
        employee_repository: IEmployeeRepository,
        site_repository: ISiteRepository,
        employee_assignment_repository: IEmployeeAssignmentRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self.time_entry_repository = time_entry_repository
        self.employee_repository = employee_repository
        self.site_repository = site_repository
        self.employee_assignment_repository = employee_assignment_repository

    async def _execute(self, request: CreateTimeEntryCommand) -> tuple[TimeEntryDTO, Sequence[AggregateRoot]]:
        employee = await self._session_employee(request)
        if not employee:
            audit.warning("action=PUNCH user_id=%s status=FAIL reason=no_employee", request.user_id)
            raise NotFoundError("No employee record for this account", context=request.user_id)
        if not employee.is_active:
            audit.warning("action=PUNCH user_id=%s employee=%s status=FAIL reason=inactive", request.user_id, employee.employee_number)
            raise EmployeeInactiveError("This employee record is deactivated", context=employee.id.value)

        # The reference location is the directory of the assignment covering today.
        try:
            site: Site = await punch_rules.resolve_today_site(
                employee, self.employee_assignment_repository, self.site_repository
            )
        except EmployeeNotAssignedError:
            audit.warning("action=PUNCH user_id=%s employee=%s status=FAIL reason=not_assigned", request.user_id, employee.employee_number)
            raise

        try:
            distance = punch_rules.ensure_within_site(request.location, site, employee_id=employee.id)
        except TooFarFromWorkplaceError as exc:
            audit.warning("action=PUNCH user_id=%s employee=%s status=FAIL reason=too_far distance=%.0fm", request.user_id, employee.employee_number, exc.distance_meters)
            raise

        entry_type = await punch_rules.next_entry_type(employee.id, self.time_entry_repository, datetime.now(UTC))

        location_confidence = (
            LocationConfidence("HIGH")
            if request.location and request.wifi_identifier
            else LocationConfidence("MEDIUM")
        )
        time_entry = TimeEntry.create(
            time_entry_id=TimeEntryId.generate(),
            employee_id=employee.id,
            entry_type=entry_type,
            location=request.location,
            location_confidence=LocationConfidence(location_confidence),
            source=request.source,
            idempotency_key=request.idempotency_key if request.idempotency_key else None,
            wifi_identifier=request.wifi_identifier,

        )
        audit.info("action=PUNCH user_id=%s employee=%s type=%s distance=%.0fm status=OK", request.user_id, employee.employee_number, entry_type.value, distance)
        return TimeEntryDTO.from_aggregate(time_entry), [time_entry]

    async def _session_employee(self, request: CreateTimeEntryCommand) -> Employee | None:
        """The record the session works with, and only if it belongs to the caller."""
        if request.employee_id is None:
            return await self.employee_repository.find_by_user_id(UserId(request.user_id))
        try:
            employee = await self.employee_repository.get_by_id(EmployeeId(request.employee_id))
        except NotFoundError:
            return None
        return employee if employee.user_id == UserId(request.user_id) else None

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, TimeEntry):
            await self.time_entry_repository.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
