from dataclasses import dataclass
from datetime import date

from core.application import Command


@dataclass(frozen=True)
class EndEmployeeAssignmentCommand(Command):
    """Set the last day of an employee assignment."""

    employee_assignment_id: str
    end_date: date
    # Who acts (from the access token): responsible roles only, capped by rank.
    actor_user_id: str = ""
    actor_role: str = ""
