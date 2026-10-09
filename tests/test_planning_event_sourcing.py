"""Planning aggregates rebuilt from their events alone (no database)."""

import json
from datetime import date, time, timedelta

import pytest

from identity.domain.value_objects.ids import EmployeeId
from planning.application.notifications import PLANNING_EVENT_MAPPERS
from planning.domain import (
    DayOfWeek,
    DuplicateDayOfWeekError,
    EmployeeScheduleId,
    InvalidScheduleDatesError,
    InvalidTimezoneError,
    InvalidVersionEffectiveDateError,
    TimeProfileDayId,
    TimeProfileId,
    TimeProfileVersionId,
)
from planning.domain.entities import EmployeeSchedule, TimeProfile, TimeProfileDay
from planning.domain.events import (
    EmployeeScheduleAssigned,
    EmployeeScheduleEnded,
    EmployeeScheduleImported,
    TimeProfileCreated,
    TimeProfileImported,
    TimeProfileVersionAdded,
)

from planning.infrastructure.persistence.event_sourced_employee_schedule_repository import (  # noqa: E402
    EMPLOYEE_SCHEDULE_EVENT_TYPES,
)
from planning.infrastructure.persistence.event_sourced_time_profile_repository import (  # noqa: E402
    TIME_PROFILE_EVENT_TYPES,
)


def round_trip(events, event_types):
    stored = []
    for event in events:
        payload = json.loads(json.dumps(event.to_payload()))
        loaded = event_types[event.get_event_name()].from_payload(payload)
        loaded.restore_identity(event.event_id, event.occurred_at)
        stored.append(loaded)
    return stored


def day(day_of_week, start, end):
    return TimeProfileDay(
        TimeProfileDayId.generate(),
        day_of_week=day_of_week,
        start_time=start,
        end_time=end,
        break_duration=timedelta(minutes=45),
        break_threshold=timedelta(hours=6),
        tolerance=timedelta(minutes=10),
    )


def profile_state(profile):
    return (
        profile.id, profile.name, profile.timezone, profile.active,
        profile.created_at, profile.updated_at, profile.version,
        [
            (
                v.id, v.version, v.effective_from, v.effective_to, v.created_at, v.updated_at,
                [
                    (d.id, d.day_of_week, d.start_time, d.end_time, d.break_duration,
                     d.break_threshold, d.tolerance, d.created_at, d.updated_at)
                    for d in v.days
                ],
            )
            for v in profile.versions
        ],
    )


def schedule_state(schedule):
    return (
        schedule.id, schedule.employee_id, schedule.time_profile_version_id, schedule.start_date,
        schedule.end_date, schedule.created_at, schedule.updated_at, schedule.version,
    )


def live_profile():
    profile = TimeProfile.create(TimeProfileId.generate(), name="  Bureau  ", timezone="Africa/Porto-Novo")
    profile.add_version(
        TimeProfileVersionId.generate(),
        effective_from=date(2026, 1, 1),
        days=(day(DayOfWeek.MONDAY, time(8), time(17)), day(DayOfWeek.TUESDAY, time(8), time(17))),
    )
    second = profile.add_version(
        TimeProfileVersionId.generate(),
        effective_from=date(2026, 6, 1),
        days=(day(DayOfWeek.FRIDAY, time(9), time(13)),),
    )
    assert second is profile.versions[-1]
    profile.add_version(TimeProfileVersionId.generate(), effective_from=date(2026, 9, 1), days=())
    return profile


def test_time_profile_is_rebuilt_from_its_events():
    profile = live_profile()
    assert profile.name == "Bureau"
    assert [v.effective_to for v in profile.versions] == [date(2026, 5, 31), date(2026, 8, 31), None]
    assert profile.version_for(date(2026, 7, 3)).day_for(date(2026, 7, 3)).start_time == time(9)

    events = profile.domain_events
    assert [type(e) for e in events] == [TimeProfileCreated] + [TimeProfileVersionAdded] * 3
    rebuilt = TimeProfile.rehydrate(profile.id, round_trip(events, TIME_PROFILE_EVENT_TYPES))
    profile._advance_version(len(events))
    assert profile_state(rebuilt) == profile_state(profile)
    assert rebuilt.version == 4


