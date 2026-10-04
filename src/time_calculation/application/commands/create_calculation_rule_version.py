from dataclasses import dataclass
from datetime import date, timedelta

from core.application import Command


@dataclass(frozen=True)
class CreateCalculationRuleVersionCommand(Command):
    """Create a calculation rule version; the previous one ends the day before."""

    effective_from: date
    min_break_duration: timedelta
    break_threshold: timedelta
    max_daily_work_duration: timedelta
    max_amplitude: timedelta
