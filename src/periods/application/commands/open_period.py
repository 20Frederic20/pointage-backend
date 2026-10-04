from dataclasses import dataclass
from datetime import date

from core.application import Command


@dataclass(frozen=True)
class OpenPeriodCommand(Command):
    """Open a new period."""

    start_date: date
    end_date: date
