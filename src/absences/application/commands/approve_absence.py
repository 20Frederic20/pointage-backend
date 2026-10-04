from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class ApproveAbsenceCommand(Command):
    """Approve a pending absence."""

    absence_id: str
