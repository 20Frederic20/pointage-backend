from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class NeutralizeAnomalyCommand(Command):
    """Resolve an anomaly covered by an approved absence."""

    absence_id: str
    anomaly_id: str
