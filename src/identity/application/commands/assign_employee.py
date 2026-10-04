from dataclasses import dataclass
from datetime import date

from core.application import Command


@dataclass(frozen=True)
class AssignEmployeeCommand(Command):
    """Assign an employee to a directory (and its site) from ``start_date``."""

    employee_id: str
    directory_id: str
    start_date: date
    end_date: date | None = None
