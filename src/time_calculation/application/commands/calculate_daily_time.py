from dataclasses import dataclass
from datetime import date

from core.application import Command


@dataclass(frozen=True)
class CalculateDailyTimeCommand(Command):
    """Calculate (or recalculate) one employee's work date (``calculerJournee``)."""

    employee_id: str
    work_date: date
