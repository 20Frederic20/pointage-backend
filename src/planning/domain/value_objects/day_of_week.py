from datetime import date
from enum import StrEnum


class DayOfWeek(StrEnum):

    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"

    @classmethod
    def of(cls, day: date) -> "DayOfWeek":
        """The day of week of a calendar date (``date.weekday()`` is 0 for Monday)."""
        return list(cls)[day.weekday()]
