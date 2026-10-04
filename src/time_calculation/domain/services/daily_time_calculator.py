from collections.abc import Sequence
from datetime import datetime, timedelta

from punch.domain import EntryType

from ..value_objects import PlannedDay

type Clocking = tuple[datetime, str]
"""A time entry reduced to what the calculation needs: (occurred at, IN/OUT)."""

type Interval = tuple[datetime, datetime]


class DailyTimeCalculator:
    """Pure calculations of one working day (no I/O), like ``DistanceCalculator``."""

    @classmethod
    def worked_time(cls, clockings: Sequence[Clocking]) -> tuple[timedelta, timedelta, bool]:
        """``calculerTempsTravail``: pair each IN with the next OUT.

        Returns ``(worked, breaks, has_unpaired)``: ``breaks`` sums the gaps
        between an OUT and the next IN; an OUT without IN or an IN left open
        makes the day unpaired (and is not counted).
        """
        worked = breaks = timedelta(0)
        has_unpaired = False
        opened_at: datetime | None = None
        last_out: datetime | None = None
        for occurred_at, entry_type in sorted(clockings):
            if entry_type == EntryType.IN:
                if opened_at is not None:
                    has_unpaired = True
                if last_out is not None:
                    breaks += occurred_at - last_out
                    last_out = None
                opened_at = occurred_at
            elif opened_at is None:
                has_unpaired = True
            else:
                worked += occurred_at - opened_at
                last_out = occurred_at
                opened_at = None
        return worked, breaks, has_unpaired or opened_at is not None

    @classmethod
    def enforce_minimum_break(
        cls,
        worked: timedelta,
        breaks: timedelta,
        *,
        break_threshold: timedelta,
        min_break_duration: timedelta,
    ) -> tuple[timedelta, timedelta]:
        """``calculerPause``: past the threshold, a too-short break is completed out of worked time."""
        if worked > break_threshold and breaks < min_break_duration:
            missing = min_break_duration - breaks
            return max(worked - missing, timedelta(0)), min_break_duration
        return worked, breaks

    @classmethod
    def absence_time(cls, planned_day: PlannedDay | None, absences: Sequence[Interval]) -> timedelta:
        """Planned time covered by approved absences (overlaps are counted once)."""
        if planned_day is None:
            return timedelta(0)
        covered = timedelta(0)
        cursor = planned_day.start
        for start, end in sorted(absences):
            start, end = max(start, cursor), min(end, planned_day.end)
            if end > start:
                covered += end - start
                cursor = end
        return covered

    @classmethod
    def lateness(
        cls, clockings: Sequence[Clocking], planned_day: PlannedDay | None, absences: Sequence[Interval]
    ) -> timedelta:
        """``calculerRetard``: first IN after the planned start, beyond the tolerance.

        No lateness without a planned day, without any IN, or when an absence
        covers the planned start.
        """
        if planned_day is None:
            return timedelta(0)
        if any(start <= planned_day.start < end for start, end in absences):
            return timedelta(0)
        first_in = min((at for at, entry_type in clockings if entry_type == EntryType.IN), default=None)
        if first_in is None:
            return timedelta(0)
        delay = first_in - planned_day.start
        return delay if delay > planned_day.tolerance else timedelta(0)

    @classmethod
    def has_overrun(
        cls,
        worked: timedelta,
        clockings: Sequence[Clocking],
        *,
        max_daily_work_duration: timedelta,
        max_amplitude: timedelta,
    ) -> bool:
        """``detecterDepassement``: too much worked time, or first-to-last clocking span too long."""
        amplitude = (
            max(at for at, _ in clockings) - min(at for at, _ in clockings) if clockings else timedelta(0)
        )
        return worked > max_daily_work_duration or amplitude > max_amplitude
