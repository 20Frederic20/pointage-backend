from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class LockPeriodCommand(Command):
    """Lock an open period (``verrouillerPeriode``)."""

    period_id: str
