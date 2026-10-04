from datetime import date, datetime, time, timedelta

from core.domain.entity import Entity

from ..errors import InvalidTimeProfileDayError
from ..value_objects import DayOfWeek, TimeProfileDayId


class TimeProfileDay(Entity[TimeProfileDayId]):
    """The planned hours of one day of week inside a profile version.

    ``break_duration`` is deducted from the planned time once the day lasts
    longer than ``break_threshold``; ``tolerance`` is the lateness grace period.
    """

    __slots__ = (
        "_break_duration",
        "_break_threshold",
        "_day_of_week",
        "_end_time",
        "_start_time",
        "_tolerance",
    )

    def __init__(
        self,
        time_profile_day_id: TimeProfileDayId,
        *,
        day_of_week: DayOfWeek,
        start_time: time,
        end_time: time,
        break_duration: timedelta,
        break_threshold: timedelta,
        tolerance: timedelta,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(time_profile_day_id, created_at=created_at, updated_at=updated_at)
        if end_time < start_time:
            raise InvalidTimeProfileDayError(
                f"{day_of_week} ends ({end_time}) before it starts ({start_time})",
                context=str(day_of_week),
            )
        if min(break_duration, break_threshold, tolerance) < timedelta(0):
            raise InvalidTimeProfileDayError(
                f"{day_of_week} has a negative break, threshold or tolerance",
                context=str(day_of_week),
            )
        self._day_of_week = DayOfWeek(day_of_week)
        self._start_time = start_time
        self._end_time = end_time
        self._break_duration = break_duration
        self._break_threshold = break_threshold
        self._tolerance = tolerance

    def is_worked(self) -> bool:
        """``estTravaille``: a day whose start equals its end is a day off."""
        return self._end_time > self._start_time

    def planned_duration(self) -> timedelta:
        """``obtenirDureeTheorique``: planned span minus the break when it applies."""
        span = datetime.combine(date.min, self._end_time) - datetime.combine(date.min, self._start_time)
        if span > self._break_threshold:
            return max(span - self._break_duration, timedelta(0))
        return span

    @property
    def day_of_week(self) -> DayOfWeek:
        return self._day_of_week

    @property
    def start_time(self) -> time:
        return self._start_time

    @property
    def end_time(self) -> time:
        return self._end_time

    @property
    def break_duration(self) -> timedelta:
        return self._break_duration

    @property
    def break_threshold(self) -> timedelta:
        return self._break_threshold

    @property
    def tolerance(self) -> timedelta:
        return self._tolerance
