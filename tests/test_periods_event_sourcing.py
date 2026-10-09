"""Period event sourcing without a database: payload round-trips and replay."""

import json
from datetime import UTC, date, datetime

import pytest

from periods.application.notifications import PERIODS_EVENT_MAPPERS
from periods.domain import InvalidPeriodDatesError, PeriodAlreadyClosedError, PeriodId, PeriodNotOpenError, PeriodStatus
from periods.domain.entities import Period
from periods.domain.events import PeriodClosed, PeriodImported, PeriodLocked, PeriodOpened
from periods.infrastructure.persistence.event_sourced_period_repository import PERIOD_EVENT_TYPES


def _replay(period_id, events):
    """Store/load simulation: JSON payload round-trip, original identity restored."""
    loaded = []
    for event in events:
        payload = json.loads(json.dumps(event.to_payload()))
        copy = PERIOD_EVENT_TYPES[event.get_event_name()].from_payload(payload)
        copy.restore_identity(event.event_id, event.occurred_at)
        loaded.append(copy)
    return Period.rehydrate(period_id, loaded)


def _state(period):
    return (
        period.id, period.start_date, period.end_date, period.status, period.closed_at,
        period.created_at, period.updated_at, period.version,
    )


def test_a_period_life_replays_to_the_same_state():
    period_id = PeriodId.generate()
    period = Period.open(period_id, start_date=date(2026, 10, 1), end_date=date(2026, 10, 31))
    assert period.status == PeriodStatus.OPEN and period.contains(date(2026, 10, 15))
    period.lock()
    with pytest.raises(PeriodNotOpenError):
        period.lock()
    period.close(has_open_blocking_anomalies=False)
    with pytest.raises(PeriodAlreadyClosedError):
        period.close(has_open_blocking_anomalies=False)
    events = period.domain_events
    assert [type(e) for e in events] == [PeriodOpened, PeriodLocked, PeriodClosed]
    period._advance_version(len(events))  # what the repository does after append

    replayed = _replay(period_id, events)
    assert replayed.status == PeriodStatus.CLOSED and replayed.closed_at is not None
    assert _state(replayed) == _state(period)
    assert replayed.version == 3


def test_invalid_dates_record_nothing():
    with pytest.raises(InvalidPeriodDatesError):
        Period.open(PeriodId.generate(), start_date=date(2026, 10, 2), end_date=date(2026, 10, 1))


def test_imported_keeps_the_full_state():
    period_id = PeriodId.generate()
    created_at = datetime(2026, 1, 1, 8, tzinfo=UTC)
    event = PeriodImported(
        period_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        status=PeriodStatus.CLOSED,
        closed_at=datetime(2026, 2, 2, 9, tzinfo=UTC),
        created_at=created_at,
    )
    event.restore_identity(event.event_id, datetime(2026, 2, 2, 9, tzinfo=UTC))
    period = Period.rehydrate(period_id, [event])
    replayed = _replay(period_id, [event])
    assert _state(replayed) == _state(period)
    assert replayed.created_at == created_at
    assert replayed.updated_at == datetime(2026, 2, 2, 9, tzinfo=UTC)
    assert replayed.status == PeriodStatus.CLOSED and replayed.version == 1


def test_every_event_is_registered_and_mapped():
    for event_type in (PeriodOpened, PeriodLocked, PeriodClosed, PeriodImported):
        assert event_type in PERIOD_EVENT_TYPES.values()
        assert event_type in PERIODS_EVENT_MAPPERS
    assert PERIODS_EVENT_MAPPERS[PeriodImported] is None
