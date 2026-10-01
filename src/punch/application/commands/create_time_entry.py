from dataclasses import dataclass

from core.application import Command
from identity.domain import EmployeeId
from identity.domain.value_objects.location import Location
from punch.domain import EntrySource, EntryType, LocationConfidence


@dataclass(frozen=True)
class CreateTimeEntryCommand(Command):
    """Create a new time entry."""

    employee_id: EmployeeId
    entry_type: EntryType
    location: Location
    location_confidence: LocationConfidence
    source: EntrySource
    idempotency_key: str | None = None
    wifi_identifier: str | None = None