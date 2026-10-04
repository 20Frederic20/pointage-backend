from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class PlannedDay:
    """What the employee's planning expects on one day, as timezone-aware instants."""

    start: datetime
    end: datetime
    planned_duration: timedelta
    tolerance: timedelta

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"Planned day ends ({self.end}) before it starts ({self.start})")
