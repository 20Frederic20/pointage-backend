from dataclasses import dataclass
from datetime import datetime

from adjustements.domain import AnomalyId, RegularizationStatus
from core.application import Command


@dataclass(frozen=True)
class CreateRegularizationRequestCommand(Command):

    anomaly_id: AnomalyId
    request_at: datetime
    reason: str
    proposed_time: datetime
    status: RegularizationStatus
    decision_comment: str | None = None
    validated_at: datetime | None = None