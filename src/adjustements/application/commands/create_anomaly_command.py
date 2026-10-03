from dataclasses import dataclass
from datetime import datetime

from core.application import Command
from adjustements.domain import Severity, AnomalyStatus, AnomalyType


@dataclass(frozen=True)
class CreateAnomalyCommand(Command):

    severity: Severity
    status: AnomalyStatus
    type: AnomalyType
    detected_at: datetime
    resolved_at: datetime | None = None
    description: str | None = None
