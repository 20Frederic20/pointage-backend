"""Primitive conversions for event payloads (JSON in the event store).

Datetimes are stored in UTC ISO 8601, so the store can compare them as text
(``payload->>'occured_at' >= '2026-10-01T00:00:00+00:00'``).
"""

from datetime import UTC, date, datetime, time, timedelta


def encode_datetime(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat() if value is not None else None


def decode_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def encode_date(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def decode_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value is not None else None


def encode_time(value: time | None) -> str | None:
    return value.isoformat() if value is not None else None


def decode_time(value: str | None) -> time | None:
    return time.fromisoformat(value) if value is not None else None


def encode_timedelta(value: timedelta | None) -> float | None:
    return value.total_seconds() if value is not None else None


def decode_timedelta(value: float | None) -> timedelta | None:
    return timedelta(seconds=value) if value is not None else None
