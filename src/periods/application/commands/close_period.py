from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class ClosePeriodCommand(Command):
    """Close a period (``cloturerPeriode``)."""

    period_id: str
