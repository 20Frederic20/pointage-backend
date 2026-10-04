from dataclasses import dataclass
from datetime import date, time, timedelta

from core.application import Command
from planning.domain import DayOfWeek


@dataclass(frozen=True)
class TimeProfileDayData:
    """The planned hours of one day of week in a new version."""

    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    break_duration: timedelta
    break_threshold: timedelta
    tolerance: timedelta


@dataclass(frozen=True)
class AddTimeProfileVersionCommand(Command):
    """Add a dated version to a time profile."""

    time_profile_id: str
    effective_from: date
    days: tuple[TimeProfileDayData, ...]
