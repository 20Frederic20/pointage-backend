from datetime import datetime

from core.domain.events import BaseEvent, decode_datetime, encode_datetime
from identity.domain.value_objects.ids import EmployeeId, UserId
from identity.domain.value_objects.location import Location

from ..value_objects import EntrySource, EntryType, LocationConfidence, TimeEntryId, TimeEntryValidationStatus


def _location(payload: dict) -> Location | None:
    if payload.get("latitude") is None or payload.get("longitude") is None:
        return None
    return Location(payload["latitude"], payload["longitude"])


def _user_id(value: str | None) -> UserId | None:
    return UserId(value) if value else None


class TimeEntryCreated(BaseEvent[TimeEntryId]):
    """An employee punched; the server decided the direction."""

    def __init__(
        self,
        time_entry_id: TimeEntryId,
        *,
        employee_id: EmployeeId,
        entry_type: EntryType,
        occured_at: datetime,
        location: Location | None,
        location_confidence: LocationConfidence,
        source: EntrySource,
        idempotency_key: str | None,
        wifi_identifier: str | None,
        assisted_by_user_id: UserId | None = None,
        photo_key: str | None = None,
        validation_status: TimeEntryValidationStatus = TimeEntryValidationStatus.COUNTED,
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
        self.assisted_by_user_id = assisted_by_user_id
        self.photo_key = photo_key
        self.validation_status = validation_status

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
            "latitude": self.location.latitude if self.location else None,
            "longitude": self.location.longitude if self.location else None,
            "location_confidence": self.location_confidence.value,
            "source": self.source.value,
            "idempotency_key": self.idempotency_key,
            "wifi_identifier": self.wifi_identifier,
            "assisted_by_user_id": self.assisted_by_user_id.value if self.assisted_by_user_id else None,
            "photo_key": self.photo_key,
            "validation_status": self.validation_status.value,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "TimeEntryCreated":
        return cls(
            TimeEntryId(payload["time_entry_id"]),
            employee_id=EmployeeId(payload["employee_id"]),
            entry_type=EntryType(payload["entry_type"]),
            occured_at=decode_datetime(payload["occured_at"]),
            location=_location(payload),
            location_confidence=LocationConfidence(payload["location_confidence"]),
            source=EntrySource(payload["source"]),
            idempotency_key=payload["idempotency_key"],
            wifi_identifier=payload["wifi_identifier"],
            assisted_by_user_id=_user_id(payload.get("assisted_by_user_id")),
            photo_key=payload.get("photo_key"),
            validation_status=TimeEntryValidationStatus(payload.get("validation_status", "COUNTED")),
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
        location: Location | None,
        location_confidence: LocationConfidence,
        source: EntrySource,
        idempotency_key: str | None,
        wifi_identifier: str | None,
        created_at: datetime,
        assisted_by_user_id: UserId | None = None,
        photo_key: str | None = None,
        validation_status: TimeEntryValidationStatus = TimeEntryValidationStatus.COUNTED,
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
        self.assisted_by_user_id = assisted_by_user_id
        self.photo_key = photo_key
        self.validation_status = validation_status
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
            "latitude": self.location.latitude if self.location else None,
            "longitude": self.location.longitude if self.location else None,
            "location_confidence": self.location_confidence.value,
            "source": self.source.value,
            "idempotency_key": self.idempotency_key,
            "wifi_identifier": self.wifi_identifier,
            "assisted_by_user_id": self.assisted_by_user_id.value if self.assisted_by_user_id else None,
            "photo_key": self.photo_key,
            "validation_status": self.validation_status.value,
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "TimeEntryImported":
        return cls(
            TimeEntryId(payload["time_entry_id"]),
            employee_id=EmployeeId(payload["employee_id"]),
            entry_type=EntryType(payload["entry_type"]),
            occured_at=decode_datetime(payload["occured_at"]),
            location=_location(payload),
            location_confidence=LocationConfidence(payload["location_confidence"]),
            source=EntrySource(payload["source"]),
            idempotency_key=payload["idempotency_key"],
            wifi_identifier=payload["wifi_identifier"],
            assisted_by_user_id=_user_id(payload.get("assisted_by_user_id")),
            photo_key=payload.get("photo_key"),
            validation_status=TimeEntryValidationStatus(payload.get("validation_status", "COUNTED")),
            created_at=decode_datetime(payload["created_at"]),
        )



class _TimeEntryDecided(BaseEvent[TimeEntryId]):
    """A manager decided on a pending time entry."""

    def __init__(self, time_entry_id: TimeEntryId, *, decided_by: UserId, decided_at: datetime) -> None:
        super().__init__()
        self.time_entry_id = time_entry_id
        self.decided_by = decided_by
        self.decided_at = decided_at

    def get_aggregate_id(self) -> TimeEntryId:
        return self.time_entry_id

    def to_payload(self) -> dict:
        return {
            "time_entry_id": self.time_entry_id.value,
            "decided_by": self.decided_by.value,
            "decided_at": encode_datetime(self.decided_at),
        }

    @classmethod
    def from_payload(cls, payload: dict):
        return cls(
            TimeEntryId(payload["time_entry_id"]),
            decided_by=UserId(payload["decided_by"]),
            decided_at=decode_datetime(payload["decided_at"]),
        )


class TimeEntryValidated(_TimeEntryDecided):
    """A pending time entry now counts."""

    def get_event_name(self) -> str:
        return "punchs.time_entry.validated"


class TimeEntryRejected(_TimeEntryDecided):
    """A pending time entry will never count."""

    def get_event_name(self) -> str:
        return "punchs.time_entry.rejected"
