from dataclasses import dataclass
from typing import Literal

from core.application import Command

from ..dtos import AnomalyDecisionDTO


@dataclass(frozen=True)
class DecideAnomalyCommand(Command):
    """A responsible validates or rejects an anomaly, and with it its time entry."""

    actor_user_id: str
    actor_role: str
    anomaly_id: str
    decision: Literal["VALIDATE", "REJECT"]
    comment: str | None = None

    Result = AnomalyDecisionDTO
