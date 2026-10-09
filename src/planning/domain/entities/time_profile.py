from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from core.domain.entity import AggregateRoot

from ..errors import InvalidTimezoneError, InvalidVersionEffectiveDateError
from ..events import TimeProfileCreated, TimeProfileImported, TimeProfileVersionAdded
from ..value_objects import TimeProfileId, TimeProfileVersionId
from .time_profile_day import TimeProfileDay
from .time_profile_version import TimeProfileVersion


class TimeProfile(AggregateRoot[TimeProfileId]):
    """A named working-time profile and its dated versions.

    Times of day in the profile are local to ``timezone`` (IANA name).
    """

    __slots__ = ("_active", "_name", "_timezone", "_versions")

    def __init__(
        self,
        time_profile_id: TimeProfileId,
        *,
        name: str,
        timezone: str,
        active: bool = True,
        versions: list[TimeProfileVersion] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(time_profile_id, created_at=created_at, updated_at=updated_at, version=version)
        _check_timezone(timezone)
        self._name = name
        self._timezone = timezone
        self._active = active
        self._versions = sorted(versions or [], key=lambda v: v.version)

    @classmethod
    def create(cls, time_profile_id: TimeProfileId, *, name: str, timezone: str) -> "TimeProfile":
        _check_timezone(timezone)
        time_profile = cls.rehydrate(time_profile_id, [])
        time_profile._raise(TimeProfileCreated(time_profile_id, name=name.strip(), timezone=timezone))
        return time_profile

    def add_version(
        self,
        time_profile_version_id: TimeProfileVersionId,
        *,
        effective_from: date,
        days: tuple[TimeProfileDay, ...],
    ) -> TimeProfileVersion:
        """Add a version starting on ``effective_from``; the previous one ends the day before."""
        previous = self._versions[-1] if self._versions else None
        closed_version_id = closed_effective_to = None
        if previous is not None:
            if effective_from <= previous.effective_from:
                raise InvalidVersionEffectiveDateError(
                    f"Version must start after {previous.effective_from}",
                    context=self.id.value,
                )
            # The day before effective_from is never before previous.effective_from (checked above).
            if previous.effective_to is None or previous.effective_to >= effective_from:
                closed_version_id = previous.id
                closed_effective_to = effective_from - timedelta(days=1)
        number = previous.version + 1 if previous is not None else 1
        # Validates the days (no duplicate day of week) before anything is recorded.
        TimeProfileVersion(
            time_profile_version_id, version=number, effective_from=effective_from, effective_to=None, days=days
        )
        self._raise(
            TimeProfileVersionAdded(
                self.id,
                time_profile_version_id=time_profile_version_id,
                version=number,
                effective_from=effective_from,
                days=tuple(_day_data(day) for day in days),
                closed_version_id=closed_version_id,
                closed_effective_to=closed_effective_to,
            )
        )
        return self._versions[-1]

    def _apply(self, event) -> None:
        match event:
            case TimeProfileCreated():
                self._name = event.name
                self._timezone = event.timezone
                self._active = True
                self._versions = []
            case TimeProfileVersionAdded():
                if event.closed_version_id is not None:
                    self.find_version(event.closed_version_id).end_on(
                        event.closed_effective_to, updated_at=event.occurred_at
                    )
                self._versions.append(
                    TimeProfileVersion(
                        event.time_profile_version_id,
                        version=event.version,
                        effective_from=event.effective_from,
                        effective_to=None,
                        days=tuple(_day(day, event.occurred_at) for day in event.days),
                        created_at=event.occurred_at,
                    )
                )
            case TimeProfileImported():
                self._name = event.name
                self._timezone = event.timezone
                self._active = event.active
                self._versions = sorted(
                    (
                        TimeProfileVersion(
                            version["id"],
                            version=version["version"],
                            effective_from=version["effective_from"],
                            effective_to=version["effective_to"],
                            days=tuple(_day(day, event.occurred_at) for day in version["days"]),
                            created_at=version["created_at"],
                            updated_at=version["updated_at"],
                        )
                        for version in event.versions
                    ),
                    key=lambda v: v.version,
                )
                self._created_at = event.created_at
            case _:
                super()._apply(event)

    def version_for(self, day: date) -> TimeProfileVersion | None:
        """``obtenirVersion``."""
        return next((v for v in self._versions if v.is_applicable(day)), None)

    def find_version(self, time_profile_version_id: TimeProfileVersionId) -> TimeProfileVersion | None:
        return next((v for v in self._versions if v.id == time_profile_version_id), None)

    def is_active_on(self, day: date) -> bool:
        """``estActif``."""
        return self._active and self.version_for(day) is not None

    @property
    def name(self) -> str:
        return self._name

    @property
    def timezone(self) -> str:
        return self._timezone

    @property
    def active(self) -> bool:
        return self._active

    @property
    def versions(self) -> tuple[TimeProfileVersion, ...]:
        return tuple(self._versions)


def _check_timezone(timezone: str) -> None:
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise InvalidTimezoneError(f"Unknown timezone {timezone!r}", context=timezone) from exc


def _day_data(day: TimeProfileDay) -> dict:
    """A day as carried by the events."""
    return {
        "id": day.id,
        "day_of_week": day.day_of_week,
        "start_time": day.start_time,
        "end_time": day.end_time,
        "break_duration": day.break_duration,
        "break_threshold": day.break_threshold,
        "tolerance": day.tolerance,
    }


def _day(data: dict, occurred_at: datetime) -> TimeProfileDay:
    """A day rebuilt from an event; imported days keep their own dates."""
    return TimeProfileDay(
        data["id"],
        day_of_week=data["day_of_week"],
        start_time=data["start_time"],
        end_time=data["end_time"],
        break_duration=data["break_duration"],
        break_threshold=data["break_threshold"],
        tolerance=data["tolerance"],
        created_at=data.get("created_at", occurred_at),
        updated_at=data.get("updated_at", occurred_at),
    )
