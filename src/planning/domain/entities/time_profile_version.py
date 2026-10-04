from datetime import date, datetime

from core.domain.entity import Entity

from ..errors import DuplicateDayOfWeekError, InvalidVersionEffectiveDateError
from ..value_objects import DayOfWeek, TimeProfileVersionId
from .time_profile_day import TimeProfileDay


class TimeProfileVersion(Entity[TimeProfileVersionId]):
    """A dated revision of a time profile; days not listed are days off."""

    __slots__ = ("_days", "_effective_from", "_effective_to", "_version")

    def __init__(
        self,
        time_profile_version_id: TimeProfileVersionId,
        *,
        version: int,
        effective_from: date,
        effective_to: date | None,
        days: tuple[TimeProfileDay, ...],
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(time_profile_version_id, created_at=created_at, updated_at=updated_at)
        weekdays = [day.day_of_week for day in days]
        if len(weekdays) != len(set(weekdays)):
            raise DuplicateDayOfWeekError(
                "A profile version cannot define the same day of week twice",
                context=time_profile_version_id.value,
            )
        if effective_to is not None and effective_to < effective_from:
            raise InvalidVersionEffectiveDateError(
                f"Version ends ({effective_to}) before it starts ({effective_from})",
                context=time_profile_version_id.value,
            )
        self._version = version
        self._effective_from = effective_from
        self._effective_to = effective_to
        self._days = tuple(days)

    def is_applicable(self, day: date) -> bool:
        """``estApplicable``."""
        return self._effective_from <= day and (self._effective_to is None or day <= self._effective_to)

    def day_for(self, day: date) -> TimeProfileDay | None:
        """The planned day for a calendar date, or ``None`` for a day off."""
        weekday = DayOfWeek.of(day)
        return next((d for d in self._days if d.day_of_week == weekday and d.is_worked()), None)

    def close(self, last_day: date) -> None:
        """End this version on ``last_day`` (inclusive)."""
        if last_day < self._effective_from:
            raise InvalidVersionEffectiveDateError(
                f"Version {self._version} cannot end ({last_day}) before it starts ({self._effective_from})",
                context=self.id.value,
            )
        self._effective_to = last_day
        self.touch()

    @property
    def version(self) -> int:
        return self._version

    @property
    def effective_from(self) -> date:
        return self._effective_from

    @property
    def effective_to(self) -> date | None:
        return self._effective_to

    @property
    def days(self) -> tuple[TimeProfileDay, ...]:
        return self._days
