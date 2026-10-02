from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot
from identity.domain.entities import Employee
from identity.domain.repositories import IEmployeeRepository
from punch.application.commands import CreateTimeEntryCommand
from punch.application.dtos import TimeEntryDTO
from punch.domain import TimeEntryId
from punch.domain.entities import TimeEntry
from punch.domain.repositories import ITimeEntryRepository


class CreateTimeEntryHandler(CommandHandler[CreateTimeEntryCommand, TimeEntryDTO]):
    """Handle the creation of a time entry."""

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        time_entry_repository: ITimeEntryRepository,
        employee_repository: IEmployeeRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self.time_entry_repository = time_entry_repository
        self.employee_repository = employee_repository

    async def _execute(self, request: CreateTimeEntryCommand) -> tuple[TimeEntryDTO, Sequence[AggregateRoot]]:
        employee: Employee = await self.employee_repository.find_by_employee_number(request.employee_number)
        location_confidence = "HIGH" if request.location and request.wifi_identifier else "MEDIUM"
        time_entry = TimeEntry.create(
            time_entry_id=TimeEntryId.generate(),
            employee_id=employee.id,
            entry_type=request.entry_type,
            location=request.location,
            location_confidence=location_confidence,
            source=request.source,
            idempotency_key=request.idempotency_key,
            wifi_identifier=request.wifi_identifier,

        )
        return TimeEntryDTO.from_aggregate(time_entry), [time_entry]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, TimeEntry):
            await self.time_entry_repository.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")