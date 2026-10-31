"""``TimeCalculationService`` counts only the time entries whose validation status is COUNTED.

In-memory fakes for the service's dependencies; real ``TimeEntry`` aggregates (no database).
"""

import asyncio
from datetime import UTC, date, datetime, timedelta

from identity.domain import EmployeeId, UserId
from periods.domain import PeriodId
from periods.domain.entities import Period
from punch.domain import EntryType, TimeEntryId, TimeEntryValidationStatus
from punch.domain.entities import TimeEntry
from punch.domain.entities import time_entry as time_entry_module
from time_calculation.application.services.time_calculation_service import TimeCalculationService
from time_calculation.domain import CalculationRuleVersionId
from time_calculation.domain.entities import CalculationRuleVersion

DAY = date(2026, 10, 7)
COUNTED = TimeEntryValidationStatus.COUNTED
PENDING = TimeEntryValidationStatus.PENDING
REJECTED = TimeEntryValidationStatus.REJECTED


class _Periods:
    def __init__(self, period):
        self._period = period

    async def find_containing(self, day):
        return self._period


class _Rules:
    def __init__(self, rules):
        self._rules = rules

    async def find_applicable(self, day):
        return self._rules


class _Results:
    async def find_by_employee_and_date(self, employee_id, work_date):
        return None


class _Schedules:
    async def find_applicable(self, employee_id, work_date):
        return None


class _Empty:
    async def find_approved_by_employee_between(self, employee_id, start, end):
        return []

    async def find_open_by_employee_between(self, employee_id, start, end):
        return []


class _TimeEntries:
    def __init__(self, entries):
        self._entries = entries

    async def find_by_employee_between(self, employee_id, start, end):
        return [e for e in self._entries if start <= e.occured_at < end]


def _entry(employee_id, entry_type, hour, status, monkeypatch):
    monkeypatch.setattr(
        time_entry_module, "_utcnow", lambda: datetime(DAY.year, DAY.month, DAY.day, hour, tzinfo=UTC)
    )
    entry = TimeEntry.create(
        TimeEntryId.generate(),
        employee_id=employee_id,
        entry_type=entry_type,
        location=None,
        validation_status=PENDING if status == REJECTED else status,
    )
    if status == REJECTED:
        entry.reject(decided_by=UserId.generate(), decided_at=datetime(2026, 10, 8, tzinfo=UTC))
    return entry


def _worked(entries, employee_id):
    period = Period.open(PeriodId.generate(), start_date=date(2026, 10, 1), end_date=date(2026, 10, 31))
    rules = CalculationRuleVersion.create(
        CalculationRuleVersionId.generate(),
        previous=None,
        effective_from=date(2026, 1, 1),
        min_break_duration=timedelta(minutes=0),
        break_threshold=timedelta(hours=24),
        max_daily_work_duration=timedelta(hours=24),
        max_amplitude=timedelta(hours=24),
    )
    empty = _Empty()
    service = TimeCalculationService(
        daily_time_result_repository=_Results(),
        calculation_rule_version_repository=_Rules(rules),
        period_repository=_Periods(period),
        employee_schedule_repository=_Schedules(),
        time_profile_repository=None,
        time_entry_repository=_TimeEntries(entries),
        absence_repository=empty,
        anomaly_repository=empty,
    )
    return asyncio.run(service.calculate_day(employee_id, DAY)).worked_duration


def test_pending_and_rejected_entries_are_not_worked_time(monkeypatch):
    employee_id = EmployeeId.generate()
    afternoon_in = _entry(employee_id, EntryType.IN, 13, PENDING, monkeypatch)
    entries = [
        _entry(employee_id, EntryType.IN, 8, COUNTED, monkeypatch),
        _entry(employee_id, EntryType.OUT, 12, COUNTED, monkeypatch),
        afternoon_in,
        _entry(employee_id, EntryType.OUT, 17, COUNTED, monkeypatch),
        _entry(employee_id, EntryType.IN, 18, REJECTED, monkeypatch),
        _entry(employee_id, EntryType.OUT, 19, REJECTED, monkeypatch),
    ]
    assert _worked(entries, employee_id) == timedelta(hours=4)

    afternoon_in.validate(decided_by=UserId.generate(), decided_at=datetime(2026, 10, 8, tzinfo=UTC))
    assert _worked(entries, employee_id) == timedelta(hours=8)
