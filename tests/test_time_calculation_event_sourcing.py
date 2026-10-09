"""Time calculation aggregates rebuilt from their stored events (no database).

Run from ``backend/``: ``uv run pytest``.
"""

import importlib
import json
from datetime import UTC, date, datetime, timedelta

import pytest

from identity.domain import EmployeeId
from periods.domain import PeriodId
from punch.domain import EntryType
from time_calculation.application.notifications import TIME_CALCULATION_EVENT_MAPPERS
from time_calculation.domain import (
    BlockedDailyTimeResultError,
    CalculationRuleVersionId,
    DailyResultStatus,
    DailyTimeResultId,
    DailyTimeResultValidatedError,
    PlannedDay,
)
from time_calculation.domain.entities import CalculationRuleVersion, DailyTimeResult
from time_calculation.domain.events import (
    CalculationRuleVersionClosed,
    CalculationRuleVersionCreated,
    CalculationRuleVersionImported,
    DailyTimeResultCalculated,
    DailyTimeResultImported,
    DailyTimeResultValidated,
)

RULE_PROPERTIES = (
    "id", "rule_version", "effective_from", "effective_to", "min_break_duration", "break_threshold",
    "max_daily_work_duration", "max_amplitude", "created_at", "updated_at",
)
RESULT_PROPERTIES = (
    "id", "employee_id", "period_id", "calculation_rule_version_id", "work_date", "planned_duration",
    "worked_duration", "break_duration", "absence_duration", "late_duration", "status", "calculated_at",
    "created_at", "updated_at",
)
DAY = date(2026, 10, 7)


def _persistence_module(name: str):
    return importlib.import_module(f"time_calculation.infrastructure.persistence.{name}")


def _replayed(aggregate_type, aggregate):
    events = []
    for event in aggregate.domain_events:
        loaded = type(event).from_payload(json.loads(json.dumps(event.to_payload())))
        loaded.restore_identity(event.event_id, event.occurred_at)
        events.append(loaded)
    return aggregate_type.rehydrate(aggregate.id, events)


def _assert_same(original, replayed, properties, version=None):
    for name in properties:
        assert getattr(replayed, name) == getattr(original, name), name
    # The original is unsaved (version 0); its stream would hold every recorded event.
    assert replayed.version == (len(original.domain_events) if version is None else version)


def _rules():
    first = CalculationRuleVersion.create(
        CalculationRuleVersionId.generate(),
        previous=None,
        effective_from=date(2026, 1, 1),
        min_break_duration=timedelta(minutes=45),
        break_threshold=timedelta(hours=6),
        max_daily_work_duration=timedelta(hours=10),
        max_amplitude=timedelta(hours=13),
    )
    second = CalculationRuleVersion.create(
        CalculationRuleVersionId.generate(),
        previous=first,
        effective_from=date(2026, 6, 1),
        min_break_duration=timedelta(minutes=30),
        break_threshold=timedelta(hours=6),
        max_daily_work_duration=timedelta(hours=9),
        max_amplitude=timedelta(hours=12),
    )
    return first, second


def test_rule_versions_replay_create_and_close():
    first, second = _rules()
    assert [type(e) for e in first.domain_events] == [CalculationRuleVersionCreated, CalculationRuleVersionClosed]
    assert first.effective_to == date(2026, 5, 31)
    assert second.rule_version == 2 and second.effective_to is None
    for rule_version in (first, second):
        _assert_same(rule_version, _replayed(CalculationRuleVersion, rule_version), RULE_PROPERTIES)
    assert _replayed(CalculationRuleVersion, first).version == 2


def _clock(hour, minute=0):
    return datetime(2026, 10, 7, hour, minute, tzinfo=UTC)


