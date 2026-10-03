from dataclasses import dataclass
from datetime import datetime

from core.application import Command
from adjustements.domain import Severity, AnomalyStatus, AnomalyType
from punch.domain import TimeEntryId


@dataclass(frozen=True)
class CreateAnomalyCommand(Command):

    time_entry_id: TimeEntryId
    severity: Severity
    status: AnomalyStatus
    type: AnomalyType
    detected_at: datetime
    resolved_at: datetime | None = None
    description: str | None = None
