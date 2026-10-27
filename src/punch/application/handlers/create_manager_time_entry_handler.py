"""Manager punch: a responsible punches for an employee, counted immediately.

No photo, no location, no anomaly: the responsible vouches for it. The time is
the server's, the direction is resolved from the employee's history.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.audit import audit
from core.domain.entity import AggregateRoot
from core.domain.errors import ConflictError, NotFoundError
from identity.domain import EmployeeId, Role, UserId
from identity.domain.errors.errors import RolePermissionDeniedError
from identity.domain.repositories import (
    IEmployeeAssignmentRepository,
    IEmployeeRepository,
    ISiteRepository,
)
from punch.application.commands import CreateManagerTimeEntryCommand
from punch.application.dtos import TimeEntryDTO
from punch.application.services import punch_rules
from punch.domain import (
    EntrySource,
    LocationConfidence,
    TimeEntryId,
    TimeEntryValidationStatus,
)
from punch.domain.entities import TimeEntry
from punch.domain.errors import (
    EmployeeNotAssignedError,
    PunchAlreadyExistsError,
    SelfManagerPunchError,
)
from punch.domain.repositories import ITimeEntryRepository


class CreateManagerTimeEntryHandler(CommandHandler[CreateManagerTimeEntryCommand, TimeEntryDTO]):
    """Role re-checked, active employee other than the caller, then a COUNTED entry."""

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        time_entry_repository: ITimeEntryRepository,
        employee_repository: IEmployeeRepository,
        employee_assignment_repository: IEmployeeAssignmentRepository,
        site_repository: ISiteRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self.time_entry_repository = time_entry_repository
        self.employee_repository = employee_repository
        self.employee_assignment_repository = employee_assignment_repository
        self.site_repository = site_repository

    async def _execute(self, request: CreateManagerTimeEntryCommand) -> tuple[TimeEntryDTO, Sequence[AggregateRoot]]:
        actor = request.actor_user_id
        action = "PUNCH_MANAGER"

        # 1. Responsible roles only (the route checks it too).
        try:
            allowed = Role(request.actor_role).at_least(Role.MANAGER)
        except ValueError:
            allowed = False
        if not allowed:
            audit.warning("action=%s user_id=%s employee=%s status=FAIL reason=role", action, actor, request.employee_id)
            raise RolePermissionDeniedError(f"Role {request.actor_role} cannot punch for an employee", context=actor)

        # 2. The punched employee: active only, and never the caller.
        try:
            employee = await self.employee_repository.get_by_id(EmployeeId(request.employee_id))
        except NotFoundError:
            employee = None
        if employee is None or not employee.is_active:
            audit.warning("action=%s user_id=%s employee=%s status=FAIL reason=unknown_employee", action, actor, request.employee_id)
            raise NotFoundError("No active employee with this id", context=request.employee_id)
        if employee.user_id == UserId(actor):
            audit.warning("action=%s user_id=%s employee=%s status=FAIL reason=self", action, actor, request.employee_id)
            raise SelfManagerPunchError("You cannot punch for yourself", context=request.employee_id)

        # 3. The employee must be assigned to a site today (no distance rule here).
        try:
            await punch_rules.resolve_today_site(employee, self.employee_assignment_repository, self.site_repository)
        except EmployeeNotAssignedError:
            audit.warning("action=%s user_id=%s employee=%s status=FAIL reason=not_assigned", action, actor, request.employee_id)
            raise

        # 4. A double tap or a network retry reuses the key: one entry only.
        time_entry_id = TimeEntryId.generate()
        try:
            await self.time_entry_repository.reserve_idempotency_key(request.idempotency_key, time_entry_id)
        except ConflictError as exc:
            audit.warning("action=%s user_id=%s employee=%s status=FAIL reason=duplicate", action, actor, request.employee_id)
            raise PunchAlreadyExistsError("This punch was already recorded", context=request.idempotency_key) from exc

        # 5. IN or OUT from the employee's history, at the server's time.
        now = datetime.now(UTC)
        entry_type = await punch_rules.next_entry_type(employee.id, self.time_entry_repository, now)

        time_entry = TimeEntry.create(
            time_entry_id,
            employee_id=employee.id,
            entry_type=entry_type,
            location=None,
            location_confidence=LocationConfidence.LOW,
            source=EntrySource.MANAGER_ASSISTED,
            idempotency_key=request.idempotency_key,
            assisted_by_user_id=UserId(actor),
            validation_status=TimeEntryValidationStatus.COUNTED,
        )
        audit.info(
            "action=%s user_id=%s employee=%s type=%s time_entry=%s status=OK",
            action, actor, request.employee_id, entry_type.value, time_entry_id.value,
        )
        return TimeEntryDTO.from_aggregate(time_entry), [time_entry]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        await self.time_entry_repository.save(aggregate)
