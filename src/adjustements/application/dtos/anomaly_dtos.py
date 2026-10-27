from dataclasses import dataclass
from datetime import datetime

from core.application import DTO
from punch.domain import TimeEntryId
from adjustements.domain import Severity, AnomalyStatus, AnomalyType, Anomaly


@dataclass(frozen=True)
class AnomalyDTO(DTO):
    id: str
    time_entry_id: str
    severity: Severity
    status: AnomalyStatus
    type: AnomalyType
    detected_at: datetime
    resolved_at: datetime | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    employee_id: str | None = None
    assisted_by_user_id: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_comment: str | None = None

    @classmethod
    def from_aggregate(cls, anomaly: Anomaly) -> "AnomalyDTO":
        return AnomalyDTO(
            id=anomaly.id.value,
            time_entry_id=anomaly.time_entry_id.value,
            severity=anomaly.severity,
            status=anomaly.status,
            type=anomaly.type,
            resolved_at=anomaly.resolved_at,
            detected_at=anomaly.detected_at,
            description=anomaly.description,
            created_at=anomaly.created_at,
            updated_at=anomaly.updated_at,
            employee_id=anomaly.employee_id.value if anomaly.employee_id else None,
            assisted_by_user_id=anomaly.assisted_by_user_id.value if anomaly.assisted_by_user_id else None,
            decided_by=anomaly.decided_by.value if anomaly.decided_by else None,
            decided_at=anomaly.decided_at,
            decision_comment=anomaly.decision_comment,
        )


@dataclass(frozen=True)
class AnomaliesPageDTO(DTO):
    items: tuple[AnomalyDTO, ...]
    total: int