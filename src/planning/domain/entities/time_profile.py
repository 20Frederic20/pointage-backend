from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from core.domain.entity import AggregateRoot

from ..errors import InvalidTimezoneError, InvalidVersionEffectiveDateError
from ..events import TimeProfileCreated, TimeProfileVersionAdded
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
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise InvalidTimezoneError(f"Unknown timezone {timezone!r}", context=timezone) from exc
        self._name = name
        self._timezone = timezone
        self._active = active
        self._versions = sorted(versions or [], key=lambda v: v.version)

    @classmethod
    def create(cls, time_profile_id: TimeProfileId, *, name: str, timezone: str) -> "TimeProfile":
        time_profile = cls(time_profile_id, name=name.strip(), timezone=timezone)
        time_profile.record_event(TimeProfileCreated(time_profile_id))
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
        if previous is not None:
            if effective_from <= previous.effective_from:
                raise InvalidVersionEffectiveDateError(
                    f"Version must start after {previous.effective_from}",
                    context=self.id.value,
                )
            if previous.effective_to is None or previous.effective_to >= effective_from:
                previous.close(effective_from - timedelta(days=1))
        new_version = TimeProfileVersion(
            time_profile_version_id,
            version=previous.version + 1 if previous is not None else 1,
            effective_from=effective_from,
            effective_to=None,
            days=days,
        )
        self._versions.append(new_version)
        self.touch()
        self.record_event(
            TimeProfileVersionAdded(self.id, time_profile_version_id=time_profile_version_id)
        )
        return new_version

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
