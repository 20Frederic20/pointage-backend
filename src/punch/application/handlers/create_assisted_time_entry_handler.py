"""Assisted punch: an employee punches for themself from a colleague's phone.

The punch is suspect by nature (the phone is not theirs): it is created
PENDING, with the selfie and the phone owner as assistant, together with an
OPEN BLOCKING ``ASSISTED_POINTING`` anomaly in the same transaction.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from adjustements.domain.entities import Anomaly
from adjustements.domain.repositories import IAnomalyRepository
from adjustements.domain.value_objects import (
    AnomalyId,
    AnomalyStatus,
    AnomalyType,
    Severity,
)
from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.audit import audit
from core.domain.entity import AggregateRoot
from core.domain.errors import ConflictError, NotFoundError
from identity.domain.errors import EmployeeInactiveError
from identity.domain import UserId
from identity.domain.repositories import (
    IEmployeeAssignmentRepository,
    IEmployeeRepository,
    ISiteRepository,
)
from punch.application.commands import CreateAssistedTimeEntryCommand
from punch.application.dtos import TimeEntryDTO
from punch.application.ports import (
    MAX_PHOTO_BYTES,
    PHOTO_EXTENSIONS,
    IPhotoStorage,
    photo_key_for,
)
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
    InvalidPhotoError,
    PunchAlreadyExistsError,
    SelfAssistedPunchError,
    TooFarFromWorkplaceError,
)
from punch.domain.repositories import ITimeEntryRepository


class CreateAssistedTimeEntryHandler(CommandHandler[CreateAssistedTimeEntryCommand, TimeEntryDTO]):
    """Create the pending time entry and its anomaly; store the selfie last."""

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        time_entry_repository: ITimeEntryRepository,
        employee_repository: IEmployeeRepository,
        site_repository: ISiteRepository,
        employee_assignment_repository: IEmployeeAssignmentRepository,
        anomaly_repository: IAnomalyRepository,
        photo_storage: IPhotoStorage,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self.time_entry_repository = time_entry_repository
        self.employee_repository = employee_repository
        self.site_repository = site_repository
        self.employee_assignment_repository = employee_assignment_repository
        self.anomaly_repository = anomaly_repository
        self.photo_storage = photo_storage

    async def _execute(self, request: CreateAssistedTimeEntryCommand) -> tuple[TimeEntryDTO, Sequence[AggregateRoot]]:
        actor = request.actor_user_id

        # 1. The selfie, before anything is looked up or written.
        self._validate_photo(request)

        # 2. The punched employee: active only, and never the caller.
        employee = await self.employee_repository.find_by_employee_number(request.employee_number)
        if employee is None:
            audit.warning("action=PUNCH_ASSISTED user_id=%s employee=%s status=FAIL reason=unknown_employee", actor, request.employee_number)
            raise NotFoundError("No employee with this number", context=request.employee_number)
        if not employee.is_active:
            audit.warning("action=PUNCH_ASSISTED user_id=%s employee=%s status=FAIL reason=inactive", actor, request.employee_number)
            raise EmployeeInactiveError("This employee is deactivated", context=request.employee_number)
        if employee.user_id == UserId(actor):
            audit.warning("action=PUNCH_ASSISTED user_id=%s employee=%s status=FAIL reason=self", actor, employee.employee_number)
            raise SelfAssistedPunchError("The assisted punch is for a colleague, not for yourself", context=employee.id.value)

        # 3. The punched employee's site, against the phone's position.
        try:
            site = await punch_rules.resolve_today_site(employee, self.employee_assignment_repository, self.site_repository)
        except EmployeeNotAssignedError:
            audit.warning("action=PUNCH_ASSISTED user_id=%s employee=%s status=FAIL reason=not_assigned", actor, employee.employee_number)
            raise
        try:
            distance = punch_rules.ensure_within_site(request.location, site, employee_id=employee.id)
        except TooFarFromWorkplaceError as exc:
            audit.warning("action=PUNCH_ASSISTED user_id=%s employee=%s status=FAIL reason=too_far distance=%.0fm", actor, employee.employee_number, exc.distance_meters)
            raise

        # 4. A double tap or a network retry reuses the key: one entry only.
        time_entry_id = TimeEntryId.generate()
        try:
            await self.time_entry_repository.reserve_idempotency_key(request.idempotency_key, time_entry_id)
        except ConflictError as exc:
            audit.warning("action=PUNCH_ASSISTED user_id=%s employee=%s status=FAIL reason=duplicate", actor, employee.employee_number)
            raise PunchAlreadyExistsError("This punch was already recorded", context=request.idempotency_key) from exc

        # 5. IN or OUT from the punched employee's history (rejected entries skipped).
        now = datetime.now(UTC)
        entry_type = await punch_rules.next_entry_type(employee.id, self.time_entry_repository, now)

        # 6. The pending entry and its anomaly, in this transaction.
        photo_key = photo_key_for(time_entry_id, request.photo_content_type)
        time_entry = TimeEntry.create(
            time_entry_id,
            employee_id=employee.id,
            entry_type=entry_type,
            location=request.location,
            location_confidence=LocationConfidence.HIGH if request.wifi_identifier else LocationConfidence.MEDIUM,
            source=EntrySource.ASSISTED,
            idempotency_key=request.idempotency_key,
            wifi_identifier=request.wifi_identifier,
            assisted_by_user_id=UserId(actor),
            photo_key=photo_key,
            validation_status=TimeEntryValidationStatus.PENDING,
        )
        anomaly = Anomaly.create(
            AnomalyId.generate(),
            time_entry_id=time_entry_id,
            type=AnomalyType.ASSISTED_POINTING,
            severity=Severity.BLOCKING,
            status=AnomalyStatus.OPEN,
            detected_at=now,
            description=f"Pointage assisté depuis le compte {actor}",
            employee_id=employee.id,
            assisted_by_user_id=UserId(actor),
        )

        # 7. The selfie, once every check passed (orphaned if the commit fails: accepted).
        await self.photo_storage.put(photo_key, request.photo, request.photo_content_type)

        audit.info(
            "action=PUNCH_ASSISTED user_id=%s employee=%s type=%s distance=%.0fm time_entry=%s status=OK",
            actor, employee.employee_number, entry_type.value, distance, time_entry_id.value,
        )
        # 8.
        return TimeEntryDTO.from_aggregate(time_entry), [time_entry, anomaly]

    @staticmethod
    def _validate_photo(request: CreateAssistedTimeEntryCommand) -> None:
        if request.photo_content_type not in PHOTO_EXTENSIONS:
            reason = f"content type {request.photo_content_type!r}"
        elif not request.photo:
            reason = "empty file"
        elif len(request.photo) > MAX_PHOTO_BYTES:
            reason = f"{len(request.photo)} bytes"
        else:
            return
        audit.warning("action=PUNCH_ASSISTED user_id=%s status=FAIL reason=invalid_photo", request.actor_user_id)
        raise InvalidPhotoError(
            f"The selfie must be a JPEG or PNG of at most {MAX_PHOTO_BYTES // (1024 * 1024)} MB ({reason})",
            context=request.actor_user_id,
        )

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, TimeEntry):
            await self.time_entry_repository.save(aggregate)
        elif isinstance(aggregate, Anomaly):
            await self.anomaly_repository.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
