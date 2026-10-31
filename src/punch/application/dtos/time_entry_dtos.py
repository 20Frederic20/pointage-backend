from dataclasses import dataclass
from datetime import datetime

from core.application import DTO
from identity.domain.value_objects.location import Location
from punch.domain import EntrySource, EntryType, LocationConfidence, TimeEntryValidationStatus
from punch.domain.entities import TimeEntry


@dataclass(frozen=True)
class TimeEntryDTO(DTO):
    id: str
    employee_id: str
    entry_type: EntryType
    location: Location | None
    location_confidence: LocationConfidence
    source: EntrySource
    created_at: datetime
    updated_at: datetime
    occured_at: datetime | None = None
    idempotency_key: str | None = None
    wifi_identifier: str | None = None
    assisted_by_user_id: str | None = None
    photo_key: str | None = None
    validation_status: str = TimeEntryValidationStatus.COUNTED.value

    @classmethod
    def from_aggregate(cls, time_entry: TimeEntry) -> "TimeEntryDTO":
        return cls(
            id=time_entry.id.value,
            employee_id=time_entry.employee_id.value,
            entry_type=EntryType(time_entry.entry_type),
            location=time_entry.location,
            location_confidence=LocationConfidence(time_entry.location_confidence),
            source=time_entry.source,
            idempotency_key=time_entry.idempotency_key,
            wifi_identifier=time_entry.wifi_identifier,
            assisted_by_user_id=time_entry.assisted_by_user_id.value if time_entry.assisted_by_user_id else None,
            photo_key=time_entry.photo_key,
            validation_status=time_entry.validation_status.value,
            occured_at=time_entry.occured_at,
            created_at=time_entry.created_at,
            updated_at=time_entry.updated_at,
        )

@dataclass(frozen=True)
class EmployeeLookupDTO(DTO):
    """What an assisted punch may show about the punched employee: nothing else."""

    employee_number: str
    first_name: str | None
    last_name: str | None


class TimeEntriesPageDTO(DTO):
    items: tuple[TimeEntryDTO, ...]
    total: int
