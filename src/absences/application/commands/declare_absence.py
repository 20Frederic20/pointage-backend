from dataclasses import dataclass
from datetime import datetime

from core.application import Command


@dataclass(frozen=True)
class DeclareAbsenceCommand(Command):
    """Declare an absence for an employee."""

    employee_id: str
    absence_type_id: str
    start_at: datetime
    end_at: datetime
    reason: str
    justification_reference: str | None = None
