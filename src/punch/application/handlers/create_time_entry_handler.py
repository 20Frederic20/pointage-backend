from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot
from identity.domain import EmployeeId
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
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self.time_entry_repository = time_entry_repository

    async def _execute(self, request: CreateTimeEntryCommand) -> tuple[TimeEntryDTO, Sequence[AggregateRoot]]:
        time_entry = await TimeEntry.create(
            time_entry_id=TimeEntryId.generate(),
            employee_id=EmployeeId(request.employee_id),
            entry_type=request.entry_type,
            location=request.location,
            location_confidence=request.location_confidence,
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