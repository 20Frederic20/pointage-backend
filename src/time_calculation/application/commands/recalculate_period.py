from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class RecalculatePeriodCommand(Command):
    """Recalculate every scheduled employee's days of a period (``recalculerPeriode``)."""

    period_id: str
