"""Adjustements aggregates rebuild from their stored events alone (no database)."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from adjustements.application.notifications import ADJUSTMENTS_EVENT_MAPPERS
from adjustements.domain import AnomalyId, AnomalyStatus, AnomalyType, RegularizationRequestId, RegularizationStatus, Severity
from adjustements.domain.entities import Anomaly, RegularizationRequest
from adjustements.domain.events import (
    AnomalyCreated,
    AnomalyImported,
    AnomalyResolved,
    RegularizationRequestCreated,
    RegularizationRequestImported,
)
from adjustements.infrastructure.persistence.event_sourced_anomaly_repository import ANOMALY_EVENT_TYPES
from adjustements.infrastructure.persistence.event_sourced_regularization_request_repository import (
    REGULARIZATION_REQUEST_EVENT_TYPES,
)
from core.domain.errors import ConflictError
from punch.domain import TimeEntryId

DETECTED = datetime(2026, 10, 7, 8, 30, tzinfo=UTC)

ANOMALY_PROPS = ("id", "time_entry_id", "type", "severity", "status", "detected_at", "resolved_at", "description",
                 "created_at", "updated_at", "version")
REQUEST_PROPS = ("id", "anomaly_id", "request_at", "reason", "proposed_time", "status", "decision_comment",
                 "validated_at", "created_at", "updated_at", "version")


def replay(aggregate_type, aggregate, event_types, events):
    stored = []
    for event in events:
        payload = json.loads(json.dumps(event.to_payload()))
        copy = event_types[event.get_event_name()].from_payload(payload)
        copy.restore_identity(event.event_id, event.occurred_at)
        stored.append(copy)
    return aggregate_type.rehydrate(aggregate.id, stored)


def assert_same(left, right, props):
    for prop in props:
        assert getattr(left, prop) == getattr(right, prop), prop


def new_anomaly() -> Anomaly:
    return Anomaly.create(
        AnomalyId.generate(),
        time_entry_id=TimeEntryId.generate(),
        type=AnomalyType.MISSING_OUT,
        severity=Severity.BLOCKING,
        status=AnomalyStatus.OPEN,
        detected_at=DETECTED,
        description="No OUT punch",
    )


def test_anomaly_life_replays_from_its_events():
    anomaly = new_anomaly()
    anomaly.resolve(resolved_at=DETECTED + timedelta(days=1))
    with pytest.raises(ConflictError):
        anomaly.resolve(resolved_at=DETECTED + timedelta(days=2))
    events = anomaly.domain_events
    assert [type(e) for e in events] == [AnomalyCreated, AnomalyResolved]
    anomaly._advance_version(len(events))

    rebuilt = replay(Anomaly, anomaly, ANOMALY_EVENT_TYPES, events)
    assert_same(rebuilt, anomaly, ANOMALY_PROPS)
    assert rebuilt.version == 2
    assert rebuilt.status == AnomalyStatus.RESOLVED


def test_anomaly_import_keeps_the_full_state():
    current = new_anomaly()
    current.resolve(resolved_at=DETECTED + timedelta(hours=3))
    event = AnomalyImported(
        current.id,
        time_entry_id=current.time_entry_id,
        type=current.type,
        severity=current.severity,
        status=current.status,
        detected_at=current.detected_at,
        resolved_at=current.resolved_at,
        description=current.description,
        created_at=DETECTED - timedelta(days=30),
    )
    event.restore_identity(event.event_id, current.updated_at)
    rebuilt = replay(Anomaly, current, ANOMALY_EVENT_TYPES, [event])
    assert rebuilt.created_at == DETECTED - timedelta(days=30)
    assert rebuilt.version == 1
    assert_same(rebuilt, current, ANOMALY_PROPS[:-3])


def test_regularization_request_life_and_import_replay():
    request = RegularizationRequest.create(
        RegularizationRequestId.generate(),
        request_at=DETECTED + timedelta(hours=1),
        reason="Forgot to punch out",
        proposed_time=DETECTED + timedelta(hours=9),
        status=RegularizationStatus.PENDING,
        anomaly_id=AnomalyId.generate(),
    )
    events = request.domain_events
    request._advance_version(len(events))
    assert_same(replay(RegularizationRequest, request, REGULARIZATION_REQUEST_EVENT_TYPES, events), request,
                REQUEST_PROPS)

    event = RegularizationRequestImported(
        request.id,
        anomaly_id=request.anomaly_id,
        request_at=request.request_at,
        reason=request.reason,
        proposed_time=request.proposed_time,
        status=RegularizationStatus.APPROVED,
        decision_comment="ok",
        validated_at=DETECTED + timedelta(days=1),
        created_at=DETECTED - timedelta(days=2),
    )
    rebuilt = replay(RegularizationRequest, request, REGULARIZATION_REQUEST_EVENT_TYPES, [event])
    assert rebuilt.created_at == DETECTED - timedelta(days=2)
    assert (rebuilt.status, rebuilt.decision_comment, rebuilt.validated_at) == (
        RegularizationStatus.APPROVED, "ok", DETECTED + timedelta(days=1))
    assert rebuilt.version == 1


def test_every_event_is_registered_and_mapped():
    for event_types, classes in (
        (ANOMALY_EVENT_TYPES, (AnomalyCreated, AnomalyResolved, AnomalyImported)),
        (REGULARIZATION_REQUEST_EVENT_TYPES, (RegularizationRequestCreated, RegularizationRequestImported)),
    ):
        assert set(event_types.values()) == set(classes)
        for name, cls in event_types.items():
            assert cls in ADJUSTMENTS_EVENT_MAPPERS
            assert cls.get_event_name(cls.__new__(cls)) == name
    assert ADJUSTMENTS_EVENT_MAPPERS[AnomalyImported] is None
    assert ADJUSTMENTS_EVENT_MAPPERS[RegularizationRequestImported] is None
