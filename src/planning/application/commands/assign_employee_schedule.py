from dataclasses import dataclass
from datetime import date

from core.application import Command


@dataclass(frozen=True)
class AssignEmployeeScheduleCommand(Command):
    """Assign a time profile version to an employee."""

    employee_id: str
    time_profile_version_id: str
    start_date: date
    end_date: date | None = None
