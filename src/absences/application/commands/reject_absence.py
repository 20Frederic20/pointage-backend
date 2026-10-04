from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class RejectAbsenceCommand(Command):
    """Reject a pending absence."""

    absence_id: str
