from datetime import date, datetime

from core.domain.events import (
    BaseEvent,
    decode_date,
    decode_datetime,
    decode_time,
    decode_timedelta,
    encode_date,
    encode_datetime,
    encode_time,
    encode_timedelta,
)

from ..value_objects import DayOfWeek, TimeProfileDayId, TimeProfileId, TimeProfileVersionId

# A day is carried as a dict: id (TimeProfileDayId), day_of_week (DayOfWeek),
# start_time / end_time (time), break_duration / break_threshold / tolerance
# (timedelta); imported days also carry created_at / updated_at (datetime).


def _day_to_payload(day: dict) -> dict:
    payload = {
        "id": day["id"].value,
        "day_of_week": day["day_of_week"].value,
        "start_time": encode_time(day["start_time"]),
        "end_time": encode_time(day["end_time"]),
        "break_duration": encode_timedelta(day["break_duration"]),
        "break_threshold": encode_timedelta(day["break_threshold"]),
        "tolerance": encode_timedelta(day["tolerance"]),
    }
    if "created_at" in day:
        payload["created_at"] = encode_datetime(day["created_at"])
        payload["updated_at"] = encode_datetime(day["updated_at"])
    return payload


def _day_from_payload(payload: dict) -> dict:
    day = {
        "id": TimeProfileDayId(payload["id"]),
        "day_of_week": DayOfWeek(payload["day_of_week"]),
        "start_time": decode_time(payload["start_time"]),
        "end_time": decode_time(payload["end_time"]),
        "break_duration": decode_timedelta(payload["break_duration"]),
        "break_threshold": decode_timedelta(payload["break_threshold"]),
        "tolerance": decode_timedelta(payload["tolerance"]),
    }
    if "created_at" in payload:
        day["created_at"] = decode_datetime(payload["created_at"])
        day["updated_at"] = decode_datetime(payload["updated_at"])
    return day


class TimeProfileCreated(BaseEvent[TimeProfileId]):
    """A time profile was created."""

    def __init__(self, time_profile_id: TimeProfileId, *, name: str, timezone: str) -> None:
        super().__init__()
        self.time_profile_id = time_profile_id
        self.name = name
        self.timezone = timezone

    def get_aggregate_id(self) -> TimeProfileId:
        return self.time_profile_id

    def get_event_name(self) -> str:
        return "planning.time_profile.created"

    def to_payload(self) -> dict:
        return {"time_profile_id": self.time_profile_id.value, "name": self.name, "timezone": self.timezone}

    @classmethod
    def from_payload(cls, payload: dict) -> "TimeProfileCreated":
        return cls(TimeProfileId(payload["time_profile_id"]), name=payload["name"], timezone=payload["timezone"])


class TimeProfileVersionAdded(BaseEvent[TimeProfileId]):
    """A new version (with its days) was added to a time profile; the previous
    version, if still open on ``effective_from``, ends on ``closed_effective_to``."""

    def __init__(
        self,
        time_profile_id: TimeProfileId,
        *,
        time_profile_version_id: TimeProfileVersionId,
        version: int,
        effective_from: date,
        days: tuple[dict, ...],
        closed_version_id: TimeProfileVersionId | None = None,
        closed_effective_to: date | None = None,
    ) -> None:
        super().__init__()
        self.time_profile_id = time_profile_id
        self.time_profile_version_id = time_profile_version_id
        self.version = version
        self.effective_from = effective_from
        self.days = tuple(days)
        self.closed_version_id = closed_version_id
        self.closed_effective_to = closed_effective_to

    def get_aggregate_id(self) -> TimeProfileId:
        return self.time_profile_id

    def get_event_name(self) -> str:
        return "planning.time_profile.version_added"

    def to_payload(self) -> dict:
        return {
            "time_profile_id": self.time_profile_id.value,
            "time_profile_version_id": self.time_profile_version_id.value,
            "version": self.version,
            "effective_from": encode_date(self.effective_from),
            "days": [_day_to_payload(day) for day in self.days],
            "closed_version_id": self.closed_version_id.value if self.closed_version_id is not None else None,
            "closed_effective_to": encode_date(self.closed_effective_to),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "TimeProfileVersionAdded":
        return cls(
            TimeProfileId(payload["time_profile_id"]),
            time_profile_version_id=TimeProfileVersionId(payload["time_profile_version_id"]),
            version=payload["version"],
            effective_from=decode_date(payload["effective_from"]),
            days=tuple(_day_from_payload(day) for day in payload["days"]),
            closed_version_id=(
                TimeProfileVersionId(payload["closed_version_id"]) if payload["closed_version_id"] is not None else None
            ),
            closed_effective_to=decode_date(payload["closed_effective_to"]),
        )


class TimeProfileImported(BaseEvent[TimeProfileId]):
    """A time profile (all its versions and days) taken over from the state
    tables when event sourcing started.

    ``versions``: dicts with id (TimeProfileVersionId), version, effective_from,
    effective_to, created_at, updated_at and days (day dicts, see above).
    """

    def __init__(
        self,
        time_profile_id: TimeProfileId,
        *,
        name: str,
        timezone: str,
        active: bool,
        versions: tuple[dict, ...],
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.time_profile_id = time_profile_id
        self.name = name
        self.timezone = timezone
        self.active = active
        self.versions = tuple(versions)
        self.created_at = created_at

    def get_aggregate_id(self) -> TimeProfileId:
        return self.time_profile_id

    def get_event_name(self) -> str:
        return "planning.time_profile.imported"

    def to_payload(self) -> dict:
        return {
            "time_profile_id": self.time_profile_id.value,
            "name": self.name,
            "timezone": self.timezone,
            "active": self.active,
            "versions": [
                {
                    "id": version["id"].value,
                    "version": version["version"],
                    "effective_from": encode_date(version["effective_from"]),
                    "effective_to": encode_date(version["effective_to"]),
                    "created_at": encode_datetime(version["created_at"]),
                    "updated_at": encode_datetime(version["updated_at"]),
                    "days": [_day_to_payload(day) for day in version["days"]],
                }
                for version in self.versions
            ],
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "TimeProfileImported":
        return cls(
            TimeProfileId(payload["time_profile_id"]),
            name=payload["name"],
            timezone=payload["timezone"],
            active=payload["active"],
            versions=tuple(
                {
                    "id": TimeProfileVersionId(version["id"]),
                    "version": version["version"],
                    "effective_from": decode_date(version["effective_from"]),
                    "effective_to": decode_date(version["effective_to"]),
                    "created_at": decode_datetime(version["created_at"]),
                    "updated_at": decode_datetime(version["updated_at"]),
                    "days": tuple(_day_from_payload(day) for day in version["days"]),
                }
                for version in payload["versions"]
            ),
            created_at=decode_datetime(payload["created_at"]),
        )
