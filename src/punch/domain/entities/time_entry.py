from datetime import UTC, datetime
from typing import Self

from core.domain.entity import AggregateRoot
from identity.domain import EmployeeId, UserId
from identity.domain.value_objects.location import Location
from punch.domain.errors.errors import TimeEntryNotPendingError
from punch.domain.events import TimeEntryCreated, TimeEntryImported, TimeEntryRejected, TimeEntryValidated
from punch.domain.value_objects import (
    EntrySource,
    EntryType,
    LocationConfidence,
    TimeEntryId,
    TimeEntryValidationStatus,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TimeEntry(AggregateRoot[TimeEntryId]):

    __slots__ = ("_employee_id", "_entry_type", "_idempotency_key", "_location_confidence", "_occured_at", "_source", "_wifi_identifier", "_location", "_assisted_by_user_id", "_photo_key", "_validation_status")

    def __init__ (
        self,
        time_entry_id: TimeEntryId,
        *,
        employee_id: EmployeeId,
        entry_type: EntryType,
        location: Location | None,
        location_confidence: LocationConfidence = LocationConfidence.MEDIUM,
        source: EntrySource = EntrySource.MOBILE,
        occured_at: datetime = _utcnow(),
        idempotency_key: str | None = None,
        wifi_identifier: str | None = None,
        assisted_by_user_id: UserId | None = None,
        photo_key: str | None = None,
        validation_status: TimeEntryValidationStatus = TimeEntryValidationStatus.COUNTED,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    )-> None:
        """

        :param time_entry_id:
        :param employee_id:
        :param occured_at:
        :param entry_type:
        :param location:
        :param location_confidence:
        :param source:
        :param idempotency_key:
        :param wifi_identifier:
        :param assisted_by_user_id:
        :param photo_key:
        :param validation_status:
        :param created_at:
        :param updated_at:
        :param version:
        """
        super().__init__(
            time_entry_id, created_at=created_at, updated_at=updated_at,
            version=version
        )
        self._employee_id = employee_id
        self._entry_type = entry_type
        self._occured_at = occured_at
        self._location = location
        self._location_confidence = location_confidence
        self._wifi_identifier = wifi_identifier
        self._source = source
        self._idempotency_key = idempotency_key
        self._assisted_by_user_id = assisted_by_user_id
        self._photo_key = photo_key
        self._validation_status = validation_status

    @classmethod
    def create(
        cls,
        time_entry_id: TimeEntryId,
        *,
        employee_id: EmployeeId,
        entry_type: EntryType,
        location: Location | None,
        location_confidence: LocationConfidence = LocationConfidence.MEDIUM,
        source: EntrySource = EntrySource.MOBILE,
        wifi_identifier: str | None = None,
        idempotency_key: str | None = None,
        assisted_by_user_id: UserId | None = None,
        photo_key: str | None = None,
        validation_status: TimeEntryValidationStatus = TimeEntryValidationStatus.COUNTED,
    ) -> Self:
        """Record a punch, timestamped now; records :class:`TimeEntryCreated`."""
        time_entry = cls.rehydrate(time_entry_id, [])
        time_entry._raise(
            TimeEntryCreated(
                time_entry_id,
                employee_id=employee_id,
                entry_type=entry_type,
                occured_at=_utcnow(),
                location=location,
                location_confidence=location_confidence,
                source=source,
                idempotency_key=idempotency_key,
                wifi_identifier=wifi_identifier,
                assisted_by_user_id=assisted_by_user_id,
                photo_key=photo_key,
                validation_status=validation_status,
            )
        )
        return time_entry

    def validate(self, *, decided_by: UserId, decided_at: datetime) -> None:
        """A pending punch now counts; records :class:`TimeEntryValidated`."""
        self._require_pending()
        self._raise(TimeEntryValidated(self.id, decided_by=decided_by, decided_at=decided_at))

    def reject(self, *, decided_by: UserId, decided_at: datetime) -> None:
        """A pending punch never counts; records :class:`TimeEntryRejected`."""
        self._require_pending()
        self._raise(TimeEntryRejected(self.id, decided_by=decided_by, decided_at=decided_at))

    def _require_pending(self) -> None:
        if self._validation_status != TimeEntryValidationStatus.PENDING:
            raise TimeEntryNotPendingError(
                f"TimeEntry {self.id} is not pending (status {self._validation_status})", context=self.id.value
            )

    def _apply(self, event) -> None:
        match event:
            case TimeEntryCreated() | TimeEntryImported():
                self._employee_id = event.employee_id
                self._entry_type = event.entry_type
                self._occured_at = event.occured_at
                self._location = event.location
                self._location_confidence = event.location_confidence
                self._source = event.source
                self._idempotency_key = event.idempotency_key
                self._wifi_identifier = event.wifi_identifier
                self._assisted_by_user_id = event.assisted_by_user_id
                self._photo_key = event.photo_key
                self._validation_status = event.validation_status
                if isinstance(event, TimeEntryImported):
                    self._created_at = event.created_at
            case TimeEntryValidated():
                self._validation_status = TimeEntryValidationStatus.COUNTED
            case TimeEntryRejected():
                self._validation_status = TimeEntryValidationStatus.REJECTED
            case _:
                super()._apply(event)

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
    def location_confidence(self) -> str:
        return self._location_confidence

    @property
    def location(self) -> Location | None:
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

    @property
    def assisted_by_user_id(self) -> UserId | None:
        return self._assisted_by_user_id

    @property
    def photo_key(self) -> str | None:
        return self._photo_key

    @property
    def validation_status(self) -> TimeEntryValidationStatus:
        return self._validation_status

    @property
    def counts(self) -> bool:
        return self._validation_status == TimeEntryValidationStatus.COUNTED
