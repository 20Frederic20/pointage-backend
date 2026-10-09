from datetime import datetime

from core.domain.events import BaseEvent, decode_datetime, encode_datetime
from identity.domain.value_objects.ids import EmployeeId
from identity.domain.value_objects.location import Location

from ..value_objects import EntrySource, EntryType, LocationConfidence, TimeEntryId


class TimeEntryCreated(BaseEvent[TimeEntryId]):
    """An employee punched; the server decided the direction."""

    def __init__(
        self,
        time_entry_id: TimeEntryId,
        *,
        employee_id: EmployeeId,
        entry_type: EntryType,
        occured_at: datetime,
        location: Location,
        location_confidence: LocationConfidence,
        source: EntrySource,
        idempotency_key: str | None,
        wifi_identifier: str | None,
    ) -> None:
        super().__init__()
        self.time_entry_id = time_entry_id
        self.employee_id = employee_id
        self.entry_type = entry_type
        self.occured_at = occured_at
        self.location = location
        self.location_confidence = location_confidence
        self.source = source
        self.idempotency_key = idempotency_key
        self.wifi_identifier = wifi_identifier

    def get_aggregate_id(self) -> TimeEntryId:
        return self.time_entry_id

    def get_event_name(self) -> str:
        return "punchs.time_entry.created"

    def to_payload(self) -> dict:
        return {
            "time_entry_id": self.time_entry_id.value,
            "employee_id": self.employee_id.value,
            "entry_type": self.entry_type.value,
            "occured_at": encode_datetime(self.occured_at),
            "latitude": self.location.latitude,
            "longitude": self.location.longitude,
            "location_confidence": self.location_confidence.value,
            "source": self.source.value,
            "idempotency_key": self.idempotency_key,
            "wifi_identifier": self.wifi_identifier,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "TimeEntryCreated":
        return cls(
            TimeEntryId(payload["time_entry_id"]),
            employee_id=EmployeeId(payload["employee_id"]),
            entry_type=EntryType(payload["entry_type"]),
            occured_at=decode_datetime(payload["occured_at"]),
            location=Location(payload["latitude"], payload["longitude"]),
            location_confidence=LocationConfidence(payload["location_confidence"]),
            source=EntrySource(payload["source"]),
            idempotency_key=payload["idempotency_key"],
            wifi_identifier=payload["wifi_identifier"],
        )


class TimeEntryImported(BaseEvent[TimeEntryId]):
    """A time entry taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        time_entry_id: TimeEntryId,
        *,
        employee_id: EmployeeId,
        entry_type: EntryType,
        occured_at: datetime,
        location: Location,
        location_confidence: LocationConfidence,
        source: EntrySource,
        idempotency_key: str | None,
        wifi_identifier: str | None,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.time_entry_id = time_entry_id
        self.employee_id = employee_id
        self.entry_type = entry_type
        self.occured_at = occured_at
        self.location = location
        self.location_confidence = location_confidence
        self.source = source
        self.idempotency_key = idempotency_key
        self.wifi_identifier = wifi_identifier
        self.created_at = created_at

    def get_aggregate_id(self) -> TimeEntryId:
        return self.time_entry_id

    def get_event_name(self) -> str:
        return "punchs.time_entry.imported"

    def to_payload(self) -> dict:
        return {
            "time_entry_id": self.time_entry_id.value,
            "employee_id": self.employee_id.value,
            "entry_type": self.entry_type.value,
            "occured_at": encode_datetime(self.occured_at),
            "latitude": self.location.latitude,
            "longitude": self.location.longitude,
            "location_confidence": self.location_confidence.value,
            "source": self.source.value,
            "idempotency_key": self.idempotency_key,
            "wifi_identifier": self.wifi_identifier,
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "TimeEntryImported":
        return cls(
            TimeEntryId(payload["time_entry_id"]),
            employee_id=EmployeeId(payload["employee_id"]),
            entry_type=EntryType(payload["entry_type"]),
            occured_at=decode_datetime(payload["occured_at"]),
            location=Location(payload["latitude"], payload["longitude"]),
            location_confidence=LocationConfidence(payload["location_confidence"]),
            source=EntrySource(payload["source"]),
            idempotency_key=payload["idempotency_key"],
            wifi_identifier=payload["wifi_identifier"],
            created_at=decode_datetime(payload["created_at"]),
        )
