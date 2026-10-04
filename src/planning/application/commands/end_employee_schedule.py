from dataclasses import dataclass
from datetime import date

from core.application import Command


@dataclass(frozen=True)
class EndEmployeeScheduleCommand(Command):
    """Set the last day of an employee schedule."""

    employee_schedule_id: str
    end_date: date
