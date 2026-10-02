from dataclasses import dataclass
from datetime import datetime

from core.application import DTO
from identity.domain.value_objects.location import Location
from punch.domain import EntrySource, EntryType, LocationConfidence
from punch.domain.entities import TimeEntry


@dataclass(frozen=True)
class TimeEntryDTO(DTO):
    id: str
    employee_id: str
    entry_type: EntryType
    location: Location
    location_confidence: LocationConfidence
    source: EntrySource
    created_at: datetime
    updated_at: datetime
    idempotency_key: str | None = None
    wifi_identifier: str | None = None

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
            created_at=time_entry.created_at,
            updated_at=time_entry.updated_at,
        )

class TimeEntriesPageDTO(DTO):
    items: tuple[TimeEntryDTO, ...]
    total: int
