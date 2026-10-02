from datetime import UTC, datetime
from typing import Self

from core.domain.entity import AggregateRoot
from identity.domain import EmployeeId
from identity.domain.value_objects.location import Location
from punch.domain.events import TimeEntryCreated
from punch.domain.value_objects import (
    EntrySource,
    EntryType,
    LocationConfidence,
    TimeEntryId,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TimeEntry(AggregateRoot[TimeEntryId]):

    __slots__ = ("_employee_id", "_entry_type", "_idempotency_key", "_is_active", "_location_confidence", "_occured_at", "_source", "_wifi_identifier", "_location")

    def __init__ (
        self,
        time_entry_id: TimeEntryId,
        *,
        employee_id: EmployeeId,
        occured_at: datetime,
        entry_type: EntryType,
        location: Location,
        location_confidence: LocationConfidence = LocationConfidence.MEDIUM,
        source: EntrySource = EntrySource.MOBILE,
        idempotency_key: str | None = None,
        wifi_identifier: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    )-> None:
        super().__init__(
            time_entry_id, created_at=created_at, updated_at=updated_at,
            version=version
        )
        self._employee_id = employee_id,
        self._entry_type = entry_type,
        self._occured_at = occured_at,
        self._location = location,
        self._location_confidence = location_confidence,
        self._wifi_identifier = wifi_identifier
        self._source = source
        self._idempotency_key = idempotency_key

    @classmethod
    def create(
        cls,
        time_entry_id: TimeEntryId,
        *,
        employee_id: EmployeeId,
        occured_at: datetime,
        entry_type: EntryType,
        location: Location,
        wifi_identifier: str | None = None,
        location_confidence: LocationConfidence = LocationConfidence.MEDIUM,
        source: EntrySource = EntrySource.MOBILE,
        idempotency_key: str,
    ) -> Self:
        """
        Founding signup: the first employee of a brand-new workspace,.
        """
        time_entry = cls(
            time_entry_id,
            employee_id=employee_id,
            occured_at=occured_at,
            location_confidence=location_confidence,
            entry_type=entry_type,
            location=location,
            wifi_identifier=wifi_identifier,
            source=source,
            idempotency_key=idempotency_key
        )
        time_entry.record_event(TimeEntryCreated(time_entry_id))
        return time_entry

    @property
    def employee_id(self) -> EmployeeId:
        return self._employee_id

    @property
    def occured_at(self) -> datetime:
        return self._occured_at

    @property
    def entry_type(self) -> str:
        return self._entry_type

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def location_confidence(self) -> str:
        return self._location_confidence

    @property
    def location(self) -> Location:
        return self._location

    @property
    def source(self) -> EntrySource:
        return self._source

    @property
    def idempotency_key(self) -> str | None:
        return self._idempotency_key

    @property
    def wifi_identifier(self) -> str | None:
        return self._wifi_identifier