def _result_life():
    _, rules = _rules()
    planned = PlannedDay(
        start=_clock(8), end=_clock(17), planned_duration=timedelta(hours=8), tolerance=timedelta(minutes=5)
    )
    result = DailyTimeResult.calculate(
        DailyTimeResultId.generate(),
        employee_id=EmployeeId.generate(),
        period_id=PeriodId.generate(),
        work_date=DAY,
        rules=rules,
        planned_day=planned,
        clockings=[(_clock(8, 20), EntryType.IN), (_clock(12), EntryType.OUT), (_clock(13), EntryType.IN)],
        absences=[],
        has_open_blocking_anomaly=True,
        has_open_anomaly=True,
    )
    assert result.status == DailyResultStatus.BLOCKED
    with pytest.raises(BlockedDailyTimeResultError):
        result.validate()
    result.recalculate(
        period_id=PeriodId.generate(),
        rules=rules,
        planned_day=planned,
        clockings=[
            (_clock(8, 20), EntryType.IN),
            (_clock(12), EntryType.OUT),
            (_clock(13), EntryType.IN),
            (_clock(17), EntryType.OUT),
        ],
        absences=[],
        has_open_blocking_anomaly=False,
        has_open_anomaly=False,
    )
    assert result.status == DailyResultStatus.NORMAL
    assert result.worked_duration == timedelta(hours=7, minutes=40)
    result.validate()
    with pytest.raises(DailyTimeResultValidatedError):
        result.recalculate(
            period_id=result.period_id, rules=rules, planned_day=None, clockings=[], absences=[],
            has_open_blocking_anomaly=False, has_open_anomaly=False,
        )
    return result


def test_daily_time_result_replays_the_computed_values():
    result = _result_life()
    assert [type(e) for e in result.domain_events] == [
        DailyTimeResultCalculated, DailyTimeResultCalculated, DailyTimeResultValidated,
    ]
    replayed = _replayed(DailyTimeResult, result)
    _assert_same(result, replayed, RESULT_PROPERTIES)
    assert replayed.version == 3 and replayed.status == DailyResultStatus.VALIDATED


def test_imported_events_round_trip_the_full_state():
    first, _ = _rules()
    created_at = datetime(2025, 12, 1, 9, tzinfo=UTC)
    rule_event = CalculationRuleVersionImported(
        first.id, rule_version=first.rule_version, effective_from=first.effective_from,
        effective_to=first.effective_to, min_break_duration=first.min_break_duration,
        break_threshold=first.break_threshold, max_daily_work_duration=first.max_daily_work_duration,
        max_amplitude=first.max_amplitude, created_at=created_at,
    )
    imported_rule = CalculationRuleVersion.rehydrate(first.id, [])
    imported_rule.apply(rule_event)
    imported_rule.record_event(rule_event)
    replayed_rule = _replayed(CalculationRuleVersion, imported_rule)
    assert replayed_rule.created_at == created_at
    _assert_same(first, replayed_rule, RULE_PROPERTIES[:-2], version=1)

    result = _result_life()
    result_event = DailyTimeResultImported(
        result.id, employee_id=result.employee_id, period_id=result.period_id,
        calculation_rule_version_id=result.calculation_rule_version_id, work_date=result.work_date,
        planned_duration=result.planned_duration, worked_duration=result.worked_duration,
        break_duration=result.break_duration, absence_duration=result.absence_duration,
        late_duration=result.late_duration, status=result.status, calculated_at=result.calculated_at,
        created_at=created_at,
    )
    imported_result = DailyTimeResult.rehydrate(result.id, [])
    imported_result.apply(result_event)
    imported_result.record_event(result_event)
    replayed_result = _replayed(DailyTimeResult, imported_result)
    assert replayed_result.created_at == created_at and replayed_result.version == 1
    _assert_same(result, replayed_result, RESULT_PROPERTIES[:-2], version=1)


def test_every_event_is_registered():
    rules = _persistence_module("event_sourced_calculation_rule_version_repository")
    results = _persistence_module("event_sourced_daily_time_result_repository")
    rule_events = {CalculationRuleVersionCreated, CalculationRuleVersionClosed, CalculationRuleVersionImported}
    result_events = {DailyTimeResultCalculated, DailyTimeResultValidated, DailyTimeResultImported}
    assert set(rules.CALCULATION_RULE_VERSION_EVENT_TYPES.values()) == rule_events
    assert set(results.DAILY_TIME_RESULT_EVENT_TYPES.values()) == result_events
    for event_types in (rules.CALCULATION_RULE_VERSION_EVENT_TYPES, results.DAILY_TIME_RESULT_EVENT_TYPES):
        for name, event_type in event_types.items():
            assert event_type in TIME_CALCULATION_EVENT_MAPPERS
            # Name of the class matches its stored name.
            assert name.endswith("." + event_type.__name__.removeprefix("CalculationRuleVersion")
                                 .removeprefix("DailyTimeResult").lower())
    assert TIME_CALCULATION_EVENT_MAPPERS[CalculationRuleVersionImported] is None
    assert TIME_CALCULATION_EVENT_MAPPERS[DailyTimeResultImported] is None