def test_time_profile_validations_record_nothing():
    with pytest.raises(InvalidTimezoneError):
        TimeProfile.create(TimeProfileId.generate(), name="x", timezone="Mars/Olympus")
    profile = live_profile()
    count = len(profile.domain_events)
    with pytest.raises(InvalidVersionEffectiveDateError):
        profile.add_version(TimeProfileVersionId.generate(), effective_from=date(2026, 9, 1), days=())
    with pytest.raises(DuplicateDayOfWeekError):
        profile.add_version(
            TimeProfileVersionId.generate(),
            effective_from=date(2027, 1, 1),
            days=(day(DayOfWeek.MONDAY, time(8), time(9)), day(DayOfWeek.MONDAY, time(10), time(11))),
        )
    assert len(profile.domain_events) == count
    assert profile.versions[-1].effective_to is None


def test_time_profile_import_carries_the_full_state():
    current = live_profile()
    event = TimeProfileImported(
        current.id,
        name=current.name,
        timezone=current.timezone,
        active=current.active,
        versions=tuple(
            {
                "id": v.id, "version": v.version, "effective_from": v.effective_from,
                "effective_to": v.effective_to, "created_at": v.created_at, "updated_at": v.updated_at,
                "days": tuple(
                    {
                        "id": d.id, "day_of_week": d.day_of_week, "start_time": d.start_time,
                        "end_time": d.end_time, "break_duration": d.break_duration,
                        "break_threshold": d.break_threshold, "tolerance": d.tolerance,
                        "created_at": d.created_at, "updated_at": d.updated_at,
                    }
                    for d in v.days
                ),
            }
            for v in current.versions
        ),
        created_at=current.created_at,
    )
    event.restore_identity(event.event_id, current.updated_at)
    imported = TimeProfile.rehydrate(current.id, round_trip([event], TIME_PROFILE_EVENT_TYPES))
    current._advance_version(1 - current.version)
    assert profile_state(imported) == profile_state(current)


def test_employee_schedule_is_rebuilt_from_its_events():
    schedule = EmployeeSchedule.assign(
        EmployeeScheduleId.generate(),
        employee_id=EmployeeId.generate(),
        time_profile_version_id=TimeProfileVersionId.generate(),
        start_date=date(2026, 1, 1),
    )
    schedule.end(date(2026, 12, 31))
    with pytest.raises(InvalidScheduleDatesError):
        schedule.end(date(2025, 12, 31))
    events = schedule.domain_events
    assert [type(e) for e in events] == [EmployeeScheduleAssigned, EmployeeScheduleEnded]
    rebuilt = EmployeeSchedule.rehydrate(schedule.id, round_trip(events, EMPLOYEE_SCHEDULE_EVENT_TYPES))
    schedule._advance_version(len(events))
    assert schedule_state(rebuilt) == schedule_state(schedule)
    assert rebuilt.end_date == date(2026, 12, 31) and rebuilt.version == 2

    event = EmployeeScheduleImported(
        schedule.id,
        employee_id=schedule.employee_id,
        time_profile_version_id=schedule.time_profile_version_id,
        start_date=schedule.start_date,
        end_date=schedule.end_date,
        created_at=schedule.created_at,
    )
    event.restore_identity(event.event_id, schedule.updated_at)
    imported = EmployeeSchedule.rehydrate(schedule.id, round_trip([event], EMPLOYEE_SCHEDULE_EVENT_TYPES))
    schedule._advance_version(-1)
    assert schedule_state(imported) == schedule_state(schedule)

    with pytest.raises(InvalidScheduleDatesError):
        EmployeeSchedule.assign(
            EmployeeScheduleId.generate(),
            employee_id=EmployeeId.generate(),
            time_profile_version_id=TimeProfileVersionId.generate(),
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
        )


def test_every_event_is_registered_and_mapped():
    time_profile_events = {TimeProfileCreated, TimeProfileVersionAdded, TimeProfileImported}
    schedule_events = {EmployeeScheduleAssigned, EmployeeScheduleEnded, EmployeeScheduleImported}
    assert set(TIME_PROFILE_EVENT_TYPES.values()) == time_profile_events
    assert set(EMPLOYEE_SCHEDULE_EVENT_TYPES.values()) == schedule_events
    for event_types in (TIME_PROFILE_EVENT_TYPES, EMPLOYEE_SCHEDULE_EVENT_TYPES):
        for name, event_type in event_types.items():
            assert event_type in PLANNING_EVENT_MAPPERS
            assert name.startswith("planning.")
    assert PLANNING_EVENT_MAPPERS[TimeProfileImported] is None
    assert PLANNING_EVENT_MAPPERS[EmployeeScheduleImported] is None
