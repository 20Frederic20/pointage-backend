from collections.abc import Sequence
from datetime import UTC, datetime

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot
from core.domain.errors import NotFoundError
from identity.domain.entities import Employee, Directory
from identity.domain.repositories import IDirectoryRepository, IEmployeeAssignmentRepository, IEmployeeRepository
from punch.application.commands import CreateTimeEntryCommand
from punch.application.dtos import TimeEntryDTO
from punch.domain import TimeEntryId, LocationConfidence
from punch.domain.entities import TimeEntry
from punch.domain.errors import EmployeeHasAlreadyPunchedThisTypeOfEntryError, EmployeeNotAssignedError
from punch.domain.repositories import ITimeEntryRepository
from punch.domain.services.distance_calculator import DistanceCalculator


class CreateTimeEntryHandler(CommandHandler[CreateTimeEntryCommand, TimeEntryDTO]):
    """Handle the creation of a time entry."""

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        time_entry_repository: ITimeEntryRepository,
        employee_repository: IEmployeeRepository,
        directory_repository: IDirectoryRepository,
        employee_assignment_repository: IEmployeeAssignmentRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self.time_entry_repository = time_entry_repository
        self.employee_repository = employee_repository
        self.directory_repository = directory_repository
        self.employee_assignment_repository = employee_assignment_repository

    async def _execute(self, request: CreateTimeEntryCommand) -> tuple[TimeEntryDTO, Sequence[AggregateRoot]]:
        employee: Employee | None = await self.employee_repository.find_by_employee_number(request.employee_number)
        if not employee:
            raise NotFoundError(f"Employee with number {request.employee_number} not found")

        # The reference location is the directory of the assignment covering today.
        assignment = await self.employee_assignment_repository.find_active(employee.id, datetime.now(UTC).date())
        if assignment is None:
            raise EmployeeNotAssignedError(
                f"Employee {request.employee_number} has no active assignment today",
                context=employee.id.value,
            )
        directory: Directory = await self.directory_repository.get_by_id(assignment.directory_id)

        distance = DistanceCalculator.calculate(
            latitude_1=request.location.latitude,
            longitude_1=request.location.longitude,
            latitude_2=directory.location.latitude,
            longitude_2=directory.location.longitude,
        )

        if distance > 100:
            raise ValueError(f"Employee {employee.id} is too far from the directory location: {distance} meters")

        last_entry: TimeEntry | None = await self.time_entry_repository.find_last_by_employee_id(employee.id)
        if last_entry and last_entry.entry_type == request.entry_type:
            raise EmployeeHasAlreadyPunchedThisTypeOfEntryError(f"Employee {employee.id} already has a time entry of type {request.entry_type}")


        location_confidence = (
            LocationConfidence("HIGH")
            if request.location and request.wifi_identifier
            else LocationConfidence("MEDIUM")
        )
        time_entry = TimeEntry.create(
            time_entry_id=TimeEntryId.generate(),
            employee_id=employee.id,
            entry_type=request.entry_type,
            location=request.location,
            location_confidence=LocationConfidence(location_confidence),
            source=request.source,
            idempotency_key=request.idempotency_key if request.idempotency_key else None,
            wifi_identifier=request.wifi_identifier,

        )
        return TimeEntryDTO.from_aggregate(time_entry), [time_entry]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, TimeEntry):
            await self.time_entry_repository.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")