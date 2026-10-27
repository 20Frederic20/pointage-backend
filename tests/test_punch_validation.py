"""TimeEntry validation status, assistant, photo and optional location (no database)."""

import json
from datetime import UTC, datetime

import pytest

from identity.domain import EmployeeId, UserId
from identity.domain.value_objects.location import Location
from punch.domain import EntrySource, EntryType, LocationConfidence, TimeEntryId, TimeEntryValidationStatus
from punch.domain.entities import TimeEntry
from punch.domain.errors.errors import TimeEntryNotPendingError
from punch.domain.events import TimeEntryCreated
from punch.infrastructure.persistence.event_sourced_time_entry_repository import TIME_ENTRY_EVENT_TYPES

DECIDED_AT = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
PROPS = ("id", "employee_id", "entry_type", "source", "location", "location_confidence", "assisted_by_user_id",
         "photo_key", "validation_status", "counts")


def replay(entry: TimeEntry) -> TimeEntry:
    stored = []
    for event in entry.domain_events:
        payload = json.loads(json.dumps(event.to_payload()))
        copy = TIME_ENTRY_EVENT_TYPES[event.get_event_name()].from_payload(payload)
        copy.restore_identity(event.event_id, event.occurred_at)
        stored.append(copy)
    return TimeEntry.rehydrate(entry.id, stored)


def assert_same(left: TimeEntry, right: TimeEntry) -> None:
    for prop in PROPS:
        assert getattr(left, prop) == getattr(right, prop), prop


def pending_entry() -> TimeEntry:
    return TimeEntry.create(
        TimeEntryId.generate(),
        employee_id=EmployeeId("emp1"),
        entry_type=EntryType.IN,
        location=Location(48.85, 2.35),
        source=EntrySource.ASSISTED,
        assisted_by_user_id=UserId("usr2"),
        photo_key="time-entries/x.jpg",
        validation_status=TimeEntryValidationStatus.PENDING,
    )


def test_pending_entry_validates_and_counts():
    entry = pending_entry()
    assert not entry.counts
    assert entry.assisted_by_user_id == UserId("usr2")
    assert entry.photo_key == "time-entries/x.jpg"

    entry.validate(decided_by=UserId("usr3"), decided_at=DECIDED_AT)

    assert entry.validation_status == TimeEntryValidationStatus.COUNTED
    assert entry.counts
    copy = replay(entry)
    assert_same(entry, copy)
    assert copy.counts
    assert copy.photo_key == "time-entries/x.jpg"


def test_pending_entry_rejects_and_never_counts():
    entry = pending_entry()

    entry.reject(decided_by=UserId("usr3"), decided_at=DECIDED_AT)

    assert entry.validation_status == TimeEntryValidationStatus.REJECTED
    assert not entry.counts
    assert_same(entry, replay(entry))


def test_decision_on_counted_or_decided_entry_is_refused():
    counted = TimeEntry.create(
        TimeEntryId.generate(), employee_id=EmployeeId("emp1"), entry_type=EntryType.IN, location=Location(48.85, 2.35)
    )
    with pytest.raises(TimeEntryNotPendingError):
        counted.validate(decided_by=UserId("usr3"), decided_at=DECIDED_AT)

    rejected = pending_entry()
    rejected.reject(decided_by=UserId("usr3"), decided_at=DECIDED_AT)
    with pytest.raises(TimeEntryNotPendingError):
        rejected.reject(decided_by=UserId("usr4"), decided_at=DECIDED_AT)
    with pytest.raises(TimeEntryNotPendingError):
        rejected.validate(decided_by=UserId("usr4"), decided_at=DECIDED_AT)


def test_entry_without_location_replays():
    entry = TimeEntry.create(
        TimeEntryId.generate(),
        employee_id=EmployeeId("emp1"),
        entry_type=EntryType.OUT,
        location=None,
        location_confidence=LocationConfidence.LOW,
        source=EntrySource.MANAGER_ASSISTED,
    )

    copy = replay(entry)

    assert copy.location is None
    assert copy.location_confidence == LocationConfidence.LOW
    assert_same(entry, copy)


def test_legacy_created_payload_replays_as_counted():
    payload = json.loads(json.dumps(pending_entry().domain_events[0].to_payload()))
    for key in ("assisted_by_user_id", "photo_key", "validation_status"):
        del payload[key]

    event = TimeEntryCreated.from_payload(payload)
    entry = TimeEntry.rehydrate(event.time_entry_id, [event])

    assert entry.validation_status == TimeEntryValidationStatus.COUNTED
    assert entry.counts
    assert entry.assisted_by_user_id is None
    assert entry.photo_key is None
