from dataclasses import dataclass
from datetime import date

from core.application import Command


@dataclass(frozen=True)
class EndEmployeeAssignmentCommand(Command):
    """Set the last day of an employee assignment."""

    employee_assignment_id: str
    end_date: date
