"""``TimeCalculationService.work_date_of``: the work date of an instant is read in
the employee's time-profile timezone, the one ``calculate_day`` builds days in."""

import asyncio
from datetime import UTC, date, datetime
from types import SimpleNamespace

from identity.domain import EmployeeId
from time_calculation.application.services.time_calculation_service import (
    TimeCalculationService,
)


class _Schedules:
    def __init__(self, schedule):
        self._schedule = schedule

    async def find_applicable(self, employee_id, work_date):
        return self._schedule


class _TimeProfiles:
    def __init__(self, profile):
        self._profile = profile

    async def find_by_version_id(self, version_id):
        return self._profile


def _service(schedule, profile):
    return TimeCalculationService(
        daily_time_result_repository=None,
        calculation_rule_version_repository=None,
        period_repository=None,
        employee_schedule_repository=_Schedules(schedule),
        time_profile_repository=_TimeProfiles(profile),
        time_entry_repository=None,
        absence_repository=None,
        anomaly_repository=None,
    )


LATE_EVENING_UTC = datetime(2026, 10, 7, 23, 30, tzinfo=UTC)  # 00:30 on the 8th in Porto-Novo (UTC+1)


def test_work_date_is_local_to_the_time_profile_zone():
    service = _service(SimpleNamespace(time_profile_version_id="v1"), SimpleNamespace(timezone="Africa/Porto-Novo"))
    assert asyncio.run(service.work_date_of(EmployeeId("emp1"), LATE_EVENING_UTC)) == date(2026, 10, 8)


def test_work_date_falls_back_to_utc_without_a_schedule_or_profile():
    assert asyncio.run(_service(None, None).work_date_of(EmployeeId("emp1"), LATE_EVENING_UTC)) == date(2026, 10, 7)
    no_profile = _service(SimpleNamespace(time_profile_version_id="v1"), None)
    assert asyncio.run(no_profile.work_date_of(EmployeeId("emp1"), LATE_EVENING_UTC)) == date(2026, 10, 7)
