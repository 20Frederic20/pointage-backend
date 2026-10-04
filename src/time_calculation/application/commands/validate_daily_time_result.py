from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class ValidateDailyTimeResultCommand(Command):
    """Validate a daily result."""

    daily_time_result_id: str
