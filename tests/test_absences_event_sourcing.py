"""Absences aggregates rebuild from their stored events alone (no database)."""

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from absences.application.notifications import ABSENCES_EVENT_MAPPERS
from absences.domain import AbsenceId, AbsenceNotPendingError, AbsenceStatus, AbsenceTypeId
from absences.domain.entities import Absence, AbsenceType
from absences.domain.events import (
    AbsenceApproved,
    AbsenceDeclared,
    AbsenceImported,
    AbsenceRejected,
    AbsenceTypeCreated,
    AbsenceTypeImported,
)
from identity.domain import EmployeeId


from absences.infrastructure.persistence.event_sourced_absence_repository import ABSENCE_EVENT_TYPES  # noqa: E402
from absences.infrastructure.persistence.event_sourced_absence_type_repository import (  # noqa: E402
    ABSENCE_TYPE_EVENT_TYPES,
)

START = datetime(2026, 10, 5, 8, 0, tzinfo=UTC)

ABSENCE_PROPS = ("id", "employee_id", "absence_type_id", "start_at", "end_at", "reason", "status",
                 "justification_reference", "created_at", "updated_at", "version")
TYPE_PROPS = ("id", "name", "paid", "counts_as_work_time", "deducts_balance", "active",
              "created_at", "updated_at", "version")


def replay(aggregate, event_types):
    stored = []
    for event in aggregate.domain_events:
        loaded = event_types[event.get_event_name()].from_payload(json.loads(json.dumps(event.to_payload())))
        loaded.restore_identity(event.event_id, event.occurred_at)
        stored.append(loaded)
    aggregate._advance_version(len(stored))  # what the event-sourced repository's save does
    return type(aggregate).rehydrate(aggregate.id, stored)


def assert_same(a, b, props):
    for prop in props:
        assert getattr(a, prop) == getattr(b, prop), prop


def sick_leave():
    return AbsenceType.create(
        AbsenceTypeId.generate(), name="  Sick leave ", paid=True, counts_as_work_time=False, deducts_balance=False
    )


def declare(absence_type):
    return Absence.declare(
        AbsenceId.generate(),
        employee_id=EmployeeId.generate(),
        absence_type=absence_type,
        start_at=START,
        end_at=START + timedelta(days=2),
        reason="Flu",
        justification_reference="cert-42",
    )


def test_absence_type_replays_from_its_events():
    absence_type = sick_leave()
    assert absence_type.name == "Sick leave" and absence_type.active
    rebuilt = replay(absence_type, ABSENCE_TYPE_EVENT_TYPES)
    assert_same(rebuilt, absence_type, TYPE_PROPS)
    assert rebuilt.version == 1


@pytest.mark.parametrize("decide, status", [("approve", AbsenceStatus.APPROVED), ("reject", AbsenceStatus.REJECTED)])
def test_absence_replays_its_whole_life(decide, status):
    absence = declare(sick_leave())
    assert absence.status == AbsenceStatus.PENDING
    getattr(absence, decide)()
    with pytest.raises(AbsenceNotPendingError):
        absence.approve()
    assert absence.status == status
    rebuilt = replay(absence, ABSENCE_EVENT_TYPES)
    assert_same(rebuilt, absence, ABSENCE_PROPS)
    assert rebuilt.version == 2


def test_neutralizing_resolves_the_anomaly_and_records_nothing_on_the_absence():
    absence = declare(sick_leave())
    absence.approve()
    resolved = {}
    anomaly = SimpleNamespace(
        id=SimpleNamespace(value="a1"),
        detected_at=START + timedelta(hours=3),
        resolve=lambda *, resolved_at: resolved.setdefault("at", resolved_at),
    )
    absence.neutralize_anomaly(anomaly, anomaly_employee_id=absence.employee_id)
    assert "at" in resolved
    assert len(absence.domain_events) == 2


def test_imported_events_carry_the_full_state():
    created_at = datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)
    updated_at = created_at + timedelta(days=1)

    type_event = AbsenceTypeImported(
        AbsenceTypeId.generate(), name="Old", paid=False, counts_as_work_time=True, deducts_balance=True,
        active=False, created_at=created_at,
    )
    type_event.restore_identity(type_event.event_id, updated_at)
    absence_type = AbsenceType.rehydrate(type_event.absence_type_id, [])
    absence_type.apply(type_event)
    absence_type.record_event(type_event)
    rebuilt_type = replay(absence_type, ABSENCE_TYPE_EVENT_TYPES)
    assert_same(rebuilt_type, absence_type, TYPE_PROPS)
    assert (rebuilt_type.created_at, rebuilt_type.updated_at, rebuilt_type.active) == (created_at, updated_at, False)

    event = AbsenceImported(
        AbsenceId.generate(), employee_id=EmployeeId.generate(), absence_type_id=absence_type.id,
        start_at=START, end_at=START + timedelta(hours=4), reason="Doctor", status=AbsenceStatus.APPROVED,
        justification_reference=None, created_at=created_at,
    )
    event.restore_identity(event.event_id, updated_at)
    absence = Absence.rehydrate(event.absence_id, [])
    absence.apply(event)
    absence.record_event(event)
    rebuilt = replay(absence, ABSENCE_EVENT_TYPES)
    assert_same(rebuilt, absence, ABSENCE_PROPS)
    assert (rebuilt.created_at, rebuilt.status, rebuilt.version) == (created_at, AbsenceStatus.APPROVED, 1)


def test_every_event_is_registered():
    for event_types, classes in (
        (ABSENCE_EVENT_TYPES, {AbsenceDeclared, AbsenceApproved, AbsenceRejected, AbsenceImported}),
        (ABSENCE_TYPE_EVENT_TYPES, {AbsenceTypeCreated, AbsenceTypeImported}),
    ):
        assert set(event_types.values()) == classes
        assert classes <= ABSENCES_EVENT_MAPPERS.keys()
    assert ABSENCES_EVENT_MAPPERS[AbsenceImported] is None
    assert ABSENCES_EVENT_MAPPERS[AbsenceTypeImported] is None
