from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from core.application import DTO

from ...domain.entities import TimeProfile, TimeProfileDay, TimeProfileVersion


@dataclass(frozen=True)
class TimeProfileDayDTO(DTO):
    id: str
    day_of_week: str
    start_time: time
    end_time: time
    break_duration: timedelta
    break_threshold: timedelta
    tolerance: timedelta
    planned_duration: timedelta

    @classmethod
    def from_entity(cls, day: TimeProfileDay) -> "TimeProfileDayDTO":
        return cls(
            id=day.id.value,
            day_of_week=day.day_of_week.value,
            start_time=day.start_time,
            end_time=day.end_time,
            break_duration=day.break_duration,
            break_threshold=day.break_threshold,
            tolerance=day.tolerance,
            planned_duration=day.planned_duration(),
        )


@dataclass(frozen=True)
class TimeProfileVersionDTO(DTO):
    id: str
    version: int
    effective_from: date
    effective_to: date | None
    days: tuple[TimeProfileDayDTO, ...]

    @classmethod
    def from_entity(cls, profile_version: TimeProfileVersion) -> "TimeProfileVersionDTO":
        return cls(
            id=profile_version.id.value,
            version=profile_version.version,
            effective_from=profile_version.effective_from,
            effective_to=profile_version.effective_to,
            days=tuple(TimeProfileDayDTO.from_entity(day) for day in profile_version.days),
        )


@dataclass(frozen=True)
class TimeProfileDTO(DTO):
    id: str
    name: str
    timezone: str
    active: bool
    versions: tuple[TimeProfileVersionDTO, ...]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_aggregate(cls, time_profile: TimeProfile) -> "TimeProfileDTO":
        return cls(
            id=time_profile.id.value,
            name=time_profile.name,
            timezone=time_profile.timezone,
            active=time_profile.active,
            versions=tuple(TimeProfileVersionDTO.from_entity(v) for v in time_profile.versions),
            created_at=time_profile.created_at,
            updated_at=time_profile.updated_at,
        )
